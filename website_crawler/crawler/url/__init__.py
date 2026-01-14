"""
URL management utilities for the website crawler.

This module provides utilities for URL normalization, validation, and filtering.
"""
from .normalizer import (
    normalize_url,
    resolve_relative_url,
    remove_fragment,
    remove_trailing_slash,
    remove_default_port,
    lowercase_domain,
    sort_query_params,
)
from .validator import (
    validate_url,
    validate_scheme,
    validate_domain,
    is_crawlable,
    validate_url_comprehensive,
)
from .filter import (
    URLFilter,
    should_crawl,
    check_robots_txt,
    match_pattern,
    is_allowed_domain,
    is_blocked_domain,
    filter_by_file_extension,
)

__all__ = [
    "normalize_url",
    "resolve_relative_url",
    "remove_fragment",
    "remove_trailing_slash",
    "remove_default_port",
    "lowercase_domain",
    "sort_query_params",
    "validate_url",
    "validate_scheme",
    "validate_domain",
    "is_crawlable",
    "validate_url_comprehensive",
    "URLFilter",
    "should_crawl",
    "check_robots_txt",
    "match_pattern",
    "is_allowed_domain",
    "is_blocked_domain",
    "filter_by_file_extension",
]