"""
Crawl strategy module for the website crawler.

This module provides different crawling strategies.
"""
from .base import BaseStrategy
from .bfs import BFSStrategy
from .sitemap import SitemapStrategy
from .adaptive import AdaptiveStrategy

__all__ = [
    'BaseStrategy',
    'BFSStrategy',
    'SitemapStrategy',
    'AdaptiveStrategy'
]
