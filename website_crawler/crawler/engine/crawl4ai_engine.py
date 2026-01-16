"""
Crawl4AI engine for the website crawler.

This module provides the core crawling functionality using the Crawl4AI library.
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from urllib.parse import urlparse

from crawl4ai import AsyncWebCrawler
from crawl4ai.models import CrawlResult

from ..models.raw_page import RawPage
from ..exceptions import CrawlError, CrawlTimeoutError, CrawlFailedError
from .browser import BrowserConfig
from .performance import (
    PerformanceConfig,
    RetryHandler,
    RateLimiter,
    ConcurrentRequestLimiter
)
from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("CrawlEngine", __name__)


class Crawl4AIEngine:
    """
    Wrapper around crawl4ai's AsyncWebCrawler.
    
    Provides a clean interface for web crawling operations.
    """
    
    def __init__(
        self,
        browser_config: Optional[BrowserConfig] = None,
        performance_config: Optional[PerformanceConfig] = None
    ):
        """
        Initialize the Crawl4AI engine.
        
        Args:
            browser_config: Browser configuration (defaults to BrowserConfig.default())
            performance_config: Performance configuration (defaults to PerformanceConfig.default())
        """
        self.browser_config = browser_config or BrowserConfig.default()
        self.performance_config = performance_config or PerformanceConfig.default()
        self.crawler: Optional[AsyncWebCrawler] = None
        
        # Initialize performance components
        self.retry_handler = RetryHandler(self.performance_config)
        self.rate_limiter = RateLimiter(self.performance_config)
        self.concurrent_limiter = ConcurrentRequestLimiter(
            self.performance_config.concurrent_requests
        )
    
    def initialize(self) -> None:
        """Initialize the crawler instance."""
        logger.log_entry("initialize", crawler_state="not_initialized")
        
        if self.crawler is None:
            # Create crawler with browser configuration
            crawler_config = self.browser_config.to_crawl4ai_config()
            logger.log_decision("CRAWLER_CREATION", f"Creating AsyncWebCrawler with headless={crawler_config.get('headless', True)}")
            self.crawler = AsyncWebCrawler(
                headless=crawler_config.get('headless', True),
                verbose=False
            )
            logger.log_state_change("crawler_not_initialized", "crawler_initialized")
            logger.log_exit("initialize", status="success")
        else:
            logger.log_decision("CRAWLER_ALREADY_INITIALIZED", "Crawler instance already exists")
            logger.log_exit("initialize", status="already_initialized")
    
    async def crawl_url(self, url: str, config: Optional[Dict[str, Any]] = None) -> RawPage:
        """
        Crawl a single URL with retry logic, rate limiting, and concurrency control.
        
        Args:
            url: The URL to crawl
            config: Optional configuration dictionary
            
        Returns:
            RawPage model with crawled content
            
        Raises:
            CrawlError: If crawling fails
            CrawlTimeoutError: If crawling times out
        """
        url_logger = logger.with_url(url)
        
        # Log FETCH start
        url_logger.info(f"[CrawlEngine] FETCH {url}")
        
        if self.crawler is None:
            url_logger.log_decision("CRAWLER_NOT_INITIALIZED", "Initializing crawler on demand")
            self.initialize()
        
        # Merge config with defaults
        crawl_config = config or {}
        timeout = crawl_config.get('timeout', self.performance_config.request_timeout)
        
        # Extract domain for rate limiting
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        
        # Acquire concurrent request slot
        async with self.concurrent_limiter:
            # Apply rate limiting
            await self.rate_limiter.wait_if_needed(domain=domain)
            
            # Perform crawl with retry logic
            async def _perform_crawl():
                """Inner function to perform the actual crawl."""
                # Build crawl options from config
                crawl_options = {}
                
                # Add markdown extraction if requested
                if crawl_config.get('extract_markdown', False):
                    crawl_options['extract_markdown'] = True
                
                # Add LLM extraction if configured
                llm_config = crawl_config.get('llm_extraction')
                if llm_config:
                    try:
                        from crawl4ai.extraction_strategy import LLMExtractionStrategy
                        from crawl4ai import LLMExtractionStrategyConfig
                        
                        llm_strategy_config = LLMExtractionStrategyConfig(
                            provider=llm_config.get('provider', 'openai'),
                            api_token=llm_config.get('api_key'),
                            model=llm_config.get('model', 'gpt-4'),
                            extraction_schema=llm_config.get('schema', {}),
                            temperature=llm_config.get('temperature', 0.0)
                        )
                        llm_strategy = LLMExtractionStrategy(config=llm_strategy_config)
                        crawl_options['extraction_strategy'] = llm_strategy
                        url_logger.log_decision("LLM_EXTRACTION_ENABLED", f"Using LLM extraction with {llm_config.get('provider')}")
                    except ImportError:
                        url_logger.warning("[CrawlEngine] LLM extraction requested but not available")
                    except Exception as e:
                        url_logger.warning(f"[CrawlEngine] Failed to setup LLM extraction: {e}")
                
                # Perform crawl with options
                result: CrawlResult = await asyncio.wait_for(
                    self.crawler.arun(url=url, **crawl_options),
                    timeout=timeout
                )
                
                # Check if crawl was successful
                success = getattr(result, 'success', True)
                if not success:
                    error_message = getattr(result, 'error_message', None) or 'Unknown error'
                    url_logger.log_decision("CRAWL_FAILED", reason=error_message)
                    raise CrawlFailedError(
                        f"Crawl failed: {error_message}",
                        url=url
                    )
                
                # Extract data from result - use safe attribute access
                # Prioritize markdown if available, otherwise use HTML
                html = getattr(result, 'html', None) or ""
                markdown = getattr(result, 'markdown', None) or ""
                
                # If markdown was extracted, prefer it (can be converted back to HTML if needed)
                if markdown and crawl_config.get('prefer_markdown', False):
                    html = markdown
                    url_logger.log_decision("MARKDOWN_PREFERRED", "Using markdown content over HTML")
                
                # Extract status_code, ensuring it's never None
                status_code = getattr(result, 'status_code', None)
                if status_code is None:
                    status_code = 200
                
                # Safely extract headers - CrawlResult may not have headers attribute
                # Try multiple possible attribute names
                headers = {}
                if hasattr(result, 'headers'):
                    headers = result.headers or {}
                elif hasattr(result, 'response_headers'):
                    headers = result.response_headers or {}
                elif hasattr(result, 'http_headers'):
                    headers = result.http_headers or {}
                # If result has a response object, try to get headers from there
                elif hasattr(result, 'response') and result.response:
                    if hasattr(result.response, 'headers'):
                        headers = result.response.headers or {}
                
                # Convert headers to dict if it's not already
                if headers and not isinstance(headers, dict):
                    try:
                        headers = dict(headers)
                    except (TypeError, ValueError):
                        headers = {}
                
                # Create RawPage model
                raw_page = RawPage(
                    url=url,
                    html=html,
                    status_code=status_code,
                    headers=headers,
                    crawl_timestamp=datetime.utcnow()
                )
                
                # Log FETCH success
                html_size = len(html.encode('utf-8')) if html else 0
                url_logger.info(f"[CrawlEngine] FETCH success ({status_code}, {html_size} bytes)")
                
                return raw_page
            
            # Execute with retry logic
            try:
                result = await self.retry_handler.retry_with_backoff(
                    _perform_crawl,
                    url=url
                )
                return result
            except asyncio.TimeoutError as e:
                url_logger.log_decision("CRAWL_TIMEOUT", reason=f"Timeout after {timeout}s")
                raise CrawlTimeoutError(
                    f"Crawl operation timed out after {timeout}s",
                    url=url,
                    timeout=timeout
                ) from e
            except CrawlError:
                raise
            except Exception as e:
                url_logger.log_decision("UNEXPECTED_CRAWL_ERROR", reason=str(e))
                raise CrawlFailedError(
                    f"Unexpected error during crawl: {str(e)}",
                    url=url
                ) from e
    
    def cleanup(self) -> None:
        """Clean up resources."""
        logger.log_entry("cleanup", crawler_state="initialized" if self.crawler is not None else "not_initialized")
        
        if self.crawler is not None:
            # Close the crawler (crawl4ai handles cleanup internally)
            logger.log_decision("CRAWLER_CLEANUP", "Cleaning up crawler instance")
            self.crawler = None
            logger.log_state_change("crawler_initialized", "crawler_cleaned_up")
            logger.log_exit("cleanup", status="success")
        else:
            logger.log_decision("CRAWLER_ALREADY_CLEANED", "Crawler already cleaned up")
            logger.log_exit("cleanup", status="already_clean")