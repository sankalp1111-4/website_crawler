"""
Crawl orchestrator for the website crawler.

Coordinates the crawling process and manages the pipeline.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .models.document import Document
from .models.raw_page import RawPage
from .url.validator import validate_url, validate_scheme, is_crawlable
from .url.normalizer import normalize_url
from .url.filter import URLFilter
from .engine.crawl4ai_engine import Crawl4AIEngine
from .engine.browser import BrowserConfig
from .engine.performance import PerformanceConfig
from .parsing.html_parser import HTMLParser
from .extraction.simple_extractor import SimpleExtractor
from storage.mongo import MongoStorage
from utils.hashing import hash_content, generate_document_id
from utils.logging_config import ComponentLoggerAdapter, get_component_logger
from .exceptions import CrawlError, StorageError, ValidationError


class CrawlOrchestrator:
    """
    Basic orchestrator for the crawling pipeline.
    
    Coordinates: crawl → extract → normalize → store
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the orchestrator.
        
        Args:
            config: Configuration dictionary
        """
        self.config = config
        
        # Initialize component-aware logger
        self.logger: ComponentLoggerAdapter = get_component_logger("Orchestrator", __name__)
        
        # Initialize components
        self.browser_config = BrowserConfig.from_config(config)
        self.engine: Optional[Crawl4AIEngine] = None
        self.html_parser = HTMLParser(config.get('extraction', {}))
        self.extractor = SimpleExtractor(config.get('extraction', {}))
        self.storage: Optional[MongoStorage] = None
        
        # Initialize performance config from crawler config
        crawler_config = config.get('crawler', {})
        performance_config_dict = {
            'request_timeout': crawler_config.get('timeout', 30),
            'page_load_timeout': crawler_config.get('timeout', 30),
            'max_retries': crawler_config.get('retries', 3),
            'rate_limit': crawler_config.get('rate_limit'),
            'concurrent_requests': crawler_config.get('concurrent_requests', 10),
        }
        self.performance_config = PerformanceConfig.from_config(performance_config_dict)
        
        # Initialize URL filter from config
        auth_config = config.get('auth', {})
        self.url_filter = URLFilter(
            respect_robots_txt=crawler_config.get('respect_robots_txt', True),
            user_agent=auth_config.get('user_agent', 'CrawlerBot'),
            allowed_domains=crawler_config.get('allowed_domains'),
            blocked_domains=crawler_config.get('blocked_domains'),
            exclude_patterns=crawler_config.get('exclude_patterns', []),
            pattern_type='regex'
        )
        
        # Storage configuration
        storage_config = config.get('storage', {})
        self.storage = MongoStorage(
            connection_string=storage_config.get('connection_string', 'mongodb://localhost:27017'),
            database=storage_config.get('database', 'crawler_db'),
            collection=storage_config.get('collection', 'crawled_pages'),
            max_document_size=storage_config.get('max_document_size', 16777216)
        )
    
    def initialize(self) -> None:
        """Initialize all components."""
        self.logger.log_entry("initialize")
        
        try:
            # Initialize engine with performance config
            self.logger.info("[Orchestrator] Initializing Crawl4AI engine")
            self.engine = Crawl4AIEngine(
                browser_config=self.browser_config,
                performance_config=self.performance_config
            )
            self.engine.initialize()
            self.logger.log_state_change("engine_uninitialized", "engine_initialized")
            
            # Connect to storage
            self.logger.info("[Orchestrator] Connecting to storage")
            self.storage.connect()
            self.logger.log_state_change("storage_disconnected", "storage_connected")
            
            self.logger.log_exit("initialize", status="success")
        except Exception as e:
            self.logger.error(f"[Orchestrator] Initialization failed: {str(e)}", exc_info=True)
            self.logger.log_exit("initialize", status="failed", error=str(e))
            raise
    
    async def crawl_url(self, url: str) -> Document:
        """
        Crawl a single URL through the complete pipeline.
        
        Pipeline:
        1. Validate URL
        2. Normalize URL
        3. Check URL filter (should_crawl)
        4. Crawl URL (get HTML)
        5. Parse HTML (extract text, links, title)
        6. Create Document model
        7. Save to MongoDB
        8. Return document
        
        Args:
            url: The URL to crawl
            
        Returns:
            Document model with extracted content
            
        Raises:
            ValidationError: If URL validation fails
            CrawlError: If crawling fails
            StorageError: If storage operations fail
        """
        # Create contextual logger with URL
        url_logger = self.logger.with_url(url)
        
        with url_logger.component_flow("crawl_url", url=url):
            try:
                # Step 1: Validate URL
                validate_url(url)
                validate_scheme(url)
                is_crawlable(url)
                url_logger.info("[Orchestrator] URL validated ✓")
                
                # Step 2: Normalize URL
                normalized_url = normalize_url(url)
                if normalized_url != url:
                    url_logger.log_transformation("URL_NORMALIZATION", url, normalized_url)
                
                # Step 2.5: Check URL filter
                crawler_config = self.config.get('crawler', {})
                auth_config = self.config.get('auth', {})
                filter_settings = {
                    'respect_robots_txt': crawler_config.get('respect_robots_txt', True),
                    'user_agent': auth_config.get('user_agent', 'CrawlerBot'),
                    'allowed_domains': crawler_config.get('allowed_domains'),
                    'blocked_domains': crawler_config.get('blocked_domains'),
                    'exclude_patterns': crawler_config.get('exclude_patterns', []),
                }
                should_crawl = self.url_filter.should_crawl(normalized_url, filters=filter_settings)
                if not should_crawl:
                    error_msg = f"URL filtered out: {normalized_url}"
                    url_logger.log_decision("URL_FILTERED", reason="URL did not pass filter criteria")
                    raise ValidationError(error_msg)
                
                # Step 3: Crawl URL
                raw_page: RawPage = await self.engine.crawl_url(
                    normalized_url,
                    config=self.config.get('crawler', {})
                )
                
                # Step 3.5: Validate HTML size
                crawler_config = self.config.get('crawler', {})
                max_html_size = crawler_config.get('max_html_size', 16777216)  # Default 16MB
                
                if raw_page.html:
                    html_size = len(raw_page.html.encode('utf-8'))
                    if html_size > max_html_size:
                        error_msg = f"HTML size ({html_size} bytes) exceeds maximum allowed size ({max_html_size} bytes)"
                        url_logger.log_decision("HTML_SIZE_INVALID", reason=error_msg)
                        raise ValidationError(error_msg)
                else:
                    url_logger.log_decision("HTML_EMPTY", "Empty HTML content received")
                
                # Step 4: Extract content (HTMLParser handles its own logging)
                try:
                    extracted = self.extractor.extract(raw_page.html, normalized_url)
                    content_text = extracted.get('text', '')
                    links_count = len(extracted.get('links', []))
                except Exception as e:
                    error_msg = f"Content extraction failed: {str(e)}"
                    url_logger.log_decision("EXTRACTION_FAILED", reason=error_msg)
                    raise CrawlError(error_msg, url=normalized_url) from e
                
                # Step 5: Validate content
                content_text = extracted.get('text', '')
                reject_empty = crawler_config.get('reject_empty_content', True)
                log_empty_warning = crawler_config.get('log_empty_content_warning', True)
                
                # Check if content is empty or only whitespace
                is_empty = not content_text or not content_text.strip()
                
                if is_empty:
                    if log_empty_warning:
                        url_logger.log_decision("CONTENT_EMPTY", "Extracted content is empty")
                    
                    if reject_empty:
                        error_msg = "Content extraction resulted in empty content"
                        url_logger.log_decision("CONTENT_REJECTED", reason=error_msg)
                        raise ValidationError(error_msg)
                else:
                    url_logger.log_decision("CONTENT_VALID", f"Content length: {len(content_text)} characters")
                
                # Step 6: Create Document model
                content_hash = hash_content(content_text)
                document_id = generate_document_id(normalized_url)
                
                document = Document(
                    document_id=document_id,
                    url=normalized_url,
                    title=extracted.get('title'),
                    content=content_text,
                    raw_html=raw_page.html,
                    links=extracted.get('links', []),
                    metadata={
                        **extracted.get('metadata', {}),
                        'status_code': raw_page.status_code,
                        'crawl_timestamp': raw_page.crawl_timestamp.isoformat(),
                        'headers': raw_page.headers
                    },
                    created_at=datetime.utcnow(),
                    hash=content_hash
                )
                
                # Step 7: Save to MongoDB (MongoStorage handles its own logging)
                self.storage.save(document.to_mongodb_dict())
                
                return document
                
            except ValidationError as e:
                url_logger.log_decision("VALIDATION_ERROR", reason=str(e))
                url_logger.error(f"[Orchestrator] Validation error: {str(e)}", exc_info=True)
                raise
            except CrawlError as e:
                url_logger.log_decision("CRAWL_ERROR", reason=str(e))
                url_logger.error(f"[Orchestrator] Crawl error: {str(e)}", exc_info=True)
                raise
            except StorageError as e:
                url_logger.log_decision("STORAGE_ERROR", reason=str(e))
                url_logger.error(f"[Orchestrator] Storage error: {str(e)}", exc_info=True)
                raise
            except Exception as e:
                url_logger.log_decision("UNEXPECTED_ERROR", reason=str(e))
                url_logger.error(f"[Orchestrator] Unexpected error processing URL: {str(e)}", exc_info=True)
                raise
    
    def cleanup(self) -> None:
        """Clean up resources."""
        self.logger.log_entry("cleanup")
        
        try:
            if self.engine:
                self.logger.info("[Orchestrator] Cleaning up engine")
                self.engine.cleanup()
                self.logger.log_state_change("engine_initialized", "engine_cleaned_up")
            
            if self.storage:
                self.logger.info("[Orchestrator] Disconnecting from storage")
                self.storage.disconnect()
                self.logger.log_state_change("storage_connected", "storage_disconnected")
            
            self.logger.log_exit("cleanup", status="success")
        except Exception as e:
            self.logger.error(f"[Orchestrator] Cleanup error: {str(e)}", exc_info=True)
            self.logger.log_exit("cleanup", status="failed", error=str(e))
            raise