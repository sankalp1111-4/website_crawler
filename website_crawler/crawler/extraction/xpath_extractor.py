"""
XPath extractor for the website crawler.

This module provides utilities for extracting content using XPath.
"""
from typing import Dict, Any, List, Optional
from lxml import html, etree
from html import unescape

from .base import BaseExtractor
from ..parsing.html_parser import HTMLParser
from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("XPathExtractor", __name__)


class XPathExtractor(BaseExtractor):
    """
    XPath-based content extractor.
    
    Uses XPath expressions to extract specific content from HTML.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize XPath extractor.
        
        Args:
            config: Configuration dictionary with XPath expressions
        """
        self.config = config or {}
        self.xpaths = self.config.get('xpaths', {})
        self.html_parser = HTMLParser(config)
        
        logger.info("[XPathExtractor] Initialized")
    
    def extract(self, url: str, html_content: str = None) -> Dict[str, Any]:
        """
        Extract content from HTML using XPath expressions.
        
        Args:
            url: The URL to extract content from
            html_content: Optional pre-fetched HTML content
            
        Returns:
            Dictionary containing extracted content and metadata
        """
        if not html_content:
            logger.warning(f"[XPathExtractor] No HTML content provided for {url}")
            return self._empty_result()
        
        url_logger = logger.with_url(url)
        
        with url_logger.component_flow("extract", url=url):
            try:
                # Parse HTML with lxml
                tree = html.fromstring(html_content)
                
                # Extract main content
                main_content = self._extract_with_xpaths(
                    tree,
                    self.xpaths.get('main_content', []),
                    'main_content'
                )
                
                # Extract title
                title = self._extract_with_xpaths(
                    tree,
                    self.xpaths.get('title', ['//h1', '//title']),
                    'title',
                    single=True
                )
                
                # Extract metadata
                metadata = self._extract_metadata(tree)
                
                # Extract links
                links = self._extract_links(tree, url)
                
                # Clean text content
                text = self._clean_text(main_content) if main_content else ""
                
                result = {
                    'text': text,
                    'title': title,
                    'links': links,
                    'metadata': metadata,
                    'html': main_content if self.config.get('include_html', False) else None
                }
                
                url_logger.info(f"[XPathExtractor] Extracted content: text={len(text)} chars, links={len(links)}")
                
                return result
                
            except Exception as e:
                url_logger.error(f"[XPathExtractor] Extraction failed: {e}", exc_info=True)
                # Fallback to simple extraction
                return self.html_parser.parse(html_content, url)
    
    def _extract_with_xpaths(
        self,
        tree: etree._Element,
        xpaths: List[str],
        field_name: str,
        single: bool = False
    ) -> Optional[str]:
        """
        Extract content using XPath expressions with fallback.
        
        Args:
            tree: lxml ElementTree object
            xpaths: List of XPath expressions to try
            field_name: Name of the field being extracted
            single: If True, return first match; if False, combine all matches
            
        Returns:
            Extracted content or None
        """
        if not xpaths:
            return None
        
        matches = []
        
        for xpath in xpaths:
            try:
                elements = tree.xpath(xpath)
                if elements:
                    if single:
                        # Return first match
                        return self._get_element_text(elements[0])
                    else:
                        # Collect all matches
                        for elem in elements:
                            text = self._get_element_text(elem)
                            if text:
                                matches.append(text)
            except Exception as e:
                logger.debug(f"[XPathExtractor] XPath '{xpath}' failed: {e}")
                continue
        
        if matches:
            return ' '.join(matches) if not single else matches[0]
        
        return None
    
    def _get_element_text(self, element: etree._Element) -> str:
        """
        Get text content from an element.
        
        Args:
            element: lxml Element object
            
        Returns:
            Text content
        """
        # Get text content and tail
        text_parts = []
        
        if element.text:
            text_parts.append(element.text.strip())
        
        # Get text from children
        for child in element:
            if child.text:
                text_parts.append(child.text.strip())
            if child.tail:
                text_parts.append(child.tail.strip())
        
        return ' '.join(text_parts)
    
    def _extract_metadata(self, tree: etree._Element) -> Dict[str, Any]:
        """
        Extract metadata from HTML.
        
        Args:
            tree: lxml ElementTree object
            
        Returns:
            Dictionary with metadata
        """
        metadata = {}
        
        # Extract meta tags using XPath if configured
        meta_xpaths = self.xpaths.get('metadata', {})
        
        if isinstance(meta_xpaths, dict):
            for key, xpath in meta_xpaths.items():
                try:
                    elements = tree.xpath(xpath)
                    if elements:
                        # Get text or attribute value
                        elem = elements[0]
                        value = elem.text or elem.get('content') or ''
                        if value:
                            metadata[key] = value.strip()
                except Exception as e:
                    logger.debug(f"[XPathExtractor] Metadata XPath '{xpath}' failed: {e}")
        
        # Fallback to standard meta tag extraction
        if not metadata:
            meta_elements = tree.xpath("//meta[@name or @property]")
            for meta in meta_elements:
                name = meta.get('name') or meta.get('property')
                content = meta.get('content')
                if name and content:
                    key = name.lower().replace('-', '_')
                    metadata[key] = content
        
        return metadata
    
    def _extract_links(self, tree: etree._Element, base_url: str) -> List[str]:
        """
        Extract links from HTML.
        
        Args:
            tree: lxml ElementTree object
            base_url: Base URL for resolving relative links
            
        Returns:
            List of absolute URLs
        """
        links = []
        
        # Use link XPath if configured
        link_xpath = self.xpaths.get('links', '//a[@href]')
        
        try:
            anchors = tree.xpath(link_xpath)
            for anchor in anchors:
                href = anchor.get('href')
                if href:
                    # Resolve relative URLs
                    from ..url.normalizer import resolve_relative_url
                    absolute_url = resolve_relative_url(href, base_url)
                    if absolute_url and absolute_url not in links:
                        links.append(absolute_url)
        except Exception as e:
            logger.debug(f"[XPathExtractor] Link extraction failed: {e}")
        
        return links
    
    def _clean_text(self, text: str) -> str:
        """
        Clean and normalize text content.
        
        Args:
            text: Raw text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Decode HTML entities
        text = unescape(text)
        
        # Normalize whitespace
        import re
        text = re.sub(r'\s+', ' ', text)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = text.strip()
        
        return text
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty extraction result."""
        return {
            'text': '',
            'title': None,
            'links': [],
            'metadata': {},
            'html': None
        }
    
    def validate(self) -> bool:
        """
        Validate that the extractor is properly configured.
        
        Returns:
            True if valid, False otherwise
        """
        # XPath extractor is always valid (can work without XPaths)
        return True
