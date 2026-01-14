"""
Performance configuration for the website crawler.

This module provides settings for timeouts, retries, rate limiting, and concurrency.
"""
import asyncio
import time
from typing import Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict
import logging

from ..exceptions import CrawlerException


logger = logging.getLogger(__name__)


class PerformanceError(CrawlerException):
    """Performance-related errors."""
    pass


@dataclass
class PerformanceConfig:
    """
    Configuration for performance-related settings.
    
    Attributes:
        request_timeout: Request timeout in seconds
        page_load_timeout: Page load timeout in seconds
        max_retries: Maximum number of retry attempts
        retry_delay: Base retry delay in seconds
        retry_backoff_factor: Exponential backoff factor
        rate_limit: Global rate limit (requests per second)
        per_domain_rate_limit: Per-domain rate limit (requests per second)
        concurrent_requests: Maximum concurrent requests
        respect_crawl_delay: Whether to respect robots.txt crawl-delay
    """
    request_timeout: int = 30
    page_load_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    retry_backoff_factor: float = 2.0
    rate_limit: Optional[float] = None  # requests per second
    per_domain_rate_limit: Optional[float] = None  # requests per second per domain
    concurrent_requests: int = 10
    respect_crawl_delay: bool = True
    
    def validate(self) -> bool:
        """
        Validate configuration values.
        
        Returns:
            True if valid
            
        Raises:
            PerformanceError: If validation fails
        """
        if self.request_timeout < 1:
            raise PerformanceError("request_timeout must be >= 1 second")
        if self.page_load_timeout < 1:
            raise PerformanceError("page_load_timeout must be >= 1 second")
        if self.max_retries < 0:
            raise PerformanceError("max_retries must be >= 0")
        if self.retry_delay < 0:
            raise PerformanceError("retry_delay must be >= 0")
        if self.retry_backoff_factor < 1:
            raise PerformanceError("retry_backoff_factor must be >= 1")
        if self.rate_limit is not None and self.rate_limit <= 0:
            raise PerformanceError("rate_limit must be > 0 if specified")
        if self.per_domain_rate_limit is not None and self.per_domain_rate_limit <= 0:
            raise PerformanceError("per_domain_rate_limit must be > 0 if specified")
        if self.concurrent_requests < 1:
            raise PerformanceError("concurrent_requests must be >= 1")
        
        return True
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "PerformanceConfig":
        """
        Create PerformanceConfig from configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            PerformanceConfig instance
        """
        return cls(
            request_timeout=config.get('request_timeout', 30),
            page_load_timeout=config.get('page_load_timeout', 30),
            max_retries=config.get('max_retries', 3),
            retry_delay=config.get('retry_delay', 1.0),
            retry_backoff_factor=config.get('retry_backoff_factor', 2.0),
            rate_limit=config.get('rate_limit'),
            per_domain_rate_limit=config.get('per_domain_rate_limit'),
            concurrent_requests=config.get('concurrent_requests', 10),
            respect_crawl_delay=config.get('respect_crawl_delay', True)
        )
    
    @classmethod
    def default(cls) -> "PerformanceConfig":
        """
        Create default PerformanceConfig.
        
        Returns:
            Default PerformanceConfig instance
        """
        return cls()


class RateLimiter:
    """
    Rate limiter for controlling request frequency.
    
    Supports both global and per-domain rate limiting.
    """
    
    def __init__(self, config: PerformanceConfig):
        """
        Initialize rate limiter.
        
        Args:
            config: Performance configuration
        """
        self.config = config
        self.global_last_request: Optional[datetime] = None
        self.domain_last_request: Dict[str, datetime] = {}
        self.domain_crawl_delay: Dict[str, float] = {}  # From robots.txt
        self._lock = asyncio.Lock()
    
    async def wait_if_needed(self, domain: Optional[str] = None) -> None:
        """
        Wait if necessary to respect rate limits.
        
        Args:
            domain: Optional domain for per-domain rate limiting
        """
        async with self._lock:
            now = datetime.utcnow()
            
            # Global rate limiting
            if self.config.rate_limit:
                min_interval = 1.0 / self.config.rate_limit
                if self.global_last_request:
                    elapsed = (now - self.global_last_request).total_seconds()
                    if elapsed < min_interval:
                        wait_time = min_interval - elapsed
                        await asyncio.sleep(wait_time)
                        now = datetime.utcnow()
                self.global_last_request = now
            
            # Per-domain rate limiting
            if domain and self.config.per_domain_rate_limit:
                min_interval = 1.0 / self.config.per_domain_rate_limit
                last_request = self.domain_last_request.get(domain)
                if last_request:
                    elapsed = (now - last_request).total_seconds()
                    if elapsed < min_interval:
                        wait_time = min_interval - elapsed
                        await asyncio.sleep(wait_time)
                        now = datetime.utcnow()
                self.domain_last_request[domain] = now
            
            # Robots.txt crawl-delay
            if domain and self.config.respect_crawl_delay:
                crawl_delay = self.domain_crawl_delay.get(domain)
                if crawl_delay:
                    last_request = self.domain_last_request.get(domain)
                    if last_request:
                        elapsed = (now - last_request).total_seconds()
                        if elapsed < crawl_delay:
                            wait_time = crawl_delay - elapsed
                            await asyncio.sleep(wait_time)
    
    def set_crawl_delay(self, domain: str, delay: float) -> None:
        """
        Set crawl delay for a domain (from robots.txt).
        
        Args:
            domain: Domain name
            delay: Crawl delay in seconds
        """
        self.domain_crawl_delay[domain] = delay


