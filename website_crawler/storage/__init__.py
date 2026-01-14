"""
Storage module for the website crawler.

This module provides utilities for storing crawled data.
"""
from .mongo import MongoStorage
from .base import BaseStorage

__all__ = ['MongoStorage', 'BaseStorage']