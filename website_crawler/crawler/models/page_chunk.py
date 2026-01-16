"""
PageChunk model for the website crawler.

Represents a single chunk from a SourcePage.
"""
from datetime import datetime
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class PageChunk(BaseModel):
    """
    Model representing a discrete chunk of content from a SourcePage.
    
    Each chunk is independently searchable and embeddable.
    """
    chunk_id: str = Field(..., description="Deterministic ID: f'{source_page_id}_chunk_{chunk_index}'")
    source_page_id: str = Field(..., description="Foreign key to SourcePage")
    chunk_index: int = Field(..., description="Sequential index within the page (0-based)")
    content: str = Field(..., description="Chunk text content")
    content_hash: str = Field(..., description="Hash of chunk content for change detection")
    chunk_size: int = Field(..., description="Character count")
    overlap_size: int = Field(default=0, description="Overlap with previous chunk (characters)")
    token_count: Optional[int] = Field(None, description="Token count (if token-aware chunking)")
    embedding: Optional[List[float]] = Field(None, description="Vector embedding for semantic search")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Chunk-level metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    version: int = Field(default=1, description="Version number (inherits from SourcePage on creation)")
    status: str = Field(default="active", description="Status: active, obsolete")
    
    def to_mongodb_dict(self) -> Dict[str, Any]:
        """
        Convert PageChunk to MongoDB-compatible dictionary.
        
        Returns:
            Dictionary ready for MongoDB storage
        """
        doc_dict = self.model_dump()
        # Convert datetime to ISO format string for MongoDB
        doc_dict['created_at'] = self.created_at.isoformat()
        doc_dict['updated_at'] = self.updated_at.isoformat()
        # Use chunk_id as _id for MongoDB
        doc_dict['_id'] = self.chunk_id
        return doc_dict
    
    @classmethod
    def from_mongodb_dict(cls, doc_dict: Dict[str, Any]) -> 'PageChunk':
        """
        Create PageChunk from MongoDB dictionary.
        
        Args:
            doc_dict: Dictionary from MongoDB
            
        Returns:
            PageChunk instance
        """
        # Handle _id field
        if '_id' in doc_dict and 'chunk_id' not in doc_dict:
            doc_dict['chunk_id'] = str(doc_dict['_id'])
        
        # Convert ISO string back to datetime
        if 'created_at' in doc_dict and isinstance(doc_dict['created_at'], str):
            doc_dict['created_at'] = datetime.fromisoformat(doc_dict['created_at'].replace('Z', '+00:00'))
        if 'updated_at' in doc_dict and isinstance(doc_dict['updated_at'], str):
            doc_dict['updated_at'] = datetime.fromisoformat(doc_dict['updated_at'].replace('Z', '+00:00'))
        
        return cls(**doc_dict)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

