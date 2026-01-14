"""
Configuration module for the website crawler.

This module handles configuration loading and validation.
"""
from pathlib import Path

from .schema import (
    MainConfig,
    CrawlerConfig,
    EngineConfig,
    StorageConfig,
    ExtractionConfig,
    StrategyConfig,
    AuthConfig,
    LoggingConfig,
)
from .loader import (
    load_config,
    get_config,
    DEFAULT_CONFIG_PATH,
)

__all__ = [
    # Configuration models
    "MainConfig",
    "CrawlerConfig",
    "EngineConfig",
    "StorageConfig",
    "ExtractionConfig",
    "StrategyConfig",
    "AuthConfig",
    "LoggingConfig",
    # Loader functions
    "load_config",
    "get_config",
    # Constants
    "DEFAULT_CONFIG_PATH",
]
