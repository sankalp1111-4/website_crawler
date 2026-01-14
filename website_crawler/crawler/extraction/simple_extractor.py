"""
Simple content extractor for Phase 1.

This module provides a minimal content extraction using HTML parser.
"""
from typing import Dict, Any
from ..parsing.html_parser import HTMLParser


class SimpleExtractor:
    """
    Simple content extractor using HTML parser.
    
    For Phase 1, this uses the HTML parser to extract text, links, and title.
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        Initialize simple extractor.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        self.html_parser = HTMLParser(config)
    
    def extract(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract content from HTML.
        
        Args:
            html: HTML content
            url: Source URL
            
        Returns:
            Dictionary with extracted content (text, links, title, metadata)
        """
        # Use HTML parser to extract all content
        parsed_data = self.html_parser.parse(html, url)
        
        return {
            'text': parsed_data.get('text', ''),
            'title': parsed_data.get('title'),
            'links': parsed_data.get('links', []),
            'metadata': parsed_data.get('metadata', {})
        }
