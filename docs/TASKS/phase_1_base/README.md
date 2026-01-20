# Phase 1: Base Crawler (MVP - End to End)

## Goal
Crawl a website → Extract content → Normalize → Store in MongoDB

## Deliverable
Working crawler that can crawl a URL, extract content, and store in MongoDB. The system must be runnable and verifiable.

## Task List

1. **TASK_01**: Data Models
   - RawPage model
   - Document model
   - Essential fields only

2. **TASK_02**: Exceptions
   - Minimal exception hierarchy
   - Crawl, Storage, Validation errors

3. **TASK_03**: URL Validation - Minimal
   - Basic URL validation
   - Scheme and crawlability checks

4. **TASK_04**: URL Normalization - Minimal
   - Absolute URL resolution
   - Fragment removal

5. **TASK_05**: Crawl4AI Engine
   - Crawl4AI integration
   - Single URL crawling
   - Basic error handling

6. **TASK_06**: Browser Config - Minimal
   - Headless mode
   - Basic browser type

7. **TASK_07**: HTML Parser
   - Text extraction
   - Link extraction
   - Title extraction

8. **TASK_08**: Content Extraction
   - Use crawl4ai built-in or minimal CSS extractor
   - Extract content for storage

9. **TASK_09**: MongoDB Storage
   - Basic CRUD operations
   - Save, get, exists methods

10. **TASK_10**: Basic Orchestrator
    - Coordinate crawl → extract → store pipeline
    - Single URL processing

## Implementation Order

```
TASK_01 (Models) 
  → TASK_02 (Exceptions)
  → TASK_03 (URL Validation)
  → TASK_04 (URL Normalization)
  → TASK_05 (Crawl4AI Engine)
  → TASK_06 (Browser Config)
  → TASK_07 (HTML Parser)
  → TASK_08 (Content Extraction)
  → TASK_09 (MongoDB Storage)
  → TASK_10 (Orchestrator)
```

## Success Criteria

- [ ] Can crawl a URL using crawl4ai
- [ ] Content is extracted from HTML
- [ ] Content is normalized (text extraction)
- [ ] Document is saved to MongoDB
- [ ] Can retrieve document from MongoDB
- [ ] Pipeline runs end-to-end without errors
- [ ] Basic error handling works
- [ ] System is runnable via main.py

## Notes

- Keep implementations minimal but complete
- Focus on correctness over features
- Avoid over-engineering
- Test after each task
- Ensure end-to-end flow works before moving to Phase 2

