# TASK 04: Headers & Proxies

## ⏸️ STATUS: DEFERRED TO END OF PHASE 3
**This task depends on TASK_03 (Session Management) and will be implemented at the end of Phase 3 after all other methods are complete and tested end-to-end.**

## Objective
Implement custom HTTP headers management and proxy support for the crawler.

## Prerequisites
- Phase 1 completed (Crawl4AI Engine)
- TASK_03 completed (Session Management) - **DEFERRED**
- Phase 2 tasks completed (except TASK_03 & TASK_04)
- Phase 3 tasks completed (all strategies, extractors, optimizations)

## Steps

### 1. Implement Headers Manager (crawler/auth/headers.py)
- Create HeadersManager class
- Implement default headers (User-Agent, Accept, etc.)
- Support custom headers from configuration
- Support per-request headers
- Support header rotation (optional)
- Integrate with crawl4ai

### 2. Implement Proxy Manager (crawler/auth/proxies.py)
- Create ProxyManager class
- Support HTTP and HTTPS proxies
- Support proxy rotation
- Support proxy authentication
- Support proxy health checking
- Handle proxy failures
- Integrate with crawl4ai

### 3. Add Configuration Support
- Headers configuration
- Proxy list configuration
- Proxy rotation strategy
- Proxy authentication

### 4. Integrate with Engine
- Pass headers to crawl4ai
- Pass proxies to crawl4ai
- Handle header/proxy errors

## Files to Create/Modify
- `crawler/auth/headers.py` - Headers management
- `crawler/auth/proxies.py` - Proxy management
- `crawler/auth/__init__.py` - Update exports
- `crawler/engine/crawl4ai_engine.py` - Integrate headers and proxies

## Source Task
- Original: TASK_14_HEADERS_PROXIES.md

## Headers Features
- Default headers (User-Agent, Accept, etc.)
- Custom headers from config
- Per-request headers
- Header rotation (optional)
- Referer management

## Proxy Features
- HTTP/HTTPS proxy support
- Proxy rotation
- Proxy authentication
- Proxy health checking
- Proxy failure handling

## Functions to Implement

### Headers
```python
class HeadersManager:
    def __init__(self, config: Dict[str, Any])
    def get_headers(self, url: str, custom_headers: Optional[Dict] = None) -> Dict[str, str]
    def set_default_headers(self, headers: Dict[str, str]) -> None
    def rotate_user_agent(self) -> None
```

### Proxies
```python
class ProxyManager:
    def __init__(self, config: Dict[str, Any])
    def get_proxy(self, url: str) -> Optional[str]
    def rotate_proxy(self) -> None
    def check_proxy_health(self, proxy: str) -> bool
    def mark_proxy_failed(self, proxy: str) -> None
```

## Validation
- [ ] Headers are set correctly
- [ ] Custom headers work
- [ ] Proxy rotation works
- [ ] Proxy authentication works
- [ ] Proxy health checking works
- [ ] Integration with engine works

## Notes
- Use realistic User-Agent strings
- Respect robots.txt user-agent rules
- Handle proxy failures gracefully
- Test with various proxy types

