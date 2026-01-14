"""
Factory modules for creating crawler components.

This package provides factories for creating extractors, strategies, and storage backends
based on configuration, following the Factory Pattern.
"""

from crawler.factories.extractor_factory import ExtractorFactory
from crawler.factories.strategy_factory import StrategyFactory
from crawler.factories.storage_factory import StorageFactory

__all__ = [
    "ExtractorFactory",
    "StrategyFactory",
    "StorageFactory",
]

