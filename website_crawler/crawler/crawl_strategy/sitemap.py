"""
Sitemap crawl strategy for the website crawler.

This module provides a sitemap-based crawling strategy.
"""
import xml.etree.ElementTree as ET
from typing import Iterator, Set, Optional, Dict, Any, List, Tuple
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
import requests
from datetime import datetime

from .base import BaseStrategy
from ..url.normalizer import normalize_url
from ..url.filter import URLFilter
from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("SitemapStrategy", __name__)


class SitemapStrategy(BaseStrategy):
    """
    Sitemap-based crawling strategy.
    
    Uses XML sitemaps to discover and prioritize URLs for crawling.
    """
    
    def __init__(
        self,
        max_pages: int = 100,
        url_filter: Optional[URLFilter] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize sitemap strategy.
        
        Args:
            max_pages: Maximum number of pages to crawl
            url_filter: Optional URL filter instance
            config: Optional configuration dictionary
        """
        self.max_pages = max_pages
        self.url_filter = url_filter
        self.config = config or {}
        
        # Store discovered URLs with metadata
        self.urls: List[Tuple[str, float, Optional[datetime]]] = []  # (url, priority, lastmod)
        self.visited: Set[str] = set()
        self.crawled_count = 0
        self._sitemap_cache: Dict[str, List[Tuple[str, float, Optional[datetime]]]] = {}
        self._current_index = 0  # For iterative URL retrieval
        self._initialized = False
        
        logger.info(f"[SitemapStrategy] Initialized with max_pages={max_pages}")
    
    def get_urls(self, start_url: str) -> Iterator[str]:
        """
        Generate URLs to crawl from sitemap.
        
        Args:
            start_url: The starting URL for the crawl
            
        Yields:
            URLs to crawl in priority order
        """
        url_logger = logger.with_url(start_url)
        
        with url_logger.component_flow("get_urls", start_url=start_url):
            # Discover and parse sitemaps
            url_logger.info(f"[SitemapStrategy] Discovering sitemaps for {start_url}")
            sitemap_urls = self._discover_sitemaps(start_url)
            
            if not sitemap_urls:
                url_logger.warning(f"[SitemapStrategy] No sitemaps found for {start_url}")
                return
            
            # Parse all sitemaps
            all_urls = []
            for sitemap_url in sitemap_urls:
                url_logger.info(f"[SitemapStrategy] Parsing sitemap: {sitemap_url}")
                urls = self._parse_sitemap(sitemap_url)
                all_urls.extend(urls)
            
            # Sort by priority (higher priority first)
            all_urls.sort(key=lambda x: x[1], reverse=True)
            
            # Filter and yield URLs
            for url, priority, lastmod in all_urls:
                if self.crawled_count >= self.max_pages:
                    url_logger.info(f"[SitemapStrategy] Reached max_pages limit ({self.max_pages})")
                    break
                
                normalized = normalize_url(url)
                
                if not self.should_crawl(normalized, 0):
                    continue
                
                url_logger.info(f"[SitemapStrategy] Yielding URL (priority={priority:.2f}, crawled={self.crawled_count + 1}/{self.max_pages}): {normalized}")
                yield normalized
                self.crawled_count += 1
                self.visited.add(normalized)
            
            url_logger.info(f"[SitemapStrategy] Sitemap crawl completed. Crawled {self.crawled_count} pages")
    
    def _discover_sitemaps(self, start_url: str) -> List[str]:
        """
        Discover sitemap URLs.
        
        Args:
            start_url: Starting URL
            
        Returns:
            List of sitemap URLs
        """
        sitemap_urls = []
        parsed = urlparse(start_url)
        base_url = f"{parsed.scheme}://{parsed.netloc}"
        
        # Try robots.txt first
        try:
            robots_url = urljoin(base_url, '/robots.txt')
            rp = RobotFileParser()
            rp.set_url(robots_url)
            rp.read()
            
            # Get sitemap URLs from robots.txt
            if hasattr(rp, 'sitemaps'):
                sitemap_urls.extend(rp.sitemaps)
            elif hasattr(rp, '_sitemaps'):
                sitemap_urls.extend(rp._sitemaps)
        except Exception as e:
            logger.debug(f"[SitemapStrategy] Could not read robots.txt: {e}")
        
        # Try common sitemap locations
        common_paths = ['/sitemap.xml', '/sitemap_index.xml', '/sitemap-index.xml']
        for path in common_paths:
            sitemap_url = urljoin(base_url, path)
            if sitemap_url not in sitemap_urls:
                sitemap_urls.append(sitemap_url)
        
        return sitemap_urls
    
    def _parse_sitemap(self, sitemap_url: str) -> List[Tuple[str, float, Optional[datetime]]]:
        """
        Parse a sitemap XML file.
        
        Args:
            sitemap_url: URL of the sitemap
            
        Returns:
            List of tuples (url, priority, lastmod)
        """
        # Check cache
        if sitemap_url in self._sitemap_cache:
            logger.debug(f"[SitemapStrategy] Using cached sitemap: {sitemap_url}")
            return self._sitemap_cache[sitemap_url]
        
        urls = []
        
        try:
            # Fetch sitemap
            response = requests.get(sitemap_url, timeout=30)
            response.raise_for_status()
            
            # Parse XML
            root = ET.fromstring(response.content)
            
            # Check if it's a sitemap index
            if root.tag.endswith('sitemapindex'):
                # Parse sitemap index
                for sitemap_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap'):
                    loc_elem = sitemap_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    if loc_elem is not None and loc_elem.text:
                        # Recursively parse nested sitemap
                        nested_urls = self._parse_sitemap(loc_elem.text.strip())
                        urls.extend(nested_urls)
            else:
                # Parse regular sitemap
                for url_elem in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                    loc_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                    priority_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}priority')
                    lastmod_elem = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}lastmod')
                    
                    if loc_elem is not None and loc_elem.text:
                        url = loc_elem.text.strip()
                        priority = 0.5  # Default priority
                        
                        if priority_elem is not None and priority_elem.text:
                            try:
                                priority = float(priority_elem.text.strip())
                            except ValueError:
                                pass
                        
                        lastmod = None
                        if lastmod_elem is not None and lastmod_elem.text:
                            try:
                                lastmod = datetime.fromisoformat(lastmod_elem.text.strip().replace('Z', '+00:00'))
                            except ValueError:
                                pass
                        
                        urls.append((url, priority, lastmod))
            
            # Cache the result
            self._sitemap_cache[sitemap_url] = urls
            logger.info(f"[SitemapStrategy] Parsed sitemap {sitemap_url}: {len(urls)} URLs found")
            
        except requests.exceptions.HTTPError as e:
            # Handle HTTP errors (404, 403, etc.) - these are expected for missing sitemaps
            if e.response.status_code == 404:
                logger.debug(f"[SitemapStrategy] Sitemap not found (404): {sitemap_url}")
            else:
                logger.warning(f"[SitemapStrategy] HTTP error parsing sitemap {sitemap_url}: {e.response.status_code} {e}")
        except requests.exceptions.RequestException as e:
            # Handle network errors
            logger.warning(f"[SitemapStrategy] Network error parsing sitemap {sitemap_url}: {e}")
        except ET.ParseError as e:
            # Handle XML parsing errors
            logger.warning(f"[SitemapStrategy] XML parsing error for sitemap {sitemap_url}: {e}")
        except Exception as e:
            # Handle any other unexpected errors
            logger.warning(f"[SitemapStrategy] Unexpected error parsing sitemap {sitemap_url}: {e}")
        
        return urls
    
    def should_crawl(self, url: str, depth: int) -> bool:
        """
        Determine if a URL should be crawled.
        
        Args:
            url: The URL to check
            depth: Current crawl depth (not used for sitemap strategy)
            
        Returns:
            True if the URL should be crawled, False otherwise
        """
        normalized = normalize_url(url)
        
        # Don't check visited here - URLs in the queue haven't been crawled yet
        # The visited set is used to prevent adding duplicates to the queue,
        # not to prevent crawling URLs that are already in the queue
        
        # Check URL filter if available
        if self.url_filter:
            filter_settings = self.config.get('filter_settings', {})
            if not self.url_filter.should_crawl(normalized, filters=filter_settings):
                logger.debug(f"[SitemapStrategy] URL {url} filtered out by URLFilter")
                return False
        
        return True
    
    def initialize(self, start_url: str) -> None:
        """
        Initialize the strategy with a start URL (discover sitemaps).
        
        Args:
            start_url: The starting URL for the crawl
        """
        logger.info(f"[SitemapStrategy] Initializing with start URL: {start_url}")
        # Discover and parse sitemaps
        sitemap_urls = self._discover_sitemaps(start_url)
        
        if sitemap_urls:
            # Parse all sitemaps
            all_urls = []
            for sitemap_url in sitemap_urls:
                logger.info(f"[SitemapStrategy] Parsing sitemap: {sitemap_url}")
                urls = self._parse_sitemap(sitemap_url)
                all_urls.extend(urls)
            
            # Sort by priority (higher priority first)
            all_urls.sort(key=lambda x: x[1], reverse=True)
            
            # Add to URLs list
            for url, priority, lastmod in all_urls:
                normalized = normalize_url(url)
                # Only add if not already in queue and passes filter
                if normalized not in self.visited and self.should_crawl(normalized, 0):
                    self.urls.append((normalized, priority, lastmod))
                    # Mark as visited to prevent duplicates when adding to queue
                    # Note: visited check is NOT used in should_crawl() to allow queued URLs to be crawled
                    self.visited.add(normalized)
            
            logger.info(f"[SitemapStrategy] Discovered {len(self.urls)} URLs from sitemaps")
        else:
            # No sitemaps found, add start URL
            normalized = normalize_url(start_url)
            if normalized not in self.visited:
                self.urls.append((normalized, 1.0, None))
                # Mark as visited to prevent duplicates in queue
                self.visited.add(normalized)
        
        self._initialized = True
    
    def add_url(self, url: str, priority: int = 0, depth: Optional[int] = None) -> None:
        """
        Add a URL to the crawl queue.
        
        Args:
            url: The URL to add
            priority: Optional priority for the URL (higher = more important)
            depth: Optional depth (not used in sitemap strategy)
        """
        normalized = normalize_url(url)
        
        # Skip if already visited
        if normalized in self.visited:
            logger.debug(f"[SitemapStrategy] Skipping already visited URL: {normalized}")
            return
        
        # Check URL filter if available
        if self.url_filter:
            filter_settings = self.config.get('filter_settings', {})
            if not self.url_filter.should_crawl(normalized, filters=filter_settings):
                logger.debug(f"[SitemapStrategy] Skipping URL {normalized} - filtered out")
                return
        
        # Add to URLs list with priority (insert in sorted position)
        self.urls.append((normalized, float(priority), None))
        # Re-sort to maintain priority order
        self.urls.sort(key=lambda x: x[1], reverse=True)
        self.visited.add(normalized)
        logger.debug(f"[SitemapStrategy] Added URL: {normalized} (priority={priority})")
    
    def get_next_url(self) -> Optional[str]:
        """
        Get the next URL from the queue (for iterative crawling).
        
        Returns:
            Next URL to crawl, or None if no more URLs available
        """
        if not self._initialized and self.urls:
            self._initialized = True
        
        while self._current_index < len(self.urls) and self.crawled_count < self.max_pages:
            url, priority, lastmod = self.urls[self._current_index]
            self._current_index += 1
            
            # Check if URL should be crawled (filter check)
            if self.should_crawl(url, 0):
                self.crawled_count += 1
                logger.info(f"[SitemapStrategy] Returning next URL (priority={priority:.2f}, {self.crawled_count}/{self.max_pages}): {url}")
                return url
            else:
                logger.debug(f"[SitemapStrategy] Skipping URL (filtered): {url}")
        
        return None
    
    def has_more_urls(self) -> bool:
        """
        Check if there are more URLs to crawl.
        
        Returns:
            True if there are more URLs, False otherwise
        """
        has_urls = self._current_index < len(self.urls) and self.crawled_count < self.max_pages
        return has_urls
    
    def reset(self) -> None:
        """Reset the strategy state."""
        self.urls.clear()
        self.visited.clear()
        self.crawled_count = 0
        self._current_index = 0
        self._initialized = False
        logger.info("[SitemapStrategy] Strategy reset")
