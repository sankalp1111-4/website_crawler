"""
Custom exceptions for the website crawler.

This module defines custom exception classes for different error scenarios
in the crawling process.
"""


class CrawlerException(Exception):
    """Base exception for all crawler-related errors."""
    pass


class CrawlError(CrawlerException):
    """General crawling errors."""
    def __init__(self, message: str, url: str = None):
        super().__init__(message)
        self.url = url
        if url:
            self.message = f"Crawl error for URL {url}: {message}"
        else:
            self.message = message


class CrawlTimeoutError(CrawlError):
    """Timeout during crawling."""
    def __init__(self, message: str = "Crawl operation timed out", url: str = None, timeout: float = None):
        super().__init__(message, url)
        self.timeout = timeout
        if timeout:
            self.message = f"Crawl timeout after {timeout}s for URL {url}: {message}" if url else f"Crawl timeout after {timeout}s: {message}"


class CrawlFailedError(CrawlError):
    """Failed to crawl a URL."""
    def __init__(self, message: str = "Failed to crawl URL", url: str = None):
        super().__init__(message, url)


class StorageError(CrawlerException):
    """Storage-related errors."""
    def __init__(self, message: str, document_id: str = None):
        super().__init__(message)
        self.document_id = document_id
        if document_id:
            self.message = f"Storage error for document {document_id}: {message}"
        else:
            self.message = message


class StorageConnectionError(StorageError):
    """Cannot connect to storage."""
    def __init__(self, message: str = "Cannot connect to storage", connection_string: str = None):
        super().__init__(message)
        self.connection_string = connection_string
        if connection_string:
            self.message = f"Cannot connect to storage at {connection_string}: {message}"


class StorageSaveError(StorageError):
    """Failed to save document."""
    def __init__(self, message: str = "Failed to save document", document_id: str = None):
        super().__init__(message, document_id)


class ValidationError(CrawlerException):
    """Validation errors."""
    pass


class InvalidURLError(ValidationError):
    """Invalid URL format."""
    def __init__(self, message: str = "Invalid URL format", url: str = None):
        super().__init__(message)
        self.url = url
        if url:
            self.message = f"Invalid URL {url}: {message}"
        else:
            self.message = message