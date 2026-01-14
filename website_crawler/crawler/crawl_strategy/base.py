"""
Base crawl strategy interface for the website crawler.

This module defines the base interface that all crawl strategies must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Iterator


class BaseStrategy(ABC):
    """
    Base class for all crawl strategies.
    
    All crawl strategies (BFS, Sitemap, Adaptive) must inherit from this class
    and implement the required methods.
    """
    
    @abstractmethod
    def get_urls(self, start_url: str) -> Iterator[str]:
        """
        Generate URLs to crawl based on the strategy.
        
        Args:
            start_url: The starting URL for the crawl
            
        Yields:
            URLs to crawl in the order determined by the strategy
        """
        pass
    
    @abstractmethod
    def should_crawl(self, url: str, depth: int) -> bool:
        """
        Determine if a URL should be crawled.
        
        Args:
            url: The URL to check
            depth: Current crawl depth
            
        Returns:
            True if the URL should be crawled, False otherwise
        """
        pass
    
    @abstractmethod
    def add_url(self, url: str, priority: int = 0) -> None:
        """
        Add a URL to the crawl queue.
        
        Args:
            url: The URL to add
            priority: Optional priority for the URL (higher = more important)
        """
        pass

