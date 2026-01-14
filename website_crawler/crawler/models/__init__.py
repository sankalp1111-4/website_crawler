"""
Models module for the website crawler.

This module defines data models for the crawler.
"""
from .raw_page import RawPage
from .document import Document

__all__ = ['RawPage', 'Document']