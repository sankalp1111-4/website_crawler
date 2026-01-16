"""
Adaptive crawl strategy for the website crawler.

This module provides an adaptive crawling strategy using Crawl4AI.
"""
import heapq
import re
from typing import Iterator, Set, Optional, Dict, Any, Tuple, Callable
from urllib.parse import urlparse

from .base import BaseStrategy
from ..url.normalizer import normalize_url
from ..url.filter import URLFilter
from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("AdaptiveStrategy", __name__)


class AdaptiveStrategy(BaseStrategy):
    """
    Adaptive/priority-based crawling strategy.
    
    Prioritizes URLs based on multiple factors:
    - Depth (shallower = higher priority)
    - Path length (shorter = higher priority)
    - Pattern matching (matching patterns = higher priority)
    - Custom priority scores
    """
    
    def __init__(
        self,
        max_depth: int = 3,
        max_pages: int = 100,
        url_filter: Optional[URLFilter] = None,
        priority_patterns: Optional[list[str]] = None,
        priority_weights: Optional[Dict[str, float]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize adaptive strategy.
        
        Args:
            max_depth: Maximum crawl depth
            max_pages: Maximum number of pages to crawl
            url_filter: Optional URL filter instance
            priority_patterns: List of URL patterns to prioritize (regex)
            priority_weights: Dictionary of priority factor weights
            config: Optional configuration dictionary
        """
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.url_filter = url_filter
        self.priority_patterns = priority_patterns or []
        self.config = config or {}
        
        # Priority weights (default values)
        default_weights = {
            'depth': 0.3,
            'path_length': 0.2,
            'pattern_match': 0.4,
            'custom': 0.1
        }
        self.priority_weights = {**default_weights, **(priority_weights or {})}
        
        # Priority queue: (-priority, url, depth) - negative for max-heap behavior
        self.queue: list[Tuple[float, str, int]] = []
        self.visited: Set[str] = set()
        self.crawled_count = 0
        self.url_priorities: Dict[str, float] = {}  # Track priorities for updates
        self._initialized = False
        
        logger.info(f"[AdaptiveStrategy] Initialized with max_depth={max_depth}, max_pages={max_pages}")
    
    def get_urls(self, start_url: str) -> Iterator[str]:
        """
        Generate URLs to crawl using priority-based selection.
        
        Args:
            start_url: The starting URL for the crawl
            
        Yields:
            URLs to crawl in priority order
        """
        url_logger = logger.with_url(start_url)
        
        with url_logger.component_flow("get_urls", start_url=start_url):
            # Normalize start URL
            normalized_start = normalize_url(start_url)
            url_logger.info(f"[AdaptiveStrategy] Starting adaptive crawl from {normalized_start}")
            
            # Calculate initial priority
            initial_priority = self._calculate_priority(normalized_start, 0)
            
            # Add start URL to queue
            heapq.heappush(self.queue, (-initial_priority, normalized_start, 0))
            self.visited.add(normalized_start)
            self.url_priorities[normalized_start] = initial_priority
            
            # Process queue
            while self.queue and self.crawled_count < self.max_pages:
                # Get highest priority URL
                neg_priority, url, depth = heapq.heappop(self.queue)
                priority = -neg_priority
                
                # Check if we should crawl this URL
                if not self.should_crawl(url, depth):
                    url_logger.log_decision("URL_SKIPPED", reason=f"URL filtered or depth exceeded: {url}")
                    continue
                
                # Yield URL for crawling
                url_logger.info(f"[AdaptiveStrategy] Yielding URL (priority={priority:.2f}, depth={depth}, crawled={self.crawled_count + 1}/{self.max_pages}): {url}")
                yield url
                
                self.crawled_count += 1
                
                # Stop if we've reached max pages
                if self.crawled_count >= self.max_pages:
                    url_logger.info(f"[AdaptiveStrategy] Reached max_pages limit ({self.max_pages})")
                    break
            
            url_logger.info(f"[AdaptiveStrategy] Adaptive crawl completed. Crawled {self.crawled_count} pages")
    
    def _calculate_priority(self, url: str, depth: int) -> float:
        """
        Calculate priority score for a URL.
        
        Args:
            url: The URL
            depth: Current crawl depth
            
        Returns:
            Priority score (higher = more important)
        """
        priority = 0.0
        
        # Depth factor (shallower = higher priority)
        if depth < self.max_depth:
            depth_factor = 1.0 / (depth + 1)
            priority += self.priority_weights['depth'] * depth_factor
        
        # Path length factor (shorter = higher priority)
        parsed = urlparse(url)
        path_length = len(parsed.path.split('/'))
        path_factor = 1.0 / path_length
        priority += self.priority_weights['path_length'] * path_factor
        
        # Pattern match factor
        pattern_match = 0.0
        for pattern in self.priority_patterns:
            try:
                if re.search(pattern, url):
                    pattern_match = 1.0
                    break
            except re.error:
                logger.warning(f"[AdaptiveStrategy] Invalid regex pattern: {pattern}")
        
        priority += self.priority_weights['pattern_match'] * pattern_match
        
        # Custom factor (can be extended)
        custom_factor = 0.0
        # Add custom priority logic here if needed
        priority += self.priority_weights['custom'] * custom_factor
        
        return priority
    
    def should_crawl(self, url: str, depth: int) -> bool:
        """
        Determine if a URL should be crawled.
        
        Args:
            url: The URL to check
            depth: Current crawl depth
            
        Returns:
            True if the URL should be crawled, False otherwise
        """
        # Check depth limit
        if depth > self.max_depth:
            logger.debug(f"[AdaptiveStrategy] URL {url} exceeds max_depth ({depth} > {self.max_depth})")
            return False
        
        # Check if already visited
        normalized = normalize_url(url)
        if normalized in self.visited:
            logger.debug(f"[AdaptiveStrategy] URL {url} already visited")
            return False
        
        # Check URL filter if available
        if self.url_filter:
            filter_settings = self.config.get('filter_settings', {})
            if not self.url_filter.should_crawl(normalized, filters=filter_settings):
                logger.debug(f"[AdaptiveStrategy] URL {url} filtered out by URLFilter")
                return False
        
        return True
    
    def initialize(self, start_url: str) -> None:
        """
        Initialize the strategy with a start URL.
        
        Args:
            start_url: The starting URL for the crawl
        """
        normalized_start = normalize_url(start_url)
        logger.info(f"[AdaptiveStrategy] Initializing with start URL: {normalized_start}")
        
        if normalized_start not in self.visited:
            depth = 0
            initial_priority = self._calculate_priority(normalized_start, depth)
            heapq.heappush(self.queue, (-initial_priority, normalized_start, depth))
            self.visited.add(normalized_start)
            self.url_priorities[normalized_start] = initial_priority
            self._initialized = True
    
    def add_url(self, url: str, priority: int = 0, depth: Optional[int] = None) -> None:
        """
        Add a URL to the crawl queue.
        
        Args:
            url: The URL to add
            priority: Optional priority for the URL (higher = more important)
            depth: Optional depth for the URL (if None, estimates from queue)
        """
        normalized = normalize_url(url)
        
        # Skip if already visited
        if normalized in self.visited:
            logger.debug(f"[AdaptiveStrategy] Skipping already visited URL: {normalized}")
            return
        
        # Determine depth
        if depth is None:
            depth = 0
            if self.queue:
                # Use minimum depth from queue + 1 as estimate
                depths = [d for _, _, d in self.queue]
                if depths:
                    depth = min(depths) + 1
        
        # Check if depth is within limits
        if depth > self.max_depth:
            logger.debug(f"[AdaptiveStrategy] Skipping URL {normalized} - depth {depth} exceeds max_depth {self.max_depth}")
            return
        
        # Check URL filter if available
        if self.url_filter:
            filter_settings = self.config.get('filter_settings', {})
            if not self.url_filter.should_crawl(normalized, filters=filter_settings):
                logger.debug(f"[AdaptiveStrategy] Skipping URL {normalized} - filtered out")
                return
        
        # Calculate priority
        calculated_priority = self._calculate_priority(normalized, depth)
        # Add custom priority boost if provided
        final_priority = calculated_priority + (priority * 0.1)  # Scale custom priority
        
        # Add to queue
        heapq.heappush(self.queue, (-final_priority, normalized, depth))
        self.visited.add(normalized)
        self.url_priorities[normalized] = final_priority
        logger.debug(f"[AdaptiveStrategy] Added URL to queue: {normalized} (priority={final_priority:.2f}, depth={depth})")
    
    def get_next_url(self) -> Optional[str]:
        """
        Get the next URL from the queue (for iterative crawling).
        
        Returns:
            Next URL to crawl, or None if no more URLs available
        """
        while self.queue and self.crawled_count < self.max_pages:
            # Get highest priority URL
            neg_priority, url, depth = heapq.heappop(self.queue)
            priority = -neg_priority  # Convert back to positive
            
            # Check if we should crawl this URL
            if self.should_crawl(url, depth):
                self.crawled_count += 1
                logger.debug(f"[AdaptiveStrategy] Returning next URL (priority={priority:.2f}, depth={depth}): {url}")
                return url
        
        return None
    
    def has_more_urls(self) -> bool:
        """
        Check if there are more URLs to crawl.
        
        Returns:
            True if there are more URLs, False otherwise
        """
        has_urls = len(self.queue) > 0 and self.crawled_count < self.max_pages
        return has_urls
    
    def update_priority(self, url: str, new_priority: float) -> None:
        """
        Update priority for a URL in the queue.
        
        Args:
            url: The URL
            new_priority: New priority value
        """
        normalized = normalize_url(url)
        if normalized in self.url_priorities:
            self.url_priorities[normalized] = new_priority
            logger.debug(f"[AdaptiveStrategy] Updated priority for {normalized}: {new_priority:.2f}")
    
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
        self.url_priorities.clear()
        self._initialized = False
        logger.info("[AdaptiveStrategy] Strategy reset")
