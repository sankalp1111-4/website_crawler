"""
Utility functions for the website crawler.

This package provides utility functions for hashing, time operations, and logging.
"""

# Logging utilities
from .logging_config import (
    setup_logging,
    get_logger,
    configure_logger_from_config,
    get_crawler_logger,
    get_storage_logger,
    get_engine_logger,
    get_extraction_logger,
    JSONFormatter,
    StructuredFormatter,
)

# Hashing utilities
from .hashing import (
    hash_url,
    hash_content,
    hash_bytes,
    generate_document_id,
    consistent_hash,
)

# Time utilities
from .time import (
    delay,
    rate_limit,
    RateLimiter,
    timeout_context,
    retry,
    TimeoutError,
    format_timestamp,
    parse_timestamp,
    get_elapsed_time,
    format_duration,
)

__all__ = [
    # Logging
    "setup_logging",
    "get_logger",
    "configure_logger_from_config",
    "get_crawler_logger",
    "get_storage_logger",
    "get_engine_logger",
    "get_extraction_logger",
    "JSONFormatter",
    "StructuredFormatter",
    # Hashing
    "hash_url",
    "hash_content",
    "hash_bytes",
    "generate_document_id",
    "consistent_hash",
    # Time
    "delay",
    "rate_limit",
    "RateLimiter",
    "timeout_context",
    "retry",
    "TimeoutError",
    "format_timestamp",
    "parse_timestamp",
    "get_elapsed_time",
    "format_duration",
]
