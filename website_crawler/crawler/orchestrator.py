"""
Crawl orchestrator for the website crawler.

Coordinates the crawling process and manages the pipeline.
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

from .models.document import Document
from .models.raw_page import RawPage
from .models.source_page import SourcePage
from .models.page_chunk import PageChunk
from .models.crawl_run import CrawlRun
from .url.validator import validate_url, validate_scheme, is_crawlable
from .url.normalizer import normalize_url
from .url.filter import URLFilter
from .engine.crawl4ai_engine import Crawl4AIEngine
from .engine.browser import BrowserConfig
from .engine.performance import PerformanceConfig
from .parsing.html_parser import HTMLParser
from .parsing.markdown import MarkdownConverter
from .extraction.simple_extractor import SimpleExtractor
from .extraction.base import BaseExtractor
from .factories.extractor_factory import ExtractorFactory
from .factories.strategy_factory import StrategyFactory
from .crawl_strategy.base import BaseStrategy
from .processing.chunking import ChunkingService
from .processing.batching import BatchProcessor
from .processing.change_detection import ChangeDetectionService
from storage.mongo import MongoStorage
from utils.hashing import hash_content, generate_document_id, generate_source_page_id, generate_crawl_run_id
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
        
        # Initialize extractor using factory (Phase 3)
        extraction_config = config.get('extraction', {})
        extractor_type = extraction_config.get('type', 'css')  # Default to CSS for Phase 3
        try:
            self.extractor: BaseExtractor = ExtractorFactory.create(
                extractor_type,
                config=extraction_config
            )
            self.logger.info(f"[Orchestrator] Using {extractor_type} extractor")
        except (ValueError, TypeError):
            # Fallback to simple extractor if factory fails
            self.logger.warning(f"[Orchestrator] Failed to create {extractor_type} extractor, using SimpleExtractor")
            self.extractor = SimpleExtractor(extraction_config)
        
        # Initialize markdown converter (Phase 3)
        self.markdown_converter = MarkdownConverter(config.get('extraction', {}))
        
        # Initialize auth config (needed for URL filter and strategy)
        auth_config = config.get('auth', {})
        crawler_config = config.get('crawler', {})
        
        # Initialize URL filter from config (needed before strategy creation)
        self.url_filter = URLFilter(
            respect_robots_txt=crawler_config.get('respect_robots_txt', True),
            user_agent=auth_config.get('user_agent', 'CrawlerBot'),
            allowed_domains=crawler_config.get('allowed_domains'),
            blocked_domains=crawler_config.get('blocked_domains'),
            exclude_patterns=crawler_config.get('exclude_patterns', []),
            pattern_type='regex'
        )
        
        # Initialize strategy (Phase 3)
        strategy_config = config.get('strategy', {})
        strategy_type = strategy_config.get('type', 'bfs')
        
        # Get max_depth and max_pages from strategy config or fallback to crawler config
        max_depth = strategy_config.get('max_depth') or crawler_config.get('max_depth', 3)
        max_pages = strategy_config.get('max_pages') or crawler_config.get('max_pages', 100)
        
        # Log strategy selection for debugging
        self.logger.info(
            f"[Orchestrator] Initializing strategy type: {strategy_type} "
            f"(strategy_config keys: {list(strategy_config.keys())})"
        )
        
        # Build strategy kwargs - only include max_depth for strategies that support it
        strategy_kwargs = {
            'max_pages': max_pages,
            'url_filter': self.url_filter,
            'config': {
                'filter_settings': {
                    'respect_robots_txt': crawler_config.get('respect_robots_txt', True),
                    'user_agent': auth_config.get('user_agent', 'CrawlerBot'),
                    'allowed_domains': crawler_config.get('allowed_domains'),
                    'blocked_domains': crawler_config.get('blocked_domains'),
                    'exclude_patterns': crawler_config.get('exclude_patterns', []),
                },
                **strategy_config
            }
        }
        
        # Only add max_depth for strategies that support it (not sitemap)
        if strategy_type != 'sitemap':
            strategy_kwargs['max_depth'] = max_depth
        
        try:
            self.strategy: Optional[BaseStrategy] = StrategyFactory.create(
                strategy_type,
                **strategy_kwargs
            )
            self.logger.info(f"[Orchestrator] Using {strategy_type} strategy")
        except (ValueError, TypeError) as e:
            self.logger.error(f"[Orchestrator] Failed to create {strategy_type} strategy: {e}", exc_info=True)
            raise ValidationError(
                f"Failed to initialize strategy '{strategy_type}': {str(e)}. "
                f"Check your strategy configuration."
            ) from e
        
        # Initialize chunking service (Phase 3) - token-aware
        # Note: Service may be None initially and created on-demand when config overrides enable it
        chunking_config = config.get('chunking', {})
        if chunking_config.get('enabled', False):
            self.chunking_service = ChunkingService(
                chunk_size_tokens=chunking_config.get('chunk_size_tokens', 512),
                chunk_overlap_tokens=chunking_config.get('chunk_overlap_tokens', 50),
                chunk_size_chars=chunking_config.get('chunk_size', 1000),  # Fallback
                chunk_overlap_chars=chunking_config.get('chunk_overlap', 200),  # Fallback
                strategy=chunking_config.get('strategy', 'sentence'),
                preserve_sentences=chunking_config.get('preserve_sentences', True),
                preserve_paragraphs=chunking_config.get('preserve_paragraphs', True),
                tokenizer=chunking_config.get('tokenizer', 'cl100k_base')
            )
            self.logger.info("[Orchestrator] Token-aware chunking service enabled")
        else:
            self.chunking_service = None
        
        # Initialize batch processor (Phase 3)
        batching_config = config.get('batching', {})
        self.batch_processor = BatchProcessor(
            batch_size=batching_config.get('batch_size', 10),
            max_concurrent=batching_config.get('max_concurrent', 5),
            fail_fast=batching_config.get('fail_fast', False)
        )
        self.logger.info("[Orchestrator] Batch processor initialized")
        
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
        
        # Storage configuration
        storage_config = config.get('storage', {})
        self.storage = MongoStorage(
            connection_string=storage_config.get('connection_string', 'mongodb://localhost:27017'),
            database=storage_config.get('database', 'crawler_db'),
            collection=storage_config.get('collection', 'crawled_pages'),
            max_document_size=storage_config.get('max_document_size', 16777216)
        )
    
    def _get_chunking_service(self) -> Optional[ChunkingService]:
        """
        Get or create chunking service based on current config.
        
        This method checks the current config (which may have been overridden)
        and creates the chunking service if enabled but not yet initialized.
        
        Returns:
            ChunkingService instance if chunking is enabled, None otherwise
        """
        chunking_config = self.config.get('chunking', {})
        if not chunking_config.get('enabled', False):
            return None
        
        # If service already exists, return it
        if self.chunking_service is not None:
            return self.chunking_service
        
        # Create service on-demand based on current config
        self.chunking_service = ChunkingService(
            chunk_size_tokens=chunking_config.get('chunk_size_tokens', 512),
            chunk_overlap_tokens=chunking_config.get('chunk_overlap_tokens', 50),
            chunk_size_chars=chunking_config.get('chunk_size', 1000),  # Fallback
            chunk_overlap_chars=chunking_config.get('chunk_overlap', 200),  # Fallback
            strategy=chunking_config.get('strategy', 'sentence'),
            preserve_sentences=chunking_config.get('preserve_sentences', True),
            preserve_paragraphs=chunking_config.get('preserve_paragraphs', True),
            tokenizer=chunking_config.get('tokenizer', 'cl100k_base')
        )
        self.logger.info("[Orchestrator] Chunking service created on-demand from config")
        return self.chunking_service
    
    def _reinitialize_components(self) -> None:
        """
        Re-initialize components based on current config.
        
        This method is called when config overrides are applied to ensure
        components (extractor, strategy, etc.) use the updated configuration.
        """
        self.logger.debug("[Orchestrator] Re-initializing components from updated config")
        
        # Re-initialize browser config
        self.browser_config = BrowserConfig.from_config(self.config)
        
        # Re-initialize HTML parser
        self.html_parser = HTMLParser(self.config.get('extraction', {}))
        
        # Re-initialize extractor
        extraction_config = self.config.get('extraction', {})
        extractor_type = extraction_config.get('type', 'css')
        try:
            self.extractor = ExtractorFactory.create(
                extractor_type,
                config=extraction_config
            )
            self.logger.info(f"[Orchestrator] Re-initialized {extractor_type} extractor")
        except (ValueError, TypeError):
            self.logger.warning(f"[Orchestrator] Failed to create {extractor_type} extractor, using SimpleExtractor")
            self.extractor = SimpleExtractor(extraction_config)
        
        # Re-initialize markdown converter
        self.markdown_converter = MarkdownConverter(self.config.get('extraction', {}))
        
        # Re-initialize URL filter
        auth_config = self.config.get('auth', {})
        crawler_config = self.config.get('crawler', {})
        self.url_filter = URLFilter(
            respect_robots_txt=crawler_config.get('respect_robots_txt', True),
            user_agent=auth_config.get('user_agent', 'CrawlerBot'),
            allowed_domains=crawler_config.get('allowed_domains'),
            blocked_domains=crawler_config.get('blocked_domains'),
            exclude_patterns=crawler_config.get('exclude_patterns', []),
            pattern_type='regex'
        )
        
        # Re-initialize strategy
        strategy_config = self.config.get('strategy', {})
        strategy_type = strategy_config.get('type', 'bfs')
        max_depth = strategy_config.get('max_depth') or crawler_config.get('max_depth', 3)
        max_pages = strategy_config.get('max_pages') or crawler_config.get('max_pages', 100)
        
        # Log strategy selection for debugging
        self.logger.info(
            f"[Orchestrator] Strategy type from config: {strategy_type} "
            f"(strategy_config keys: {list(strategy_config.keys())})"
        )
        
        # Build strategy kwargs - only include max_depth for strategies that support it
        strategy_kwargs = {
            'max_pages': max_pages,
            'url_filter': self.url_filter,
            'config': {
                'filter_settings': {
                    'respect_robots_txt': crawler_config.get('respect_robots_txt', True),
                    'user_agent': auth_config.get('user_agent', 'CrawlerBot'),
                    'allowed_domains': crawler_config.get('allowed_domains'),
                    'blocked_domains': crawler_config.get('blocked_domains'),
                    'exclude_patterns': crawler_config.get('exclude_patterns', []),
                },
                **strategy_config
            }
        }
        
        # Only add max_depth for strategies that support it (not sitemap)
        if strategy_type != 'sitemap':
            strategy_kwargs['max_depth'] = max_depth
        
        try:
            self.strategy = StrategyFactory.create(
                strategy_type,
                **strategy_kwargs
            )
            log_msg = f"[Orchestrator] Re-initialized {strategy_type} strategy (max_pages={max_pages}"
            if strategy_type != 'sitemap':
                log_msg += f", max_depth={max_depth}"
            log_msg += ")"
            self.logger.info(log_msg)
        except (ValueError, TypeError) as e:
            self.logger.error(f"[Orchestrator] Failed to create {strategy_type} strategy: {e}", exc_info=True)
            raise ValidationError(
                f"Failed to initialize strategy '{strategy_type}': {str(e)}. "
                f"Check your strategy configuration."
            ) from e
        
        # Re-initialize chunking service if enabled
        chunking_config = self.config.get('chunking', {})
        if chunking_config.get('enabled', False):
            self.chunking_service = ChunkingService(
                chunk_size_tokens=chunking_config.get('chunk_size_tokens', 512),
                chunk_overlap_tokens=chunking_config.get('chunk_overlap_tokens', 50),
                chunk_size_chars=chunking_config.get('chunk_size', 1000),
                chunk_overlap_chars=chunking_config.get('chunk_overlap', 200),
                strategy=chunking_config.get('strategy', 'sentence'),
                preserve_sentences=chunking_config.get('preserve_sentences', True),
                preserve_paragraphs=chunking_config.get('preserve_paragraphs', True),
                tokenizer=chunking_config.get('tokenizer', 'cl100k_base')
            )
            self.logger.info("[Orchestrator] Re-initialized chunking service")
        else:
            # If chunking is disabled, set to None (but keep existing if it was already created)
            # This allows disabling chunking via config override
            if chunking_config.get('enabled') is False:  # Explicitly False, not just missing
                self.chunking_service = None
        
        # Re-initialize batch processor
        batching_config = self.config.get('batching', {})
        self.batch_processor = BatchProcessor(
            batch_size=batching_config.get('batch_size', 10),
            max_concurrent=batching_config.get('max_concurrent', 5),
            fail_fast=batching_config.get('fail_fast', False)
        )
        
        # Re-initialize performance config
        performance_config_dict = {
            'request_timeout': crawler_config.get('timeout', 30),
            'page_load_timeout': crawler_config.get('timeout', 30),
            'max_retries': crawler_config.get('retries', 3),
            'rate_limit': crawler_config.get('rate_limit'),
            'concurrent_requests': crawler_config.get('concurrent_requests', 10),
        }
        self.performance_config = PerformanceConfig.from_config(performance_config_dict)
        
        # Update engine config if engine is already initialized
        if self.engine is not None:
            self.engine.browser_config = self.browser_config
            self.engine.performance_config = self.performance_config
    
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
                
                # Step 4: Extract content (extractor handles its own logging)
                try:
                    # Use extractor's extract method (supports url, html_content signature)
                    # BaseExtractor signature: extract(self, url: str, html_content: str = None)
                    extracted = self.extractor.extract(normalized_url, raw_page.html)
                    content_text = extracted.get('text', '')
                    links_count = len(extracted.get('links', []))
                except Exception as e:
                    error_msg = f"Content extraction failed: {str(e)}"
                    url_logger.log_decision("EXTRACTION_FAILED", reason=error_msg)
                    raise CrawlError(error_msg, url=normalized_url) from e
                
                # Step 4.5: Convert to markdown if enabled (Phase 3)
                markdown_content = None
                if self.config.get('extraction', {}).get('generate_markdown', False):
                    try:
                        markdown_content = self.markdown_converter.convert(raw_page.html, normalized_url)
                        url_logger.log_decision("MARKDOWN_GENERATED", f"Generated {len(markdown_content)} chars of markdown")
                    except Exception as e:
                        url_logger.warning(f"[Orchestrator] Markdown conversion failed: {e}")
                        # Continue without markdown
                
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
                
                # Step 5.5: Chunk content if enabled (Phase 3)
                # Note: This is the legacy crawl_url method. For new code, use crawl_url_unified.
                chunks = None
                chunking_service = self._get_chunking_service()
                if chunking_service:
                    try:
                        # Use chunk_content method (unified architecture)
                        # Note: This method returns PageChunk objects, which is different from the old Document chunks
                        # For legacy compatibility, we'll skip chunking in this method
                        # The unified method (crawl_url_unified) should be used instead
                        url_logger.warning("[Orchestrator] Chunking is enabled but crawl_url method doesn't support it. Use crawl_url_unified instead.")
                        chunks = None
                    except Exception as e:
                        url_logger.warning(f"[Orchestrator] Chunking failed: {e}")
                        # Continue without chunks
                
                # Step 6: Create Document model
                content_hash = hash_content(content_text)
                document_id = generate_document_id(normalized_url)
                
                # Update chunk document_ids if chunks were created
                if chunks:
                    for chunk in chunks:
                        chunk.document_id = document_id
                        chunk.chunk_id = f"{document_id}_chunk_{chunk.chunk_index}"
                
                document = Document(
                    document_id=document_id,
                    url=normalized_url,
                    title=extracted.get('title'),
                    content=content_text,
                    raw_html=raw_page.html,
                    markdown=markdown_content,  # Phase 3: Add markdown support
                    links=extracted.get('links', []),
                    metadata={
                        **extracted.get('metadata', {}),
                        'status_code': raw_page.status_code,
                        'crawl_timestamp': raw_page.crawl_timestamp.isoformat(),
                        'headers': raw_page.headers,
                        'extractor_type': self.config.get('extraction', {}).get('type', 'simple'),  # Phase 3
                        'chunks_count': len(chunks) if chunks else 0  # Phase 3: Add chunk count
                    },
                    created_at=datetime.utcnow(),
                    hash=content_hash
                )
                
                # Step 7: Save to MongoDB (MongoStorage handles its own logging)
                self.storage.save(document.to_mongodb_dict())
                
                # Step 7.5: Optionally save chunks to MongoDB (Phase 3)
                # Note: Chunking not fully supported in legacy crawl_url method
                if chunks and chunking_service:
                    try:
                        for chunk in chunks:
                            chunk_dict = {
                                '_id': chunk.chunk_id,
                                'document_id': chunk.document_id,
                                'chunk_index': chunk.chunk_index,
                                'content': chunk.content,
                                'chunk_size': chunk.chunk_size,
                                'overlap_size': chunk.overlap_size,
                                'metadata': chunk.metadata,
                                'created_at': datetime.utcnow().isoformat()
                            }
                            # Save to a separate chunks collection
                            # Note: This requires storage to support multiple collections
                            # For now, we'll log that chunks were created
                            url_logger.debug(f"[Orchestrator] Chunk {chunk.chunk_index} created: {len(chunk.content)} chars")
                    except Exception as e:
                        url_logger.warning(f"[Orchestrator] Failed to save chunks: {e}")
                
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
    
    async def crawl_with_strategy(self, start_url: str) -> List[Document]:
        """
        Crawl multiple URLs using the configured strategy.
        
        This method uses the strategy to discover and crawl URLs iteratively:
        1. Initialize strategy with start URL
        2. While strategy has URLs:
           - Get next URL from strategy
           - Crawl URL
           - Extract content and links
           - Add discovered links to strategy
           - Save document
        3. Continue until limits reached or no more URLs
        
        Args:
            start_url: The starting URL for the crawl
            
        Returns:
            List of Document models for all crawled pages
            
        Raises:
            ValidationError: If URL validation fails
            CrawlError: If crawling fails
            StorageError: If storage operations fail
        """
        url_logger = self.logger.with_url(start_url)
        
        with url_logger.component_flow("crawl_with_strategy", start_url=start_url):
            if not self.strategy:
                error_msg = "No strategy configured. Cannot perform strategy-based crawl."
                url_logger.log_decision("STRATEGY_MISSING", reason=error_msg)
                raise ValidationError(error_msg)
            
            documents: List[Document] = []
            
            try:
                # Initialize strategy with start URL
                url_logger.info(f"[Orchestrator] Initializing {type(self.strategy).__name__} strategy with start URL: {start_url}")
                
                # For BFS strategy, use initialize method if available
                if hasattr(self.strategy, 'initialize'):
                    self.strategy.initialize(start_url)
                else:
                    # For other strategies, add start URL
                    self.strategy.add_url(start_url, priority=0, depth=0)
                
                # Track depth for link discovery
                url_depth_map: Dict[str, int] = {normalize_url(start_url): 0}
                
                # Iterative crawling loop
                while self.strategy.has_more_urls():
                    # Get next URL from strategy
                    next_url = self.strategy.get_next_url()
                    if not next_url:
                        url_logger.info("[Orchestrator] No more URLs available from strategy")
                        break
                    
                    # Get depth for this URL
                    # Try to get from strategy's current_depth if available (BFS strategy)
                    if hasattr(self.strategy, 'current_depth'):
                        current_depth = self.strategy.current_depth
                    else:
                        # Fall back to our tracking map
                        current_depth = url_depth_map.get(normalize_url(next_url), 0)
                    
                    # Update our tracking map
                    url_depth_map[normalize_url(next_url)] = current_depth
                    
                    url_logger.info(f"[Orchestrator] Crawling URL from strategy (depth={current_depth}): {next_url}")
                    
                    try:
                        # Crawl the URL
                        document = await self.crawl_url(next_url)
                        documents.append(document)
                        
                        # Extract links and add them to strategy
                        discovered_links = document.links
                        if discovered_links:
                            url_logger.info(f"[Orchestrator] Discovered {len(discovered_links)} links, adding to strategy")
                            
                            for link in discovered_links:
                                normalized_link = normalize_url(link)
                                # Add link to strategy at depth + 1
                                next_depth = current_depth + 1
                                self.strategy.add_url(link, priority=0, depth=next_depth)
                                url_depth_map[normalized_link] = next_depth
                        else:
                            url_logger.debug(f"[Orchestrator] No links discovered from {next_url}")
                    
                    except (ValidationError, CrawlError, StorageError) as e:
                        url_logger.warning(f"[Orchestrator] Failed to crawl {next_url}: {e}")
                        # Continue with next URL
                        continue
                    except Exception as e:
                        url_logger.error(f"[Orchestrator] Unexpected error crawling {next_url}: {e}", exc_info=True)
                        # Continue with next URL
                        continue
                
                url_logger.info(f"[Orchestrator] Strategy-based crawl completed. Crawled {len(documents)} documents")
                return documents
                
            except Exception as e:
                url_logger.error(f"[Orchestrator] Strategy-based crawl failed: {e}", exc_info=True)
                raise
    
    async def crawl_url_unified(self, url: str, crawl_run_id: Optional[str] = None) -> SourcePage:
        """
        Crawl a single URL using the unified data architecture.
        
        This method uses SourcePage, PageChunk models with change detection.
        
        Pipeline:
        1. Validate and normalize URL
        2. Check for existing SourcePage
        3. Crawl URL and extract content
        4. Detect changes (page-level and chunk-level)
        5. Generate chunks if needed
        6. Save/update SourcePage and PageChunks incrementally
        
        Args:
            url: The URL to crawl
            crawl_run_id: Optional CrawlRun ID (for multi-page crawls)
            
        Returns:
            SourcePage model
            
        Raises:
            ValidationError: If URL validation fails
            CrawlError: If crawling fails
            StorageError: If storage operations fail
        """
        url_logger = self.logger.with_url(url)
        
        with url_logger.component_flow("crawl_url_unified", url=url):
            try:
                # Step 1: Validate and normalize URL
                validate_url(url)
                validate_scheme(url)
                is_crawlable(url)
                normalized_url = normalize_url(url)
                
                # Generate deterministic source_page_id
                source_page_id = generate_source_page_id(normalized_url)
                
                # Step 2: Check for existing SourcePage
                existing_source_page_dict = self.storage.get_source_page(source_page_id=source_page_id)
                existing_source_page = None
                if existing_source_page_dict:
                    existing_source_page = SourcePage.from_mongodb_dict(existing_source_page_dict)
                    url_logger.info(f"[Orchestrator] Found existing SourcePage: {source_page_id}")
                
                # Step 3: Check URL filter
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
                    raise ValidationError(f"URL filtered out: {normalized_url}")
                
                # Step 4: Crawl URL
                raw_page: RawPage = await self.engine.crawl_url(
                    normalized_url,
                    config=self.config.get('crawler', {})
                )
                
                # Step 5: Extract content
                extracted = self.extractor.extract(normalized_url, raw_page.html)
                content_text = extracted.get('text', '')
                
                # Validate content
                if not content_text or not content_text.strip():
                    if crawler_config.get('reject_empty_content', True):
                        raise ValidationError("Content extraction resulted in empty content")
                
                # Step 6: Compute content hash
                content_hash = hash_content(content_text)
                
                # Step 7: Detect changes
                page_changed, is_new_page = ChangeDetectionService.detect_page_changes(
                    existing_source_page,
                    content_text,
                    content_hash
                )
                
                # Step 8: Generate chunks if chunking enabled
                # Use helper method to get chunking service (handles config overrides)
                chunking_service = self._get_chunking_service()
                new_chunks = []
                existing_chunks = []
                if chunking_service:
                    # Get existing chunks
                    if existing_source_page:
                        existing_chunks = self.storage.get_page_chunks(source_page_id, status="active")
                    
                    # Generate new chunks
                    version = existing_source_page.version + 1 if existing_source_page and page_changed else (
                        1 if is_new_page else existing_source_page.version
                    )
                    new_chunks = chunking_service.chunk_content(
                        source_page_id=source_page_id,
                        content=content_text,
                        version=version,
                        metadata={
                            'url': normalized_url,
                            'title': extracted.get('title'),
                            'extractor_type': self.config.get('extraction', {}).get('type', 'simple')
                        }
                    )
                    
                    # Detect chunk changes
                    chunks_to_save, unchanged_chunk_ids, obsolete_chunk_ids = ChangeDetectionService.detect_chunk_changes(
                        existing_chunks,
                        new_chunks
                    )
                    
                    # Save chunks
                    if chunks_to_save:
                        chunk_dicts = [chunk.to_mongodb_dict() for chunk in chunks_to_save]
                        self.storage.save_page_chunks_batch(chunk_dicts)
                        url_logger.info(f"[Orchestrator] Saved {len(chunks_to_save)} new/changed chunks")
                    
                    # Mark obsolete chunks
                    if obsolete_chunk_ids:
                        self.storage.mark_chunks_obsolete(source_page_id, unchanged_chunk_ids + [c.chunk_id for c in chunks_to_save])
                        url_logger.info(f"[Orchestrator] Marked {len(obsolete_chunk_ids)} chunks as obsolete")
                else:
                    # No chunking - just track that we have 0 chunks
                    new_chunks = []
                
                # Step 9: Create or update SourcePage
                if is_new_page:
                    source_page = SourcePage(
                        source_page_id=source_page_id,
                        url=url,
                        normalized_url=normalized_url,
                        content_hash=content_hash,
                        version=1,
                        last_crawled=datetime.utcnow(),
                        first_crawled=datetime.utcnow(),
                        status="active",
                        status_code=raw_page.status_code,
                        total_chunks=len(new_chunks),
                        metadata={
                            **extracted.get('metadata', {}),
                            'title': extracted.get('title'),
                            'crawl_timestamp': raw_page.crawl_timestamp.isoformat(),
                            'headers': raw_page.headers,
                            'extractor_type': self.config.get('extraction', {}).get('type', 'simple'),
                            'links': extracted.get('links', [])
                        },
                        crawl_run_id=crawl_run_id
                    )
                elif page_changed:
                    source_page = SourcePage(
                        source_page_id=source_page_id,
                        url=url,
                        normalized_url=normalized_url,
                        content_hash=content_hash,
                        version=existing_source_page.version + 1,
                        last_crawled=datetime.utcnow(),
                        first_crawled=existing_source_page.first_crawled,
                        status="active",
                        status_code=raw_page.status_code,
                        total_chunks=len(new_chunks),
                        metadata={
                            **extracted.get('metadata', {}),
                            'title': extracted.get('title'),
                            'crawl_timestamp': raw_page.crawl_timestamp.isoformat(),
                            'headers': raw_page.headers,
                            'extractor_type': self.config.get('extraction', {}).get('type', 'simple'),
                            'links': extracted.get('links', [])
                        },
                        crawl_run_id=crawl_run_id or existing_source_page.crawl_run_id
                    )
                else:
                    # Unchanged - just update last_crawled
                    source_page = existing_source_page
                    source_page.last_crawled = datetime.utcnow()
                    if crawl_run_id:
                        source_page.crawl_run_id = crawl_run_id
                
                # Step 10: Save SourcePage
                self.storage.save_source_page(source_page.to_mongodb_dict())
                
                url_logger.info(f"[Orchestrator] Saved SourcePage: {source_page_id} (version={source_page.version})")
                return source_page
                
            except ValidationError as e:
                url_logger.error(f"[Orchestrator] Validation error: {str(e)}", exc_info=True)
                raise
            except CrawlError as e:
                url_logger.error(f"[Orchestrator] Crawl error: {str(e)}", exc_info=True)
                raise
            except StorageError as e:
                url_logger.error(f"[Orchestrator] Storage error: {str(e)}", exc_info=True)
                raise
            except Exception as e:
                url_logger.error(f"[Orchestrator] Unexpected error: {str(e)}", exc_info=True)
                raise
    
    async def crawl_with_strategy_unified(self, start_url: str) -> CrawlRun:
        """
        Crawl multiple URLs using the unified data architecture.
        
        This method uses SourcePage, PageChunk, and CrawlRun models.
        
        Args:
            start_url: The starting URL for the crawl
            
        Returns:
            CrawlRun model with statistics
            
        Raises:
            ValidationError: If URL validation fails
            CrawlError: If crawling fails
            StorageError: If storage operations fail
        """
        url_logger = self.logger.with_url(start_url)
        
        with url_logger.component_flow("crawl_with_strategy_unified", start_url=start_url):
            if not self.strategy:
                raise ValidationError("No strategy configured. Cannot perform strategy-based crawl.")
            
            # Create CrawlRun
            crawl_run_id = generate_crawl_run_id(start_url)
            crawl_run = CrawlRun(
                crawl_run_id=crawl_run_id,
                start_url=start_url,
                crawl_type="multi_page",
                strategy_type=self.config.get('strategy', {}).get('type', 'bfs'),
                start_time=datetime.utcnow(),
                status="running",
                config_snapshot=self.config.copy()
            )
            self.storage.save_crawl_run(crawl_run.to_mongodb_dict())
            
            source_pages: List[SourcePage] = []
            total_pages_discovered = 0
            total_pages_failed = 0
            total_chunks_created = 0
            max_depth_reached = 0
            
            try:
                # Initialize strategy
                if hasattr(self.strategy, 'initialize'):
                    self.strategy.initialize(start_url)
                else:
                    self.strategy.add_url(start_url, priority=0, depth=0)
                
                url_depth_map: Dict[str, int] = {normalize_url(start_url): 0}
                
                # Crawling loop
                while self.strategy.has_more_urls():
                    next_url = self.strategy.get_next_url()
                    if not next_url:
                        break
                    
                    current_depth = url_depth_map.get(normalize_url(next_url), 0)
                    max_depth_reached = max(max_depth_reached, current_depth)
                    total_pages_discovered += 1
                    
                    try:
                        # Crawl URL using unified method
                        source_page = await self.crawl_url_unified(next_url, crawl_run_id=crawl_run_id)
                        source_pages.append(source_page)
                        total_chunks_created += source_page.total_chunks
                        
                        # Extract links and add to strategy
                        links = source_page.metadata.get('links', [])
                        if links:
                            for link in links:
                                normalized_link = normalize_url(link)
                                next_depth = current_depth + 1
                                self.strategy.add_url(link, priority=0, depth=next_depth)
                                url_depth_map[normalized_link] = next_depth
                    except (ValidationError, CrawlError, StorageError) as e:
                        url_logger.warning(f"[Orchestrator] Failed to crawl {next_url}: {e}")
                        total_pages_failed += 1
                        continue
                    except Exception as e:
                        url_logger.error(f"[Orchestrator] Unexpected error crawling {next_url}: {e}", exc_info=True)
                        total_pages_failed += 1
                        continue
                
                # Update CrawlRun
                crawl_run.end_time = datetime.utcnow()
                crawl_run.status = "completed" if total_pages_failed == 0 else "partial"
                crawl_run.total_pages_discovered = total_pages_discovered
                crawl_run.total_pages_crawled = len(source_pages)
                crawl_run.total_pages_failed = total_pages_failed
                crawl_run.total_chunks_created = total_chunks_created
                crawl_run.max_depth = max_depth_reached
                crawl_run.max_pages = self.config.get('crawler', {}).get('max_pages')
                
                self.storage.save_crawl_run(crawl_run.to_mongodb_dict())
                
                url_logger.info(f"[Orchestrator] Strategy-based crawl completed: {len(source_pages)} pages, {total_chunks_created} chunks")
                return crawl_run
                
            except Exception as e:
                # Mark crawl as failed
                crawl_run.end_time = datetime.utcnow()
                crawl_run.status = "failed"
                crawl_run.error_summary = {'error': str(e)}
                self.storage.save_crawl_run(crawl_run.to_mongodb_dict())
                url_logger.error(f"[Orchestrator] Strategy-based crawl failed: {e}", exc_info=True)
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