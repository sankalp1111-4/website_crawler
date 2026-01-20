# TASK 06: Browser Configuration - Minimal

## Objective
Implement minimal browser configuration management for crawl4ai.

## Prerequisites
- TASK_05 completed (Crawl4AI Engine)

## Steps

### 1. Implement Browser Configuration (crawler/engine/browser.py)
- Create BrowserConfig class (simple data class or Pydantic model)
- Implement minimal configuration:
  - Browser type (chromium default)
  - Headless mode (True/False)
  - Basic viewport size (optional)
- Convert configuration to crawl4ai format
- Add basic validation

### 2. Add Default Configuration
- Default desktop profile
- Support config file override

### 3. Integrate with Engine
- Pass browser config to crawl4ai
- Support global browser config

## Files to Create/Modify
- `crawler/engine/browser.py` - Browser configuration
- `crawler/engine/__init__.py` - Update exports

## Browser Configuration Options (Minimal)
- **browser_type**: "chromium" (default)
- **headless**: bool (default: True)
- **viewport**: Optional[Dict] (optional for Phase 1)

## Phase 1 Simplifications
- **Removed**: Multiple browser types, mobile/tablet profiles, timezone, geolocation, JavaScript/CSS/image controls
- **Focus**: Essential settings only - headless mode and basic browser type
- **Deferred to Phase 2**: Advanced browser configurations

## Functions to Implement
```python
class BrowserConfig:
    def __init__(self, config: Dict[str, Any])
    def to_crawl4ai_config(self) -> Dict[str, Any]
    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> BrowserConfig
    @classmethod
    def default(cls) -> BrowserConfig
```

## Validation
- [ ] Browser config is created correctly
- [ ] Configuration is converted to crawl4ai format
- [ ] Default config works
- [ ] Configuration is passed to engine correctly

## Notes
- Match crawl4ai's expected configuration format
- Keep configuration minimal for Phase 1
- Advanced configurations come in Phase 2

