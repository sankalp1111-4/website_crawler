# TASK 04: URL Normalization - Minimal

## Objective
Implement minimal URL normalization to ensure consistent URL representation and avoid duplicate crawling.

## Prerequisites
- TASK_03 completed (URL Validation)

## Steps

### 1. Implement URL Normalizer (crawler/url/normalizer.py)
- **normalize_url(url: str, base_url: Optional[str] = None) -> str**: Normalize a URL
- **resolve_relative_url(relative: str, base: str) -> str**: Resolve relative URLs
- **remove_fragment(url: str) -> str**: Remove URL fragment (#section)
- Use urllib.parse for URL operations

### 2. Basic Normalization Rules
- Convert to absolute URL if relative
- Remove fragment (#section)
- Basic URL cleaning

## Files to Create/Modify
- `crawler/url/normalizer.py` - URL normalization logic
- `crawler/url/__init__.py` - Update exports

## Phase 1 Simplifications
- **Removed**: Query parameter sorting, trailing slash handling, port removal, domain lowercasing
- **Focus**: Essential normalization only - absolute URLs and fragment removal
- **Deferred to Phase 2**: Advanced normalization rules

## Functions to Implement
```python
def normalize_url(url: str, base_url: Optional[str] = None) -> str
def resolve_relative_url(relative: str, base: str) -> str
def remove_fragment(url: str) -> str
```

## Validation
- [ ] URLs are normalized consistently
- [ ] Relative URLs are resolved correctly
- [ ] Fragments are removed
- [ ] Same URLs produce same normalized form

## Notes
- Use urllib.parse.urljoin for URL joining
- Keep normalization simple for Phase 1
- More advanced normalization comes in Phase 2

