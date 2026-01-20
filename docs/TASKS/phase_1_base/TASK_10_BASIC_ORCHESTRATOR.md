# TASK 10: Basic Orchestrator

## Objective
Create a basic orchestrator that coordinates the crawling pipeline: crawl → extract → normalize → store.

## Prerequisites
- TASK_05 completed (Crawl4AI Engine)
- TASK_07 completed (HTML Parser)
- TASK_08 completed (Content Extraction)
- TASK_09 completed (MongoDB Storage)
- TASK_03 completed (URL Validation)
- TASK_04 completed (URL Normalization)

## Steps

### 1. Implement Basic Orchestrator (crawler/orchestrator.py)
- Create CrawlOrchestrator class
- Implement crawl_pipeline() method:
  - Accept start URL
  - Validate URL
  - Normalize URL
  - Crawl URL using Crawl4AI Engine
  - Extract content using HTML Parser
  - Create Document model
  - Save to MongoDB Storage
  - Return document
- Add basic error handling
- Add logging

### 2. Integrate All Components
- Initialize crawl4ai engine
- Initialize HTML parser
- Initialize MongoDB storage
- Coordinate the pipeline flow

### 3. Add Basic Error Handling
- Handle crawl errors
- Handle extraction errors
- Handle storage errors
- Log errors appropriately

## Files to Create/Modify
- `crawler/orchestrator.py` - Orchestrator implementation
- `crawler/__init__.py` - Update exports if needed

## Orchestrator Interface
```python
class CrawlOrchestrator:
    def __init__(self, config: Dict[str, Any])
    async def crawl_url(self, url: str) -> Document
    def initialize(self) -> None
    def cleanup(self) -> None
```

## Pipeline Flow
1. Validate URL
2. Normalize URL
3. Crawl URL (get HTML)
4. Parse HTML (extract text, links, title)
5. Create Document model
6. Save to MongoDB
7. Return document

## Phase 1 Scope
- **Focus**: Single URL crawling pipeline
- **Deferred to Phase 2**: Multi-URL crawling, retry logic, better error handling
- **Deferred to Phase 3**: Strategy-based crawling, batch processing, advanced coordination

## Error Handling
- Validate URL before crawling
- Handle crawl failures
- Handle extraction failures
- Handle storage failures
- Log all errors

## Validation
- [ ] Can crawl a single URL end-to-end
- [ ] Content is extracted correctly
- [ ] Document is saved to MongoDB
- [ ] Errors are handled gracefully
- [ ] Pipeline completes successfully
- [ ] All components are properly initialized and cleaned up

## Notes
- Keep orchestrator simple for Phase 1
- Focus on making the pipeline work end-to-end
- More advanced orchestration comes in later phases
- Ensure proper async/await handling
- Ensure proper resource cleanup

