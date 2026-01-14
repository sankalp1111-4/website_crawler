# Website Crawler - Phase-Wise Implementation Plan

## Overview
This document outlines the refactored 3-phase implementation plan focused on delivering a working MVP first, then stabilizing, then optimizing.

## Guiding Principles
- **Phase 1**: Minimal but complete, runnable, verifiable MVP
- **Phase 2**: Stabilization, correctness, error handling
- **Phase 3**: Advanced features, optimizations, multiple strategies/extractors

## Phase Mapping Summary

### PHASE 1: BASE CRAWLER (MVP - END TO END)
**Goal**: Crawl a website → Extract content → Normalize → Store in MongoDB

**Tasks**:
1. Data Models (from TASK_05)
2. Exceptions (from TASK_06)
3. URL Validation - Minimal (from TASK_07, simplified)
4. URL Normalization - Minimal (from TASK_08, simplified)
5. Crawl4AI Engine (from TASK_10)
6. Browser Config - Minimal (from TASK_11, simplified)
7. HTML Parser (from TASK_23)
8. Simple Content Extraction (use crawl4ai built-in or minimal CSS extractor)
9. MongoDB Storage (new task)
10. Basic Orchestrator (new task)

**Deliverable**: Working crawler that can crawl a URL, extract content, and store in MongoDB

---

### PHASE 2: STABILIZATION & CORRECTNESS
**Goal**: Improve error handling, validation, and robustness

**Tasks**:
1. URL Filtering (from TASK_09)
2. Performance Settings (from TASK_12)
3. Session Management (from TASK_13)
4. Headers & Proxies (from TASK_14)
5. Enhanced Error Handling
6. Improved Validation
7. Better Logging & Observability

**Deliverable**: Robust crawler with proper error handling and validation

---

### PHASE 3: OPTIMIZATIONS & ADVANCED FEATURES
**Goal**: Add multiple strategies, extractors, and optimizations

**Tasks**:
1. Strategy Base Interface (from TASK_15)
2. BFS Strategy (from TASK_16)
3. Sitemap Strategy (from TASK_17)
4. Adaptive Strategy (from TASK_18)
5. Extractor Base Interface (from TASK_19)
6. CSS Extractor - Full (from TASK_20)
7. XPath Extractor (from TASK_21)
8. LLM Extractor (from TASK_22)
9. Markdown Conversion (from TASK_24)
10. Advanced Performance Optimizations
11. Chunking & Batching

**Deliverable**: Feature-rich crawler with multiple strategies and extractors

---

## Detailed Task Mapping

### Original Tasks → New Phase Structure

