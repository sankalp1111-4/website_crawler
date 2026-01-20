# TASK 06: CSS Extractor

## Objective
Implement a CSS selector-based content extractor that uses CSS selectors to extract specific content from HTML.

## Prerequisites
- TASK_05 completed (Extractor Base Interface)
- requirements.txt with beautifulsoup4

## Steps

### 1. Implement CSS Extractor (crawler/extraction/css_extractor.py)
- Create CSSExtractor class inheriting from BaseExtractor
- Use BeautifulSoup4 for HTML parsing
- Implement CSS selector-based extraction:
  - Support multiple CSS selectors
  - Extract text content
  - Extract HTML content
  - Extract attributes
  - Handle missing selectors gracefully
- Implement required abstract methods
- Add selector matching:
  - Try selectors in order
  - Return first match or combine matches
  - Support selector fallbacks

### 2. Add Content Extraction
- Extract main content using selectors
- Extract title
- Extract metadata (meta tags)
- Extract links
- Clean extracted text

### 3. Add Configuration Support
- CSS selector configuration
- Selector priority/order
- Extraction options (text only, include HTML, etc.)

## Files to Create/Modify
- `crawler/extraction/css_extractor.py` - CSS extractor implementation
- `crawler/extraction/__init__.py` - Update exports

## Source Task
- Original: TASK_20_CSS_EXTRACTOR.md

## CSS Selector Configuration
```json
{
  "selectors": {
    "main_content": ["article", ".content", "#main"],
    "title": ["h1", "title"],
    "metadata": {
      "description": "meta[name='description']",
      "keywords": "meta[name='keywords']"
    }
  }
}
```

## Validation
- [ ] CSS selectors work correctly
- [ ] Content is extracted accurately
- [ ] Selector fallbacks work
- [ ] Missing selectors are handled gracefully
- [ ] Text cleaning works

## Notes
- Use BeautifulSoup4 for HTML parsing
- Support CSS selector syntax
- Handle malformed HTML gracefully

