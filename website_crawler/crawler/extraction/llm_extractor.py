"""
LLM-based extractor for the website crawler.

This module provides utilities for extracting content using LLM-based methods.
"""
from typing import Dict, Any, Optional
import json

from .base import BaseExtractor
from ..parsing.html_parser import HTMLParser
from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("LLMExtractor", __name__)


class LLMExtractor(BaseExtractor):
    """
    LLM-based content extractor using Crawl4AI's LLM extraction capabilities.
    
    Uses language models for intelligent content extraction.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize LLM extractor.
        
        Args:
            config: Configuration dictionary with LLM settings
        """
        self.config = config or {}
        self.llm_config = self.config.get('llm', {})
        self.html_parser = HTMLParser(config)
        
        # LLM provider configuration
        self.provider = self.llm_config.get('provider', 'openai')
        self.model = self.llm_config.get('model', 'gpt-4')
        self.api_key = self._get_api_key()
        self.schema = self.llm_config.get('schema', {})
        self.temperature = self.llm_config.get('temperature', 0.0)
        
        # Check if LLM is available
        self.llm_available = self._check_llm_availability()
        
        if not self.llm_available:
            logger.warning("[LLMExtractor] LLM not available, will fallback to simple extraction")
        else:
            logger.info(f"[LLMExtractor] Initialized with provider={self.provider}, model={self.model}")
    
    def _get_api_key(self) -> Optional[str]:
        """Get API key from config or environment."""
        api_key = self.llm_config.get('api_key')
        
        if api_key and api_key.startswith('env:'):
            # Get from environment variable
            import os
            env_var = api_key[4:]  # Remove 'env:' prefix
            return os.getenv(env_var)
        
        return api_key
    
    def _check_llm_availability(self) -> bool:
        """Check if LLM extraction is available."""
        # Check if API key is available
        if not self.api_key:
            return False
        
        # Check if required packages are available
        try:
            # Try to import crawl4ai's LLM features
            from crawl4ai.extraction_strategy import LLMExtractionStrategy
            return True
        except ImportError:
            logger.debug("[LLMExtractor] Crawl4AI LLM features not available")
            return False
    
    def extract(self, url: str, html_content: str = None) -> Dict[str, Any]:
        """
        Extract content from HTML using LLM.
        
        Args:
            url: The URL to extract content from
            html_content: Optional pre-fetched HTML content
            
        Returns:
            Dictionary containing extracted content and metadata
        """
        if not html_content:
            logger.warning(f"[LLMExtractor] No HTML content provided for {url}")
            return self._empty_result()
        
        url_logger = logger.with_url(url)
        
        with url_logger.component_flow("extract", url=url):
            # Try LLM extraction if available
            if self.llm_available:
                try:
                    result = self._extract_with_llm(html_content, url)
                    if result:
                        url_logger.info(f"[LLMExtractor] LLM extraction successful: text={len(result.get('text', ''))} chars")
                        return result
                except Exception as e:
                    url_logger.warning(f"[LLMExtractor] LLM extraction failed: {e}, falling back to simple extraction")
            
            # Fallback to simple extraction
            url_logger.info("[LLMExtractor] Using fallback extraction")
            return self.html_parser.parse(html_content, url)
    
    def _extract_with_llm(self, html_content: str, url: str) -> Optional[Dict[str, Any]]:
        """
        Extract content using LLM.
        
        Args:
            html_content: HTML content
            url: Source URL
            
        Returns:
            Extracted content dictionary or None
        """
        try:
            from crawl4ai.extraction_strategy import LLMExtractionStrategy
            from crawl4ai import LLMExtractionStrategyConfig
            
            # Create extraction schema
            extraction_schema = self.schema or {
                "title": "string",
                "content": "string",
                "metadata": "object"
            }
            
            # Configure LLM extraction
            llm_config = LLMExtractionStrategyConfig(
                provider=self.provider,
                api_token=self.api_key,
                model=self.model,
                extraction_schema=extraction_schema,
                temperature=self.temperature
            )
            
            # Create extraction strategy
            strategy = LLMExtractionStrategy(config=llm_config)
            
            # Extract content
            # Note: This is a simplified example - actual implementation may vary
            # based on crawl4ai's API
            result = strategy.extract(html_content)
            
            if result and isinstance(result, dict):
                return {
                    'text': result.get('content', ''),
                    'title': result.get('title'),
                    'links': result.get('links', []),
                    'metadata': result.get('metadata', {}),
                    'confidence': result.get('confidence', 1.0)
                }
            
            return None
            
        except ImportError:
            logger.warning("[LLMExtractor] Crawl4AI LLM features not available")
            return None
        except Exception as e:
            logger.error(f"[LLMExtractor] LLM extraction error: {e}", exc_info=True)
            return None
    
    def _empty_result(self) -> Dict[str, Any]:
        """Return empty extraction result."""
        return {
            'text': '',
            'title': None,
            'links': [],
            'metadata': {},
            'confidence': 0.0
        }
    
    def validate(self) -> bool:
        """
        Validate that the extractor is properly configured.
        
        Returns:
            True if valid, False otherwise
        """
        if not self.llm_available:
            logger.warning("[LLMExtractor] LLM not available - extractor will use fallback")
            return True  # Still valid, just uses fallback
        
        if not self.api_key:
            logger.warning("[LLMExtractor] No API key configured")
            return False
        
        return True
