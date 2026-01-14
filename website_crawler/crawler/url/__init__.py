"""
URL management utilities for the website crawler.

This module provides utilities for URL normalization, validation, and filtering.
"""
from .normalizer import normalize_url, resolve_relative_url, remove_fragment
from .validator import validate_url, validate_scheme, is_crawlable

__all__ = [
    "normalize_url",
    "resolve_relative_url",
    "remove_fragment",
    "validate_url",
    "validate_scheme",
    "is_crawlable",
]