| Original Task | New Phase | New Task | Changes |
|--------------|-----------|----------|---------|
| TASK_05 | Phase 1 | TASK_01 | Simplified: Removed ExtractedContent model, focused on essential fields |
| TASK_06 | Phase 1 | TASK_02 | Simplified: Minimal exception hierarchy (Crawl, Storage, Validation only) |
| TASK_07 | Phase 1 | TASK_03 | Simplified: Basic validation only (scheme, crawlability), removed domain/malicious pattern detection |
| TASK_08 | Phase 1 | TASK_04 | Simplified: Essential normalization only (absolute URLs, fragment removal), removed query sorting, port handling |
| TASK_10 | Phase 1 | TASK_05 | Simplified: Single URL crawling, basic error handling, removed batch/advanced retry |
| TASK_11 | Phase 1 | TASK_06 | Simplified: Minimal config (headless, browser type), removed mobile/tablet profiles, timezone, etc. |
| TASK_23 | Phase 1 | TASK_07 | Kept as-is: Essential HTML parsing for extraction |
| - | Phase 1 | TASK_08 | NEW: Simple content extraction (use crawl4ai built-in or minimal CSS) |
| - | Phase 1 | TASK_09 | NEW: MongoDB Storage (referenced in plan but not in TASK_04-24) |
| - | Phase 1 | TASK_10 | NEW: Basic Orchestrator (referenced in plan but not in TASK_04-24) |
| TASK_09 | Phase 2 | TASK_01 | Kept as-is: URL Filtering (robots.txt, patterns, domain filtering) |
| TASK_12 | Phase 2 | TASK_02 | Kept as-is: Performance Settings (timeouts, retries, rate limiting) |
| TASK_13 | Phase 2 | TASK_03 | Kept as-is: Session Management |
| TASK_14 | Phase 2 | TASK_04 | Kept as-is: Headers & Proxies |
| - | Phase 2 | TASK_05 | NEW: Enhanced Error Handling (expand exceptions, recovery strategies) |
| - | Phase 2 | TASK_06 | NEW: Enhanced Validation (improve validation rules, normalization) |
| - | Phase 2 | TASK_07 | NEW: Logging & Observability (structured logging, metrics) |
| TASK_15 | Phase 3 | TASK_01 | Kept as-is: Strategy Base Interface |
| TASK_16 | Phase 3 | TASK_02 | Kept as-is: BFS Strategy |
| TASK_17 | Phase 3 | TASK_03 | Kept as-is: Sitemap Strategy |
| TASK_18 | Phase 3 | TASK_04 | Kept as-is: Adaptive Strategy |
| TASK_19 | Phase 3 | TASK_05 | Kept as-is: Extractor Base Interface |
| TASK_20 | Phase 3 | TASK_06 | Kept as-is: CSS Extractor (full implementation) |
| TASK_21 | Phase 3 | TASK_07 | Kept as-is: XPath Extractor |
| TASK_22 | Phase 3 | TASK_08 | Kept as-is: LLM Extractor |
| TASK_24 | Phase 3 | TASK_09 | Kept as-is: Markdown Conversion |
| - | Phase 3 | TASK_10 | NEW: Chunking & Batching (advanced feature) |

### Key Decisions

#### Phase 1 Simplifications
- **URL Validation (TASK_07)**: Removed complex domain validation, malicious pattern detection → Phase 1 only needs basic scheme/crawlability checks
- **URL Normalization (TASK_08)**: Removed query parameter sorting, trailing slash handling, port removal → Phase 1 only needs absolute URL resolution and fragment removal
- **Browser Config (TASK_11)**: Removed mobile/tablet profiles, timezone, geolocation, JavaScript/CSS controls → Phase 1 only needs headless mode and basic browser type
- **Data Models (TASK_05)**: Removed ExtractedContent model → Phase 1 uses crawl4ai's built-in extraction directly
- **Crawl4AI Engine (TASK_10)**: Removed batch crawling, advanced retry logic → Phase 1 focuses on single URL crawling

#### Phase 1 Additions
- **MongoDB Storage**: Essential for MVP but was missing from TASK_04-24 list
- **Basic Orchestrator**: Essential for MVP to coordinate the pipeline but was missing from TASK_04-24 list
- **Simple Content Extraction**: New task to clarify extraction approach for Phase 1

#### Phase 2 Additions
- **Enhanced Error Handling**: Expand exception hierarchy and add recovery strategies
- **Enhanced Validation**: Improve validation rules and normalization beyond Phase 1 basics
- **Logging & Observability**: Structured logging and metrics for production readiness

#### Phase 3 Additions
- **Chunking & Batching**: Advanced feature for handling large documents and batch processing

### Tasks Not Included in Original TASK_04-24
- TASK_25 (MongoDB Storage) - Added as Phase 1 TASK_09
- TASK_26 (Storage Factory) - Deferred (factory patterns not needed for MVP)
- TASK_27 (Extractor Factory) - Deferred to Phase 3 (if needed)
- TASK_28 (Strategy Factory) - Deferred to Phase 3 (if needed)
- TASK_29 (Orchestrator) - Added as Phase 1 TASK_10

