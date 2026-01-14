"""
URL validation utilities for the website crawler.

This module provides functions to validate URLs before crawling.
"""
from urllib.parse import urlparse
from ..exceptions import InvalidURLError


def validate_url(url: str) -> bool:
    """
    Check if URL is valid.
    
    Args:
        url: The URL string to validate
        
    Returns:
        True if the URL is valid
        
    Raises:
        InvalidURLError: If the URL is invalid
    """
    if not url or not isinstance(url, str):
        raise InvalidURLError("URL must be a non-empty string", url)
    
    url = url.strip()
    if not url:
        raise InvalidURLError("URL cannot be empty", url)
    
    try:
        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise InvalidURLError("URL must have a scheme and netloc", url)
    except Exception as e:
        raise InvalidURLError(f"Invalid URL format: {str(e)}", url) from e
    
    return True


def validate_scheme(url: str) -> bool:
    """
    Validate URL scheme (http, https).
    
    Args:
        url: The URL to validate
        
    Returns:
        True if the scheme is valid
        
    Raises:
        InvalidURLError: If the scheme is invalid
    """
    if not url:
        raise InvalidURLError("URL cannot be empty", url)
    
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        
        if scheme not in ['http', 'https']:
            raise InvalidURLError(f"URL scheme must be http or https, got: {scheme}", url)
    except InvalidURLError:
        raise
    except Exception as e:
        raise InvalidURLError(f"Error validating scheme: {str(e)}", url) from e
    
    return True


def is_crawlable(url: str) -> bool:
    """
    Check if URL should be crawled (not mailto:, javascript:, etc.).
    
    Args:
        url: The URL to check
        
    Returns:
        True if the URL is crawlable
        
    Raises:
        InvalidURLError: If the URL is not crawlable
    """
    if not url:
        raise InvalidURLError("URL cannot be empty", url)
    
    try:
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        
        # Non-crawlable schemes
        non_crawlable_schemes = [
            'mailto', 'javascript', 'data', 'file', 'ftp', 'tel', 'sms'
        ]
        
        if scheme in non_crawlable_schemes:
            raise InvalidURLError(f"URL scheme '{scheme}' is not crawlable", url)
    except InvalidURLError:
        raise
    except Exception as e:
        raise InvalidURLError(f"Error checking crawlability: {str(e)}", url) from e
    
    return True