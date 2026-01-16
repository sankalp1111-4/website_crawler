"""
MongoDB storage backend for the website crawler.

This module provides a MongoDB storage backend.
"""
import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, PyMongoError
from pymongo.operations import ReplaceOne

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
        
        # Collections for new unified architecture
        self.source_pages_collection = None
        self.page_chunks_collection = None
        self.crawl_runs_collection = None
    
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
            
            # Initialize collections for new unified architecture
            self.source_pages_collection = self.db["source_pages"]
            self.page_chunks_collection = self.db["page_chunks"]
            self.crawl_runs_collection = self.db["crawl_runs"]
            
            # Create indexes for efficient queries
            self._create_indexes()
            
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
            self.source_pages_collection = None
            self.page_chunks_collection = None
            self.crawl_runs_collection = None
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
    
    def _create_indexes(self) -> None:
        """Create indexes for efficient queries on new collections."""
        try:
            # SourcePage indexes
            if self.source_pages_collection is not None:
                self.source_pages_collection.create_index("url", unique=True)
                self.source_pages_collection.create_index("normalized_url", unique=True)
                self.source_pages_collection.create_index("last_crawled")
                self.source_pages_collection.create_index([("status", 1), ("last_crawled", -1)])
                self.source_pages_collection.create_index("crawl_run_id")
                self.source_pages_collection.create_index("content_hash")
                logger.debug("[MongoStorage] Created indexes for source_pages collection")
            
            # PageChunk indexes
            if self.page_chunks_collection is not None:
                self.page_chunks_collection.create_index([("source_page_id", 1), ("chunk_index", 1)], unique=True)
                self.page_chunks_collection.create_index("source_page_id")
                self.page_chunks_collection.create_index("content_hash")
                self.page_chunks_collection.create_index("updated_at")
                self.page_chunks_collection.create_index([("status", 1), ("source_page_id", 1)])
                logger.debug("[MongoStorage] Created indexes for page_chunks collection")
            
            # CrawlRun indexes
            if self.crawl_runs_collection is not None:
                self.crawl_runs_collection.create_index("start_time", unique=False)
                self.crawl_runs_collection.create_index([("status", 1), ("start_time", -1)])
                self.crawl_runs_collection.create_index("start_url")
                self.crawl_runs_collection.create_index("crawl_type")
                logger.debug("[MongoStorage] Created indexes for crawl_runs collection")
        except Exception as e:
            logger.warning(f"[MongoStorage] Failed to create indexes: {e}")
    
    def save_source_page(self, source_page: Dict[str, Any]) -> bool:
        """
        Save a SourcePage to MongoDB.
        
        Args:
            source_page: SourcePage dictionary
            
        Returns:
            True if save was successful
            
        Raises:
            StorageSaveError: If save fails
        """
        if self.source_pages_collection is None:
            raise StorageError("Not connected to MongoDB. Call connect() first.")
        
        source_page_id = source_page.get('source_page_id') or source_page.get('_id')
        doc_logger = logger.with_request_id(source_page_id) if source_page_id else logger
        
        with doc_logger.component_flow("save_source_page", source_page_id=source_page_id):
            try:
                if not source_page_id:
                    raise StorageSaveError("SourcePage must have a 'source_page_id' field")
                
                mongo_doc = source_page.copy()
                mongo_doc['_id'] = source_page_id
                
                self.source_pages_collection.replace_one(
                    {'_id': source_page_id},
                    mongo_doc,
                    upsert=True
                )
                doc_logger.info(f"[MongoStorage] Saved source_page → {source_page_id[:20]}...")
                return True
            except PyMongoError as e:
                doc_logger.error(f"[MongoStorage] Failed to save source_page: {e}")
                raise StorageSaveError(f"Failed to save source_page: {str(e)}", document_id=source_page_id) from e
    
    def get_source_page(self, source_page_id: Optional[str] = None, url: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieve a SourcePage by ID or URL.
        
        Args:
            source_page_id: SourcePage ID
            url: URL (normalized_url will be used)
            
        Returns:
            SourcePage dictionary if found, None otherwise
        """
        if self.source_pages_collection is None:
            raise StorageError("Not connected to MongoDB. Call connect() first.")
        
        try:
            if source_page_id:
                doc = self.source_pages_collection.find_one({'_id': source_page_id})
            elif url:
                doc = self.source_pages_collection.find_one({'normalized_url': url})
            else:
                raise ValueError("Either source_page_id or url must be provided")
            
            if doc and '_id' in doc:
                doc['source_page_id'] = str(doc['_id'])
            return doc
        except PyMongoError as e:
            raise StorageError(f"Failed to retrieve source_page: {str(e)}") from e
    
    def save_page_chunk(self, page_chunk: Dict[str, Any]) -> bool:
        """
        Save a PageChunk to MongoDB.
        
        Args:
            page_chunk: PageChunk dictionary
            
        Returns:
            True if save was successful
            
        Raises:
            StorageSaveError: If save fails
        """
        if self.page_chunks_collection is None:
            raise StorageError("Not connected to MongoDB. Call connect() first.")
        
        chunk_id = page_chunk.get('chunk_id') or page_chunk.get('_id')
        doc_logger = logger.with_request_id(chunk_id) if chunk_id else logger
        
        with doc_logger.component_flow("save_page_chunk", chunk_id=chunk_id):
            try:
                if not chunk_id:
                    raise StorageSaveError("PageChunk must have a 'chunk_id' field")
                
                mongo_doc = page_chunk.copy()
                mongo_doc['_id'] = chunk_id
                
                self.page_chunks_collection.replace_one(
                    {'_id': chunk_id},
                    mongo_doc,
                    upsert=True
                )
                doc_logger.debug(f"[MongoStorage] Saved page_chunk → {chunk_id[:30]}...")
                return True
            except PyMongoError as e:
                doc_logger.error(f"[MongoStorage] Failed to save page_chunk: {e}")
                raise StorageSaveError(f"Failed to save page_chunk: {str(e)}", document_id=chunk_id) from e
    
    def save_page_chunks_batch(self, page_chunks: List[Dict[str, Any]]) -> int:
        """
        Save multiple PageChunks in a batch.
        
        Args:
            page_chunks: List of PageChunk dictionaries
            
        Returns:
            Number of chunks saved
        """
        if self.page_chunks_collection is None:
            raise StorageError("Not connected to MongoDB. Call connect() first.")
        
        if not page_chunks:
            return 0
        
        try:
            # Prepare documents for bulk write
            operations = []
            for chunk in page_chunks:
                chunk_id = chunk.get('chunk_id') or chunk.get('_id')
                if not chunk_id:
                    continue
                mongo_doc = chunk.copy()
                mongo_doc['_id'] = chunk_id
                operations.append(
                    ReplaceOne(
                        {'_id': chunk_id},
                        mongo_doc,
                        upsert=True
                    )
                )
            
            if operations:
                result = self.page_chunks_collection.bulk_write(operations, ordered=False)
                logger.info(f"[MongoStorage] Saved {result.upserted_count + result.modified_count} page_chunks in batch")
                return result.upserted_count + result.modified_count
            return 0
        except PyMongoError as e:
            logger.error(f"[MongoStorage] Failed to save page_chunks batch: {e}")
            raise StorageError(f"Failed to save page_chunks batch: {str(e)}") from e
    
    def get_page_chunks(self, source_page_id: str, status: str = "active") -> List[Dict[str, Any]]:
        """
        Retrieve all PageChunks for a SourcePage.
        
        Args:
            source_page_id: SourcePage ID
            status: Filter by status (default: "active")
            
        Returns:
            List of PageChunk dictionaries, sorted by chunk_index
        """
        if self.page_chunks_collection is None:
            raise StorageError("Not connected to MongoDB. Call connect() first.")
        
        try:
            query = {'source_page_id': source_page_id, 'status': status}
            chunks = list(self.page_chunks_collection.find(query).sort('chunk_index', 1))
            for chunk in chunks:
                if '_id' in chunk:
                    chunk['chunk_id'] = str(chunk['_id'])
            return chunks
        except PyMongoError as e:
            raise StorageError(f"Failed to retrieve page_chunks: {str(e)}") from e
    
    def mark_chunks_obsolete(self, source_page_id: str, exclude_chunk_ids: List[str]) -> int:
        """
        Mark chunks as obsolete except for the provided chunk IDs.
        
        Args:
            source_page_id: SourcePage ID
            exclude_chunk_ids: List of chunk IDs to keep active
            
        Returns:
            Number of chunks marked as obsolete
        """
        if self.page_chunks_collection is None:
            raise StorageError("Not connected to MongoDB. Call connect() first.")
        
        try:
            result = self.page_chunks_collection.update_many(
                {
                    'source_page_id': source_page_id,
                    'chunk_id': {'$nin': exclude_chunk_ids},
                    'status': 'active'
                },
                {
                    '$set': {'status': 'obsolete', 'updated_at': datetime.utcnow().isoformat()}
                }
            )
            logger.info(f"[MongoStorage] Marked {result.modified_count} chunks as obsolete for source_page {source_page_id}")
            return result.modified_count
        except PyMongoError as e:
            logger.error(f"[MongoStorage] Failed to mark chunks obsolete: {e}")
            raise StorageError(f"Failed to mark chunks obsolete: {str(e)}") from e
    
    def save_crawl_run(self, crawl_run: Dict[str, Any]) -> bool:
        """
        Save a CrawlRun to MongoDB.
        
        Args:
            crawl_run: CrawlRun dictionary
            
        Returns:
            True if save was successful
            
        Raises:
            StorageSaveError: If save fails
        """
        if self.crawl_runs_collection is None:
            raise StorageError("Not connected to MongoDB. Call connect() first.")
        
        crawl_run_id = crawl_run.get('crawl_run_id') or crawl_run.get('_id')
        doc_logger = logger.with_request_id(crawl_run_id) if crawl_run_id else logger
        
        with doc_logger.component_flow("save_crawl_run", crawl_run_id=crawl_run_id):
            try:
                if not crawl_run_id:
                    raise StorageSaveError("CrawlRun must have a 'crawl_run_id' field")
                
                mongo_doc = crawl_run.copy()
                mongo_doc['_id'] = crawl_run_id
                
                self.crawl_runs_collection.replace_one(
                    {'_id': crawl_run_id},
                    mongo_doc,
                    upsert=True
                )
                doc_logger.info(f"[MongoStorage] Saved crawl_run → {crawl_run_id[:20]}...")
                return True
            except PyMongoError as e:
                doc_logger.error(f"[MongoStorage] Failed to save crawl_run: {e}")
                raise StorageSaveError(f"Failed to save crawl_run: {str(e)}", document_id=crawl_run_id) from e
    
    def get_crawl_run(self, crawl_run_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a CrawlRun by ID.
        
        Args:
            crawl_run_id: CrawlRun ID
            
        Returns:
            CrawlRun dictionary if found, None otherwise
        """
        if self.crawl_runs_collection is None:
            raise StorageError("Not connected to MongoDB. Call connect() first.")
        
        try:
            doc = self.crawl_runs_collection.find_one({'_id': crawl_run_id})
            if doc and '_id' in doc:
                doc['crawl_run_id'] = str(doc['_id'])
            return doc
        except PyMongoError as e:
            raise StorageError(f"Failed to retrieve crawl_run: {str(e)}") from e