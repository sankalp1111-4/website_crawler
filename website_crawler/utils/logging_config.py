"""
Logging configuration for the website crawler.

This module provides centralized logging setup and configuration.
"""
import json
import logging
import logging.handlers
import os
import sys
import time
import uuid
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from datetime import datetime
from contextlib import contextmanager
from collections import defaultdict


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
        
        # Add component if present
        if hasattr(record, "component"):
            log_data["component"] = record.component
        else:
            # Derive from logger name
            log_data["component"] = record.name.split('.')[-1]
        
        # Add flow information if present
        if hasattr(record, "flow"):
            log_data["flow"] = record.flow
        
        # Add correlation ID if present
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        
        # Add request ID if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add URL if present
        if hasattr(record, "url"):
            log_data["url"] = record.url
        
        # Add performance metrics if present
        if hasattr(record, "duration"):
            log_data["duration"] = record.duration
        if hasattr(record, "duration_ms"):
            log_data["duration_ms"] = record.duration_ms
        
        # Add method if present (from flow logging)
        if hasattr(record, "method"):
            log_data["method"] = record.method
        
        # Add inputs/outputs if present
        if hasattr(record, "inputs"):
            log_data["inputs"] = record.inputs
        if hasattr(record, "outputs"):
            log_data["outputs"] = record.outputs
        
        # Add decision/state change info if present
        if hasattr(record, "decision"):
            log_data["decision"] = record.decision
        if hasattr(record, "reason"):
            log_data["reason"] = record.reason
        if hasattr(record, "from_state"):
            log_data["from_state"] = record.from_state
        if hasattr(record, "to_state"):
            log_data["to_state"] = record.to_state
        if hasattr(record, "transformation"):
            log_data["transformation"] = record.transformation
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)
        
        # Add any other custom attributes
        excluded_keys = [
            "name", "msg", "args", "created", "filename", "funcName",
            "levelname", "levelno", "lineno", "module", "msecs",
            "message", "pathname", "process", "processName", "relativeCreated",
            "thread", "threadName", "exc_info", "exc_text", "stack_info",
            "correlation_id", "request_id", "url", "duration", "duration_ms", "extra_fields",
            "component", "flow", "method", "inputs", "outputs", "decision", "reason",
            "from_state", "to_state", "transformation"
        ]
        for key, value in record.__dict__.items():
            if key not in excluded_keys:
                if not key.startswith("_"):
                    log_data[key] = value
        
        return json.dumps(log_data)


