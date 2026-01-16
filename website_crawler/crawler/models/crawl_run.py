"""
CrawlRun model for the website crawler.

Represents a single crawl execution (works for both single-page and multi-page crawls).
"""
from datetime import datetime
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class CrawlRun(BaseModel):
    """
    Model representing a single crawl execution.
    
    Works for both single-page and multi-page crawls.
    Tracks overall crawl statistics and status.
    """
    crawl_run_id: str = Field(..., description="Deterministic ID: f'run_{timestamp}_{hash(start_url)}'")
    start_url: str = Field(..., description="Starting URL (for both single and multi-page)")
    crawl_type: str = Field(..., description="Type: 'single_page' or 'multi_page'")
    strategy_type: Optional[str] = Field(None, description="Strategy: 'bfs', 'sitemap', 'adaptive', None (for single-page)")
    start_time: datetime = Field(default_factory=datetime.utcnow, description="Crawl start timestamp")
    end_time: Optional[datetime] = Field(None, description="Crawl end timestamp (None if in progress)")
    status: str = Field(default="running", description="Status: running, completed, failed, partial")
    total_pages_discovered: int = Field(default=0, description="Total URLs discovered")
    total_pages_crawled: int = Field(default=0, description="Successfully crawled pages")
    total_pages_failed: int = Field(default=0, description="Failed pages")
    total_chunks_created: int = Field(default=0, description="Total chunks generated")
    max_depth: Optional[int] = Field(None, description="Maximum depth reached")
    max_pages: Optional[int] = Field(None, description="Maximum pages limit")
    config_snapshot: Dict[str, Any] = Field(default_factory=dict, description="Configuration used for this run")
    error_summary: Optional[Dict[str, Any]] = Field(None, description="Summary of errors encountered")
    
    def to_mongodb_dict(self) -> Dict[str, Any]:
        """
        Convert CrawlRun to MongoDB-compatible dictionary.
        
        Returns:
            Dictionary ready for MongoDB storage
        """
        doc_dict = self.model_dump()
        # Convert datetime to ISO format string for MongoDB
        doc_dict['start_time'] = self.start_time.isoformat()
        if self.end_time:
            doc_dict['end_time'] = self.end_time.isoformat()
        # Use crawl_run_id as _id for MongoDB
        doc_dict['_id'] = self.crawl_run_id
        return doc_dict
    
    @classmethod
    def from_mongodb_dict(cls, doc_dict: Dict[str, Any]) -> 'CrawlRun':
        """
        Create CrawlRun from MongoDB dictionary.
        
        Args:
            doc_dict: Dictionary from MongoDB
            
        Returns:
            CrawlRun instance
        """
        # Handle _id field
        if '_id' in doc_dict and 'crawl_run_id' not in doc_dict:
            doc_dict['crawl_run_id'] = str(doc_dict['_id'])
        
        # Convert ISO string back to datetime
        if 'start_time' in doc_dict and isinstance(doc_dict['start_time'], str):
            doc_dict['start_time'] = datetime.fromisoformat(doc_dict['start_time'].replace('Z', '+00:00'))
        if 'end_time' in doc_dict and isinstance(doc_dict['end_time'], str):
            doc_dict['end_time'] = datetime.fromisoformat(doc_dict['end_time'].replace('Z', '+00:00'))
        
        return cls(**doc_dict)
    
    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

