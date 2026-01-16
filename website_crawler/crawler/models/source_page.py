"""
SourcePage model for the website crawler.

Represents a single crawled URL (works for both single-page and multi-page crawls).
"""
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class SourcePage(BaseModel):
    """
    Model representing a single crawled URL.
    
    This model works for both single-page and multi-page crawls.
    Each SourcePage can have multiple PageChunks.
    """
    source_page_id: str = Field(..., description="Deterministic ID: hash(normalized_url)")
    url: str = Field(..., description="Original URL")
    normalized_url: str = Field(..., description="Canonical normalized URL representation")
    content_hash: str = Field(..., description="Hash of full extracted content for change detection")
    version: int = Field(default=1, description="Incrementing version number (starts at 1)")
    last_crawled: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of most recent successful crawl")
    first_crawled: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of first crawl")
    status: str = Field(default="active", description="Status: active, failed, archived")
    status_code: Optional[int] = Field(None, description="HTTP status code from last crawl")
    total_chunks: int = Field(default=0, description="Number of chunks generated from this page")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Page-level metadata (title, headers, etc.)")
    crawl_run_id: Optional[str] = Field(None, description="Reference to CrawlRun (for multi-page crawls)")
    
    def to_mongodb_dict(self) -> Dict[str, Any]:
        """
        Convert SourcePage to MongoDB-compatible dictionary.
        
        Returns:
            Dictionary ready for MongoDB storage
        """
        doc_dict = self.model_dump()
        # Convert datetime to ISO format string for MongoDB
        doc_dict['last_crawled'] = self.last_crawled.isoformat()
        doc_dict['first_crawled'] = self.first_crawled.isoformat()
        # Use source_page_id as _id for MongoDB
        doc_dict['_id'] = self.source_page_id
        return doc_dict
    
    @classmethod
    def from_mongodb_dict(cls, doc_dict: Dict[str, Any]) -> 'SourcePage':
        """
        Create SourcePage from MongoDB dictionary.
        
        Args:
            doc_dict: Dictionary from MongoDB
            
        Returns:
            SourcePage instance
        """
        # Handle _id field
        if '_id' in doc_dict and 'source_page_id' not in doc_dict:
            doc_dict['source_page_id'] = str(doc_dict['_id'])
        
        # Convert ISO string back to datetime
        if 'last_crawled' in doc_dict and isinstance(doc_dict['last_crawled'], str):
            doc_dict['last_crawled'] = datetime.fromisoformat(doc_dict['last_crawled'].replace('Z', '+00:00'))
        if 'first_crawled' in doc_dict and isinstance(doc_dict['first_crawled'], str):
            doc_dict['first_crawled'] = datetime.fromisoformat(doc_dict['first_crawled'].replace('Z', '+00:00'))
        
        return cls(**doc_dict)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

