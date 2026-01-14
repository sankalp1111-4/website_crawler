"""
URL filtering utilities for the website crawler.

This module provides functions to filter URLs based on various criteria,
including robots.txt rules, URL patterns, and domain restrictions.
"""
import re
import fnmatch
from typing import Dict, Any, List, Optional, Set
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser
from urllib.request import urlopen, Request
import logging

from ..exceptions import CrawlerException
from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("URLFilter", __name__)


class URLFilter:
    """
    Utility class for filtering URLs.
    
    Handles URL filtering tasks such as:
    - Robots.txt compliance
    - Pattern-based filtering (include/exclude)
    - Domain restrictions
    - File type filtering
    """
    
    def __init__(
        self,
        respect_robots_txt: bool = True,
        user_agent: str = "CrawlerBot",
        allowed_domains: Optional[List[str]] = None,
        blocked_domains: Optional[List[str]] = None,
        allowed_extensions: Optional[List[str]] = None,
        blocked_extensions: Optional[List[str]] = None,
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None,
        pattern_type: str = "regex"
    ):
        """
        Initialize the URL filter.
        
        Args:
            respect_robots_txt: Whether to respect robots.txt rules
            user_agent: User agent string for robots.txt checks
            allowed_domains: List of allowed domains (None = all allowed)
            blocked_domains: List of blocked domains
            allowed_extensions: List of allowed file extensions (None = all allowed)
            blocked_extensions: List of blocked file extensions
            include_patterns: List of patterns to include (regex or glob)
            exclude_patterns: List of patterns to exclude (regex or glob)
            pattern_type: Type of pattern matching - "regex" or "glob"
        """
        self.respect_robots_txt = respect_robots_txt
        self.user_agent = user_agent
        self.allowed_domains = set(allowed_domains or [])
        self.blocked_domains = set(blocked_domains or [])
        self.allowed_extensions = set(ext.lower() for ext in (allowed_extensions or []))
        self.blocked_extensions = set(ext.lower() for ext in (blocked_extensions or []))
        self.include_patterns = include_patterns or []
        self.exclude_patterns = exclude_patterns or []
        self.pattern_type = pattern_type
        
        # Cache for robots.txt parsers (domain -> RobotFileParser)
        self._robots_cache: Dict[str, RobotFileParser] = {}
        self._robots_loaded: Set[str] = set()  # Track which domains we've attempted to load
    
    def should_crawl(self, url: str, filters: Optional[Dict[str, Any]] = None) -> bool:
        """
        Determine if a URL should be crawled based on filter rules.
        
        Args:
            url: The URL to check
            filters: Optional additional filter overrides (can override any filter setting)
            
        Returns:
            True if the URL should be crawled, False otherwise
        """
        url_logger = logger.with_url(url)
        
        with url_logger.component_flow("should_crawl", url=url, has_filters=bool(filters)):
            if not url:
                url_logger.log_decision("URL_EMPTY", "Empty URL provided")
                url_logger.log_exit("should_crawl", decision="rejected", reason="empty_url")
                return False
            
            # Apply filter overrides if provided, otherwise use instance attributes
            respect_robots = filters.get('respect_robots_txt', self.respect_robots_txt) if filters else self.respect_robots_txt
            user_agent = filters.get('user_agent', self.user_agent) if filters else self.user_agent
            
            # Handle allowed_domains - convert set to list if needed, preserve None
            if filters and 'allowed_domains' in filters:
                if filters['allowed_domains'] is None:
                    allowed_domains = None
                elif isinstance(filters['allowed_domains'], (set, list)):
                    allowed_domains = list(filters['allowed_domains'])
                else:
                    allowed_domains = filters['allowed_domains']
            else:
                allowed_domains = list(self.allowed_domains) if self.allowed_domains else None
            
            # Handle blocked_domains - convert set to list if needed, preserve None
            if filters and 'blocked_domains' in filters:
                if filters['blocked_domains'] is None:
                    blocked_domains = None
                elif isinstance(filters['blocked_domains'], (set, list)):
                    blocked_domains = list(filters['blocked_domains'])
                else:
                    blocked_domains = filters['blocked_domains']
            else:
                blocked_domains = list(self.blocked_domains) if self.blocked_domains else None
            
            exclude_patterns = filters.get('exclude_patterns', self.exclude_patterns) if filters else self.exclude_patterns
            include_patterns = filters.get('include_patterns', self.include_patterns) if filters else self.include_patterns
            
            url_logger.log_entry("apply_filters", 
                               respect_robots=respect_robots,
                               allowed_domains_count=len(allowed_domains) if allowed_domains else 0,
                               blocked_domains_count=len(blocked_domains) if blocked_domains else 0,
                               exclude_patterns_count=len(exclude_patterns),
                               include_patterns_count=len(include_patterns))
            
            # 1. Check robots.txt (if enabled)
            if respect_robots:
                url_logger.log_entry("check_robots_txt", url=url, user_agent=user_agent)
                robots_allowed = self.check_robots_txt(url, user_agent)
                if not robots_allowed:
                    url_logger.log_decision("ROBOTS_TXT_BLOCKED", "URL blocked by robots.txt")
                    url_logger.log_exit("should_crawl", decision="rejected", reason="robots_txt")
                    return False
                url_logger.info("[URLFilter] Robots.txt allowed ✓")
                url_logger.log_exit("check_robots_txt", decision="allowed")
            else:
                url_logger.log_decision("ROBOTS_TXT_SKIPPED", "robots.txt check disabled")
            
            # 2. Check domain restrictions
            url_logger.log_entry("check_allowed_domain", url=url, allowed_domains=allowed_domains)
            if not self.is_allowed_domain(url, allowed_domains):
                url_logger.log_decision("DOMAIN_NOT_ALLOWED", "Domain not in allowed list")
                url_logger.log_exit("should_crawl", decision="rejected", reason="domain_not_allowed")
                return False
            url_logger.log_decision("DOMAIN_ALLOWED", "Domain is in allowed list")
            url_logger.log_exit("check_allowed_domain", decision="allowed")
            
            url_logger.log_entry("check_blocked_domain", url=url, blocked_domains=blocked_domains)
            if self.is_blocked_domain(url, blocked_domains):
                url_logger.log_decision("DOMAIN_BLOCKED", "Domain in blocked list")
                url_logger.log_exit("should_crawl", decision="rejected", reason="domain_blocked")
                return False
            url_logger.log_decision("DOMAIN_NOT_BLOCKED", "Domain not in blocked list")
            url_logger.log_exit("check_blocked_domain", decision="not_blocked")
            
            # 3. Check file extension filters
            url_logger.log_entry("check_file_extension", url=url)
            if not self.filter_by_file_extension(url, self.allowed_extensions, self.blocked_extensions):
                url_logger.log_decision("FILE_EXTENSION_BLOCKED", "URL blocked by file extension filter")
                url_logger.log_exit("should_crawl", decision="rejected", reason="file_extension")
                return False
            url_logger.log_decision("FILE_EXTENSION_ALLOWED", "File extension passed filter")
            url_logger.log_exit("check_file_extension", decision="allowed")
            
            # 4. Check include patterns (if any, URL must match at least one)
            if include_patterns:
                url_logger.log_entry("check_include_patterns", url=url, patterns=include_patterns)
                matched = False
                matched_pattern = None
                for pattern in include_patterns:
                    if self.match_pattern(url, pattern, self.pattern_type):
                        matched = True
                        matched_pattern = pattern
                        break
                if not matched:
                    url_logger.log_decision("INCLUDE_PATTERN_NOT_MATCHED", "URL doesn't match any include patterns")
                    url_logger.log_exit("should_crawl", decision="rejected", reason="include_pattern")
                    return False
                url_logger.log_decision("INCLUDE_PATTERN_MATCHED", f"URL matched pattern: {matched_pattern}")
                url_logger.log_exit("check_include_patterns", decision="matched", pattern=matched_pattern)
            
            # 5. Check exclude patterns (URL must not match any)
            url_logger.log_entry("check_exclude_patterns", url=url, patterns=exclude_patterns)
            for pattern in exclude_patterns:
                if self.match_pattern(url, pattern, self.pattern_type):
                    url_logger.log_decision("EXCLUDE_PATTERN_MATCHED", f"URL matched exclude pattern: {pattern}")
                    url_logger.log_exit("should_crawl", decision="rejected", reason="exclude_pattern", pattern=pattern)
                    return False
            url_logger.log_decision("EXCLUDE_PATTERN_NOT_MATCHED", "URL doesn't match any exclude patterns")
            url_logger.log_exit("check_exclude_patterns", decision="not_matched")
            
            url_logger.info("[URLFilter] URL passed all filters ✓")
            url_logger.log_exit("should_crawl", decision="allowed")
            return True
    
    def check_robots_txt(self, url: str, user_agent: Optional[str] = None) -> bool:
        """
        Check if URL is allowed by robots.txt rules.
        
        Args:
            url: The URL to check
            user_agent: User agent string (defaults to instance user_agent)
            
        Returns:
            True if URL is allowed, False if blocked or error
        """
        url_logger = logger.with_url(url)
        
        if not self.respect_robots_txt:
            url_logger.log_decision("ROBOTS_TXT_DISABLED", "robots.txt checking disabled")
            return True
        
        user_agent = user_agent or self.user_agent
        
        try:
            parsed = urlparse(url)
            domain = f"{parsed.scheme}://{parsed.netloc}"
            
            url_logger.log_entry("check_robots_txt", url=url, domain=domain, user_agent=user_agent)
            
            # Get or create robots.txt parser for this domain
            if domain not in self._robots_cache:
                robots_url = urljoin(domain, "/robots.txt")
                url_logger.log_decision("ROBOTS_TXT_NOT_CACHED", f"Loading robots.txt from {robots_url}")
                rp = RobotFileParser()
                rp.set_url(robots_url)
                
                # Try to read robots.txt
                try:
                    rp.read()
                    self._robots_loaded.add(domain)
                    url_logger.log_state_change("robots_txt_not_loaded", "robots_txt_loaded", robots_url=robots_url)
                    url_logger.log_decision("ROBOTS_TXT_LOADED", f"Successfully loaded robots.txt from {robots_url}")
                except Exception as e:
                    # If robots.txt doesn't exist or can't be read, allow by default
                    url_logger.log_decision("ROBOTS_TXT_LOAD_FAILED", f"Could not load robots.txt: {str(e)}, allowing by default")
                    # Create a permissive parser that allows all
                    rp = None
                    self._robots_loaded.add(domain)
                
                self._robots_cache[domain] = rp
            else:
                url_logger.log_decision("ROBOTS_TXT_CACHED", f"Using cached robots.txt for {domain}")
            
            rp = self._robots_cache[domain]
            
            # If robots.txt couldn't be loaded, allow by default
            if rp is None:
                url_logger.log_decision("ROBOTS_TXT_ALLOW_DEFAULT", "robots.txt unavailable, allowing by default")
                url_logger.log_exit("check_robots_txt", decision="allowed", reason="default")
                return True
            
            # Check if URL path is allowed
            path = parsed.path or "/"
            allowed = rp.can_fetch(user_agent, url)
            
            if not allowed:
                url_logger.log_decision("ROBOTS_TXT_DISALLOWS", f"robots.txt disallows {user_agent} from {url}")
            else:
                url_logger.log_decision("ROBOTS_TXT_ALLOWS", f"robots.txt allows {user_agent} from {url}")
            
            url_logger.log_exit("check_robots_txt", decision="allowed" if allowed else "blocked")
            return allowed
            
        except Exception as e:
            # On any error, log and allow by default (fail open)
            url_logger.log_decision("ROBOTS_TXT_ERROR", f"Error checking robots.txt: {str(e)}, allowing by default")
            url_logger.warning(f"[URLFilter] Error checking robots.txt for {url}: {e}", exc_info=True)
            url_logger.log_exit("check_robots_txt", decision="allowed", reason="error_default")
            return True
    
    def match_pattern(self, url: str, pattern: str, pattern_type: Optional[str] = None) -> bool:
        """
        Match URL against pattern (regex or glob).
        
        Args:
            url: The URL to match
            pattern: The pattern to match against
            pattern_type: Type of pattern - "regex" or "glob" (defaults to instance pattern_type)
            
        Returns:
            True if URL matches pattern, False otherwise
        """
        pattern_type = pattern_type or self.pattern_type
        
        if pattern_type == "regex":
            try:
                return bool(re.search(pattern, url))
            except re.error as e:
                logger.warning(f"Invalid regex pattern '{pattern}': {e}")
                return False
        elif pattern_type == "glob":
            return fnmatch.fnmatch(url, pattern)
        else:
            logger.warning(f"Unknown pattern type: {pattern_type}, defaulting to regex")
            try:
                return bool(re.search(pattern, url))
            except re.error:
                return False
    
    def is_allowed_domain(self, url: str, allowed_domains: Optional[List[str]] = None) -> bool:
        """
        Check if domain is allowed.
        
        Args:
            url: The URL to check
            allowed_domains: List of allowed domains (None = all allowed)
            
        Returns:
            True if domain is allowed or no restrictions, False otherwise
        """
        if not allowed_domains:
            return True
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove port if present
            if ':' in domain:
                domain = domain.split(':')[0]
            
            # Check if domain matches any allowed domain
            for allowed in allowed_domains:
                allowed_lower = allowed.lower()
                # Exact match or subdomain match
                if domain == allowed_lower or domain.endswith('.' + allowed_lower):
                    return True
            
            return False
        except Exception as e:
            logger.warning(f"Error checking allowed domain for {url}: {e}")
            return False
    
    def is_blocked_domain(self, url: str, blocked_domains: Optional[List[str]] = None) -> bool:
        """
        Check if domain is blocked.
        
        Args:
            url: The URL to check
            blocked_domains: List of blocked domains
            
        Returns:
            True if domain is blocked, False otherwise
        """
        if not blocked_domains:
            return False
        
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # Remove port if present
            if ':' in domain:
                domain = domain.split(':')[0]
            
            # Check if domain matches any blocked domain
            for blocked in blocked_domains:
                blocked_lower = blocked.lower()
                # Exact match or subdomain match
                if domain == blocked_lower or domain.endswith('.' + blocked_lower):
                    return True
            
            return False
        except Exception as e:
            logger.warning(f"Error checking blocked domain for {url}: {e}")
            return False
    
    def filter_by_file_extension(
        self,
        url: str,
        allowed_extensions: Optional[List[str]] = None,
        blocked_extensions: Optional[List[str]] = None
    ) -> bool:
        """
        Filter by file extension.
        
        Args:
            url: The URL to check
            allowed_extensions: List of allowed extensions (None = all allowed)
            blocked_extensions: List of blocked extensions
            
        Returns:
            True if extension is allowed, False otherwise
        """
        try:
            parsed = urlparse(url)
            path = parsed.path.lower()
            
            # Extract extension
            if '.' in path:
                ext = path.split('.')[-1].split('?')[0]  # Remove query params
            else:
                # No extension - typically HTML pages
                ext = None
            
            # Check blocked extensions first
            if blocked_extensions and ext and ext in blocked_extensions:
                return False
            
            # Check allowed extensions
            if allowed_extensions:
                # If no extension, typically allow (HTML pages)
                if ext is None:
                    return True
                return ext in allowed_extensions
            
            # No restrictions
            return True
            
        except Exception as e:
            logger.warning(f"Error filtering by extension for {url}: {e}")
            return True
    
    def add_include_pattern(self, pattern: str) -> None:
        """
        Add an include pattern for URL filtering.
        
        Args:
            pattern: Regex or glob pattern to include
        """
        if pattern not in self.include_patterns:
            self.include_patterns.append(pattern)
    
    def add_exclude_pattern(self, pattern: str) -> None:
        """
        Add an exclude pattern for URL filtering.
        
        Args:
            pattern: Regex or glob pattern to exclude
        """
        if pattern not in self.exclude_patterns:
            self.exclude_patterns.append(pattern)
    
    def clear_robots_cache(self) -> None:
        """Clear the robots.txt cache."""
        self._robots_cache.clear()
        self._robots_loaded.clear()


