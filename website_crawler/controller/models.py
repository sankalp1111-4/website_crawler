"""Simplified public API models - intent-based configuration only."""
from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class ClientCrawlRequest(BaseModel):
    """Public API request - intent-based only."""
    
    url: HttpUrl = Field(..., description="URL to crawl")
    
    max_pages: Optional[int] = Field(default=None, ge=1, le=10000)
    max_depth: Optional[int] = Field(default=None, ge=1, le=10)
    
    strategy: Literal["auto", "sitemap", "bfs", "dfs"] = Field(
        default="auto",
        description="Crawl strategy. 'auto' selects best strategy automatically"
    )
    
    render_js: bool = Field(default=True, description="Enable JavaScript rendering")
    
    extract: Dict[str, bool] = Field(
        default_factory=lambda: {
            "text": True,
            "links": True,
            "images": False,
            "metadata": True
        }
    )
    
    selectors: Optional[Dict[str, str]] = Field(
        default=None,
        description="CSS selectors (e.g., {'title': 'h1', 'content': '.main'})"
    )
    
    allowed_domains: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    
    auth: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Auth: {'headers': {...}, 'cookies': {...}, 'basic_auth': {...}}"
    )
    
    enable_chunking: bool = Field(default=False, description="Enable document chunking")


class ClientBatchCrawlRequest(BaseModel):
    """Simplified batch crawl request - same as ClientCrawlRequest."""
    
    url: HttpUrl = Field(..., description="Starting URL for crawl")
    max_pages: Optional[int] = Field(default=None, ge=1, le=10000)
    max_depth: Optional[int] = Field(default=None, ge=1, le=10)
    strategy: Literal["auto", "sitemap", "bfs", "dfs"] = Field(default="auto")
    render_js: bool = Field(default=True)
    extract: Dict[str, bool] = Field(default_factory=lambda: {
        "text": True,
        "links": True,
        "images": False,
        "metadata": True
    })
    selectors: Optional[Dict[str, str]] = None
    allowed_domains: Optional[List[str]] = None
    exclude_patterns: Optional[List[str]] = None
    auth: Optional[Dict[str, Any]] = None
    enable_chunking: bool = Field(default=False)

