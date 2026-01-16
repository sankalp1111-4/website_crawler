"""
Hashing utilities for the website crawler.

This module provides utilities for generating hashes for URLs, content, and document IDs.
"""
import hashlib
from typing import Optional
from datetime import datetime


def hash_url(url: str, algorithm: str = "sha256") -> str:
    """
    Hash a URL for deduplication purposes.
    
    Args:
        url: URL to hash
        algorithm: Hash algorithm to use (md5, sha256)
        
    Returns:
        Hexadecimal hash string
        
    Example:
        >>> hash_url("https://example.com/page")
        'a1b2c3d4e5f6...'
    """
    url_bytes = url.encode("utf-8")
    
    if algorithm.lower() == "md5":
        hash_obj = hashlib.md5(url_bytes)
    elif algorithm.lower() == "sha256":
        hash_obj = hashlib.sha256(url_bytes)
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}. Use 'md5' or 'sha256'")
    
    return hash_obj.hexdigest()


def hash_content(content: str, algorithm: str = "sha256") -> str:
    """
    Hash content for change detection.
    
    Args:
        content: Content string to hash
        algorithm: Hash algorithm to use (md5, sha256)
        
    Returns:
        Hexadecimal hash string
        
    Example:
        >>> hash_content("<html>...</html>")
        'f1e2d3c4b5a6...'
    """
    content_bytes = content.encode("utf-8")
    
    if algorithm.lower() == "md5":
        hash_obj = hashlib.md5(content_bytes)
    elif algorithm.lower() == "sha256":
        hash_obj = hashlib.sha256(content_bytes)
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}. Use 'md5' or 'sha256'")
    
    return hash_obj.hexdigest()


def generate_document_id(url: str, timestamp: Optional[str] = None) -> str:
    """
    Generate a unique document ID from URL and timestamp.
    
    Args:
        url: URL of the document
        timestamp: Optional timestamp string (ISO format). If None, uses current time.
        
    Returns:
        Unique document ID string
        
    Example:
        >>> generate_document_id("https://example.com/page")
        'doc_a1b2c3d4e5f6_2024-01-01T12:00:00'
    """
    if timestamp is None:
        timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Hash the URL
    url_hash = hash_url(url, algorithm="sha256")
    
    # Use first 12 characters of hash for brevity
    short_hash = url_hash[:12]
    
    # Create document ID
    doc_id = f"doc_{short_hash}_{timestamp.replace(':', '-').replace('.', '-')}"
    
    return doc_id


def generate_source_page_id(normalized_url: str) -> str:
    """
    Generate a deterministic source_page_id from normalized URL.
    
    This ID is deterministic - same URL always produces same ID.
    Used for idempotent operations and change detection.
    
    Args:
        normalized_url: Normalized URL
        
    Returns:
        Deterministic source_page_id string
        
    Example:
        >>> generate_source_page_id("https://example.com/page")
        'src_abc123def456'
    """
    # Hash the normalized URL
    url_hash = hash_url(normalized_url, algorithm="sha256")
    
    # Use first 16 characters of hash for brevity
    short_hash = url_hash[:16]
    
    # Create deterministic source_page_id
    source_page_id = f"src_{short_hash}"
    
    return source_page_id


def generate_crawl_run_id(start_url: str, timestamp: Optional[datetime] = None) -> str:
    """
    Generate a deterministic crawl_run_id from start URL and timestamp.
    
    Args:
        start_url: Starting URL for the crawl
        timestamp: Optional timestamp. If None, uses current time.
        
    Returns:
        Crawl run ID string
        
    Example:
        >>> generate_crawl_run_id("https://example.com")
        'run_20240101_120000_abc123'
    """
    if timestamp is None:
        timestamp = datetime.utcnow()
    
    # Hash the start URL
    url_hash = hash_url(start_url, algorithm="sha256")
    short_hash = url_hash[:8]
    
    # Format timestamp
    timestamp_str = timestamp.strftime("%Y%m%d_%H%M%S")
    
    # Create crawl run ID
    crawl_run_id = f"run_{timestamp_str}_{short_hash}"
    
    return crawl_run_id


def hash_bytes(data: bytes, algorithm: str = "sha256") -> str:
    """
    Hash binary data.
    
    Args:
        data: Binary data to hash
        algorithm: Hash algorithm to use (md5, sha256)
        
    Returns:
        Hexadecimal hash string
        
    Example:
        >>> hash_bytes(b"binary data")
        'a1b2c3d4e5f6...'
    """
    if algorithm.lower() == "md5":
        hash_obj = hashlib.md5(data)
    elif algorithm.lower() == "sha256":
        hash_obj = hashlib.sha256(data)
    else:
        raise ValueError(f"Unsupported algorithm: {algorithm}. Use 'md5' or 'sha256'")
    
    return hash_obj.hexdigest()


def consistent_hash(key: str, nodes: int = 100) -> int:
    """
    Generate a consistent hash value for distributed systems.
    
    Uses MD5 hash and maps to a node index.
    
    Args:
        key: Key to hash
        nodes: Number of nodes in the system
        
    Returns:
        Node index (0 to nodes-1)
        
    Example:
        >>> consistent_hash("https://example.com/page", nodes=10)
        7
    """
    hash_value = hash_url(key, algorithm="md5")
    # Convert first 8 characters to integer
    hash_int = int(hash_value[:8], 16)
    return hash_int % nodes
