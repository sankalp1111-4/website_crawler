"""Controller models for API requests and responses."""
from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


# ============================================================================
# Request Models
# ============================================================================

class ConfigOverride(BaseModel):
    """Type-safe configuration override model for advanced use cases."""
    crawler: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Override crawler configuration"
    )
    engine: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Override engine configuration"
    )
    extraction: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Override extraction configuration"
    )
    strategy: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Override strategy configuration"
    )
    chunking: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Override chunking configuration"
    )
    
    model_config = ConfigDict(extra="forbid")  # Prevent unknown fields


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
    
    priority_patterns: Optional[List[str]] = Field(
        default=None,
        description="URL patterns to prioritize during crawling (regex patterns)"
    )
    
    wait_for: Optional[str] = Field(
        default=None,
        description="CSS selector or timeout to wait for before extraction (e.g., '.content-loaded' or 'networkidle')"
    )
    
    enable_chunking: bool = Field(default=False, description="Enable document chunking")
    
    config_override: Optional[ConfigOverride] = Field(
        default=None,
        description="Advanced configuration override (use with caution)"
    )


# ============================================================================
# Response Models
# ============================================================================

class CrawlResponse(BaseModel):
    """Response model for crawl endpoint."""
    success: bool = Field(
        ...,
        description="Whether the crawl was successful",
        examples=[True, False]
    )
    document_id: Optional[str] = Field(
        None,
        description="Document ID if successful. This ID can be used to retrieve the crawled document from storage.",
        examples=["507f1f77bcf86cd799439011", "doc_abc123xyz"]
    )
    url: str = Field(
        ...,
        description="Crawled URL",
        examples=["https://example.com", "https://www.example.com/page"]
    )
    message: str = Field(
        ...,
        description="Response message",
        examples=["Crawl completed successfully", "Crawl failed"]
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Any warnings encountered during the crawl process",
        examples=[[], ["Empty content detected", "Timeout occurred"]]
    )


class BatchCrawlResponse(BaseModel):
    """Response model for batch crawl endpoint."""
    success: bool = Field(
        ...,
        description="Whether the crawl was successful",
        examples=[True, False]
    )
    documents_count: int = Field(
        ...,
        description="Number of documents crawled",
        examples=[1, 10, 50]
    )
    document_ids: list[str] = Field(
        default_factory=list,
        description="List of document IDs for crawled documents",
        examples=[["doc1", "doc2", "doc3"]]
    )
    start_url: str = Field(
        ...,
        description="Starting URL",
        examples=["https://example.com"]
    )
    message: str = Field(
        ...,
        description="Response message",
        examples=["Batch crawl completed successfully", "Batch crawl failed"]
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Any warnings encountered during the crawl process",
        examples=[[], ["Some URLs failed to crawl"]]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "documents_count": 10,
                    "document_ids": ["doc1", "doc2", "doc3"],
                    "start_url": "https://example.com",
                    "message": "Batch crawl completed successfully",
                    "warnings": []
                },
                {
                    "success": True,
                    "documents_count": 5,
                    "document_ids": ["doc1", "doc2"],
                    "start_url": "https://example.com/page",
                    "message": "Batch crawl completed successfully",
                    "warnings": ["Empty content detected in some pages"]
                }
            ]
        }
    )

