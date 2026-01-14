"""
Raw page model for the website crawler.

This module defines the data model for raw crawled pages.
"""
from datetime import datetime
from typing import Dict, Optional
from pydantic import BaseModel, Field, field_validator
from urllib.parse import urlparse


class RawPage(BaseModel):
    """
    Model representing a raw crawled page.
    
    This model stores the raw HTML content and metadata from a crawled page.
    """
    url: str = Field(..., description="The URL of the page")
    html: str = Field(..., description="Raw HTML content")
    status_code: int = Field(..., description="HTTP status code")
    headers: Dict[str, str] = Field(default_factory=dict, description="HTTP response headers")
    crawl_timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the page was crawled")
    
    @field_validator('url')
    @classmethod
    def validate_url(cls, v: str) -> str:
        """Validate URL format."""
        if not v:
            raise ValueError("URL cannot be empty")
        parsed = urlparse(v)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL format: {v}")
        return v
    
    @field_validator('status_code')
    @classmethod
    def validate_status_code(cls, v: int) -> int:
        """Validate status code is in valid range."""
        if not (100 <= v <= 599):
            raise ValueError(f"Invalid HTTP status code: {v}")
        return v
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }