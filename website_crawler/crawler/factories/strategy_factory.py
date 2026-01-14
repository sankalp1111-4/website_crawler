"""
Factory for creating crawl strategies.

This module provides a factory to create crawl strategy instances based on configuration.
Supports BFS, Sitemap, and Adaptive strategies.
"""

from typing import Dict, Type, Any
from crawler.crawl_strategy.base import BaseStrategy
from crawler.crawl_strategy.bfs import BFSStrategy
from crawler.crawl_strategy.sitemap import SitemapStrategy
from crawler.crawl_strategy.adaptive import AdaptiveStrategy


class StrategyFactory:
    """
    Factory for creating crawl strategies.
    
    This factory creates the appropriate strategy instance based on the
    strategy type specified in the configuration.
    """
    
    # Registry of available strategies
    _strategies: Dict[str, Type[BaseStrategy]] = {
        "bfs": BFSStrategy,
        "sitemap": SitemapStrategy,
        "adaptive": AdaptiveStrategy,
    }
    
    @classmethod
    def create(cls, strategy_type: str, **kwargs: Any) -> BaseStrategy:
        """
        Create a crawl strategy based on type.
        
        Args:
            strategy_type: Type of strategy ("bfs", "sitemap", or "adaptive")
            **kwargs: Additional configuration parameters for the strategy
                     (e.g., max_depth for BFS, sitemap_url for Sitemap)
        
        Returns:
            Instance of the requested strategy implementing BaseStrategy
        
        Raises:
            ValueError: If strategy_type is not supported
            TypeError: If the strategy class cannot be instantiated with provided kwargs
        
        Example:
            >>> # Create a BFS strategy
            >>> strategy = StrategyFactory.create("bfs", max_depth=3, max_pages=100)
            >>> 
            >>> # Create a Sitemap strategy
            >>> strategy = StrategyFactory.create("sitemap", sitemap_url="https://example.com/sitemap.xml")
        """
        if strategy_type not in cls._strategies:
            available = ", ".join(cls._strategies.keys())
            raise ValueError(
                f"Unknown strategy type: '{strategy_type}'. "
                f"Available types: {available}"
            )
        
        strategy_class = cls._strategies[strategy_type]
        
        try:
            return strategy_class(**kwargs)
        except Exception as e:
            raise TypeError(
                f"Failed to create {strategy_type} strategy with provided parameters: {e}"
            ) from e
    
    @classmethod
    def register(cls, strategy_type: str, strategy_class: Type[BaseStrategy]) -> None:
        """
        Register a new strategy type.
        
        This allows extending the factory with custom strategies at runtime.
        
        Args:
            strategy_type: Name identifier for the strategy type
            strategy_class: Class that implements BaseStrategy
        
        Example:
            >>> from crawler.crawl_strategy.custom_strategy import CustomStrategy
            >>> StrategyFactory.register("custom", CustomStrategy)
            >>> strategy = StrategyFactory.create("custom", param1="value")
        """
        if not issubclass(strategy_class, BaseStrategy):
            raise TypeError(
                f"Strategy class must inherit from BaseStrategy, "
                f"got {strategy_class.__name__}"
            )
        cls._strategies[strategy_type] = strategy_class
    
    @classmethod
    def get_available_types(cls) -> list[str]:
        """
        Get list of available strategy types.
        
        Returns:
            List of strategy type names that can be created
        """
        return list(cls._strategies.keys())

