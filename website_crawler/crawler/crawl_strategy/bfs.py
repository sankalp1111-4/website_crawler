"""
BFS crawl strategy for the website crawler.

This module provides a breadth-first search crawling strategy.
"""
from collections import deque
from typing import Iterator, Set, Optional, Dict, Any, Tuple
from urllib.parse import urlparse

from .base import BaseStrategy
from ..url.normalizer import normalize_url
from ..url.filter import URLFilter
from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("BFSStrategy", __name__)


class BFSStrategy(BaseStrategy):
    """
    Breadth-First Search crawling strategy.
    
    Crawls URLs level by level, processing all URLs at depth N before
    moving to depth N+1.
    """
    
    def __init__(
        self,
        max_depth: int = 3,
        max_pages: int = 100,
        url_filter: Optional[URLFilter] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize BFS strategy.
        
        Args:
            max_depth: Maximum crawl depth
            max_pages: Maximum number of pages to crawl
            url_filter: Optional URL filter instance
            config: Optional configuration dictionary
        """
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.url_filter = url_filter
        self.config = config or {}
        
        # Queue: (url, depth, priority)
        self.queue: deque = deque()
        self.visited: Set[str] = set()
        self.crawled_count = 0
        
        # Track current depth being processed
        self.current_depth = 0
        
        # Track if strategy has been initialized with start URL
        self._initialized = False
        
        logger.info(f"[BFSStrategy] Initialized with max_depth={max_depth}, max_pages={max_pages}")
    
    def initialize(self, start_url: str) -> None:
        """
        Initialize the strategy with a start URL.
        
        Args:
            start_url: The starting URL for the crawl
        """
        normalized_start = normalize_url(start_url)
        logger.info(f"[BFSStrategy] Initializing with start URL: {normalized_start}")
        
        # Initialize queue with start URL at depth 0
        # Mark as visited to prevent re-adding, but should_crawl() won't reject it
        # because visited check is removed from should_crawl()
        if normalized_start not in self.visited:
            self.queue.append((normalized_start, 0, 0))
            self.visited.add(normalized_start)
            self._initialized = True
    
    def get_urls(self, start_url: str) -> Iterator[str]:
        """
        Generate URLs to crawl using BFS algorithm.
        
        Args:
            start_url: The starting URL for the crawl
            
        Yields:
            URLs to crawl in breadth-first order
        """
        url_logger = logger.with_url(start_url)
        
        with url_logger.component_flow("get_urls", start_url=start_url):
            # Initialize if not already done
            if not self._initialized:
                self.initialize(start_url)
            
            # Process queue level by level
            while self.queue and self.crawled_count < self.max_pages:
                # Get next URL from queue
                url, depth, priority = self.queue.popleft()
                
                # Update current depth
                self.current_depth = depth
                
                # Check if we should crawl this URL
                if not self.should_crawl(url, depth):
                    url_logger.log_decision("URL_SKIPPED", reason=f"URL filtered or depth exceeded: {url}")
                    continue
                
                # Mark as visited when we're about to crawl it
                normalized = normalize_url(url)
                self.visited.add(normalized)
                
                # Yield URL for crawling
                url_logger.info(f"[BFSStrategy] Yielding URL (depth={depth}, crawled={self.crawled_count + 1}/{self.max_pages}): {url}")
                yield url
                
                self.crawled_count += 1
                
                # Stop if we've reached max pages
                if self.crawled_count >= self.max_pages:
                    url_logger.info(f"[BFSStrategy] Reached max_pages limit ({self.max_pages})")
                    break
            
            url_logger.info(f"[BFSStrategy] BFS crawl completed. Crawled {self.crawled_count} pages")
    
    def should_crawl(self, url: str, depth: int) -> bool:
        """
        Determine if a URL should be crawled.
        
        Args:
            url: The URL to check
            depth: Current crawl depth
            
        Returns:
            True if the URL should be crawled, False otherwise
        """
        normalized = normalize_url(url)
        
        # Check depth limit
        if depth > self.max_depth:
            logger.debug(f"[BFSStrategy] URL {url} exceeds max_depth ({depth} > {self.max_depth})")
            return False
        
        # Don't check visited here - URLs in the queue haven't been crawled yet
        # The visited set is used to prevent adding duplicates to the queue,
        # not to prevent crawling URLs that are already in the queue
        
        # Check URL filter if available
        if self.url_filter:
            filter_settings = self.config.get('filter_settings', {})
            if not self.url_filter.should_crawl(normalized, filters=filter_settings):
                logger.debug(f"[BFSStrategy] URL {url} filtered out by URLFilter")
                return False
        
        return True
    
    def add_url(self, url: str, priority: int = 0, depth: Optional[int] = None) -> None:
        """
        Add a URL to the crawl queue.
        
        Args:
            url: The URL to add
            priority: Optional priority for the URL (higher = more important)
            depth: Optional depth for the URL (if None, uses current_depth + 1)
        """
        normalized = normalize_url(url)
        
        # Skip if already visited
        if normalized in self.visited:
            logger.debug(f"[BFSStrategy] Skipping already visited URL: {normalized}")
            return
        
        # Determine depth
        if depth is None:
            depth = self.current_depth + 1
        
        # Check if depth is within limits
        if depth > self.max_depth:
            logger.debug(f"[BFSStrategy] Skipping URL {normalized} - depth {depth} exceeds max_depth {self.max_depth}")
            return
        
        # Check URL filter if available
        if self.url_filter:
            filter_settings = self.config.get('filter_settings', {})
            if not self.url_filter.should_crawl(normalized, filters=filter_settings):
                logger.debug(f"[BFSStrategy] Skipping URL {normalized} - filtered out")
                return
        
        # Add to queue (don't mark as visited yet - that happens when it's crawled)
        self.queue.append((normalized, depth, priority))
        # Mark as visited now to prevent adding duplicates to the queue
        # This is safe because we check visited before adding, so this URL won't be added again
        self.visited.add(normalized)
        logger.debug(f"[BFSStrategy] Added URL to queue: {normalized} (depth={depth}, priority={priority})")
    
    def add_links(self, links: list[str], current_depth: int) -> None:
        """
        Add multiple links to the crawl queue.
        
        Args:
            links: List of URLs to add
            current_depth: Current crawl depth (links will be added at depth + 1)
        """
        for link in links:
            self.add_url(link, priority=0, depth=current_depth + 1)
    
    def get_next_url(self) -> Optional[str]:
        """
        Get the next URL from the queue (for iterative crawling).
        
        Returns:
            Next URL to crawl, or None if no more URLs available
        """
        # Process queue until we find a valid URL or queue is empty
        while self.queue and self.crawled_count < self.max_pages:
            url, depth, priority = self.queue.popleft()
            self.current_depth = depth
            
            # Check if we should crawl this URL
            if self.should_crawl(url, depth):
                # Mark as visited when we're about to crawl it
                normalized = normalize_url(url)
                self.visited.add(normalized)
                self.crawled_count += 1
                logger.debug(f"[BFSStrategy] Returning next URL (depth={depth}): {url}")
                return url
        
        return None
    
    def has_more_urls(self) -> bool:
        """
        Check if there are more URLs to crawl.
        
        Returns:
            True if there are more URLs, False otherwise
        """
        # Check if queue has URLs and we haven't exceeded max_pages
        has_urls = len(self.queue) > 0 and self.crawled_count < self.max_pages
        return has_urls
    
    def get_queue_size(self) -> int:
        """Get the current queue size."""
        return len(self.queue)
    
    def get_visited_count(self) -> int:
        """Get the number of visited URLs."""
        return len(self.visited)
    
    def reset(self) -> None:
        """Reset the strategy state."""
        self.queue.clear()
        self.visited.clear()
        self.crawled_count = 0
        self.current_depth = 0
        self._initialized = False
        logger.info("[BFSStrategy] Strategy reset")
