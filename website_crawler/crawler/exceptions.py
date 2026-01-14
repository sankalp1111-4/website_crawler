"""
Custom exceptions for the website crawler.

This module defines custom exception classes for different error scenarios
in the crawling process.
"""
from datetime import datetime
from typing import Optional, Dict, Any


class CrawlerException(Exception):
    """
    Base exception for all crawler-related errors.
    
    Provides common functionality for error context and error codes.
    """
    
    # Error code constants
    ERROR_CODE_UNKNOWN = "UNKNOWN"
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize exception.
        
        Args:
            message: Error message
            error_code: Optional error code for programmatic handling
            context: Optional context dictionary with additional error information
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.ERROR_CODE_UNKNOWN
        self.context = context or {}
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for logging/serialization.
        
        Returns:
            Dictionary representation of the exception
        """
        return {
            "error_type": type(self).__name__,
            "error_code": self.error_code,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "context": self.context
        }
    
    def __str__(self) -> str:
        """String representation of the exception."""
        if self.context:
            context_str = ", ".join(f"{k}={v}" for k, v in self.context.items())
            return f"{self.message} [{self.error_code}] ({context_str})"
        return f"{self.message} [{self.error_code}]"


class CrawlError(CrawlerException):
    """General crawling errors."""
    
    ERROR_CODE_CRAWL_FAILED = "CRAWL_FAILED"
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize crawl error.
        
        Args:
            message: Error message
            url: Optional URL that caused the error
            error_code: Optional error code
            context: Optional context dictionary
        """
        context = context or {}
        if url:
            context['url'] = url
        
        super().__init__(
            message,
            error_code=error_code or self.ERROR_CODE_CRAWL_FAILED,
            context=context
        )
        self.url = url
        
        if url:
            self.message = f"Crawl error for URL {url}: {message}"
        else:
            self.message = message


