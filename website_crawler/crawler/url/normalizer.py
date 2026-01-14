"""
URL normalization utilities for the website crawler.

This module provides functions to normalize URLs for consistent processing.
"""
from typing import Optional
from urllib.parse import urlparse, urlunparse, urljoin


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """
    Normalize a URL to a standard form.
    
    Args:
        url: The URL to normalize
        base_url: Optional base URL for resolving relative URLs
        
    Returns:
        Normalized URL string
    """
    if not url:
        return url
    
    url = url.strip()
    
    # Resolve relative URLs if base_url is provided
    if base_url:
        url = resolve_relative_url(url, base_url)
    
    # Remove fragment
    url = remove_fragment(url)
    
    return url


def resolve_relative_url(relative: str, base: str) -> str:
    """
    Resolve relative URLs to absolute URLs.
    
    Args:
        relative: The relative URL to resolve
        base: The base URL
        
    Returns:
        Absolute URL string
    """
    if not relative:
        return base
    
    if not base:
        return relative
    
    # If relative URL is already absolute, return it
    parsed = urlparse(relative)
    if parsed.scheme and parsed.netloc:
        return relative
    
    # Use urljoin to resolve relative URL
    return urljoin(base, relative)


def remove_fragment(url: str) -> str:
    """
    Remove URL fragment (#section).
    
    Args:
        url: The URL to process
        
    Returns:
        URL without fragment
    """
    if not url:
        return url
    
    parsed = urlparse(url)
    # Reconstruct URL without fragment
    normalized = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        ''  # Remove fragment
    ))
    
    return normalized