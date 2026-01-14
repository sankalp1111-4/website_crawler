# TASK 02: Performance Settings

## Objective
Implement performance-related settings including timeouts, retries, rate limiting, and connection pooling.

## Prerequisites
- Phase 1 completed (Crawl4AI Engine)
- Time utilities from original TASK_03

## Steps

### 1. Implement Performance Settings (crawler/engine/performance.py)
- Create PerformanceConfig class
- Implement settings for:
  - Request timeout (seconds)
  - Page load timeout (seconds)
  - Max retries per URL
  - Retry delay (with exponential backoff)
  - Rate limiting (requests per second)
  - Concurrent requests limit

### 2. Implement Rate Limiting
- Support per-domain rate limiting
- Support global rate limiting
- Add jitter to avoid thundering herd

### 3. Implement Retry Logic
- Support exponential backoff
- Support max retry attempts
- Log retry attempts
- Handle different error types differently

### 4. Integrate with Engine
- Apply timeouts to crawl operations
- Apply rate limiting to requests
- Apply retry logic to failed requests

## Files to Create/Modify
- `crawler/engine/performance.py` - Performance settings
- `crawler/engine/__init__.py` - Update exports
- `crawler/engine/crawl4ai_engine.py` - Integrate performance settings

## Source Task
- Original: TASK_12_PERFORMANCE_SETTINGS.md

## Performance Settings
- **request_timeout**: int (seconds)
- **page_load_timeout**: int (seconds)
- **max_retries**: int
- **retry_delay**: float (seconds)
- **rate_limit**: float (requests per second)
- **concurrent_requests**: int

## Functions to Implement
```python
class PerformanceConfig:
    def __init__(self, config: Dict[str, Any])
    def validate(self) -> bool
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> PerformanceConfig
    @classmethod
    def default(cls) -> PerformanceConfig
```

## Retry Logic
- Retry on timeout errors
- Retry on network errors
- Don't retry on 4xx errors (except 429)
- Retry on 5xx errors
- Use exponential backoff

## Validation
- [ ] Timeouts are applied correctly
- [ ] Rate limiting works
- [ ] Retry logic works with exponential backoff
- [ ] Concurrent requests are limited correctly
- [ ] Performance config is validated

## Notes
- Balance performance with politeness
- Respect robots.txt crawl-delay
- Monitor resource usage
- Test with various scenarios