class CrawlTimeoutError(CrawlError):
    """Timeout during crawling."""
    
    ERROR_CODE_TIMEOUT = "CRAWL_TIMEOUT"
    
    def __init__(
        self,
        message: str = "Crawl operation timed out",
        url: Optional[str] = None,
        timeout: Optional[float] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize timeout error.
        
        Args:
            message: Error message
            url: Optional URL that timed out
            timeout: Optional timeout value in seconds
            error_code: Optional error code
            context: Optional context dictionary
        """
        context = context or {}
        if timeout is not None:
            context['timeout'] = timeout
        
        super().__init__(
            message,
            url=url,
            error_code=error_code or self.ERROR_CODE_TIMEOUT,
            context=context
        )
        self.timeout = timeout
        
        if timeout and url:
            self.message = f"Crawl timeout after {timeout}s for URL {url}: {message}"
        elif timeout:
            self.message = f"Crawl timeout after {timeout}s: {message}"
        elif url:
            self.message = f"Crawl timeout for URL {url}: {message}"


class CrawlFailedError(CrawlError):
    """Failed to crawl a URL."""
    
    ERROR_CODE_CRAWL_FAILED = "CRAWL_FAILED"
    
    def __init__(
        self,
        message: str = "Failed to crawl URL",
        url: Optional[str] = None,
        status_code: Optional[int] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize crawl failed error.
        
        Args:
            message: Error message
            url: Optional URL that failed
            status_code: Optional HTTP status code
            error_code: Optional error code
            context: Optional context dictionary
        """
        context = context or {}
        if status_code is not None:
            context['status_code'] = status_code
        
        super().__init__(
            message,
            url=url,
            error_code=error_code or self.ERROR_CODE_CRAWL_FAILED,
            context=context
        )
        self.status_code = status_code


class NetworkError(CrawlError):
    """Network-related errors."""
    
    ERROR_CODE_NETWORK = "NETWORK_ERROR"
    
    def __init__(
        self,
        message: str = "Network error occurred",
        url: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            url=url,
            error_code=error_code or self.ERROR_CODE_NETWORK,
            context=context
        )


class StorageError(CrawlerException):
    """Storage-related errors."""
    
    ERROR_CODE_STORAGE = "STORAGE_ERROR"
    
    def __init__(
        self,
        message: str,
        document_id: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize storage error.
        
        Args:
            message: Error message
            document_id: Optional document ID
            error_code: Optional error code
            context: Optional context dictionary
        """
        context = context or {}
        if document_id:
            context['document_id'] = document_id
        
        super().__init__(
            message,
            error_code=error_code or self.ERROR_CODE_STORAGE,
            context=context
        )
        self.document_id = document_id
        
        if document_id:
            self.message = f"Storage error for document {document_id}: {message}"
        else:
            self.message = message


class StorageConnectionError(StorageError):
    """Cannot connect to storage."""
    
    ERROR_CODE_STORAGE_CONNECTION = "STORAGE_CONNECTION_ERROR"
    
    def __init__(
        self,
        message: str = "Cannot connect to storage",
        connection_string: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize storage connection error.
        
        Args:
            message: Error message
            connection_string: Optional connection string
            error_code: Optional error code
            context: Optional context dictionary
        """
        context = context or {}
        if connection_string:
            # Don't include full connection string in context for security
            context['has_connection_string'] = True
        
        super().__init__(
            message,
            error_code=error_code or self.ERROR_CODE_STORAGE_CONNECTION,
            context=context
        )
        self.connection_string = connection_string
        
        if connection_string:
            # Mask sensitive parts of connection string
            masked = self._mask_connection_string(connection_string)
            self.message = f"Cannot connect to storage at {masked}: {message}"
        else:
            self.message = message
    
    @staticmethod
    def _mask_connection_string(conn_str: str) -> str:
        """Mask sensitive parts of connection string."""
        if '@' in conn_str:
            # Mask credentials
            parts = conn_str.split('@')
            if len(parts) == 2:
                return f"***@{parts[1]}"
        return conn_str


class StorageSaveError(StorageError):
    """Failed to save document."""
    
    ERROR_CODE_STORAGE_SAVE = "STORAGE_SAVE_ERROR"
    
    def __init__(
        self,
        message: str = "Failed to save document",
        document_id: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            document_id=document_id,
            error_code=error_code or self.ERROR_CODE_STORAGE_SAVE,
            context=context
        )


class ValidationError(CrawlerException):
    """Validation errors."""
    
    ERROR_CODE_VALIDATION = "VALIDATION_ERROR"
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize validation error.
        
        Args:
            message: Error message
            field: Optional field name that failed validation
            error_code: Optional error code
            context: Optional context dictionary
        """
        context = context or {}
        if field:
            context['field'] = field
        
        super().__init__(
            message,
            error_code=error_code or self.ERROR_CODE_VALIDATION,
            context=context
        )
        self.field = field


class InvalidURLError(ValidationError):
    """Invalid URL format."""
    
    ERROR_CODE_INVALID_URL = "INVALID_URL"
    
    def __init__(
        self,
        message: str = "Invalid URL format",
        url: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize invalid URL error.
        
        Args:
            message: Error message
            url: Optional invalid URL
            error_code: Optional error code
            context: Optional context dictionary
        """
        context = context or {}
        if url:
            context['url'] = url
        
        super().__init__(
            message,
            field='url',
            error_code=error_code or self.ERROR_CODE_INVALID_URL,
            context=context
        )
        self.url = url
        
        if url:
            self.message = f"Invalid URL {url}: {message}"
        else:
            self.message = message


class ConfigurationError(CrawlerException):
    """Configuration-related errors."""
    
    ERROR_CODE_CONFIG = "CONFIGURATION_ERROR"
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize configuration error.
        
        Args:
            message: Error message
            config_key: Optional configuration key that caused the error
            error_code: Optional error code
            context: Optional context dictionary
        """
        context = context or {}
        if config_key:
            context['config_key'] = config_key
        
        super().__init__(
            message,
            error_code=error_code or self.ERROR_CODE_CONFIG,
            context=context
        )
        self.config_key = config_key


class ConfigurationValidationError(ConfigurationError):
    """Configuration validation errors."""
    
    ERROR_CODE_CONFIG_VALIDATION = "CONFIG_VALIDATION_ERROR"
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            message,
            config_key=config_key,
            error_code=error_code or self.ERROR_CODE_CONFIG_VALIDATION,
            context=context
        )


class ExtractionError(CrawlerException):
    """Content extraction errors."""
    
    ERROR_CODE_EXTRACTION = "EXTRACTION_ERROR"
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        extractor_type: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize extraction error.
        
        Args:
            message: Error message
            url: Optional URL being extracted
            extractor_type: Optional extractor type
            error_code: Optional error code
            context: Optional context dictionary
        """
        context = context or {}
        if url:
            context['url'] = url
        if extractor_type:
            context['extractor_type'] = extractor_type
        
        super().__init__(
            message,
            error_code=error_code or self.ERROR_CODE_EXTRACTION,
            context=context
        )
        self.url = url
        self.extractor_type = extractor_type


class ExtractionTimeoutError(ExtractionError):
    """Extraction timeout errors."""
    
    ERROR_CODE_EXTRACTION_TIMEOUT = "EXTRACTION_TIMEOUT"
    
    def __init__(
        self,
        message: str = "Extraction operation timed out",
        url: Optional[str] = None,
        extractor_type: Optional[str] = None,
        timeout: Optional[float] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        context = context or {}
        if timeout is not None:
            context['timeout'] = timeout
        
        super().__init__(
            message,
            url=url,
            extractor_type=extractor_type,
            error_code=error_code or self.ERROR_CODE_EXTRACTION_TIMEOUT,
            context=context
        )
        self.timeout = timeout


class ParsingError(CrawlerException):
    """HTML/XML parsing errors."""
    
    ERROR_CODE_PARSING = "PARSING_ERROR"
    
    def __init__(
        self,
        message: str,
        url: Optional[str] = None,
        parser_type: Optional[str] = None,
        error_code: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize parsing error.
        
        Args:
            message: Error message
            url: Optional URL being parsed
            parser_type: Optional parser type
            error_code: Optional error code
            context: Optional context dictionary
        """
        context = context or {}
        if url:
            context['url'] = url
        if parser_type:
            context['parser_type'] = parser_type
        
        super().__init__(
            message,
            error_code=error_code or self.ERROR_CODE_PARSING,
            context=context
        )
        self.url = url
        self.parser_type = parser_type
