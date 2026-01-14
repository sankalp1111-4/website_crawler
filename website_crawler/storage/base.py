"""
Base storage interface for the website crawler.

This module defines the base interface for storage backends.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseStorage(ABC):
    """
    Base class for all storage backends.
    
    All storage implementations (MongoDB, PostgreSQL, S3, etc.) must inherit
    from this class and implement the required methods.
    """
    
    @abstractmethod
    def save(self, document: Dict[str, Any]) -> bool:
        """
        Save a document to storage.
        
        Args:
            document: Dictionary containing the document data
            
        Returns:
            True if save was successful, False otherwise
        """
        pass
    
    @abstractmethod
    def get(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID.
        
        Args:
            document_id: Unique identifier for the document
            
        Returns:
            Document dictionary if found, None otherwise
        """
        pass
    
    @abstractmethod
    def exists(self, document_id: str) -> bool:
        """
        Check if a document exists.
        
        Args:
            document_id: Unique identifier for the document
            
        Returns:
            True if document exists, False otherwise
        """
        pass
    
    @abstractmethod
    def connect(self) -> bool:
        """
        Establish connection to storage backend.
        
        Returns:
            True if connection successful, False otherwise
        """
        pass
    
    @abstractmethod
    def disconnect(self) -> None:
        """Close connection to storage backend."""
        pass
