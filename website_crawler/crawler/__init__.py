"""
Crawler module for the website crawler.

This module contains the main crawler components.
"""

# Core orchestrator
from .orchestrator import CrawlOrchestrator

# Exceptions
from .exceptions import (
    CrawlerException,
    CrawlError,
    CrawlTimeoutError,
    CrawlFailedError,
    NetworkError,
    StorageError,
    StorageConnectionError,
    StorageSaveError,
    ValidationError,
    InvalidURLError,
    ConfigurationError,
    ConfigurationValidationError,
    ExtractionError,
    ExtractionTimeoutError,
    ParsingError,
)

# Models
from .models import (
    RawPage,
    Document,
    SourcePage,
    PageChunk,
    CrawlRun,
)

# Factories
from .factories import (
    ExtractorFactory,
    StrategyFactory,
    StorageFactory,
)

# Engine
from .engine import (
    Crawl4AIEngine,
    BrowserConfig,
    PerformanceConfig,
)

# Extractors
from .extraction import (
    BaseExtractor,
    SimpleExtractor,
    CSSExtractor,
    XPathExtractor,
    LLMExtractor,
)

# Strategies
from .crawl_strategy import (
    BaseStrategy,
    BFSStrategy,
    SitemapStrategy,
    AdaptiveStrategy,
)

__all__ = [
    # Core
    "CrawlOrchestrator",
    # Exceptions
    "CrawlerException",
    "CrawlError",
    "CrawlTimeoutError",
    "CrawlFailedError",
    "NetworkError",
    "StorageError",
    "StorageConnectionError",
    "StorageSaveError",
    "ValidationError",
    "InvalidURLError",
    "ConfigurationError",
    "ConfigurationValidationError",
    "ExtractionError",
    "ExtractionTimeoutError",
    "ParsingError",
    # Models
    "RawPage",
    "Document",
    "SourcePage",
    "PageChunk",
    "CrawlRun",
    # Factories
    "ExtractorFactory",
    "StrategyFactory",
    "StorageFactory",
    # Engine
    "Crawl4AIEngine",
    "BrowserConfig",
    "PerformanceConfig",
    # Extractors
    "BaseExtractor",
    "SimpleExtractor",
    "CSSExtractor",
    "XPathExtractor",
    "LLMExtractor",
    # Strategies
    "BaseStrategy",
    "BFSStrategy",
    "SitemapStrategy",
    "AdaptiveStrategy",
]