class RetryHandler:
    """
    Handler for retry logic with exponential backoff.
    """
    
    def __init__(self, config: PerformanceConfig):
        """
        Initialize retry handler.
        
        Args:
            config: Performance configuration
        """
        self.config = config
    
    def should_retry(self, attempt: int, error: Exception) -> bool:
        """
        Determine if a request should be retried.
        
        Args:
            attempt: Current attempt number (0-indexed)
            error: The exception that occurred
            
        Returns:
            True if should retry, False otherwise
        """
        if attempt >= self.config.max_retries:
            return False
        
        # Don't retry on 4xx errors (except 429 - Too Many Requests)
        if hasattr(error, 'status_code'):
            status = error.status_code
            if 400 <= status < 500 and status != 429:
                return False
        
        # Retry on timeouts, network errors, and 5xx errors
        error_type = type(error).__name__
        retryable_errors = [
            'TimeoutError',
            'asyncio.TimeoutError',
            'ConnectionError',
            'CrawlTimeoutError',
            'CrawlFailedError',
        ]
        
        if any(err in error_type for err in retryable_errors):
            return True
        
        # Retry on 429 (Too Many Requests) and 5xx errors
        if hasattr(error, 'status_code'):
            status = error.status_code
            if status == 429 or (500 <= status < 600):
                return True
        
        return False
    
    def get_retry_delay(self, attempt: int) -> float:
        """
        Calculate retry delay with exponential backoff.
        
        Args:
            attempt: Current attempt number (0-indexed)
            
        Returns:
            Delay in seconds
        """
        delay = self.config.retry_delay * (self.config.retry_backoff_factor ** attempt)
        # Add small random jitter to avoid thundering herd
        import random
        jitter = random.uniform(0, delay * 0.1)  # Up to 10% jitter
        return delay + jitter
    
    async def retry_with_backoff(
        self,
        func,
        *args,
        url: Optional[str] = None,
        **kwargs
    ) -> Any:
        """
        Execute a function with retry logic and exponential backoff.
        
        Args:
            func: Async function to execute
            *args: Positional arguments for func
            url: Optional URL for logging
            **kwargs: Keyword arguments for func
            
        Returns:
            Result of func
            
        Raises:
            Exception: If all retries are exhausted
        """
        last_error = None
        
        for attempt in range(self.config.max_retries + 1):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                if not self.should_retry(attempt, e):
                    logger.debug(
                        f"Not retrying {url or 'request'} after attempt {attempt + 1}: {type(e).__name__}"
                    )
                    raise
                
                if attempt < self.config.max_retries:
                    delay = self.get_retry_delay(attempt)
                    logger.info(
                        f"Retrying {url or 'request'} after {delay:.2f}s "
                        f"(attempt {attempt + 1}/{self.config.max_retries + 1}): {type(e).__name__}"
                    )
                    await asyncio.sleep(delay)
        
        # All retries exhausted
        logger.error(
            f"All retries exhausted for {url or 'request'} after {self.config.max_retries + 1} attempts"
        )
        raise last_error


class ConcurrentRequestLimiter:
    """
    Limiter for concurrent requests using semaphore.
    """
    
    def __init__(self, max_concurrent: int):
        """
        Initialize concurrent request limiter.
        
        Args:
            max_concurrent: Maximum concurrent requests
        """
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.active_count = 0
    
    async def acquire(self) -> None:
        """Acquire a slot for a concurrent request."""
        await self.semaphore.acquire()
        self.active_count += 1
    
    def release(self) -> None:
        """Release a slot for a concurrent request."""
        self.semaphore.release()
        self.active_count -= 1
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.acquire()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        self.release()
