# TASK 08: Content Extraction

## Objective
Implement simple content extraction from HTML. For Phase 1, use crawl4ai's built-in extraction or a minimal CSS-based approach.

## Prerequisites
- TASK_07 completed (HTML Parser)
- TASK_05 completed (Crawl4AI Engine)

## Steps

### Option A: Use Crawl4AI Built-in Extraction (Recommended for Phase 1)
- Leverage crawl4ai's built-in content extraction
- Use crawl4ai's markdown conversion if available
- Extract text content directly from crawl4ai response

### Option B: Minimal CSS Extractor (If crawl4ai extraction is insufficient)
- Create simple CSSExtractor class
- Use BeautifulSoup4 for parsing
- Implement basic text extraction using common selectors (article, main, .content)
- Fallback to body text if no specific selector matches

### 1. Implement Extraction Logic
- Extract main content from HTML
- Use HTML parser for text extraction
- Combine title and content
- Handle extraction failures gracefully

### 2. Integrate with Pipeline
- Extract content after crawling
- Pass extracted content to document model

## Files to Create/Modify
- `crawler/extraction/__init__.py` - Module exports
- Optionally: `crawler/extraction/simple_extractor.py` - If not using crawl4ai built-in

## Phase 1 Approach
- **Prefer**: Use crawl4ai's built-in extraction capabilities
- **Alternative**: Minimal CSS selector-based extraction
- **Deferred to Phase 3**: Full extractor framework, multiple extractors (CSS, XPath, LLM)

## Extraction Strategy
1. Try crawl4ai's built-in extraction first
2. If not available, use HTML parser's text extraction
3. Combine title and content
4. Store in Document model

## Validation
- [ ] Content is extracted from HTML
- [ ] Text is clean and readable
- [ ] Title is extracted correctly
- [ ] Extraction handles failures gracefully
- [ ] Content is suitable for storage

## Notes
- For Phase 1, prefer simplicity over complexity
- Full extractor framework comes in Phase 3
- Focus on getting content extracted and stored

