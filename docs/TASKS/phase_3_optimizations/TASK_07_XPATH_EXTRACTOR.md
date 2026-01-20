# TASK 07: XPath Extractor

## Objective
Implement an XPath-based content extractor that uses XPath expressions to extract specific content from HTML.

## Prerequisites
- TASK_05 completed (Extractor Base Interface)
- requirements.txt with lxml

## Steps

### 1. Implement XPath Extractor (crawler/extraction/xpath_extractor.py)
- Create XPathExtractor class inheriting from BaseExtractor
- Use lxml for XPath evaluation
- Implement XPath-based extraction:
  - Support multiple XPath expressions
  - Extract text content
  - Extract HTML content
  - Extract attributes
  - Handle missing XPath gracefully
- Implement required abstract methods
- Add XPath matching:
  - Try XPath expressions in order
  - Return first match or combine matches
  - Support XPath fallbacks

### 2. Add Content Extraction
- Extract main content using XPath
- Extract title
- Extract metadata
- Extract links
- Clean extracted text

### 3. Add Configuration Support
- XPath expression configuration
- XPath priority/order
- Extraction options

## Files to Create/Modify
- `crawler/extraction/xpath_extractor.py` - XPath extractor implementation
- `crawler/extraction/__init__.py` - Update exports

## Source Task
- Original: TASK_21_XPATH_EXTRACTOR.md

## XPath Configuration
```json
{
  "xpaths": {
    "main_content": ["//article", "//div[@class='content']", "//main"],
    "title": ["//h1", "//title"],
    "metadata": {
      "description": "//meta[@name='description']/@content",
      "keywords": "//meta[@name='keywords']/@content"
    }
  }
}
```

## Validation
- [ ] XPath expressions work correctly
- [ ] Content is extracted accurately
- [ ] XPath fallbacks work
- [ ] Missing XPath are handled gracefully
- [ ] Text cleaning works

## Notes
- Use lxml for XPath evaluation
- Support XPath 1.0 syntax
- Handle malformed HTML gracefully

