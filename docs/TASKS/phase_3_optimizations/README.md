# Phase 3: Optimizations & Advanced Features

## Goal
Add multiple strategies, extractors, and optimizations. Expand the crawler with advanced features for different use cases.

## Deliverable
Feature-rich crawler with multiple strategies, extractors, markdown conversion, chunking, and batching capabilities.

## Task List

1. **TASK_01**: Strategy Base Interface
   - Abstract base class for strategies
   - Strategy interface definition

2. **TASK_02**: BFS Strategy
   - Breadth-first search crawling
   - Depth tracking

3. **TASK_03**: Sitemap Strategy
   - XML sitemap parsing
   - Sitemap-based URL discovery

4. **TASK_04**: Adaptive Strategy
   - Priority-based crawling
   - Multi-factor prioritization

5. **TASK_05**: Extractor Base Interface
   - Abstract base class for extractors
   - Extractor interface definition

6. **TASK_06**: CSS Extractor
   - CSS selector-based extraction
   - Selector fallbacks

7. **TASK_07**: XPath Extractor
   - XPath-based extraction
   - XPath expression support

8. **TASK_08**: LLM Extractor
   - LLM-based intelligent extraction
   - Schema-based extraction

9. **TASK_09**: Markdown Conversion
   - HTML to Markdown conversion
   - Structure preservation

10. **TASK_10**: Chunking & Batching
    - Document chunking
    - Batch processing

11. **TASK_11**: Session Management (from Phase 2)
    - Cookie management
    - Session persistence
    - Per-domain sessions
    - **Note**: Implemented at the end after all other methods are complete and tested end-to-end

12. **TASK_12**: Headers & Proxies (from Phase 2)
    - Custom headers
    - Proxy support
    - Proxy rotation
    - **Note**: Depends on Session Management, so implemented after TASK_11

## Implementation Order

```
TASK_01 (Strategy Base)
  → TASK_02 (BFS Strategy)
  → TASK_03 (Sitemap Strategy)
  → TASK_04 (Adaptive Strategy)
  → TASK_05 (Extractor Base)
  → TASK_06 (CSS Extractor)
  → TASK_07 (XPath Extractor)
  → TASK_08 (LLM Extractor)
  → TASK_09 (Markdown Conversion)
  → TASK_10 (Chunking & Batching)
  → TASK_11 (Session Management) [Deferred from Phase 2]
  → TASK_12 (Headers & Proxies) [Deferred from Phase 2, depends on TASK_11]
```

## Success Criteria

- [ ] Multiple crawling strategies work
- [ ] Multiple extractors work
- [ ] Strategies can be selected via configuration
- [ ] Extractors can be selected via configuration
- [ ] Markdown conversion works
- [ ] Chunking works correctly
- [ ] Batch processing works
- [ ] System is extensible with new strategies/extractors
- [ ] Advanced features integrate well with existing system
- [ ] Session management works correctly (end of Phase 3)
- [ ] Headers and proxies work correctly (end of Phase 3)
- [ ] All methods tested end-to-end before session management and headers/proxies

## Notes

- Build on Phase 1 and Phase 2 foundations
- Focus on extensibility
- Ensure strategies and extractors are configurable
- Test each strategy and extractor independently
- Consider factory patterns for strategy/extractor creation

