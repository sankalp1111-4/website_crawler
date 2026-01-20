"""
Pydantic models for configuration validation.
"""
from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


class CrawlerConfig(BaseModel):
    """Crawling settings configuration."""
    max_depth: int = Field(default=3, ge=1, le=10, description="Maximum crawling depth")
    max_pages: int = Field(default=100, ge=1, le=10000, description="Maximum pages to crawl")
    delay: float = Field(default=1.0, ge=0.0, le=60.0, description="Delay between requests in seconds")
    timeout: int = Field(default=30, ge=1, le=300, description="Request timeout in seconds")
    retries: int = Field(default=3, ge=0, le=10, description="Number of retry attempts")
    rate_limit: Optional[float] = Field(default=None, ge=0.0, description="Rate limit (requests per second)")
    respect_robots_txt: bool = Field(default=True, description="Whether to respect robots.txt")
    follow_redirects: bool = Field(default=True, description="Whether to follow HTTP redirects")
    max_redirects: int = Field(default=5, ge=0, le=20, description="Maximum number of redirects to follow")
    max_html_size: int = Field(default=16777216, ge=1024, description="Maximum HTML size in bytes (default: 16MB)")
    reject_empty_content: bool = Field(default=True, description="Reject documents with empty content")
    log_empty_content_warning: bool = Field(default=True, description="Log warning for empty content even if not rejected")
    allowed_domains: Optional[List[str]] = Field(default=None, description="List of allowed domains (None = all allowed)")
    blocked_domains: Optional[List[str]] = Field(default=None, description="List of blocked domains")
    exclude_patterns: List[str] = Field(default_factory=list, description="URL patterns to exclude from crawling")
    user_agent: Optional[str] = Field(default="CrawlerBot", description="User agent string for robots.txt and requests")
    
    model_config = {"frozen": True}


class EngineConfig(BaseModel):
    """Engine-specific settings configuration."""
    headless: bool = Field(default=True, description="Run browser in headless mode")
    browser_type: Literal["chromium", "firefox", "webkit"] = Field(
        default="chromium", 
        description="Browser type to use"
    )
    viewport_width: int = Field(default=1920, ge=320, le=7680, description="Viewport width in pixels")
    viewport_height: int = Field(default=1080, ge=240, le=4320, description="Viewport height in pixels")
    wait_for: Optional[str] = Field(default=None, description="CSS selector or timeout to wait for")
    wait_timeout: int = Field(default=30, ge=0, le=300, description="Wait timeout in seconds")
    js_enabled: bool = Field(default=True, description="Enable JavaScript execution")
    images_enabled: bool = Field(default=True, description="Load images")
    css_enabled: bool = Field(default=True, description="Load CSS")
    
    model_config = {"frozen": True}


class StorageConfig(BaseModel):
    """Storage settings configuration."""
    type: Literal["mongodb", "file", "memory"] = Field(
        default="mongodb",
        description="Storage backend type"
    )
    connection_string: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection string"
    )
    database: str = Field(default="crawler_db", description="Database name")
    collection: str = Field(default="crawled_pages", description="Collection name")
    username: Optional[str] = Field(default=None, description="Database username")
    password: Optional[str] = Field(default=None, description="Database password")
    auth_source: Optional[str] = Field(default=None, description="Authentication source")
    max_pool_size: int = Field(default=100, ge=1, le=1000, description="Maximum connection pool size")
    max_document_size: int = Field(default=16777216, ge=1024, description="Maximum document size in bytes before save (default: 16MB)")
    
    model_config = {"frozen": True}


class ExtractionConfig(BaseModel):
    """Extraction settings configuration."""
    type: Literal["css", "xpath", "llm", "auto"] = Field(
        default="css",
        description="Extractor type"
    )
    selectors: Dict[str, str] = Field(
        default_factory=dict,
        description="CSS selectors or XPath expressions for extraction"
    )
    extract_text: bool = Field(default=True, description="Extract text content")
    extract_links: bool = Field(default=True, description="Extract links")
    extract_images: bool = Field(default=False, description="Extract images")
    extract_metadata: bool = Field(default=True, description="Extract metadata")
    clean_html: bool = Field(default=True, description="Clean HTML before extraction")
    
    model_config = {"frozen": True}


class StrategyConfig(BaseModel):
    """Strategy settings configuration."""
    type: Literal["bfs", "dfs", "sitemap", "adaptive"] = Field(
        default="bfs",
        description="Crawling strategy type"
    )
    max_depth: Optional[int] = Field(default=None, ge=1, le=10, description="Strategy-specific max depth override")
    max_pages: Optional[int] = Field(default=None, ge=1, le=10000, description="Strategy-specific max pages override")
    priority_patterns: List[str] = Field(
        default_factory=list,
        description="URL patterns to prioritize"
    )
    exclude_patterns: List[str] = Field(
        default_factory=list,
        description="URL patterns to exclude"
    )
    
    model_config = {"frozen": True}


