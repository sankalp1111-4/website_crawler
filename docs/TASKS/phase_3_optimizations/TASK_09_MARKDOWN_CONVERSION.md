# TASK 09: Markdown Conversion

## Objective
Implement HTML to Markdown conversion to create clean, readable markdown representations of crawled content.

## Prerequisites
- Phase 1 TASK_07 completed (HTML Parser)
- requirements.txt with markdownify or html2text

## Steps

### 1. Implement Markdown Converter (crawler/parsing/markdown.py)
- Create MarkdownConverter class
- Use markdownify or html2text library
- Implement HTML to Markdown conversion:
  - Convert HTML elements to Markdown
  - Preserve structure (headings, lists, links)
  - Handle code blocks
  - Handle tables
  - Handle images
- Add conversion options:
  - Heading style
  - List style
  - Link style
  - Code block style
  - Image handling

### 2. Add Content Processing
- Clean HTML before conversion
- Preserve important formatting
- Handle special cases (nested lists, complex tables)
- Normalize markdown output

### 3. Integrate with Parser
- Use parsed HTML from HTMLParser
- Convert to markdown
- Store in Document model

## Files to Create/Modify
- `crawler/parsing/markdown.py` - Markdown conversion logic
- `crawler/parsing/__init__.py` - Update exports
- `crawler/models/document.py` - Add markdown field support

## Source Task
- Original: TASK_24_MARKDOWN_CONVERSION.md

## Conversion Features
- HTML to Markdown conversion
- Structure preservation
- Link conversion
- Image conversion
- Code block conversion
- Table conversion

## Validation
- [ ] HTML is converted to Markdown correctly
- [ ] Structure is preserved
- [ ] Links are converted correctly
- [ ] Images are handled
- [ ] Code blocks are converted
- [ ] Output is valid Markdown

## Notes
- Use markdownify or html2text library
- Handle edge cases (nested structures, etc.)
- Test with various HTML structures