class StructuredFormatter(logging.Formatter):
    """Human-readable structured formatter for development."""
    
    def __init__(self):
        super().__init__(
            fmt="%(asctime)s | %(levelname)-8s | %(component)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with component information."""
        # Add component to record if not present
        if not hasattr(record, 'component'):
            # Try to extract from logger name
            record.component = record.name.split('.')[-1]
        return super().format(record)


class SimpleFormatter(logging.Formatter):
    """Simple formatter that outputs only the message - no timestamps, no metadata."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as simple message only."""
        return record.getMessage()


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
    elif format_type.lower() == "simple":
        formatter = SimpleFormatter()
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


class ComponentLoggerAdapter(logging.LoggerAdapter):
    """
    Enhanced logger adapter for component-aware, flow-wise, state-change logging.
    
    Automatically includes component name, tracks flow, and logs state changes.
    """
    
    def __init__(
        self,
        logger: logging.Logger,
        component: str,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize component logger adapter.
        
        Args:
            logger: Base logger instance
            component: Component name (e.g., "Orchestrator", "CrawlEngine", "URLFilter")
            context: Optional context dictionary
        """
        super().__init__(logger, context or {})
        self.component = component
        # Add component to context
        if self.extra is None:
            self.extra = {}
        self.extra['component'] = component
    
    def process(self, msg, kwargs):
        """Process log message and add context."""
        # Add context to extra
        extra = kwargs.get('extra', {})
        if self.extra:
            extra.update(self.extra)
        # Ensure component is always included
        extra['component'] = self.component
        kwargs['extra'] = extra
        return msg, kwargs
    
    def with_url(self, url: str) -> "ComponentLoggerAdapter":
        """
        Create a new adapter with URL context.
        
        Args:
            url: URL to add to context
            
        Returns:
            New ComponentLoggerAdapter with URL context
        """
        new_context = self.extra.copy() if self.extra else {}
        new_context['url'] = url
        return ComponentLoggerAdapter(self.logger, self.component, new_context)
    
    def with_request_id(self, request_id: str) -> "ComponentLoggerAdapter":
        """
        Create a new adapter with request ID context.
        
        Args:
            request_id: Request ID to add to context
            
        Returns:
            New ComponentLoggerAdapter with request ID context
        """
        new_context = self.extra.copy() if self.extra else {}
        new_context['request_id'] = request_id
        return ComponentLoggerAdapter(self.logger, self.component, new_context)
    
    def with_correlation_id(self, correlation_id: str) -> "ComponentLoggerAdapter":
        """
        Create a new adapter with correlation ID context.
        
        Args:
            correlation_id: Correlation ID to add to context
            
        Returns:
            New ComponentLoggerAdapter with correlation ID context
        """
        new_context = self.extra.copy() if self.extra else {}
        new_context['correlation_id'] = correlation_id
        return ComponentLoggerAdapter(self.logger, self.component, new_context)
    
    def log_entry(self, method: str, **inputs) -> None:
        """
        Log component method entry with inputs.
        
        Args:
            method: Method name being called
            **inputs: Input parameters to log
        """
        # Simple format: [Component] START method
        self.info(
            f"[{self.component}] START {method}",
            extra={'flow': 'entry', 'method': method, 'inputs': inputs}
        )
    
    def log_exit(self, method: str, **outputs) -> None:
        """
        Log component method exit with outputs.
        
        Args:
            method: Method name that completed
            **outputs: Output values to log
        """
        # Simple format: [Component] END method (status, duration)
        status = outputs.get('status', 'completed')
        duration = outputs.get('duration')
        if duration:
            duration_str = f"{duration:.2f}s"
            self.info(
                f"[{self.component}] END {method} ({status}, {duration_str})",
                extra={'flow': 'exit', 'method': method, 'outputs': outputs}
            )
        else:
            self.info(
                f"[{self.component}] END {method} ({status})",
                extra={'flow': 'exit', 'method': method, 'outputs': outputs}
            )
    
    def log_decision(self, decision: str, reason: Optional[str] = None, **context) -> None:
        """
        Log a decision made by the component.
        
        Args:
            decision: The decision made (e.g., "URL_ALLOWED", "RETRY_NEEDED")
            reason: Optional reason for the decision
            **context: Additional context about the decision
        """
        # Simple format: [Component] Decision ✓
        # Convert decision to readable format
        readable_decision = decision.replace('_', ' ').title()
        msg = f"[{self.component}] {readable_decision} ✓"
        self.info(
            msg,
            extra={'flow': 'decision', 'decision': decision, 'reason': reason, **context}
        )
    
    def log_state_change(self, from_state: str, to_state: str, **context) -> None:
        """
        Log a state change.
        
        Args:
            from_state: Previous state
            to_state: New state
            **context: Additional context about the state change
        """
        self.info(
            f"[{self.component}] {from_state} → {to_state}",
            extra={
                'flow': 'state_change',
                'from_state': from_state,
                'to_state': to_state,
                **context
            }
        )
    
    def log_transformation(self, transformation: str, input_value: Any, output_value: Any, **context) -> None:
        """
        Log a transformation performed by the component.
        
        Args:
            transformation: Description of the transformation
            input_value: Input value
            output_value: Output value
            **context: Additional context
        """
        self.info(
            f"[{self.component}] {transformation}: {input_value!r} → {output_value!r}",
            extra={
                'flow': 'transformation',
                'transformation': transformation,
                'input': str(input_value),
                'output': str(output_value),
                **context
            }
        )
    
    def log_performance(
        self,
        operation: str,
        duration: float,
        level: int = logging.INFO,
        **kwargs
    ) -> None:
        """
        Log performance metrics.
        
        Args:
            operation: Name of the operation
            duration: Duration in seconds
            level: Log level
            **kwargs: Additional context
        """
        extra = self.extra.copy() if self.extra else {}
        extra.update({
            'duration': duration,
            'duration_ms': duration * 1000,
            'operation': operation,
            'flow': 'performance',
        })
        extra.update(kwargs)
        
        # Simple format: [Component] END operation (success, duration)
        status = kwargs.get('status', 'success')
        duration_str = f"{duration:.2f}s"
        self.log(
            level,
            f"[{self.component}] END {operation} ({status}, {duration_str})",
            extra=extra
        )
    
    @contextmanager
    def component_flow(self, method: str, **inputs):
        """
        Context manager for component method flow logging (entry/exit).
        
        Args:
            method: Method name
            **inputs: Input parameters
            
        Example:
            >>> with logger.component_flow("crawl_url", url=url):
            ...     # do work
            ...     return result
        """
        self.log_entry(method, **inputs)
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.log_exit(method, status='success', duration=duration)
    
    @contextmanager
    def performance_log(self, operation: str, **kwargs):
        """
        Context manager for performance logging.
        
        Args:
            operation: Name of the operation
            **kwargs: Additional context
            
        Example:
            >>> with logger.performance_log("crawl_url", url=url):
            ...     # do work
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.log_performance(operation, duration, **kwargs)


class ContextualLoggerAdapter(ComponentLoggerAdapter):
    """
    Backward compatibility alias for ComponentLoggerAdapter.
    
    Deprecated: Use ComponentLoggerAdapter instead.
    """
    def __init__(self, logger: logging.Logger, context: Optional[Dict[str, Any]] = None):
        # Extract component from context if provided, otherwise use logger name
        component = context.get('component', logger.name.split('.')[-1]) if context else logger.name.split('.')[-1]
        super().__init__(logger, component, context)


def get_contextual_logger(name: str, context: Optional[Dict[str, Any]] = None) -> ComponentLoggerAdapter:
    """
    Get a contextual logger adapter.
    
    Args:
        name: Logger name
        context: Optional initial context
        
    Returns:
        ComponentLoggerAdapter instance
    """
    # Extract component from context or derive from name
    component = context.get('component', name.split('.')[-1]) if context else name.split('.')[-1]
    return ComponentLoggerAdapter(get_logger(name), component, context)


def get_component_logger(component: str, module_name: Optional[str] = None) -> ComponentLoggerAdapter:
    """
    Get a component-aware logger adapter.
    
    Args:
        component: Component name (e.g., "Orchestrator", "CrawlEngine", "URLFilter")
        module_name: Optional module name for logger hierarchy (defaults to component)
        
    Returns:
        ComponentLoggerAdapter instance
        
    Example:
        >>> logger = get_component_logger("Orchestrator", "crawler.orchestrator")
        >>> logger.log_entry("crawl_url", url="https://example.com")
    """
    logger_name = module_name or f"website_crawler.{component.lower()}"
    return ComponentLoggerAdapter(get_logger(logger_name), component)


class MetricsCollector:
    """
    Simple metrics collector for tracking crawler performance.
    
    This is a basic implementation. For production, consider using
    a dedicated metrics library like Prometheus.
    """
    
    def __init__(self):
        """Initialize metrics collector."""
        self.counters: Dict[str, int] = defaultdict(int)
        self.timers: Dict[str, list] = defaultdict(list)
        self.gauges: Dict[str, float] = {}
    
    def increment(self, metric: str, value: int = 1) -> None:
        """
        Increment a counter metric.
        
        Args:
            metric: Metric name
            value: Value to increment by
        """
        self.counters[metric] += value
    
    def record_timing(self, metric: str, duration: float) -> None:
        """
        Record a timing metric.
        
        Args:
            metric: Metric name
            duration: Duration in seconds
        """
        self.timers[metric].append(duration)
    
    def set_gauge(self, metric: str, value: float) -> None:
        """
        Set a gauge metric.
        
        Args:
            metric: Metric name
            value: Gauge value
        """
        self.gauges[metric] = value
    
    def get_counter(self, metric: str) -> int:
        """
        Get counter value.
        
        Args:
            metric: Metric name
            
        Returns:
            Counter value
        """
        return self.counters.get(metric, 0)
    
    def get_timing_stats(self, metric: str) -> Dict[str, float]:
        """
        Get timing statistics.
        
        Args:
            metric: Metric name
            
        Returns:
            Dictionary with min, max, avg, count
        """
        timings = self.timers.get(metric, [])
        if not timings:
            return {"min": 0, "max": 0, "avg": 0, "count": 0}
        
        return {
            "min": min(timings),
            "max": max(timings),
            "avg": sum(timings) / len(timings),
            "count": len(timings)
        }
    
    def get_gauge(self, metric: str) -> Optional[float]:
        """
        Get gauge value.
        
        Args:
            metric: Metric name
            
        Returns:
            Gauge value or None
        """
        return self.gauges.get(metric)
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.counters.clear()
        self.timers.clear()
        self.gauges.clear()
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert metrics to dictionary.
        
        Returns:
            Dictionary representation of metrics
        """
        timing_stats = {
            metric: self.get_timing_stats(metric)
            for metric in self.timers.keys()
        }
        
        return {
            "counters": dict(self.counters),
            "timings": timing_stats,
            "gauges": dict(self.gauges)
        }


# Global metrics collector instance
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> MetricsCollector:
    """
    Get the global metrics collector instance.
    
    Returns:
        MetricsCollector instance
    """
    global _metrics_collector
    if _metrics_collector is None:
        _metrics_collector = MetricsCollector()
    return _metrics_collector


def reset_metrics() -> None:
    """Reset the global metrics collector."""
    global _metrics_collector
    if _metrics_collector is not None:
        _metrics_collector.reset()


def generate_request_id() -> str:
    """
    Generate a unique request ID.
    
    Returns:
        Unique request ID string
    """
    return str(uuid.uuid4())


def generate_correlation_id() -> str:
    """
    Generate a unique correlation ID.
    
    Returns:
        Unique correlation ID string
    """
    return str(uuid.uuid4())
