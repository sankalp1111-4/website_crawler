# TASK 03: URL Validation - Minimal

## Objective
Implement minimal URL validation to ensure only valid URLs are processed by the crawler.

## Prerequisites
- TASK_02 completed (Exceptions)

## Steps

### 1. Implement URL Validator (crawler/url/validator.py)
- **validate_url(url: str) -> bool**: Check if URL is valid
- **validate_scheme(url: str) -> bool**: Validate URL scheme (http, https)
- **is_crawlable(url: str) -> bool**: Check if URL should be crawled (not mailto:, javascript:, etc.)
- Use urllib.parse for URL parsing
- Raise InvalidURLError for invalid URLs

### 2. Add Basic Validation Rules
- Only allow http and https schemes
- Reject non-crawlable URLs (mailto:, javascript:, data:, etc.)
- Basic URL format validation

## Files to Create/Modify
- `crawler/url/validator.py` - URL validation logic
- `crawler/url/__init__.py` - Module exports

## Phase 1 Simplifications
- **Removed**: Complex domain validation, malicious pattern detection
- **Focus**: Basic validation only - scheme and crawlability
- **Deferred to Phase 2**: Domain validation, pattern matching, robots.txt

## Functions to Implement
```python
def validate_url(url: str) -> bool
def validate_scheme(url: str) -> bool
def is_crawlable(url: str) -> bool
```

## Validation
- [ ] Valid URLs pass validation
- [ ] Invalid URLs raise InvalidURLError
- [ ] Non-crawlable URLs are rejected
- [ ] Edge cases are handled (empty strings, None, etc.)

## Notes
- Use Python's urllib.parse for URL parsing
- Keep validation simple for Phase 1
- More advanced validation comes in Phase 2

