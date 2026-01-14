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
from .engine.crawl4ai_engine import Crawl4AIEngine
from .engine.browser import BrowserConfig
from .parsing.html_parser import HTMLParser
from .extraction.simple_extractor import SimpleExtractor
from storage.mongo import MongoStorage
from utils.hashing import hash_content, generate_document_id
from .exceptions import CrawlError, StorageError, ValidationError

logger = logging.getLogger(__name__)


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
        
        # Initialize components
        self.browser_config = BrowserConfig.from_config(config)
        self.engine: Optional[Crawl4AIEngine] = None
        self.html_parser = HTMLParser(config.get('extraction', {}))
        self.extractor = SimpleExtractor(config.get('extraction', {}))
        self.storage: Optional[MongoStorage] = None
        
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
        # Initialize engine
        self.engine = Crawl4AIEngine(self.browser_config)
        self.engine.initialize()
        
        # Connect to storage
        self.storage.connect()
        
        logger.info("Orchestrator initialized")
    
    async def crawl_url(self, url: str) -> Document:
        """
        Crawl a single URL through the complete pipeline.
        
        Pipeline:
        1. Validate URL
        2. Normalize URL
        3. Crawl URL (get HTML)
        4. Parse HTML (extract text, links, title)
        5. Create Document model
        6. Save to MongoDB
        7. Return document
        
        Args:
            url: The URL to crawl
            
        Returns:
            Document model with extracted content
            
        Raises:
            ValidationError: If URL validation fails
            CrawlError: If crawling fails
            StorageError: If storage operations fail
        """
        try:
            # Step 1: Validate URL
            logger.info(f"Validating URL: {url}")
            validate_url(url)
            validate_scheme(url)
            is_crawlable(url)
            
            # Step 2: Normalize URL
            logger.info(f"Normalizing URL: {url}")
            normalized_url = normalize_url(url)
            logger.info(f"Normalized URL: {normalized_url}")
            
            # Step 3: Crawl URL
            logger.info(f"Crawling URL: {normalized_url}")
            raw_page: RawPage = await self.engine.crawl_url(
                normalized_url,
                config=self.config.get('crawler', {})
            )
            logger.info(f"Successfully crawled URL: {normalized_url} (status: {raw_page.status_code})")
            
            # Step 3.5: Validate HTML size
            crawler_config = self.config.get('crawler', {})
            max_html_size = crawler_config.get('max_html_size', 16777216)  # Default 16MB
            
            if raw_page.html:
                html_size = len(raw_page.html.encode('utf-8'))
                if html_size > max_html_size:
                    error_msg = f"HTML size ({html_size} bytes) exceeds maximum allowed size ({max_html_size} bytes)"
                    logger.error(f"HTML size validation failed for URL {normalized_url}: {error_msg}")
                    raise ValidationError(error_msg)
                logger.debug(f"HTML size validation passed: {html_size} bytes")
            else:
                logger.warning(f"Empty HTML content received for URL: {normalized_url}")
            
            # Step 4: Extract content
            logger.info(f"Extracting content from: {normalized_url}")
            try:
                extracted = self.extractor.extract(raw_page.html, normalized_url)
            except Exception as e:
                error_msg = f"Content extraction failed: {str(e)}"
                logger.error(f"Extraction error for URL {normalized_url}: {error_msg}")
                raise CrawlError(error_msg, url=normalized_url) from e
            
            # Step 5: Validate content
            content_text = extracted.get('text', '')
            reject_empty = crawler_config.get('reject_empty_content', True)
            log_empty_warning = crawler_config.get('log_empty_content_warning', True)
            
            # Check if content is empty or only whitespace
            is_empty = not content_text or not content_text.strip()
            
            if is_empty:
                if log_empty_warning:
                    logger.warning(f"Empty content extracted from URL: {normalized_url}")
                
                if reject_empty:
                    error_msg = "Content extraction resulted in empty content"
                    logger.error(f"Content validation failed for URL {normalized_url}: {error_msg}")
                    raise ValidationError(error_msg)
            
            # Step 6: Create Document model
            logger.info(f"Creating document for: {normalized_url}")
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
            
            # Step 7: Save to MongoDB
            logger.info(f"Saving document to MongoDB: {document_id}")
            self.storage.save(document.to_mongodb_dict())
            logger.info(f"Successfully saved document: {document_id}")
            
            return document
            
        except ValidationError as e:
            logger.error(f"Validation error for URL {url}: {str(e)}")
            raise
        except CrawlError as e:
            logger.error(f"Crawl error for URL {url}: {str(e)}")
            raise
        except StorageError as e:
            logger.error(f"Storage error for URL {url}: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error processing URL {url}: {str(e)}")
            raise
    
    def cleanup(self) -> None:
        """Clean up resources."""
        if self.engine:
            self.engine.cleanup()
        
        if self.storage:
            self.storage.disconnect()
        
        logger.info("Orchestrator cleaned up")