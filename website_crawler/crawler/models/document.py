"""
Document model for the website crawler.

This module defines the data model for processed documents.
"""
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from bson import ObjectId


class Document(BaseModel):
    """
    Model representing a processed document ready for storage.
    
    This model stores normalized content extracted from a crawled page.
    """
    document_id: str = Field(..., description="Unique document identifier")
    url: str = Field(..., description="Source URL")
    title: Optional[str] = Field(None, description="Page title")
    content: str = Field(..., description="Normalized text content")
    raw_html: Optional[str] = Field(None, description="Original HTML (optional for Phase 1)")
    markdown: Optional[str] = Field(None, description="Markdown representation of content (Phase 3)")
    links: List[str] = Field(default_factory=list, description="Extracted links from the page")
    images: List[str] = Field(default_factory=list, description="Extracted image URLs from the page")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Combined metadata")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Document creation timestamp")
    hash: str = Field(..., description="Content hash for change detection")
    
    def to_mongodb_dict(self) -> Dict[str, Any]:
        """
        Convert document to MongoDB-compatible dictionary.
        
        Returns:
            Dictionary ready for MongoDB storage
        """
        doc_dict = self.model_dump()
        # Convert datetime to ISO format string for MongoDB
        doc_dict['created_at'] = self.created_at.isoformat()
        # Use document_id as _id for MongoDB
        doc_dict['_id'] = self.document_id
        return doc_dict
    
    @classmethod
    def from_mongodb_dict(cls, doc_dict: Dict[str, Any]) -> 'Document':
        """
        Create Document from MongoDB dictionary.
        
        Args:
            doc_dict: Dictionary from MongoDB
            
        Returns:
            Document instance
        """
        # Handle _id field
        if '_id' in doc_dict and 'document_id' not in doc_dict:
            doc_dict['document_id'] = str(doc_dict['_id'])
        
        # Convert ISO string back to datetime
        if 'created_at' in doc_dict and isinstance(doc_dict['created_at'], str):
            doc_dict['created_at'] = datetime.fromisoformat(doc_dict['created_at'].replace('Z', '+00:00'))
        
        return cls(**doc_dict)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            ObjectId: lambda v: str(v)
        }