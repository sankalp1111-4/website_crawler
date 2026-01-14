"""
URL validation utilities for the website crawler.

This module provides functions to validate URLs before crawling.
"""
import re
from urllib.parse import urlparse
from typing import Optional, List

from ..exceptions import InvalidURLError


# Maximum URL length (RFC 7230 recommends 8000, but we'll be more conservative)
MAX_URL_LENGTH = 2048

# Common malicious patterns
MALICIOUS_PATTERNS = [
    r'javascript:',
    r'data:text/html',
    r'vbscript:',
    r'file://',
    r'<script',
    r'%3Cscript',  # URL-encoded <script
    r'%3C%2Fscript',  # URL-encoded </script
]

# Valid schemes
VALID_SCHEMES = {'http', 'https'}

# Non-crawlable schemes
NON_CRAWLABLE_SCHEMES = {
    'mailto', 'javascript', 'data', 'file', 'ftp', 'tel', 'sms', 'vbscript'
}


def validate_url(url: str, max_length: int = MAX_URL_LENGTH) -> bool:
    """
    Check if URL is valid with enhanced validation.
    
    Args:
        url: The URL string to validate
        max_length: Maximum allowed URL length
        
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
    
    # Check URL length
    if len(url) > max_length:
        raise InvalidURLError(
            f"URL exceeds maximum length of {max_length} characters (got {len(url)})",
            url
        )
    
    # Check for malicious patterns
    url_lower = url.lower()
    for pattern in MALICIOUS_PATTERNS:
        if re.search(pattern, url_lower, re.IGNORECASE):
            raise InvalidURLError(
                f"URL contains potentially malicious pattern: {pattern}",
                url
            )
    
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
        
        if not scheme:
            raise InvalidURLError("URL must have a scheme", url)
        
        if scheme not in VALID_SCHEMES:
            raise InvalidURLError(
                f"URL scheme must be one of {VALID_SCHEMES}, got: {scheme}",
                url
            )
    except InvalidURLError:
        raise
    except Exception as e:
        raise InvalidURLError(f"Error validating scheme: {str(e)}", url) from e
    
    return True


def validate_domain(url: str, allowed_domains: Optional[List[str]] = None) -> bool:
    """
    Validate URL domain.
    
    Args:
        url: The URL to validate
        allowed_domains: Optional list of allowed domains
        
    Returns:
        True if the domain is valid
        
    Raises:
        InvalidURLError: If the domain is invalid
    """
    if not url:
        raise InvalidURLError("URL cannot be empty", url)
    
    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        
        if not domain:
            raise InvalidURLError("URL must have a domain", url)
        
        # Remove port if present
        if ':' in domain:
            domain = domain.split(':')[0]
        
        # Basic domain format validation
        if not re.match(r'^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?(\.[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?)*$', domain):
            raise InvalidURLError(f"Invalid domain format: {domain}", url)
        
        # Check allowed domains if specified
        if allowed_domains:
            allowed = False
            for allowed_domain in allowed_domains:
                allowed_domain_lower = allowed_domain.lower()
                if domain == allowed_domain_lower or domain.endswith('.' + allowed_domain_lower):
                    allowed = True
                    break
            
            if not allowed:
                raise InvalidURLError(
                    f"Domain {domain} is not in allowed domains list",
                    url
                )
        
    except InvalidURLError:
        raise
    except Exception as e:
        raise InvalidURLError(f"Error validating domain: {str(e)}", url) from e
    
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
        
        if scheme in NON_CRAWLABLE_SCHEMES:
            raise InvalidURLError(
                f"URL scheme '{scheme}' is not crawlable",
                url
            )
    except InvalidURLError:
        raise
    except Exception as e:
        raise InvalidURLError(f"Error checking crawlability: {str(e)}", url) from e
    
    return True


def validate_url_comprehensive(
    url: str,
    max_length: int = MAX_URL_LENGTH,
    allowed_domains: Optional[List[str]] = None
) -> bool:
    """
    Comprehensive URL validation.
    
    Performs all validation checks:
    - Basic format validation
    - Length validation
    - Malicious pattern detection
    - Scheme validation
    - Domain validation
    - Crawlability check
    
    Args:
        url: The URL to validate
        max_length: Maximum allowed URL length
        allowed_domains: Optional list of allowed domains
        
    Returns:
        True if the URL passes all validation checks
        
    Raises:
        InvalidURLError: If any validation check fails
    """
    # Basic validation
    validate_url(url, max_length=max_length)
    
    # Scheme validation
    validate_scheme(url)
    
    # Domain validation
    validate_domain(url, allowed_domains=allowed_domains)
    
    # Crawlability check
    is_crawlable(url)
    
    return True
