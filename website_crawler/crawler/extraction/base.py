"""
Base extraction interface for the website crawler.

This module defines the base interface for content extraction.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseExtractor(ABC):
    """
    Base class for all content extractors.
    
    All extractors (CSS, XPath, LLM) must inherit from this class
    and implement the required methods.
    """
    
    @abstractmethod
    def extract(self, url: str, html_content: str = None) -> Dict[str, Any]:
        """
        Extract content from a URL or HTML content.
        
        Args:
            url: The URL to extract content from
            html_content: Optional pre-fetched HTML content
            
        Returns:
            Dictionary containing extracted content and metadata
        """
        pass
    
    @abstractmethod
    def validate(self) -> bool:
        """
        Validate that the extractor is properly configured.
        
        Returns:
            True if the extractor is valid, False otherwise
        """
        pass
