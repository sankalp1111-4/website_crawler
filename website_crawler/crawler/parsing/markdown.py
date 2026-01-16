"""
Markdown generation for the website crawler.

This module provides utilities for generating Markdown content.
"""
from typing import Optional, Dict, Any
import re

from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("MarkdownConverter", __name__)


class MarkdownConverter:
    """
    HTML to Markdown converter.
    
    Converts HTML content to clean Markdown format.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize markdown converter.
        
        Args:
            config: Optional configuration dictionary
        """
        self.config = config or {}
        
        # Try to use markdownify if available
        self._markdownify_available = self._check_markdownify()
        
        if not self._markdownify_available:
            logger.info("[MarkdownConverter] markdownify not available, using basic conversion")
        else:
            logger.info("[MarkdownConverter] Initialized with markdownify")
    
    def _check_markdownify(self) -> bool:
        """Check if markdownify is available."""
        try:
            import markdownify
            return True
        except ImportError:
            return False
    
    def convert(self, html: str, url: Optional[str] = None) -> str:
        """
        Convert HTML to Markdown.
        
        Args:
            html: HTML content to convert
            url: Optional source URL for logging
            
        Returns:
            Markdown content
        """
        if not html:
            return ""
        
        url_logger = logger.with_url(url) if url else logger
        
        with url_logger.component_flow("convert", url=url, html_length=len(html)):
            try:
                if self._markdownify_available:
                    return self._convert_with_markdownify(html)
                else:
                    return self._convert_basic(html)
            except Exception as e:
                url_logger.error(f"[MarkdownConverter] Conversion failed: {e}", exc_info=True)
                # Fallback to basic conversion
                return self._convert_basic(html)
    
    def _convert_with_markdownify(self, html: str) -> str:
        """
        Convert HTML to Markdown using markdownify library.
        
        Args:
            html: HTML content
            
        Returns:
            Markdown content
        """
        import markdownify
        
        # Configure markdownify options
        options = {
            'heading_style': self.config.get('heading_style', 'ATX'),
            'bullets': self.config.get('bullets', '-'),
            'strip': self.config.get('strip', ['script', 'style']),
            'convert': self.config.get('convert', ['a', 'img', 'p', 'br', 'strong', 'em', 'code', 'pre', 'blockquote', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6'])
        }
        
        markdown = markdownify.markdownify(html, **options)
        
        # Clean up markdown
        markdown = self._clean_markdown(markdown)
        
        return markdown
    
    def _convert_basic(self, html: str) -> str:
        """
        Basic HTML to Markdown conversion (fallback).
        
        Args:
            html: HTML content
            
        Returns:
            Markdown content
        """
        from bs4 import BeautifulSoup
        from html import unescape
        
        soup = BeautifulSoup(html, 'lxml')
        
        # Remove script and style elements
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        
        # Convert headings
        for i in range(1, 7):
            for heading in soup.find_all(f'h{i}'):
                text = heading.get_text(strip=True)
                if text:
                    heading.replace_with(f"{'#' * i} {text}\n\n")
        
        # Convert links
        for link in soup.find_all('a', href=True):
            text = link.get_text(strip=True)
            href = link.get('href', '')
            if text and href:
                link.replace_with(f"[{text}]({href})")
        
        # Convert images
        for img in soup.find_all('img', src=True):
            alt = img.get('alt', '')
            src = img.get('src', '')
            if src:
                img.replace_with(f"![{alt}]({src})\n")
        
        # Convert lists
        for ul in soup.find_all('ul'):
            items = []
            for li in ul.find_all('li', recursive=False):
                text = li.get_text(strip=True)
                if text:
                    items.append(f"- {text}")
            if items:
                ul.replace_with('\n'.join(items) + '\n\n')
        
        for ol in soup.find_all('ol'):
            items = []
            for i, li in enumerate(ol.find_all('li', recursive=False), 1):
                text = li.get_text(strip=True)
                if text:
                    items.append(f"{i}. {text}")
            if items:
                ol.replace_with('\n'.join(items) + '\n\n')
        
        # Convert code blocks
        for pre in soup.find_all('pre'):
            code = pre.get_text()
            pre.replace_with(f"```\n{code}\n```\n\n")
        
        for code in soup.find_all('code'):
            text = code.get_text()
            if code.parent.name != 'pre':  # Don't double-process code in pre
                code.replace_with(f"`{text}`")
        
        # Convert blockquotes
        for blockquote in soup.find_all('blockquote'):
            text = blockquote.get_text(strip=True)
            if text:
                blockquote.replace_with(f"> {text}\n\n")
        
        # Convert paragraphs
        for p in soup.find_all('p'):
            text = p.get_text(strip=True)
            if text:
                p.replace_with(f"{text}\n\n")
        
        # Get final text
        text = soup.get_text(separator='\n')
        
        # Clean up
        text = unescape(text)
        text = re.sub(r'\n{3,}', '\n\n', text)  # Remove excessive newlines
        text = text.strip()
        
        return text
    
    def _clean_markdown(self, markdown: str) -> str:
        """
        Clean and normalize markdown content.
        
        Args:
            markdown: Raw markdown content
            
        Returns:
            Cleaned markdown
        """
        if not markdown:
            return ""
        
        # Remove excessive newlines
        markdown = re.sub(r'\n{3,}', '\n\n', markdown)
        
        # Remove trailing whitespace
        lines = [line.rstrip() for line in markdown.split('\n')]
        markdown = '\n'.join(lines)
        
        # Remove leading/trailing newlines
        markdown = markdown.strip()
        
        return markdown
