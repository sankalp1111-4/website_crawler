"""
Crawl4AI engine for the website crawler.

This module provides the core crawling functionality using the Crawl4AI library.
"""
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime

from crawl4ai import AsyncWebCrawler
from crawl4ai.models import CrawlResult

from ..models.raw_page import RawPage
from ..exceptions import CrawlError, CrawlTimeoutError, CrawlFailedError
from .browser import BrowserConfig


class Crawl4AIEngine:
    """
    Wrapper around crawl4ai's AsyncWebCrawler.
    
    Provides a clean interface for web crawling operations.
    """
    
    def __init__(self, browser_config: Optional[BrowserConfig] = None):
        """
        Initialize the Crawl4AI engine.
        
        Args:
            browser_config: Browser configuration (defaults to BrowserConfig.default())
        """
        self.browser_config = browser_config or BrowserConfig.default()
        self.crawler: Optional[AsyncWebCrawler] = None
    
    def initialize(self) -> None:
        """Initialize the crawler instance."""
        if self.crawler is None:
            # Create crawler with browser configuration
            crawler_config = self.browser_config.to_crawl4ai_config()
            self.crawler = AsyncWebCrawler(
                headless=crawler_config.get('headless', True),
                verbose=False
            )
    
    async def crawl_url(self, url: str, config: Optional[Dict[str, Any]] = None) -> RawPage:
        """
        Crawl a single URL.
        
        Args:
            url: The URL to crawl
            config: Optional configuration dictionary
            
        Returns:
            RawPage model with crawled content
            
        Raises:
            CrawlError: If crawling fails
            CrawlTimeoutError: If crawling times out
        """
        if self.crawler is None:
            self.initialize()
        
        # Merge config with defaults
        crawl_config = config or {}
        timeout = crawl_config.get('timeout', 30)
        
        try:
            # Perform the crawl
            result: CrawlResult = await asyncio.wait_for(
                self.crawler.arun(url=url),
                timeout=timeout
            )
            
            # Check if crawl was successful
            success = getattr(result, 'success', True)
            if not success:
                error_message = getattr(result, 'error_message', None) or 'Unknown error'
                raise CrawlFailedError(
                    f"Crawl failed: {error_message}",
                    url=url
                )
            
            # Extract data from result - use safe attribute access
            html = getattr(result, 'html', None) or getattr(result, 'markdown', None) or ""
            status_code = getattr(result, 'status_code', 200) or 200
            
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
            
            return raw_page
            
        except asyncio.TimeoutError as e:
            raise CrawlTimeoutError(
                f"Crawl operation timed out after {timeout}s",
                url=url,
                timeout=timeout
            ) from e
        except CrawlError:
            raise
        except Exception as e:
            raise CrawlFailedError(
                f"Unexpected error during crawl: {str(e)}",
                url=url
            ) from e
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.crawler is not None:
            # Close the crawler (crawl4ai handles cleanup internally)
            self.crawler = None