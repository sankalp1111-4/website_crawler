# TASK 09: MongoDB Storage

## Objective
Implement MongoDB storage backend to save crawled documents.

## Prerequisites
- TASK_01 completed (Data models - Document)
- TASK_02 completed (Exceptions)
- MongoDB installed and accessible
- pymongo in requirements.txt

## Steps

### 1. Implement MongoDB Storage (storage/mongo.py)
- Create MongoStorage class implementing BaseStorage interface
- Implement connection management:
  - connect() - Connect to MongoDB
  - disconnect() - Close connection
- Implement document operations:
  - save(document: Dict) -> bool - Save document (upsert based on document_id)
  - get(document_id: str) -> Optional[Dict] - Retrieve document
  - exists(document_id: str) -> bool - Check if document exists
- Handle connection errors
- Convert Document model to MongoDB document format

### 2. Add Configuration Support
- MongoDB connection string from config
- Database name from config
- Collection name from config
- Basic connection options

### 3. Add Error Handling
- Handle connection errors
- Handle save errors
- Raise StorageError exceptions appropriately

## Files to Create/Modify
- `storage/mongo.py` - MongoDB storage implementation
- `storage/__init__.py` - Update exports

## Storage Interface
```python
class MongoStorage(BaseStorage):
    def connect(self) -> bool
    def disconnect(self) -> None
    def save(self, document: Dict[str, Any]) -> bool
    def get(self, document_id: str) -> Optional[Dict[str, Any]]
    def exists(self, document_id: str) -> bool
```

## Phase 1 Scope
- **Focus**: Basic CRUD operations - save, get, exists
- **Deferred to Phase 2**: Indexes, queries, batch operations, connection pooling
- **Deferred to Phase 3**: Advanced queries, aggregation, chunking support

## Configuration
- MongoDB connection string (from config or environment)
- Database name
- Collection name (default: "documents")

## Document Structure
- Use Document model structure
- document_id as _id field (or use MongoDB ObjectId)
- Store all document fields as-is

## Validation
- [ ] Can connect to MongoDB
- [ ] Can save documents
- [ ] Can retrieve documents
- [ ] Can check document existence
- [ ] Error handling works correctly
- [ ] Connection cleanup works

## Notes
- Use pymongo for MongoDB operations
- Handle connection errors gracefully
- Keep implementation simple for Phase 1
- More advanced features come in later phases
- Consider upsert logic (update if exists, insert if not)

