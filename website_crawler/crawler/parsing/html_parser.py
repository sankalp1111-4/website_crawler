"""
HTML parsing for the website crawler.

This module provides utilities for parsing HTML content.
"""
import re
import logging
from typing import Dict, Any, List, Optional
from bs4 import BeautifulSoup, Tag
from html import unescape

from ..url.normalizer import resolve_relative_url
from ..exceptions import CrawlError
from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("HTMLParser", __name__)


class HTMLParser:
    """
    HTML parser for extracting content from HTML.
    
    Handles text extraction, link extraction, and metadata extraction.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize HTML parser.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
    
    def parse(self, html: str, url: str) -> Dict[str, Any]:
        """
        Parse HTML and extract all relevant information.
        
        Args:
            html: HTML content to parse
            url: Base URL for resolving relative links
            
        Returns:
            Dictionary with extracted data (text, links, title, metadata, images)
        """
        url_logger = logger.with_url(url)
        
        with url_logger.component_flow("parse", url=url, html_length=len(html) if html else 0):
            # Extract components (no individual logging - too granular)
            text = self.extract_text(html)
            links = self.extract_links(html, url)
            title = self.extract_title(html)
            metadata = self.extract_metadata(html)
            images = self.extract_images(html, url)
            
            result = {
                'text': text,
                'links': links,
                'title': title,
                'metadata': metadata,
                'images': images
            }
            
            # Log in simple format: [HTMLParser] Parsed HTML → text=139 chars, links=1, images=2
            text_len = len(text)
            links_count = len(links)
            images_count = len(images)
            url_logger.info(f"[HTMLParser] Parsed HTML → text={text_len} chars, links={links_count}, images={images_count}")
            
            return result
    
    def extract_text(self, html: str) -> str:
        """
        Extract text content from HTML.
        
        Args:
            html: HTML content
            
        Returns:
            Extracted text content
            
        Raises:
            CrawlError: If parsing fails critically
        """
        if not html:
            return ""
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Remove script and style elements
            for script in soup(["script", "style", "noscript"]):
                script.decompose()
            
            # Get text
            text = soup.get_text()
            
            # Clean text
            text = self.clean_text(text)
            
            return text
        except Exception as e:
            error_msg = f"Failed to extract text from HTML: {str(e)}"
            logger.error(f"[HTMLParser] {error_msg}", exc_info=True)
            # Return empty string as fallback, but log the error
            # The orchestrator will handle empty content validation
            return ""
    
    def extract_links(self, html: str, base_url: str) -> List[str]:
        """
        Extract all links from HTML.
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative links
            
        Returns:
            List of absolute URLs
        """
        if not html or not base_url:
            return []
        
        links = []
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Find all anchor tags
            for anchor in soup.find_all('a', href=True):
                href = anchor['href']
                if href:
                    # Resolve relative URLs
                    absolute_url = resolve_relative_url(href, base_url)
                    if absolute_url and absolute_url not in links:
                        links.append(absolute_url)
        except Exception as e:
            error_msg = f"Failed to extract links from HTML: {str(e)}"
            logger.warning(error_msg, exc_info=True)
            # Return empty list as fallback, but log the warning
        
        return links
    
    def extract_title(self, html: str) -> Optional[str]:
        """
        Extract page title from HTML.
        
        Args:
            html: HTML content
            
        Returns:
            Page title or None
        """
        if not html:
            return None
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            title_tag = soup.find('title')
            if title_tag:
                title = title_tag.get_text().strip()
                return title if title else None
        except Exception as e:
            error_msg = f"Failed to extract title from HTML: {str(e)}"
            logger.warning(error_msg, exc_info=True)
            # Return None as fallback
        
        return None
    
    def extract_metadata(self, html: str) -> Dict[str, Any]:
        """
        Extract basic metadata from HTML.
        
        Args:
            html: HTML content
            
        Returns:
            Dictionary with metadata
        """
        metadata = {}
        
        if not html:
            return metadata
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Extract meta tags
            for meta in soup.find_all('meta'):
                name = meta.get('name') or meta.get('property')
                content = meta.get('content')
                
                if name and content:
                    # Normalize name (lowercase, replace - with _)
                    key = name.lower().replace('-', '_')
                    metadata[key] = content
            
            # Extract description
            description_tag = soup.find('meta', attrs={'name': 'description'})
            if description_tag and description_tag.get('content'):
                metadata['description'] = description_tag['content']
            
        except Exception as e:
            error_msg = f"Failed to extract metadata from HTML: {str(e)}"
            logger.warning(error_msg, exc_info=True)
            # Return empty dict as fallback
        
        return metadata
    
    def extract_images(self, html: str, base_url: str) -> List[str]:
        """
        Extract all image URLs from HTML.
        
        Handles:
        - src attribute (standard image source)
        - srcset attribute (responsive images, extracts all URLs)
        - data-src attribute (lazy-loaded images)
        
        Args:
            html: HTML content
            base_url: Base URL for resolving relative URLs
            
        Returns:
            List of absolute image URLs (duplicates removed)
        """
        if not html or not base_url:
            return []
        
        images = set()  # Use set to automatically remove duplicates
        
        try:
            soup = BeautifulSoup(html, 'lxml')
            
            # Find all img tags
            for img in soup.find_all('img'):
                # Extract from src attribute
                src = img.get('src')
                if src:
                    absolute_url = resolve_relative_url(src, base_url)
                    if absolute_url:
                        images.add(absolute_url)
                
                # Extract from srcset attribute (responsive images)
                # srcset format: "image1.jpg 1x, image2.jpg 2x" or "image1.jpg 300w, image2.jpg 600w"
                srcset = img.get('srcset')
                if srcset:
                    # Parse srcset: split by comma, then extract URL (before space or comma)
                    for srcset_item in srcset.split(','):
                        srcset_item = srcset_item.strip()
                        # Extract URL (everything before the first space)
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
                
                # Also check data-srcset (lazy-loaded responsive images)
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
                
                # Check data-srcset in source elements
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
            error_msg = f"Failed to extract images from HTML: {str(e)}"
            logger.warning(error_msg, exc_info=True)
            # Return empty list as fallback, but log the warning
        
        # Convert set to sorted list for consistent output
        return sorted(list(images))
    
    def clean_text(self, text: str) -> str:
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
        text = re.sub(r'\s+', ' ', text)
        
        # Normalize line breaks
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Strip leading/trailing whitespace
        text = text.strip()
        
        return text