# Convenience functions for backward compatibility
def should_crawl(url: str, filters: Dict[str, Any]) -> bool:
    """
    Determine if URL should be crawled based on filter rules.
    
    Args:
        url: The URL to check
        filters: Filter configuration dictionary
        
    Returns:
        True if the URL should be crawled, False otherwise
    """
    filter_instance = URLFilter(
        respect_robots_txt=filters.get('respect_robots_txt', True),
        user_agent=filters.get('user_agent', 'CrawlerBot'),
        allowed_domains=filters.get('allowed_domains'),
        blocked_domains=filters.get('blocked_domains'),
        allowed_extensions=filters.get('allowed_extensions'),
        blocked_extensions=filters.get('blocked_extensions'),
        include_patterns=filters.get('include_patterns'),
        exclude_patterns=filters.get('exclude_patterns'),
        pattern_type=filters.get('pattern_type', 'regex')
    )
    return filter_instance.should_crawl(url)


def check_robots_txt(url: str, user_agent: str = "CrawlerBot") -> bool:
    """
    Check if URL is allowed by robots.txt rules.
    
    Args:
        url: The URL to check
        user_agent: User agent string
        
    Returns:
        True if URL is allowed, False if blocked
    """
    filter_instance = URLFilter(respect_robots_txt=True, user_agent=user_agent)
    return filter_instance.check_robots_txt(url, user_agent)


