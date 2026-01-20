# TASK 05: Crawl4AI Engine Integration

## Objective
Integrate the crawl4ai library to create a wrapper that provides a clean interface for web crawling operations.

## Prerequisites
- TASK_01 completed (Data models - RawPage)
- TASK_02 completed (Exceptions)
- requirements.txt with crawl4ai

## Steps

### 1. Study Crawl4AI Documentation
- Review crawl4ai API and usage patterns
- Understand AsyncWebCrawler class
- Understand crawl() method parameters
- Understand response structure

### 2. Implement Crawl4AI Engine Wrapper (crawler/engine/crawl4ai_engine.py)
- Create Crawl4AIEngine class
- Wrap AsyncWebCrawler from crawl4ai
- Implement crawl_url() method:
  - Accept URL and basic configuration
  - Call crawl4ai's crawl() method
  - Handle async operations
  - Convert response to RawPage model
  - Handle errors and timeouts
- Add basic error handling and conversion to custom exceptions

### 3. Integrate with Configuration
- Load basic crawl4ai settings from config
- Support headless mode
- Support basic browser settings

### 4. Add Response Processing
- Extract HTML content
- Extract status code
- Extract headers
- Create RawPage model from response

## Files to Create/Modify
- `crawler/engine/crawl4ai_engine.py` - Crawl4AI integration
- `crawler/engine/__init__.py` - Module exports

## Engine Interface
```python
class Crawl4AIEngine:
    async def crawl_url(self, url: str, config: Dict[str, Any]) -> RawPage
    def initialize(self) -> None
    def cleanup(self) -> None
```

## Phase 1 Simplifications
- **Removed**: Batch crawling, advanced retry logic, complex error handling
- **Focus**: Single URL crawling with basic error handling
- **Deferred to Phase 2**: Performance settings, retry logic, rate limiting

## Configuration Options (Minimal)
- Headless mode
- Basic browser type
- Basic timeout settings

## Error Handling
- Convert crawl4ai exceptions to custom exceptions
- Handle timeout errors
- Handle network errors

## Validation
- [ ] Can crawl a simple URL successfully
- [ ] Returns RawPage model with correct data
- [ ] Handles errors gracefully
- [ ] Configuration is respected
- [ ] Async operations work correctly

## Notes
- Use async/await for crawl4ai operations
- Ensure proper resource cleanup
- Keep implementation simple for Phase 1
- Advanced features come in Phase 2

