"""
Time utilities for the website crawler.

This module provides utilities for time-related operations including delays,
rate limiting, timeouts, and retry logic.
"""
import random
import time
import signal
from contextlib import contextmanager
from functools import wraps
from typing import Callable, Any, Optional, Type, Tuple
from datetime import datetime, timedelta


def delay(seconds: float, jitter: float = 0.1) -> None:
    """
    Delay execution with optional jitter to avoid thundering herd.
    
    Args:
        seconds: Base delay in seconds
        jitter: Jitter factor (0.0 to 1.0). Actual delay will be
                seconds * (1 + random(-jitter, jitter))
    
    Example:
        >>> delay(1.0, jitter=0.1)  # Sleeps between 0.9 and 1.1 seconds
    """
    if jitter > 0:
        jitter_amount = random.uniform(-jitter, jitter)
        actual_delay = seconds * (1 + jitter_amount)
        actual_delay = max(0, actual_delay)  # Ensure non-negative
    else:
        actual_delay = seconds
    
    time.sleep(actual_delay)


class RateLimiter:
    """Rate limiter using token bucket algorithm."""
    
    def __init__(self, calls: int, period: float):
        """
        Initialize rate limiter.
        
        Args:
            calls: Maximum number of calls allowed
            period: Time period in seconds
        """
        self.calls = calls
        self.period = period
        self.tokens = calls
        self.last_update = time.time()
        self.lock = False
    
    def acquire(self) -> None:
        """Acquire a token, blocking if necessary."""
        current_time = time.time()
        elapsed = current_time - self.last_update
        
        # Refill tokens based on elapsed time
        if elapsed > 0:
            tokens_to_add = (elapsed / self.period) * self.calls
            self.tokens = min(self.calls, self.tokens + tokens_to_add)
            self.last_update = current_time
        
        # Wait if no tokens available
        if self.tokens < 1:
            wait_time = (1 - self.tokens) * (self.period / self.calls)
            time.sleep(wait_time)
            self.tokens = 0
            self.last_update = time.time()
        else:
            self.tokens -= 1


def rate_limit(calls: int, period: float):
    """
    Decorator for rate limiting function calls.
    
    Args:
        calls: Maximum number of calls allowed
        period: Time period in seconds
        
    Example:
        >>> @rate_limit(calls=10, period=1.0)
        ... def fetch_page(url):
        ...     return requests.get(url)
    """
    limiter = RateLimiter(calls, period)
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            limiter.acquire()
            return func(*args, **kwargs)
        return wrapper
    return decorator


class TimeoutError(Exception):
    """Raised when an operation times out."""
    pass


@contextmanager
def timeout_context(timeout: float):
    """
    Context manager for timeout operations.
    
    Note: Uses signal.SIGALRM which is Unix-only. On Windows, this will
    raise NotImplementedError. For cross-platform timeouts, consider using
    concurrent.futures with timeout parameter.
    
    Args:
        timeout: Timeout in seconds
        
    Raises:
        TimeoutError: If operation exceeds timeout
        NotImplementedError: On Windows (SIGALRM not available)
        
    Example:
        >>> with timeout_context(5.0):
        ...     long_running_operation()
    """
    if not hasattr(signal, 'SIGALRM'):
        raise NotImplementedError(
            "timeout_context requires signal.SIGALRM which is not available on Windows. "
            "Consider using concurrent.futures.ThreadPoolExecutor with timeout parameter."
        )
    
    def timeout_handler(signum, frame):
        raise TimeoutError(f"Operation timed out after {timeout} seconds")
    
    # Set up signal handler (Unix only)
    old_handler = signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(int(timeout))
    
    try:
        yield
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, old_handler)


def retry(
    max_attempts: int = 3,
    backoff: float = 1.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        backoff: Base backoff time in seconds
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function called on each retry
                 (receives exception and attempt number)
        
    Example:
        >>> @retry(max_attempts=3, backoff=2.0)
        ... def fetch_data():
        ...     return requests.get("https://example.com")
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_attempts:
                        # Calculate exponential backoff
                        wait_time = backoff * (2 ** (attempt - 1))
                        
                        if on_retry:
                            on_retry(e, attempt)
                        
                        time.sleep(wait_time)
                    else:
                        # Last attempt failed
                        raise
            
            # Should never reach here, but just in case
            if last_exception:
                raise last_exception
            
        return wrapper
    return decorator


def format_timestamp(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format timestamp to string.
    
    Args:
        dt: Datetime object (defaults to current time)
        format_str: Format string
        
    Returns:
        Formatted timestamp string
        
    Example:
        >>> format_timestamp()
        '2024-01-01 12:00:00'
    """
    if dt is None:
        dt = datetime.now()
    return dt.strftime(format_str)


def parse_timestamp(timestamp_str: str, format_str: str = "%Y-%m-%d %H:%M:%S") -> datetime:
    """
    Parse timestamp string to datetime object.
    
    Args:
        timestamp_str: Timestamp string
        format_str: Format string
        
    Returns:
        Datetime object
        
    Example:
        >>> parse_timestamp("2024-01-01 12:00:00")
        datetime(2024, 1, 1, 12, 0, 0)
    """
    return datetime.strptime(timestamp_str, format_str)


def get_elapsed_time(start_time: datetime) -> timedelta:
    """
    Get elapsed time since start time.
    
    Args:
        start_time: Start datetime
        
    Returns:
        Elapsed time as timedelta
        
    Example:
        >>> start = datetime.now()
        >>> # ... do work ...
        >>> elapsed = get_elapsed_time(start)
    """
    return datetime.now() - start_time


def format_duration(seconds: float) -> str:
    """
    Format duration in seconds to human-readable string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted duration string
        
    Example:
        >>> format_duration(3661)
        '1h 1m 1s'
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if hours > 0:
        parts.append(f"{hours}h")
    if minutes > 0:
        parts.append(f"{minutes}m")
    if secs > 0 or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)