def match_pattern(url: str, pattern: str, pattern_type: str = "regex") -> bool:
    """
    Match URL against pattern (regex or glob).
    
    Args:
        url: The URL to match
        pattern: The pattern to match against
        pattern_type: Type of pattern - "regex" or "glob"
        
    Returns:
        True if URL matches pattern, False otherwise
    """
    filter_instance = URLFilter(pattern_type=pattern_type)
    return filter_instance.match_pattern(url, pattern, pattern_type)


def is_allowed_domain(url: str, allowed_domains: List[str]) -> bool:
    """
    Check if domain is allowed.
    
    Args:
        url: The URL to check
        allowed_domains: List of allowed domains
        
    Returns:
        True if domain is allowed, False otherwise
    """
    filter_instance = URLFilter(allowed_domains=allowed_domains)
    return filter_instance.is_allowed_domain(url, allowed_domains)


def is_blocked_domain(url: str, blocked_domains: List[str]) -> bool:
    """
    Check if domain is blocked.
    
    Args:
        url: The URL to check
        blocked_domains: List of blocked domains
        
    Returns:
        True if domain is blocked, False otherwise
    """
    filter_instance = URLFilter(blocked_domains=blocked_domains)
    return filter_instance.is_blocked_domain(url, blocked_domains)


def filter_by_file_extension(url: str, allowed_extensions: List[str]) -> bool:
    """
    Filter by file extension.
    
    Args:
        url: The URL to check
        allowed_extensions: List of allowed extensions
        
    Returns:
        True if extension is allowed, False otherwise
    """
    filter_instance = URLFilter(allowed_extensions=allowed_extensions)
    return filter_instance.filter_by_file_extension(url, allowed_extensions, None)
