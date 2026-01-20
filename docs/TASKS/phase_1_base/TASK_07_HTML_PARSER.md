# TASK 07: HTML Parser

## Objective
Implement HTML parsing utilities to extract text, clean content, and prepare HTML for storage.

## Prerequisites
- requirements.txt with beautifulsoup4
- TASK_01 completed (Data models)

## Steps

### 1. Implement HTML Parser (crawler/parsing/html_parser.py)
- Create HTMLParser class
- Implement HTML parsing using BeautifulSoup4:
  - Parse HTML content
  - Extract text content
  - Remove scripts and styles
  - Handle encoding issues
- Implement basic content cleaning:
  - Remove extra whitespace
  - Normalize line breaks
- Implement link extraction:
  - Extract all links (a tags)
  - Resolve relative URLs using normalizer
- Implement metadata extraction:
  - Extract page title
  - Extract basic meta tags

### 2. Add Text Extraction
- Extract main text content
- Preserve paragraph structure

### 3. Add Basic Content Normalization
- Normalize whitespace
- Remove HTML entities
- Decode special characters

## Files to Create/Modify
- `crawler/parsing/html_parser.py` - HTML parsing logic
- `crawler/parsing/__init__.py` - Module exports

## Phase 1 Scope
- **Focus**: Essential parsing - text extraction, link extraction, title extraction
- **Deferred to Phase 3**: Structured data extraction (JSON-LD, microdata), advanced metadata extraction

## Parsing Features
- HTML parsing
- Text extraction
- Basic content cleaning
- Link extraction
- Title extraction
- Basic metadata extraction

## Functions to Implement
```python
class HTMLParser:
    def __init__(self, config: Optional[Dict[str, Any]] = None)
    def parse(self, html: str, url: str) -> Dict[str, Any]
    def extract_text(self, html: str) -> str
    def extract_links(self, html: str, base_url: str) -> List[str]
    def extract_title(self, html: str) -> Optional[str]
    def clean_text(self, text: str) -> str
```

## Validation
- [ ] HTML is parsed correctly
- [ ] Text is extracted accurately
- [ ] Links are extracted correctly
- [ ] Title is extracted
- [ ] Content cleaning works
- [ ] Encoding issues are handled
- [ ] Malformed HTML is handled gracefully

## Notes
- Use BeautifulSoup4 for parsing
- Handle various HTML encodings
- Keep parsing focused on essential features for Phase 1
- More advanced parsing features come in Phase 3

