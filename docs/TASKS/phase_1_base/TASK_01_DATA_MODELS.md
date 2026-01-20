# TASK 01: Data Models

## Objective
Define essential data models using Pydantic for type safety and validation. These models represent the core data structures for the crawler pipeline.

## Prerequisites
- Configuration system completed (TASK_02 from original plan)

## Steps

### 1. Implement RawPage Model (crawler/models/raw_page.py)
- **url**: str - The URL of the page
- **html**: str - Raw HTML content
- **status_code**: int - HTTP status code
- **headers**: Dict[str, str] - HTTP response headers
- **crawl_timestamp**: datetime - When the page was crawled
- Use Pydantic BaseModel
- Add basic validation for URL format

### 2. Implement Document Model (crawler/models/document.py)
- **document_id**: str - Unique document identifier (can use URL hash)
- **url**: str - Source URL
- **title**: Optional[str] - Page title
- **content**: str - Normalized text content
- **raw_html**: Optional[str] - Original HTML (optional for Phase 1)
- **links**: List[str] - Extracted links from the page
- **metadata**: Dict[str, Any] - Combined metadata
- **created_at**: datetime - Document creation timestamp
- **hash**: str - Content hash for change detection
- Use Pydantic BaseModel
- Add methods for MongoDB serialization

### 3. Update models/__init__.py
- Export all model classes

## Files to Create/Modify
- `crawler/models/raw_page.py` - Raw page model
- `crawler/models/document.py` - Final document model
- `crawler/models/__init__.py` - Module exports

## Phase 1 Simplifications
- **Removed**: ExtractedContent model (will use crawl4ai's built-in extraction for Phase 1)
- **Simplified**: Document model - focus on essential fields only
- **Note**: Models should be minimal but complete for MVP

## Validation
- [ ] All models can be instantiated with valid data
- [ ] Validation errors are raised for invalid data
- [ ] Models serialize to dict correctly for MongoDB
- [ ] Type hints are correct

## Notes
- Use Pydantic v2 features
- Keep models simple for Phase 1
- Focus on MongoDB compatibility

