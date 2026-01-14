"""
Browser configuration for the website crawler.

This module provides browser and runtime options for crawling.
"""
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class BrowserConfig(BaseModel):
    """
    Browser configuration for crawl4ai.
    
    Minimal configuration for Phase 1.
    """
    browser_type: str = Field(default="chromium", description="Browser type (chromium, firefox, webkit)")
    headless: bool = Field(default=True, description="Run browser in headless mode")
    viewport: Optional[Dict[str, int]] = Field(default=None, description="Viewport size (width, height)")
    
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'BrowserConfig':
        """
        Create BrowserConfig from configuration dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            BrowserConfig instance
        """
        engine_config = config.get('engine', {})
        return cls(
            browser_type=engine_config.get('browser_type', 'chromium'),
            headless=engine_config.get('headless', True),
            viewport=engine_config.get('viewport', None)
        )
    
    @classmethod
    def default(cls) -> 'BrowserConfig':
        """
        Create default browser configuration.
        
        Returns:
            BrowserConfig with default values
        """
        return cls(
            browser_type="chromium",
            headless=True,
            viewport=None
        )
    
    def to_crawl4ai_config(self) -> Dict[str, Any]:
        """
        Convert to crawl4ai configuration format.
        
        Returns:
            Dictionary compatible with crawl4ai
        """
        config = {
            'headless': self.headless,
        }
        
        if self.viewport:
            config['viewport'] = self.viewport
        
        return config