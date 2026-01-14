"""
MongoDB storage backend for the website crawler.

This module provides a MongoDB storage backend.
"""
import logging
import json
from typing import Dict, Any, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError

from .base import BaseStorage
from crawler.exceptions import StorageError, StorageConnectionError, StorageSaveError
from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("MongoStorage", __name__)


class MongoStorage(BaseStorage):
    """
    MongoDB storage implementation.
    
    Provides basic CRUD operations for storing crawled documents.
    """
    
    def __init__(self, connection_string: str, database: str, collection: str = "documents", max_document_size: int = 16777216):
        """
        Initialize MongoDB storage.
        
        Args:
            connection_string: MongoDB connection string
            database: Database name
            collection: Collection name (default: "documents")
            max_document_size: Maximum document size in bytes before save (default: 16MB)
        """
        self.connection_string = connection_string
        self.database_name = database
        self.collection_name = collection
        self.max_document_size = max_document_size
        self.client: Optional[MongoClient] = None
        self.db = None
        self.collection = None
    
    def connect(self) -> bool:
        """
        Establish connection to MongoDB.
        
        Returns:
            True if connection successful, False otherwise
            
        Raises:
            StorageConnectionError: If connection fails
        """
        logger.log_entry("connect", 
                        database=self.database_name,
                        collection=self.collection_name,
                        connection_string=self.connection_string[:50] + "..." if len(self.connection_string) > 50 else self.connection_string)
        
        try:
            logger.log_decision("MONGO_CLIENT_CREATION", "Creating MongoDB client")
            self.client = MongoClient(
                self.connection_string,
                serverSelectionTimeoutMS=5000
            )
            # Test connection
            logger.log_entry("ping_mongodb")
            self.client.admin.command('ping')
            logger.log_decision("MONGO_PING_SUCCESS", "MongoDB ping successful")
            logger.log_exit("ping_mongodb", status="success")
            
            self.db = self.client[self.database_name]
            self.collection = self.db[self.collection_name]
            logger.log_state_change("storage_disconnected", "storage_connected", 
                                  database=self.database_name,
                                  collection=self.collection_name)
            logger.log_exit("connect", status="success")
            return True
        except ConnectionFailure as e:
            logger.log_decision("MONGO_CONNECTION_FAILED", reason=str(e))
            logger.log_exit("connect", status="failed", error=str(e))
            raise StorageConnectionError(
                f"Failed to connect to MongoDB: {str(e)}",
                connection_string=self.connection_string
            ) from e
        except Exception as e:
            logger.log_decision("MONGO_CONNECTION_ERROR", reason=str(e))
            logger.log_exit("connect", status="failed", error=str(e))
            raise StorageConnectionError(
                f"Unexpected error connecting to MongoDB: {str(e)}",
                connection_string=self.connection_string
            ) from e
    
    def disconnect(self) -> None:
        """Close connection to MongoDB."""
        logger.log_entry("disconnect", has_client=bool(self.client))
        
        if self.client:
            logger.log_decision("MONGO_DISCONNECT", "Closing MongoDB connection")
            self.client.close()
            self.client = None
            self.db = None
            self.collection = None
            logger.log_state_change("storage_connected", "storage_disconnected")
            logger.log_exit("disconnect", status="success")
        else:
            logger.log_decision("MONGO_ALREADY_DISCONNECTED", "Already disconnected")
            logger.log_exit("disconnect", status="already_disconnected")
    
    def save(self, document: Dict[str, Any]) -> bool:
        """
        Save a document to MongoDB (upsert based on document_id).
        
        Args:
            document: Dictionary containing the document data
            
        Returns:
            True if save was successful, False otherwise
            
        Raises:
            StorageSaveError: If save fails
        """
        if self.collection is None:
            logger.log_decision("STORAGE_NOT_CONNECTED", "Not connected to MongoDB")
            raise StorageError("Not connected to MongoDB. Call connect() first.")
        
        # Use document_id as _id
        document_id = document.get('document_id') or document.get('_id')
        
        doc_logger = logger
        if document_id:
            doc_logger = logger.with_request_id(document_id)
        
        with doc_logger.component_flow("save", document_id=document_id):
            try:
                if not document_id:
                    doc_logger.log_decision("DOCUMENT_ID_MISSING", "Document must have a 'document_id' field")
                    raise StorageSaveError("Document must have a 'document_id' field")
                
                # Prepare document for MongoDB
                mongo_doc = document.copy()
                mongo_doc['_id'] = document_id
                
                # Validate document size before saving
                # Estimate size by serializing to JSON
                try:
                    document_json = json.dumps(mongo_doc, default=str)
                    document_size = len(document_json.encode('utf-8'))
                    
                    if document_size > self.max_document_size:
                        error_msg = (
                            f"Document size ({document_size} bytes) exceeds maximum allowed size "
                            f"({self.max_document_size} bytes). Document ID: {document_id}"
                        )
                        doc_logger.log_decision("DOCUMENT_SIZE_EXCEEDED", reason=error_msg)
                        raise StorageSaveError(error_msg, document_id=document_id)
                except (TypeError, ValueError) as e:
                    # If JSON serialization fails, log warning but continue
                    doc_logger.warning(f"[MongoStorage] Could not validate document size for {document_id}: {str(e)}")
                
                # Upsert document
                self.collection.replace_one(
                    {'_id': document_id},
                    mongo_doc,
                    upsert=True
                )
                # Log in simple format: [MongoStorage] Saved document → doc_...
                doc_logger.info(f"[MongoStorage] Saved document → {document_id[:20]}...")
                return True
            except StorageSaveError:
                # Re-raise StorageSaveError as-is
                doc_logger.log_exit("save", status="failed", error_type="StorageSaveError")
                raise
            except PyMongoError as e:
                doc_logger.log_decision("MONGO_SAVE_ERROR", reason=str(e))
                doc_logger.log_exit("save", status="failed", error=str(e))
                raise StorageSaveError(
                    f"Failed to save document: {str(e)}",
                    document_id=document.get('document_id')
                ) from e
            except Exception as e:
                doc_logger.log_decision("UNEXPECTED_SAVE_ERROR", reason=str(e))
                doc_logger.log_exit("save", status="failed", error=str(e))
                raise StorageSaveError(
                    f"Unexpected error saving document: {str(e)}",
                    document_id=document.get('document_id')
                ) from e
    
    def get(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a document by ID.
        
        Args:
            document_id: Unique identifier for the document
            
        Returns:
            Document dictionary if found, None otherwise
        """
        if self.collection is None:
            raise StorageError("Not connected to MongoDB. Call connect() first.")
        
        try:
            doc = self.collection.find_one({'_id': document_id})
            if doc:
                # Convert ObjectId to string if present
                if '_id' in doc:
                    doc['document_id'] = str(doc['_id'])
                return doc
            return None
        except PyMongoError as e:
            raise StorageError(f"Failed to retrieve document: {str(e)}") from e
    
    def exists(self, document_id: str) -> bool:
        """
        Check if a document exists.
        
        Args:
            document_id: Unique identifier for the document
            
        Returns:
            True if document exists, False otherwise
        """
        if self.collection is None:
            raise StorageError("Not connected to MongoDB. Call connect() first.")
        
        try:
            count = self.collection.count_documents({'_id': document_id}, limit=1)
            return count > 0
        except PyMongoError as e:
            raise StorageError(f"Failed to check document existence: {str(e)}") from e