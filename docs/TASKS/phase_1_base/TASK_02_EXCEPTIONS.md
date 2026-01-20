# TASK 02: Exception Handling

## Objective
Define essential custom exception classes for error handling in the crawler system.

## Prerequisites
- None (standalone task)

## Steps

### 1. Implement Essential Exceptions (crawler/exceptions.py)
Create minimal exception hierarchy:

- **CrawlerException**: Base exception for all crawler errors
  - **CrawlError**: General crawling errors
    - **CrawlTimeoutError**: Timeout during crawling
    - **CrawlFailedError**: Failed to crawl a URL
  - **StorageError**: Storage-related errors
    - **StorageConnectionError**: Cannot connect to storage
    - **StorageSaveError**: Failed to save document
  - **ValidationError**: Validation errors
    - **InvalidURLError**: Invalid URL format

### 2. Add Basic Exception Context
- Include URL in exception messages when relevant
- Make error messages descriptive

## Files to Create/Modify
- `crawler/exceptions.py` - Custom exception classes

## Phase 1 Simplifications
- **Removed**: Complex exception hierarchy (ExtractionError, ConfigurationError, etc.)
- **Focus**: Only exceptions needed for MVP (crawl, storage, validation)

## Exception Hierarchy
```
CrawlerException
├── CrawlError
│   ├── CrawlTimeoutError
│   └── CrawlFailedError
├── StorageError
│   ├── StorageConnectionError
│   └── StorageSaveError
└── ValidationError
    └── InvalidURLError
```

## Validation
- [ ] All exceptions can be raised and caught
- [ ] Exception messages are clear
- [ ] Exception hierarchy is logical

## Notes
- Keep exceptions simple for Phase 1
- Can expand in Phase 2

