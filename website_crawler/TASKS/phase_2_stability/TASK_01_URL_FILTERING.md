# TASK 01: URL Filtering

## Objective
Implement URL filtering to exclude unwanted URLs based on robots.txt, patterns, and other rules.

## Prerequisites
- Phase 1 completed (URL Validation, URL Normalization)
- TASK_02 from Phase 1 (Exceptions)

## Steps

### 1. Implement URL Filter (crawler/url/filter.py)
- **should_crawl(url: str, filters: Dict[str, Any]) -> bool**: Determine if URL should be crawled
- **check_robots_txt(url: str, user_agent: str) -> bool**: Check robots.txt rules
- **match_pattern(url: str, pattern: str) -> bool**: Match URL against pattern (regex or glob)
- **is_allowed_domain(url: str, allowed_domains: List[str]) -> bool**: Check if domain is allowed
- **is_blocked_domain(url: str, blocked_domains: List[str]) -> bool**: Check if domain is blocked
- **filter_by_file_extension(url: str, allowed_extensions: List[str]) -> bool**: Filter by file extension

### 2. Implement Robots.txt Support
- Parse robots.txt files
- Check if URL is allowed for given user agent
- Cache robots.txt rules
- Handle missing or invalid robots.txt gracefully

### 3. Implement Pattern Matching
- Support regex patterns
- Support glob patterns
- Support include/exclude lists

### 4. Add Filter Configuration
- Allow/block domain lists
- Pattern matching rules
- File extension filters
- Robots.txt respect flag

## Files to Create/Modify
- `crawler/url/filter.py` - URL filtering logic
- `crawler/url/__init__.py` - Update exports

## Source Task
- Original: TASK_09_URL_FILTERING.md

## Filtering Rules
- Respect robots.txt (if enabled)
- Check allowed/blocked domains
- Match against include/exclude patterns
- Filter by file extension

## Functions to Implement
```python
def should_crawl(url: str, filters: Dict[str, Any]) -> bool
def check_robots_txt(url: str, user_agent: str = "CrawlerBot") -> bool
def match_pattern(url: str, pattern: str, pattern_type: str = "regex") -> bool
def is_allowed_domain(url: str, allowed_domains: List[str]) -> bool
def is_blocked_domain(url: str, blocked_domains: List[str]) -> bool
def filter_by_file_extension(url: str, allowed_extensions: List[str]) -> bool
```

## Validation
- [ ] URLs are filtered correctly based on rules
- [ ] Robots.txt is respected when enabled
- [ ] Pattern matching works for regex and glob
- [ ] Domain filtering works correctly
- [ ] File extension filtering works

## Notes
- Use urllib.robotparser for robots.txt
- Cache robots.txt to avoid repeated fetches
- Make filtering configurable
- Log filtered URLs for debugging

