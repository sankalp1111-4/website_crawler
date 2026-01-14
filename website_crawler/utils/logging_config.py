"""
Logging configuration for the website crawler.

This module provides centralized logging setup and configuration.
"""
import json
import logging
import logging.handlers
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        return json.dumps(log_data)


class StructuredFormatter(logging.Formatter):
    """Human-readable structured formatter for development."""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )


def setup_logging(
    level: str = "INFO",
    format_type: str = "json",
    log_file: Optional[str] = None,
    console_enabled: bool = True,
    file_enabled: bool = False,
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    correlation_id: Optional[str] = None
) -> None:
    """
    Set up logging configuration for the crawler.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Format type - "json" for structured JSON, "text" for readable
        log_file: Optional file path to write logs to
        console_enabled: Whether to enable console logging
        file_enabled: Whether to enable file logging
        max_bytes: Maximum size of log file before rotation
        backup_count: Number of backup log files to keep
        correlation_id: Optional correlation ID for request tracking
    
    Example:
        >>> setup_logging(level="DEBUG", log_file="crawler.log", format_type="json")
    """
    # Convert string level to logging constant
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Choose formatter based on format type
    if format_type.lower() == "json":
        formatter = JSONFormatter()
    else:
        formatter = StructuredFormatter()
    
    # Console handler
    if console_enabled:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # File handler with rotation
    if file_enabled and log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8"
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Add correlation ID to all log records if provided
    if correlation_id:
        old_factory = logging.getLogRecordFactory()
        
        def record_factory(*args, **kwargs):
            record = old_factory(*args, **kwargs)
            record.correlation_id = correlation_id
            return record
        
        logging.setLogRecordFactory(record_factory)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Configured logger instance
    
    Example:
        >>> logger = get_logger(__name__)
        >>> logger.info("Starting crawler")
    """
    return logging.getLogger(name)


def configure_logger_from_config(config: Dict[str, Any]) -> None:
    """
    Configure logging from a configuration dictionary.
    
    Args:
        config: Configuration dictionary with logging settings
    """
    logging_config = config.get("logging", {})
    
    setup_logging(
        level=logging_config.get("level", "INFO"),
        format_type=logging_config.get("format", "json"),
        log_file=logging_config.get("file_path"),
        console_enabled=logging_config.get("console_enabled", True),
        file_enabled=logging_config.get("file_enabled", False),
        max_bytes=logging_config.get("max_bytes", 10 * 1024 * 1024),
        backup_count=logging_config.get("backup_count", 5),
    )


# Module-specific loggers
def get_crawler_logger() -> logging.Logger:
    """Get logger for crawler module."""
    return get_logger("website_crawler.crawler")


def get_storage_logger() -> logging.Logger:
    """Get logger for storage module."""
    return get_logger("website_crawler.storage")


def get_engine_logger() -> logging.Logger:
    """Get logger for engine module."""
    return get_logger("website_crawler.engine")


def get_extraction_logger() -> logging.Logger:
    """Get logger for extraction module."""
    return get_logger("website_crawler.extraction")