class LoggingConfig(BaseModel):
    """Logging settings configuration."""
    level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO",
        description="Logging level"
    )
    format: Literal["json", "text", "simple", "detailed"] = Field(
        default="simple",
        description="Log format type"
    )
    file_path: Optional[str] = Field(default=None, description="Log file path")
    console_enabled: bool = Field(default=True, description="Enable console logging")
    file_enabled: bool = Field(default=False, description="Enable file logging")
    max_bytes: int = Field(default=10485760, ge=1024, description="Max log file size in bytes")
    backup_count: int = Field(default=5, ge=0, description="Number of backup log files")
    
    model_config = {"frozen": True}


class MainConfig(BaseModel):
    """Root configuration combining all configuration sections."""
    crawler: CrawlerConfig = Field(default_factory=CrawlerConfig)
    engine: EngineConfig = Field(default_factory=EngineConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    extraction: ExtractionConfig = Field(default_factory=ExtractionConfig)
    strategy: StrategyConfig = Field(default_factory=StrategyConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    # Optional client identifier for multi-tenant support
    client_id: Optional[str] = Field(default=None, description="Client identifier for multi-tenant support")
    
    model_config = {"frozen": True}
    
    def validate_config(self) -> None:
        """
        Perform comprehensive configuration validation.
        
        Raises:
            ConfigurationValidationError: If validation fails
        """
        # Import here to avoid circular dependencies
        try:
            from ..crawler.exceptions import ConfigurationValidationError
        except ImportError:
            # Fallback for absolute import if relative doesn't work
            from website_crawler.crawler.exceptions import ConfigurationValidationError
        
        # Validate crawler config dependencies
        if self.crawler.max_depth < 1:
            raise ConfigurationValidationError(
                "crawler.max_depth must be >= 1",
                config_key="crawler.max_depth"
            )
        
        if self.crawler.max_pages < 1:
            raise ConfigurationValidationError(
                "crawler.max_pages must be >= 1",
                config_key="crawler.max_pages"
            )
        
        # Validate storage config
        if self.storage.type == "mongodb":
            if not self.storage.connection_string:
                raise ConfigurationValidationError(
                    "storage.connection_string is required for MongoDB storage",
                    config_key="storage.connection_string"
                )
        
        # Validate strategy config
        if self.strategy.max_depth is not None:
            if self.strategy.max_depth < 1:
                raise ConfigurationValidationError(
                    "strategy.max_depth must be >= 1 if specified",
                    config_key="strategy.max_depth"
                )
            if self.strategy.max_depth > self.crawler.max_depth:
                raise ConfigurationValidationError(
                    f"strategy.max_depth ({self.strategy.max_depth}) cannot exceed "
                    f"crawler.max_depth ({self.crawler.max_depth})",
                    config_key="strategy.max_depth"
                )
        
        if self.strategy.max_pages is not None:
            if self.strategy.max_pages < 1:
                raise ConfigurationValidationError(
                    "strategy.max_pages must be >= 1 if specified",
                    config_key="strategy.max_pages"
                )
            if self.strategy.max_pages > self.crawler.max_pages:
                raise ConfigurationValidationError(
                    f"strategy.max_pages ({self.strategy.max_pages}) cannot exceed "
                    f"crawler.max_pages ({self.crawler.max_pages})",
                    config_key="strategy.max_pages"
                )
        
        # Validate extraction config
        if self.extraction.type not in ["css", "xpath", "llm", "auto"]:
            raise ConfigurationValidationError(
                f"extraction.type must be one of ['css', 'xpath', 'llm', 'auto'], "
                f"got: {self.extraction.type}",
                config_key="extraction.type"
            )
        
        # Validate engine config
        if self.engine.viewport_width < 320 or self.engine.viewport_width > 7680:
            raise ConfigurationValidationError(
                f"engine.viewport_width must be between 320 and 7680, got: {self.engine.viewport_width}",
                config_key="engine.viewport_width"
            )
        
        if self.engine.viewport_height < 240 or self.engine.viewport_height > 4320:
            raise ConfigurationValidationError(
                f"engine.viewport_height must be between 240 and 4320, got: {self.engine.viewport_height}",
                config_key="engine.viewport_height"
            )
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> "MainConfig":
        """
        Create MainConfig from dictionary with validation.
        
        Args:
            config_dict: Configuration dictionary
            
        Returns:
            Validated MainConfig instance
            
        Raises:
            ConfigurationValidationError: If validation fails
        """
        try:
            config = cls(**config_dict)
            config.validate_config()
            return config
        except Exception as e:
            # Import here to avoid circular dependencies
            try:
                from ..crawler.exceptions import ConfigurationValidationError
            except ImportError:
                # Fallback for absolute import if relative doesn't work
                from website_crawler.crawler.exceptions import ConfigurationValidationError
            
            if isinstance(e, ConfigurationValidationError):
                raise
            raise ConfigurationValidationError(
                f"Invalid configuration: {str(e)}",
                context={"original_error": str(e)}
            ) from e