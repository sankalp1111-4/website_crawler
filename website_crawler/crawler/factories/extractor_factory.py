"""
Factory for creating content extractors.

This module provides a factory to create extractor instances based on configuration.
Supports CSS, XPath, and LLM extractors.
"""

from typing import Dict, Type, Any
from crawler.extraction.base import BaseExtractor
from crawler.extraction.css_extractor import CSSExtractor
from crawler.extraction.xpath_extractor import XPathExtractor
from crawler.extraction.llm_extractor import LLMExtractor


class ExtractorFactory:
    """
    Factory for creating content extractors.
    
    This factory creates the appropriate extractor instance based on the
    extractor type specified in the configuration.
    """
    
    # Registry of available extractors
    _extractors: Dict[str, Type[BaseExtractor]] = {
        "css": CSSExtractor,
        "xpath": XPathExtractor,
        "llm": LLMExtractor,
    }
    
    @classmethod
    def create(cls, extractor_type: str, **kwargs: Any) -> BaseExtractor:
        """
        Create an extractor based on type.
        
        Args:
            extractor_type: Type of extractor ("css", "xpath", or "llm")
            **kwargs: Additional configuration parameters for the extractor
                     (e.g., selectors for CSS, model for LLM)
        
        Returns:
            Instance of the requested extractor implementing BaseExtractor
        
        Raises:
            ValueError: If extractor_type is not supported
            TypeError: If the extractor class cannot be instantiated with provided kwargs
        
        Example:
            >>> # Create a CSS extractor
            >>> extractor = ExtractorFactory.create("css", selectors=["article", ".content"])
            >>> 
            >>> # Create an LLM extractor
            >>> extractor = ExtractorFactory.create("llm", model="gpt-4", prompt="Extract main content")
        """
        if extractor_type not in cls._extractors:
            available = ", ".join(cls._extractors.keys())
            raise ValueError(
                f"Unknown extractor type: '{extractor_type}'. "
                f"Available types: {available}"
            )
        
        extractor_class = cls._extractors[extractor_type]
        
        try:
            return extractor_class(**kwargs)
        except Exception as e:
            raise TypeError(
                f"Failed to create {extractor_type} extractor with provided parameters: {e}"
            ) from e
    
    @classmethod
    def register(cls, extractor_type: str, extractor_class: Type[BaseExtractor]) -> None:
        """
        Register a new extractor type.
        
        This allows extending the factory with custom extractors at runtime.
        
        Args:
            extractor_type: Name identifier for the extractor type
            extractor_class: Class that implements BaseExtractor
        
        Example:
            >>> from crawler.extraction.custom_extractor import CustomExtractor
            >>> ExtractorFactory.register("custom", CustomExtractor)
            >>> extractor = ExtractorFactory.create("custom", param1="value")
        """
        if not issubclass(extractor_class, BaseExtractor):
            raise TypeError(
                f"Extractor class must inherit from BaseExtractor, "
                f"got {extractor_class.__name__}"
            )
        cls._extractors[extractor_type] = extractor_class
    
    @classmethod
    def get_available_types(cls) -> list[str]:
        """
        Get list of available extractor types.
        
        Returns:
            List of extractor type names that can be created
        """
        return list(cls._extractors.keys())

