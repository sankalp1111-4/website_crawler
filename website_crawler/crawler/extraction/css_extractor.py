"""
CSS selector extractor for the website crawler.

This module provides utilities for extracting content using CSS selectors.
"""
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup, Tag
from html import unescape

from .base import BaseExtractor
from ..parsing.html_parser import HTMLParser
from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("CSSExtractor", __name__)


class CSSExtractor(BaseExtractor):
    """
    CSS selector-based content extractor.
    
    Uses CSS selectors to extract specific content from HTML.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize CSS extractor.
        
        Args:
            config: Configuration dictionary with selectors
        """
        self.config = config or {}
        self.selectors = self.config.get('selectors', {})
        self.html_parser = HTMLParser(config)
        
        logger.info("[CSSExtractor] Initialized")
    
    def extract(self, url: str, html_content: str = None) -> Dict[str, Any]:
        """
        Extract content from HTML using CSS selectors.
        
        Args:
            url: The URL to extract content from
            html_content: Optional pre-fetched HTML content
            
        Returns:
            Dictionary containing extracted content and metadata
        """
        if not html_content:
            logger.warning(f"[CSSExtractor] No HTML content provided for {url}")
            return self._empty_result()
        
        url_logger = logger.with_url(url)
        
        with url_logger.component_flow("extract", url=url):
            try:
                soup = BeautifulSoup(html_content, 'lxml')
                
                # Get content selectors - support both 'content' and 'main_content' keys
                # Also support both string and list formats
                content_selectors = self.selectors.get('content') or self.selectors.get('main_content', [])
                if isinstance(content_selectors, str):
                    content_selectors = [content_selectors]
                elif not isinstance(content_selectors, list):
                    content_selectors = []
                
                # Extract main content
                main_content = self._extract_with_selectors(
                    soup,
                    content_selectors,
                    'main_content'
                )
                
                # Get title selectors - support both string and list formats
                title_selectors = self.selectors.get('title', ['h1', 'title'])
                if isinstance(title_selectors, str):
                    title_selectors = [title_selectors]
                elif not isinstance(title_selectors, list):
                    title_selectors = ['h1', 'title']
                
                # Extract title
                title = self._extract_with_selectors(
                    soup,
                    title_selectors,
                    'title',
                    single=True
                )
                
                # Extract metadata
                metadata = self._extract_metadata(soup)
                
                # Extract links
                links = self._extract_links(soup, url)
                
                # Extract images
                images = self._extract_images(soup, url)
                
                # Clean text content
                text = self._clean_text(main_content) if main_content else ""
                
                # Fallback: If no content was extracted and no selectors were provided,
                # extract all text from body as a fallback
                if not text and not content_selectors:
                    url_logger.debug("[CSSExtractor] No selectors provided, extracting all body text as fallback")
                    body = soup.find('body')
                    if body:
                        text = self._clean_text(self._get_element_text(body))
                    else:
                        # If no body tag, extract from html root
                        text = self._clean_text(self._get_element_text(soup))
                
                # If selectors were provided but didn't match, try fallback extraction
                if not text and content_selectors:
                    url_logger.debug("[CSSExtractor] Selectors didn't match, falling back to body text extraction")
                    body = soup.find('body')
                    if body:
                        text = self._clean_text(self._get_element_text(body))
                    else:
                        text = self._clean_text(self._get_element_text(soup))
                
                result = {
                    'text': text,
                    'title': title,
                    'links': links,
                    'images': images,
                    'metadata': metadata,
                    'html': main_content if self.config.get('include_html', False) else None
                }
                
                url_logger.info(f"[CSSExtractor] Extracted content: text={len(text)} chars, links={len(links)}, images={len(images)}")
                
                return result
                
            except Exception as e:
                url_logger.error(f"[CSSExtractor] Extraction failed: {e}", exc_info=True)
                # Fallback to simple extraction
                return self.html_parser.parse(html_content, url)
    
    def _extract_with_selectors(
        self,
        soup: BeautifulSoup,
        selectors: List[str],
        field_name: str,
        single: bool = False
    ) -> Optional[str]:
        """
        Extract content using CSS selectors with fallback.
        
        Args:
            soup: BeautifulSoup object
            selectors: List of CSS selectors to try (can be empty)
            field_name: Name of the field being extracted
            single: If True, return first match; if False, combine all matches
            
        Returns:
            Extracted content or None
        """
        if not selectors:
            return None
        
        matches = []
        
        for selector in selectors:
            try:
                elements = soup.select(selector)
                if elements:
                    if single:
                        # Return first match
                        text = self._get_element_text(elements[0])
                        if text and text.strip():
                            return text
                    else:
                        # Collect all matches
                        for elem in elements:
                            text = self._get_element_text(elem)
                            if text and text.strip():
                                matches.append(text)
            except Exception as e:
                logger.debug(f"[CSSExtractor] Selector '{selector}' failed: {e}")
                continue
        
        if matches:
            combined = ' '.join(matches) if not single else matches[0]
            return combined if combined.strip() else None
        
        return None
    
    def _get_element_text(self, element: Tag) -> str:
        """
        Get text content from an element.
        
        Args:
            element: BeautifulSoup Tag element
            
        Returns:
            Text content
        """
        # Remove script and style elements
        for script in element(["script", "style", "noscript"]):
            script.decompose()
        
        return element.get_text(separator=' ', strip=True)
    
    def _extract_metadata(self, soup: BeautifulSoup) -> Dict[str, Any]:
        """
        Extract metadata from HTML.
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dictionary with metadata
        """
        metadata = {}
        
        # Extract meta tags using selectors if configured
        meta_selectors = self.selectors.get('metadata', {})
        
        if isinstance(meta_selectors, dict):
            for key, selector in meta_selectors.items():
                try:
                    elements = soup.select(selector)
                    if elements:
                        # Try to get content attribute or text
                        elem = elements[0]
                        value = elem.get('content') or elem.get_text(strip=True)
                        if value:
                            metadata[key] = value
                except Exception as e:
                    logger.debug(f"[CSSExtractor] Metadata selector '{selector}' failed: {e}")
        
        # Fallback to standard meta tag extraction
        if not metadata:
            for meta in soup.find_all('meta'):
                name = meta.get('name') or meta.get('property')
                content = meta.get('content')
                if name and content:
                    key = name.lower().replace('-', '_')
                    metadata[key] = content
        
        return metadata
    
    def _extract_links(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract links from HTML.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
            
        Returns:
            List of absolute URLs
        """
        links = []
        
        # Use link selector if configured
        link_selector = self.selectors.get('links', 'a[href]')
        
        try:
            for anchor in soup.select(link_selector):
                href = anchor.get('href')
                if href:
                    # Resolve relative URLs
                    from ..url.normalizer import resolve_relative_url
                    absolute_url = resolve_relative_url(href, base_url)
                    if absolute_url and absolute_url not in links:
                        links.append(absolute_url)
        except Exception as e:
            logger.debug(f"[CSSExtractor] Link extraction failed: {e}")
        
        return links
    
    def _extract_images(self, soup: BeautifulSoup, base_url: str) -> List[str]:
        """
        Extract image URLs from HTML.
        
        Handles src, srcset, data-src, and data-srcset attributes.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of absolute image URLs (duplicates removed)
        """
        images = set()  # Use set to automatically remove duplicates
        
        try:
            from ..url.normalizer import resolve_relative_url
            
            # Find all img tags
            for img in soup.find_all('img'):
                # Extract from src attribute
                src = img.get('src')
                if src:
                    absolute_url = resolve_relative_url(src, base_url)
                    if absolute_url:
                        images.add(absolute_url)
                
                # Extract from srcset attribute (responsive images)
                srcset = img.get('srcset')
                if srcset:
                    for srcset_item in srcset.split(','):
                        srcset_item = srcset_item.strip()
                        url_part = srcset_item.split()[0] if srcset_item.split() else srcset_item
                        if url_part:
                            absolute_url = resolve_relative_url(url_part, base_url)
                            if absolute_url:
                                images.add(absolute_url)
                
                # Extract from data-src attribute (lazy-loaded images)
                data_src = img.get('data-src')
                if data_src:
                    absolute_url = resolve_relative_url(data_src, base_url)
                    if absolute_url:
                        images.add(absolute_url)
                
                # Extract from data-srcset (lazy-loaded responsive images)
                data_srcset = img.get('data-srcset')
                if data_srcset:
                    for srcset_item in data_srcset.split(','):
                        srcset_item = srcset_item.strip()
                        url_part = srcset_item.split()[0] if srcset_item.split() else srcset_item
                        if url_part:
                            absolute_url = resolve_relative_url(url_part, base_url)
                            if absolute_url:
                                images.add(absolute_url)
            
            # Also check picture/source elements (for responsive images)
            for source in soup.find_all('source'):
                srcset = source.get('srcset')
                if srcset:
                    for srcset_item in srcset.split(','):
                        srcset_item = srcset_item.strip()
                        url_part = srcset_item.split()[0] if srcset_item.split() else srcset_item
                        if url_part:
                            absolute_url = resolve_relative_url(url_part, base_url)
                            if absolute_url:
                                images.add(absolute_url)
                
                data_srcset = source.get('data-srcset')
                if data_srcset:
                    for srcset_item in data_srcset.split(','):
                        srcset_item = srcset_item.strip()
                        url_part = srcset_item.split()[0] if srcset_item.split() else srcset_item
                        if url_part:
                            absolute_url = resolve_relative_url(url_part, base_url)
                            if absolute_url:
                                images.add(absolute_url)
        except Exception as e:
            logger.debug(f"[CSSExtractor] Image extraction failed: {e}")
        
        # Convert set to sorted list for consistent output
        return sorted(list(images))
    
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
            'images': [],
            'metadata': {},
            'html': None
        }
    
    def validate(self) -> bool:
        """
        Validate that the extractor is properly configured.
        
        Returns:
            True if valid, False otherwise
        """
        # CSS extractor is always valid (can work without selectors)
        return True
