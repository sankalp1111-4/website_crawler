"""
Base crawl strategy interface for the website crawler.

This module defines the base interface that all crawl strategies must implement.
"""

from abc import ABC, abstractmethod
from typing import List, Iterator, Optional


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
    def add_url(self, url: str, priority: int = 0, depth: Optional[int] = None) -> None:
        """
        Add a URL to the crawl queue.
        
        Args:
            url: The URL to add
            priority: Optional priority for the URL (higher = more important)
            depth: Optional depth for the URL
        """
        pass
    
    def get_next_url(self) -> Optional[str]:
        """
        Get the next URL from the strategy queue (for iterative crawling).
        
        This is a convenience method for iterative crawling where URLs are
        added dynamically as links are discovered.
        
        Returns:
            Next URL to crawl, or None if no more URLs available
        """
        # Default implementation: try to get from iterator
        # Subclasses should override for better performance
        try:
            if not hasattr(self, '_url_iterator'):
                return None
            return next(self._url_iterator)
        except StopIteration:
            return None
    
    def has_more_urls(self) -> bool:
        """
        Check if there are more URLs to crawl.
        
        Returns:
            True if there are more URLs, False otherwise
        """
        # Default implementation - subclasses should override
        return False

