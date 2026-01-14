"""
URL normalization utilities for the website crawler.

This module provides functions to normalize URLs for consistent processing.
"""
from typing import Optional, Dict, Any
from urllib.parse import urlparse, urlunparse, urljoin, parse_qs, urlencode


def normalize_url(
    url: str,
    base_url: Optional[str] = None,
    remove_trailing_slash: bool = True,
    remove_default_port: bool = True,
    lowercase_domain: bool = True,
    sort_query_params: bool = True,
    remove_fragment: bool = True
) -> str:
    """
    Normalize a URL to a standard form with enhanced options.
    
    This function is idempotent - calling it multiple times with the same
    input will produce the same output.
    
    Args:
        url: The URL to normalize
        base_url: Optional base URL for resolving relative URLs
        remove_trailing_slash: Whether to remove trailing slash from path
        remove_default_port: Whether to remove default ports (80, 443)
        lowercase_domain: Whether to lowercase the domain
        sort_query_params: Whether to sort query parameters
        remove_fragment: Whether to remove URL fragment
        
    Returns:
        Normalized URL string
    """
    if not url:
        return url
    
    url = url.strip()
    
    # Resolve relative URLs if base_url is provided
    if base_url:
        url = resolve_relative_url(url, base_url)
    
    try:
        parsed = urlparse(url)
        
        # Normalize scheme (lowercase)
        scheme = parsed.scheme.lower() if parsed.scheme else ''
        
        # Normalize netloc (domain)
        netloc = parsed.netloc
        if netloc:
            if lowercase_domain:
                netloc = netloc.lower()
            
            # Remove default ports
            if remove_default_port:
                if ':' in netloc:
                    host, port = netloc.rsplit(':', 1)
                    port_int = int(port)
                    if (scheme == 'http' and port_int == 80) or \
                       (scheme == 'https' and port_int == 443):
                        netloc = host
        
        # Normalize path
        path = parsed.path
        if remove_trailing_slash and path and path != '/' and path.endswith('/'):
            path = path.rstrip('/')
        
        # Normalize query parameters
        query = parsed.query
        if sort_query_params and query:
            # Parse and sort query parameters
            query_params = parse_qs(query, keep_blank_values=True)
            # Sort by key
            sorted_params = sorted(query_params.items())
            # Rebuild query string
            query = urlencode(sorted_params, doseq=True)
        
        # Normalize fragment
        fragment = '' if remove_fragment else (parsed.fragment or '')
        
        # Reconstruct normalized URL
        normalized = urlunparse((
            scheme,
            netloc,
            path,
            parsed.params,
            query,
            fragment
        ))
        
        return normalized
        
    except Exception:
        # If parsing fails, return original URL
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


def remove_trailing_slash(url: str) -> str:
    """
    Remove trailing slash from URL path.
    
    Args:
        url: The URL to process
        
    Returns:
        URL without trailing slash (unless path is just '/')
    """
    if not url:
        return url
    
    parsed = urlparse(url)
    path = parsed.path
    
    if path and path != '/' and path.endswith('/'):
        path = path.rstrip('/')
    
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))


def remove_default_port(url: str) -> str:
    """
    Remove default ports (80 for http, 443 for https) from URL.
    
    Args:
        url: The URL to process
        
    Returns:
        URL without default ports
    """
    if not url:
        return url
    
    parsed = urlparse(url)
    netloc = parsed.netloc
    
    if netloc and ':' in netloc:
        host, port = netloc.rsplit(':', 1)
        try:
            port_int = int(port)
            scheme = parsed.scheme.lower()
            if (scheme == 'http' and port_int == 80) or \
               (scheme == 'https' and port_int == 443):
                netloc = host
        except ValueError:
            pass  # Invalid port, keep as is
    
    return urlunparse((
        parsed.scheme,
        netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))


def lowercase_domain(url: str) -> str:
    """
    Convert domain to lowercase.
    
    Args:
        url: The URL to process
        
    Returns:
        URL with lowercase domain
    """
    if not url:
        return url
    
    parsed = urlparse(url)
    netloc = parsed.netloc.lower() if parsed.netloc else ''
    
    return urlunparse((
        parsed.scheme,
        netloc,
        parsed.path,
        parsed.params,
        parsed.query,
        parsed.fragment
    ))


def sort_query_params(url: str) -> str:
    """
    Sort query parameters alphabetically.
    
    Args:
        url: The URL to process
        
    Returns:
        URL with sorted query parameters
    """
    if not url:
        return url
    
    parsed = urlparse(url)
    query = parsed.query
    
    if not query:
        return url
    
    # Parse and sort query parameters
    query_params = parse_qs(query, keep_blank_values=True)
    sorted_params = sorted(query_params.items())
    sorted_query = urlencode(sorted_params, doseq=True)
    
    return urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        sorted_query,
        parsed.fragment
    ))
