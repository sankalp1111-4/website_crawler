# Testing Guide - Website Crawler Service

This guide provides comprehensive testing instructions for the Website Crawler Service, including configuration explanations, usage examples, and end-to-end testing scenarios.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Data Storage Architecture](#data-storage-architecture)
3. [Configuration Overview](#configuration-overview)
4. [Configuration Options](#configuration-options)
5. [Testing Scenarios](#testing-scenarios)
6. [API Testing Examples](#api-testing-examples)
7. [Manual Testing Workflows](#manual-testing-workflows)

---

## Getting Started

### Prerequisites

- MongoDB running (default: `mongodb://localhost:27017`)
- Python 3.8+ with dependencies installed
- FastAPI server running

### Start the Service

```bash
# Navigate to project directory
cd website_crawler

# Start the FastAPI server
python main.py

# Or using uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API will be available at: `http://localhost:8000`

**Important Note**: By default, chunking is disabled. To verify that content is actually scraped and stored, you need to enable chunking in your config override. See [Data Storage Architecture](#data-storage-architecture) section for details.

### Verify Service Health

```bash
# Check health endpoint
curl http://localhost:8000/health

# Expected response:
# {
#   "status": "healthy",
#   "timestamp": "2024-01-01T12:00:00",
#   "service": "website-crawler",
#   "version": "1.0.0"
# }
```

---

## Data Storage Architecture

**Important**: Understanding where content is stored is crucial for verifying scraped data.

### Collections in MongoDB

The crawler uses three main collections in MongoDB:

1. **`source_pages`** - Stores page metadata and tracking information
   - Contains: URL, normalized URL, content hash, timestamps, status, metadata (title, links, headers)
   - Does NOT contain: Actual scraped text content
   - Always created when a page is crawled

2. **`page_chunks`** - Stores actual scraped text content
   - Contains: Chunked text content, chunk metadata, token counts
   - Only created if `chunking.enabled: true` in config
   - **This is where you'll find the actual scraped content**

3. **`crawl_runs`** - Stores multi-page crawl session information
   - Contains: Crawl statistics, start URL, strategy type, timestamps
   - Only created for batch/multi-page crawls

### How to Verify Content Was Scraped

**To see the actual scraped content, you MUST enable chunking:**

```json
{
  "chunking": {
    "enabled": true,
    "chunk_size_tokens": 512,
    "chunk_overlap_tokens": 50
  }
}
```

**Without chunking enabled:**
- Only `source_pages` document is created
- Contains metadata (title, links, headers) but NOT the text content
- Content hash is stored for change detection, but not the actual text

**With chunking enabled:**
- `source_pages` document is created (metadata)
- `page_chunks` documents are created (actual text content)
- You can verify content by querying `page_chunks` collection

### Quick Verification Query

```bash
# After crawling, get source_page_id from API response
source_page_id="src_0f115db062b7c0dd"

# Check if content exists (chunks)
mongosh crawler_db
db.page_chunks.find({"source_page_id": source_page_id}).count()

# View actual content
db.page_chunks.find(
  {"source_page_id": source_page_id},
  {"chunk_index": 1, "content": 1}
).sort({"chunk_index": 1})
```

---

## Configuration Overview

The crawler uses a hierarchical configuration system with the following priorities:
1. **Default config** (`config/defaults.json`) - Base configuration
2. **Environment variables** - Override defaults
3. **Config overrides in API requests** - Per-request customization

### Configuration Structure

```json
{
  "crawler": { ... },      // Crawl behavior settings
  "engine": { ... },       // Browser engine settings
  "storage": { ... },      // Storage backend settings
  "extraction": { ... },   // Content extraction settings
  "strategy": { ... },     // Crawling strategy settings
  "chunking": { ... },     // Document chunking settings
  "batching": { ... },     // Batch processing settings
  "auth": { ... },         // Authentication settings
  "logging": { ... }       // Logging settings
}
```

---

## Configuration Options

### 1. Crawler Configuration

Controls the core crawling behavior.

| Config Key | Default | Type | Why Use | Single-Line Usage |
|------------|---------|------|---------|-------------------|
| `max_depth` | 3 | int | Limit crawling depth to control scope | `{"crawler": {"max_depth": 2}}` |
| `max_pages` | 100 | int | Limit total pages crawled to prevent runaway crawls | `{"crawler": {"max_pages": 50}}` |
| `delay` | 1.0 | float | Add delay between requests to be polite to servers | `{"crawler": {"delay": 2.0}}` |
| `timeout` | 30 | int | Set request timeout in seconds | `{"crawler": {"timeout": 60}}` |
| `retries` | 3 | int | Number of retry attempts for failed requests | `{"crawler": {"retries": 5}}` |
| `rate_limit` | null | float | Limit requests per second (null = no limit) | `{"crawler": {"rate_limit": 2.0}}` |
| `respect_robots_txt` | true | bool | Respect robots.txt to avoid banned URLs | `{"crawler": {"respect_robots_txt": false}}` |
| `follow_redirects` | true | bool | Follow HTTP redirects automatically | `{"crawler": {"follow_redirects": false}}` |
| `max_redirects` | 5 | int | Maximum redirects to follow | `{"crawler": {"max_redirects": 10}}` |
| `max_html_size` | 16777216 | int | Maximum HTML size in bytes (16MB default) | `{"crawler": {"max_html_size": 33554432}}` |
| `reject_empty_content` | true | bool | Reject pages with no content | `{"crawler": {"reject_empty_content": false}}` |
| `allowed_domains` | null | list | Whitelist domains for crawling | `{"crawler": {"allowed_domains": ["example.com"]}}` |
| `blocked_domains` | null | list | Blacklist domains to skip | `{"crawler": {"blocked_domains": ["ads.example.com"]}}` |
| `exclude_patterns` | [] | list | URL patterns to exclude (regex) | `{"crawler": {"exclude_patterns": ["/login", "/admin"]}}` |

### 2. Engine Configuration

Controls browser engine behavior.

| Config Key | Default | Type | Why Use | Single-Line Usage |
|------------|---------|------|---------|-------------------|
| `headless` | true | bool | Run browser in headless mode (no GUI) | `{"engine": {"headless": false}}` |
| `browser_type` | "chromium" | str | Choose browser (chromium/firefox/webkit) | `{"engine": {"browser_type": "firefox"}}` |
| `viewport_width` | 1920 | int | Set browser viewport width | `{"engine": {"viewport_width": 1366}}` |
| `viewport_height` | 1080 | int | Set browser viewport height | `{"engine": {"viewport_height": 768}}` |
| `wait_for` | null | str | CSS selector to wait for before extraction | `{"engine": {"wait_for": ".content-loaded"}}` |
| `wait_timeout` | 30 | int | Timeout for wait_for selector | `{"engine": {"wait_timeout": 60}}` |
| `js_enabled` | true | bool | Enable JavaScript execution | `{"engine": {"js_enabled": false}}` |
| `images_enabled` | true | bool | Load images (disable for speed) | `{"engine": {"images_enabled": false}}` |
| `css_enabled` | true | bool | Load CSS (disable for speed) | `{"engine": {"css_enabled": false}}` |

### 3. Storage Configuration

Controls storage backend settings.

| Config Key | Default | Type | Why Use | Single-Line Usage |
|------------|---------|------|---------|-------------------|
| `type` | "mongodb" | str | Storage backend type | `{"storage": {"type": "mongodb"}}` |
| `connection_string` | "mongodb://localhost:27017" | str | MongoDB connection string | `{"storage": {"connection_string": "mongodb://user:pass@host:27017"}}` |
| `database` | "crawler_db" | str | Database name | `{"storage": {"database": "my_crawler_db"}}` |
| `collection` | "crawled_pages" | str | Collection name | `{"storage": {"collection": "pages"}}` |
| `max_pool_size` | 100 | int | Maximum connection pool size | `{"storage": {"max_pool_size": 50}}` |
| `max_document_size` | 16777216 | int | Max document size before save (16MB) | `{"storage": {"max_document_size": 33554432}}` |

### 4. Extraction Configuration

Controls content extraction behavior.

| Config Key | Default | Type | Why Use | Single-Line Usage |
|------------|---------|------|---------|-------------------|
| `type` | "css" | str | Extractor type (css/xpath/llm/auto) | `{"extraction": {"type": "xpath"}}` |
| `selectors` | {} | dict | CSS/XPath selectors for content | `{"extraction": {"selectors": {"title": "h1", "content": ".main"}}}` |
| `extract_text` | true | bool | Extract text content | `{"extraction": {"extract_text": true}}` |
| `extract_links` | true | bool | Extract links from pages | `{"extraction": {"extract_links": true}}` |
| `extract_images` | false | bool | Extract image URLs | `{"extraction": {"extract_images": true}}` |
| `extract_metadata` | true | bool | Extract page metadata | `{"extraction": {"extract_metadata": true}}` |
| `clean_html` | true | bool | Clean HTML before extraction | `{"extraction": {"clean_html": false}}` |

### 5. Strategy Configuration

Controls crawling strategy for multi-page crawls.

| Config Key | Default | Type | Why Use | Single-Line Usage |
|------------|---------|------|---------|-------------------|
| `type` | "bfs" | str | Strategy type (bfs/sitemap/adaptive) | `{"strategy": {"type": "sitemap"}}` |
| `max_depth` | null | int | Strategy-specific depth override | `{"strategy": {"max_depth": 5}}` |
| `max_pages` | null | int | Strategy-specific page limit override | `{"strategy": {"max_pages": 200}}` |
| `priority_patterns` | [] | list | URL patterns to prioritize | `{"strategy": {"priority_patterns": ["/blog/", "/docs/"]}}` |
| `exclude_patterns` | [] | list | URL patterns to exclude | `{"strategy": {"exclude_patterns": ["/login", "/admin"]}}` |

**Strategy Types:**
- **bfs**: Breadth-first search - crawls level by level
- **sitemap**: Uses sitemap.xml for URL discovery (efficient)
- **adaptive**: Automatically adapts based on site structure

### 6. Chunking Configuration

Controls document chunking for large content.

| Config Key | Default | Type | Why Use | Single-Line Usage |
|------------|---------|------|---------|-------------------|
| `enabled` | false | bool | Enable document chunking | `{"chunking": {"enabled": true}}` |
| `chunk_size_tokens` | 512 | int | Maximum tokens per chunk | `{"chunking": {"chunk_size_tokens": 1024}}` |
| `chunk_overlap_tokens` | 50 | int | Overlap between chunks in tokens | `{"chunking": {"chunk_overlap_tokens": 100}}` |
| `chunk_size` | 1000 | int | Fallback chunk size in characters | `{"chunking": {"chunk_size": 2000}}` |
| `chunk_overlap` | 200 | int | Fallback overlap in characters | `{"chunking": {"chunk_overlap": 400}}` |
| `strategy` | "sentence" | str | Chunking strategy (sentence/paragraph/token) | `{"chunking": {"strategy": "paragraph"}}` |
| `preserve_sentences` | true | bool | Preserve sentence boundaries | `{"chunking": {"preserve_sentences": true}}` |
| `preserve_paragraphs` | true | bool | Preserve paragraph boundaries | `{"chunking": {"preserve_paragraphs": true}}` |
| `tokenizer` | "cl100k_base" | str | Tokenizer model name | `{"chunking": {"tokenizer": "cl100k_base"}}` |

### 7. Batching Configuration

Controls batch processing for multiple URLs.

| Config Key | Default | Type | Why Use | Single-Line Usage |
|------------|---------|------|---------|-------------------|
| `batch_size` | 10 | int | Number of URLs per batch | `{"batching": {"batch_size": 20}}` |
| `max_concurrent` | 5 | int | Maximum concurrent requests | `{"batching": {"max_concurrent": 10}}` |
| `fail_fast` | false | bool | Stop on first error | `{"batching": {"fail_fast": true}}` |

### 8. Auth Configuration

Controls authentication and headers.

| Config Key | Default | Type | Why Use | Single-Line Usage |
|------------|---------|------|---------|-------------------|
| `headers` | {} | dict | Custom HTTP headers | `{"auth": {"headers": {"X-API-Key": "secret"}}}` |
| `cookies` | {} | dict | HTTP cookies | `{"auth": {"cookies": {"session": "abc123"}}}` |
| `proxies` | [] | list | Proxy URLs | `{"auth": {"proxies": ["http://proxy:8080"]}}` |
| `user_agent` | null | str | Custom user agent | `{"auth": {"user_agent": "MyBot/1.0"}}` |
| `basic_auth` | null | dict | Basic auth credentials | `{"auth": {"basic_auth": {"username": "user", "password": "pass"}}}` |

### 9. Logging Configuration

Controls logging behavior.

| Config Key | Default | Type | Why Use | Single-Line Usage |
|------------|---------|------|---------|-------------------|
| `level` | "INFO" | str | Log level (DEBUG/INFO/WARNING/ERROR) | `{"logging": {"level": "DEBUG"}}` |
| `format` | "simple" | str | Log format (json/text/simple/detailed) | `{"logging": {"format": "json"}}` |
| `file_path` | null | str | Log file path | `{"logging": {"file_path": "/tmp/crawler.log"}}` |
| `console_enabled` | true | bool | Enable console logging | `{"logging": {"console_enabled": false}}` |
| `file_enabled` | false | bool | Enable file logging | `{"logging": {"file_enabled": true}}` |

---

## Testing Scenarios

### Quick Tips for Using curl Commands

**Simplified Format**: All curl examples now use a cleaner, more readable format:
- **Minimal examples** first - shows the simplest way to use each feature
- **Full config examples** when needed - shows all available options
- **Chunking included** - Most examples include `"chunking": {"enabled": true}` so you can verify content in MongoDB
- **Inline JSON** - Configs are compact and easy to read

**Common Pattern**:
```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "config_override": {
      "chunking": {"enabled": true}  # Always add this to see content!
    }
  }'
```

**Remember**: 
- Single page = `/crawl` endpoint
- Multi-page = `/crawl/batch` endpoint with `"use_strategy": true`
- Always enable chunking if you want to verify scraped content in MongoDB

---

### Scenario 1: Single Page Crawl (Basic)

**Objective**: Test basic single-page crawling without any special features.

**Minimal Request** (uses defaults):
```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**With Chunking** (to see actual content in MongoDB):
```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "config_override": {
      "chunking": {"enabled": true}
    }
  }'
```

**Full Config** (all options):
```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "config_override": {
      "chunking": {"enabled": true, "chunk_size_tokens": 512},
      "crawler": {"timeout": 30},
      "extraction": {"extract_text": true, "extract_links": true}
    }
  }'
```

**Expected Result**:
- Single page crawled
- Content extracted and stored in MongoDB
- Document ID (source_page_id) returned in response
- **Important**: To verify scraped content is stored, chunking must be enabled. Without chunking, only metadata and content hash are stored.

**Verify in MongoDB**:
```bash
# Connect to MongoDB
mongosh crawler_db

# 1. Check SourcePage was created (contains metadata, not actual content)
db.source_pages.findOne({"url": "https://example.com"})

# 2. Get the source_page_id from the response or query above
source_page_id = "src_0f115db062b7c0dd"  # Replace with actual ID from response

# 3. Check PageChunks for actual scraped content (only if chunking enabled)
db.page_chunks.find({"source_page_id": source_page_id}).pretty()

# 4. View actual content text
db.page_chunks.find(
  {"source_page_id": source_page_id}, 
  {"content": 1, "chunk_index": 1, "chunk_size": 1}
).sort({"chunk_index": 1})

# 5. Check metadata in SourcePage
db.source_pages.findOne(
  {"url": "https://example.com"},
  {"metadata": 1, "content_hash": 1, "total_chunks": 1, "status": 1}
)
```

**Note**: 
- **SourcePage** (`source_pages` collection): Stores page metadata, URL, timestamps, content hash, but NOT the actual text content
- **PageChunk** (`page_chunks` collection): Stores the actual scraped text content, but only if `chunking.enabled: true`
- To verify content was scraped properly, enable chunking and check the `page_chunks` collection

---

### Scenario 2: Single Page with CSS Selectors

**Objective**: Test targeted content extraction using CSS selectors.

**Simple Request**:
```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/blog/post",
    "config_override": {
      "extraction": {
        "selectors": {"title": "h1", "content": "article", "author": ".author"}
      },
      "chunking": {"enabled": true}
    }
  }'
```

**Note**: CSS is the default extraction type, so `"type": "css"` is optional.

**Expected Result**:
- Page crawled with targeted selectors
- Structured content extracted (title, content, author)
- Content saved with selector-based structure

---

### Scenario 3: Single Page with XPath Selectors

**Objective**: Test XPath-based extraction for complex page structures.

**Simple Request**:
```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "config_override": {
      "extraction": {
        "type": "xpath",
        "selectors": {"title": "//h1", "content": "//div[@class='content']"}
      },
      "chunking": {"enabled": true}
    }
  }'
```

---

### Scenario 4: Multi-Page Crawl (BFS Strategy)

**Objective**: Test multi-page crawling using BFS strategy.

**Simple Request**:
```bash
curl -X POST "http://localhost:8000/crawl/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "use_strategy": true,
    "config_override": {
      "strategy": {"type": "bfs", "max_pages": 10},
      "chunking": {"enabled": true}
    }
  }'
```

**With More Options**:
```bash
curl -X POST "http://localhost:8000/crawl/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "use_strategy": true,
    "config_override": {
      "strategy": {"type": "bfs", "max_depth": 2, "max_pages": 10},
      "crawler": {"delay": 1.0},
      "chunking": {"enabled": true}
    }
  }'
```

**Expected Result**:
- Multiple pages crawled (up to 10)
- Pages crawled level by level (BFS)
- All documents stored in MongoDB

**Verify in MongoDB**:
```bash
# Check crawl run
db.crawl_runs.findOne({"start_url": "https://example.com"})

# Count source pages for this crawl run
db.source_pages.countDocuments({"crawl_run_id": "<crawl_run_id>"})

# View source pages
db.source_pages.find({"crawl_run_id": "<crawl_run_id>"}).limit(5).pretty()
```

---

### Scenario 5: Multi-Page Crawl (Sitemap Strategy)

**Objective**: Test efficient sitemap-based URL discovery.

**Simple Request**:
```bash
curl -X POST "http://localhost:8000/crawl/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "use_strategy": true,
    "config_override": {
      "strategy": {"type": "sitemap", "max_pages": 50},
      "chunking": {"enabled": true}
    }
  }'
```

**Expected Result**:
- URLs discovered from sitemap.xml
- Faster discovery than link-following
- Priority patterns applied if specified

---

### Scenario 6: Multi-Page Crawl (Adaptive Strategy)

**Objective**: Test adaptive strategy that chooses the best method.

**Simple Request**:
```bash
curl -X POST "http://localhost:8000/crawl/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "use_strategy": true,
    "config_override": {
      "strategy": {"type": "adaptive", "max_pages": 100},
      "chunking": {"enabled": true}
    }
  }'
```

---

### Scenario 7: Single Page with Chunking Enabled

**Objective**: Test document chunking on a single large page.

**Minimal Request**:
```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/long-article",
    "config_override": {
      "chunking": {"enabled": true}
    }
  }'
```

**With Custom Chunking**:
```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/long-article",
    "config_override": {
      "chunking": {
        "enabled": true,
        "chunk_size_tokens": 512,
        "chunk_overlap_tokens": 50
      }
    }
  }'
```

**Expected Result**:
- Large document chunked into smaller pieces
- Chunks preserve sentence boundaries
- Chunks stored with metadata (index, size, overlap)
- Original document also stored

**Verify in MongoDB**:
```bash
# Get source_page_id from API response
source_page_id = "<source_page_id_from_response>"

# Check SourcePage
db.source_pages.findOne({"_id": source_page_id})

# Check PageChunks (actual content is here)
db.page_chunks.find({"source_page_id": source_page_id}).sort({"chunk_index": 1}).pretty()

# View content summary
db.page_chunks.find(
  {"source_page_id": source_page_id},
  {"chunk_index": 1, "content": 1, "chunk_size": 1, "token_count": 1}
).sort({"chunk_index": 1})

# Count chunks
db.page_chunks.countDocuments({"source_page_id": source_page_id, "status": "active"})
```

---

### Scenario 8: Multi-Page with Chunking and Batching

**Objective**: Test end-to-end: multi-page crawl with chunking and batch processing.

**Simple Request**:
```bash
curl -X POST "http://localhost:8000/crawl/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "use_strategy": true,
    "config_override": {
      "strategy": {"type": "bfs", "max_pages": 20},
      "chunking": {"enabled": true},
      "batching": {"max_concurrent": 5}
    }
  }'
```

**Full Config** (all options):
```bash
curl -X POST "http://localhost:8000/crawl/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "use_strategy": true,
    "config_override": {
      "strategy": {"type": "bfs", "max_depth": 2, "max_pages": 20},
      "chunking": {"enabled": true, "chunk_size_tokens": 1024},
      "batching": {"batch_size": 10, "max_concurrent": 5},
      "crawler": {"delay": 1.0}
    }
  }'
```

**Expected Result**:
- 20 pages crawled using BFS strategy
- Each page chunked if content is large
- Pages processed in batches of 10
- Up to 5 concurrent requests
- All documents and chunks stored

**Verify End-to-End**:
```bash
# 1. Check crawl run was created
db.crawl_runs.findOne({"start_url": "https://example.com"})

# 2. Get crawl_run_id from above
crawl_run_id = "<crawl_run_id_from_above>"

# 3. Check source pages were created
db.source_pages.countDocuments({"crawl_run_id": crawl_run_id})
db.source_pages.find({"crawl_run_id": crawl_run_id}).limit(5).pretty()

# 4. Get source_page_ids
source_page_ids = db.source_pages.find({"crawl_run_id": crawl_run_id}, {"_id": 1}).toArray().map(d => d._id)

# 5. Check chunks were created (actual content is here)
db.page_chunks.countDocuments({"source_page_id": {$in: source_page_ids}, "status": "active"})

# 6. View sample chunks with content
db.page_chunks.find(
  {"source_page_id": {$in: source_page_ids}, "status": "active"},
  {"source_page_id": 1, "chunk_index": 1, "content": 1, "chunk_size": 1}
).limit(10).pretty()

# 7. Verify content was scraped (check a specific page)
sample_source_page_id = source_page_ids[0]
db.page_chunks.find(
  {"source_page_id": sample_source_page_id},
  {"content": 1, "chunk_index": 1}
).sort({"chunk_index": 1}).limit(3)
```

---

### Scenario 9: Single Page with Custom Headers/Auth

**Objective**: Test crawling with authentication and custom headers.

**Simple Request**:
```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/protected",
    "config_override": {
      "auth": {
        "headers": {"Authorization": "Bearer token123"},
        "user_agent": "MyBot/1.0"
      },
      "chunking": {"enabled": true}
    }
  }'
```

**With Cookies**:
```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/protected",
    "config_override": {
      "auth": {
        "headers": {"Authorization": "Bearer token123"},
        "cookies": {"session_id": "abc123"}
      },
      "chunking": {"enabled": true}
    }
  }'
```

---

### Scenario 10: Single Page with Wait-For Selector

**Objective**: Test waiting for dynamic content to load.

**Simple Request**:
```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/spa",
    "config_override": {
      "engine": {"wait_for": ".content-loaded"},
      "chunking": {"enabled": true}
    }
  }'
```

**With Custom Timeout**:
```bash
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/spa",
    "config_override": {
      "engine": {"wait_for": ".content-loaded", "wait_timeout": 60},
      "chunking": {"enabled": true}
    }
  }'
```

---

### Scenario 11: Fast Crawl (Performance Optimized)

**Objective**: Test high-speed crawling with optimizations.

**Simple Request**:
```bash
curl -X POST "http://localhost:8000/crawl/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "use_strategy": true,
    "config_override": {
      "strategy": {"type": "bfs", "max_pages": 50},
      "engine": {"images_enabled": false, "css_enabled": false},
      "crawler": {"delay": 0.1},
      "batching": {"max_concurrent": 10},
      "chunking": {"enabled": true}
    }
  }'
```

---

### Scenario 12: Domain Restricted Crawl

**Objective**: Test domain whitelisting/blacklisting.

**Simple Request**:
```bash
curl -X POST "http://localhost:8000/crawl/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "use_strategy": true,
    "config_override": {
      "strategy": {"type": "bfs", "max_pages": 20},
      "crawler": {
        "allowed_domains": ["example.com"],
        "exclude_patterns": ["/api/", "/admin/"]
      },
      "chunking": {"enabled": true}
    }
  }'
```

---

## API Testing Examples

### Using cURL

```bash
# 1. Basic single page crawl (minimal)
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# 2. Single page with chunking (to see content in MongoDB)
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "config_override": {"chunking": {"enabled": true}}
  }'

# 3. Single page with CSS selectors
curl -X POST "http://localhost:8000/crawl" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "config_override": {
      "extraction": {"selectors": {"title": "h1", "content": "article"}},
      "chunking": {"enabled": true}
    }
  }'

# 4. Batch crawl (simple)
curl -X POST "http://localhost:8000/crawl/batch" \
  -H "Content-Type: application/json" \
  -d '{
    "start_url": "https://example.com",
    "use_strategy": true,
    "config_override": {
      "strategy": {"type": "bfs", "max_pages": 10},
      "chunking": {"enabled": true}
    }
  }'
```

### Using Python requests

```python
import requests

# Single page crawl
response = requests.post(
    "http://localhost:8000/crawl",
    json={
        "url": "https://example.com",
        "config_override": {
            "extraction": {
                "type": "css",
                "selectors": {"title": "h1"}
            }
        }
    }
)
print(response.json())

# Batch crawl with chunking
response = requests.post(
    "http://localhost:8000/crawl/batch",
    json={
        "start_url": "https://example.com",
        "use_strategy": True,
        "config_override": {
            "strategy": {"type": "bfs", "max_pages": 20},
            "chunking": {
                "enabled": True,
                "chunk_size_tokens": 512
            }
        }
    }
)
print(response.json())
```

### Using JavaScript/Node.js

```javascript
// Single page crawl
fetch('http://localhost:8000/crawl', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    url: 'https://example.com',
    config_override: {
      extraction: {
        type: 'css',
        selectors: {title: 'h1'}
      }
    }
  })
})
.then(res => res.json())
.then(data => console.log(data));

// Batch crawl
fetch('http://localhost:8000/crawl/batch', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    start_url: 'https://example.com',
    use_strategy: true,
    config_override: {
      strategy: {type: 'bfs', max_pages: 10},
      chunking: {enabled: true, chunk_size_tokens: 512}
    }
  })
})
.then(res => res.json())
.then(data => console.log(data));
```

---

## Manual Testing Workflows

### Workflow 1: Complete End-to-End Test (Recommended First Test)

1. **Start MongoDB** (if not running)
   ```bash
   mongod
   ```

2. **Start the Crawler Service**
   ```bash
   cd website_crawler
   python main.py
   ```

3. **Test Health Endpoint**
   ```bash
   curl http://localhost:8000/health
   ```

4. **Run Single Page Crawl** (with chunking to see content)
   ```bash
   curl -X POST "http://localhost:8000/crawl" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://example.com",
       "config_override": {"chunking": {"enabled": true}}
     }'
   ```

5. **Verify in MongoDB**
   ```bash
   mongosh crawler_db
   
   # Check SourcePage (metadata)
   db.source_pages.find().limit(1).pretty()
   
   # If chunking was enabled, check actual content
   source_page_id = "<source_page_id_from_response>"
   db.page_chunks.find({"source_page_id": source_page_id}).limit(1).pretty()
   ```

6. **Run Multi-Page Crawl** (with chunking to see content)
   ```bash
   curl -X POST "http://localhost:8000/crawl/batch" \
     -H "Content-Type: application/json" \
     -d '{
       "start_url": "https://example.com",
       "use_strategy": true,
       "config_override": {
         "strategy": {"type": "bfs", "max_pages": 5},
         "chunking": {"enabled": true}
       }
     }'
   ```

7. **Verify Results**
   ```bash
   # Count source pages
   db.source_pages.countDocuments()
   
   # View crawl runs
   db.crawl_runs.find().pretty()
   
   # View source pages with metadata
   db.source_pages.find().limit(5).pretty()
   
   # If chunking enabled, view actual content
   db.page_chunks.find().limit(5).pretty()
   ```

---

### Workflow 2: Test Chunking and Batching

1. **Crawl a large page with chunking**
   ```bash
   curl -X POST "http://localhost:8000/crawl" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://example.com/long-article",
       "config_override": {
         "chunking": {
           "enabled": true,
           "chunk_size_tokens": 512,
           "chunk_overlap_tokens": 50
         }
       }
     }'
   ```

2. **Verify chunks in MongoDB**
   ```bash
   # Get source_page_id from API response (this is the document_id)
   source_page_id="<source_page_id_from_response>"
   
   # Check SourcePage metadata
   db.source_pages.findOne({"_id": source_page_id})
   
   # Check chunks (actual scraped content is here)
   db.page_chunks.find({"source_page_id": source_page_id}).sort({"chunk_index": 1}).pretty()
   
   # View content text
   db.page_chunks.find(
     {"source_page_id": source_page_id},
     {"chunk_index": 1, "content": 1, "chunk_size": 1}
   ).sort({"chunk_index": 1})
   ```

3. **Test batch crawl with chunking**
   ```bash
   curl -X POST "http://localhost:8000/crawl/batch" \
     -H "Content-Type: application/json" \
     -d '{
       "start_url": "https://example.com",
       "use_strategy": true,
       "config_override": {
         "strategy": {"type": "bfs", "max_pages": 10},
         "chunking": {"enabled": true},
         "batching": {"max_concurrent": 3}
       }
     }'
   ```

---

### Workflow 3: Test Different Extractors

1. **Test CSS Extractor**
   ```bash
   curl -X POST "http://localhost:8000/crawl" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://example.com",
       "config_override": {
         "extraction": {"selectors": {"title": "h1", "content": "article"}},
         "chunking": {"enabled": true}
       }
     }'
   ```

2. **Test XPath Extractor**
   ```bash
   curl -X POST "http://localhost:8000/crawl" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://example.com",
       "config_override": {
         "extraction": {
           "type": "xpath",
           "selectors": {"title": "//h1", "content": "//article"}
         },
         "chunking": {"enabled": true}
       }
     }'
   ```

---

### Workflow 4: Test Different Strategies

1. **Test BFS Strategy**
   ```bash
   curl -X POST "http://localhost:8000/crawl/batch" \
     -H "Content-Type: application/json" \
     -d '{
       "start_url": "https://example.com",
       "use_strategy": true,
       "config_override": {
         "strategy": {"type": "bfs", "max_pages": 10},
         "chunking": {"enabled": true}
       }
     }'
   ```

2. **Test Sitemap Strategy**
   ```bash
   curl -X POST "http://localhost:8000/crawl/batch" \
     -H "Content-Type: application/json" \
     -d '{
       "start_url": "https://example.com",
       "use_strategy": true,
       "config_override": {
         "strategy": {"type": "sitemap", "max_pages": 50},
         "chunking": {"enabled": true}
       }
     }'
   ```

3. **Test Adaptive Strategy**
   ```bash
   curl -X POST "http://localhost:8000/crawl/batch" \
     -H "Content-Type: application/json" \
     -d '{
       "start_url": "https://example.com",
       "use_strategy": true,
       "config_override": {
         "strategy": {"type": "adaptive", "max_pages": 100},
         "chunking": {"enabled": true}
       }
     }'
   ```

---

## Configuration Switching Guide

### How to Switch Configurations

**Method 1: API Request Override (Recommended for Testing)**
- Use `config_override` in API requests
- Changes apply only to that request
- No server restart needed

**Method 2: Environment Variables**
```bash
export CRAWLER_MAX_DEPTH=5
export ENGINE_HEADLESS=false
export EXTRACTION_TYPE=xpath
python main.py
```

**Method 3: Update defaults.json**
```json
{
  "crawler": {
    "max_depth": 5,
    "max_pages": 200
  }
}
```
- Requires server restart
- Applies to all requests (unless overridden)

---

## Troubleshooting

### Common Issues

1. **MongoDB Connection Error**
   - Check MongoDB is running: `mongod`
   - Verify connection string in config
   - Check network/firewall settings

2. **Timeout Errors**
   - Increase `crawler.timeout`
   - Increase `engine.wait_timeout`
   - Check network connectivity

3. **Empty Content Warnings**
   - Disable `reject_empty_content` to see what's being extracted
   - Check selectors match page structure
   - Verify JavaScript is enabled for dynamic content

4. **Rate Limiting**
   - Increase `crawler.delay`
   - Reduce `batching.max_concurrent`
   - Set `crawler.rate_limit` appropriately

5. **Memory Issues**
   - Reduce `batching.batch_size`
   - Reduce `crawler.max_pages`
   - Enable chunking for large documents

---

## MongoDB Query Examples

### View Source Pages (Metadata)
```javascript
// View all source pages
db.source_pages.find().limit(10).pretty()

// Find by URL
db.source_pages.findOne({"url": "https://example.com"})

// Find by normalized URL
db.source_pages.findOne({"normalized_url": "https://example.com/"})

// View metadata including title, links, etc.
db.source_pages.findOne(
  {"url": "https://example.com"},
  {"metadata": 1, "content_hash": 1, "total_chunks": 1, "status": 1}
)
```

### View Page Chunks (Actual Content)
```javascript
// View all chunks
db.page_chunks.find().limit(10).pretty()

// Find chunks for a specific source page (actual scraped content)
source_page_id = "src_0f115db062b7c0dd"
db.page_chunks.find({"source_page_id": source_page_id}).sort({"chunk_index": 1}).pretty()

// View only content text
db.page_chunks.find(
  {"source_page_id": source_page_id},
  {"chunk_index": 1, "content": 1, "chunk_size": 1}
).sort({"chunk_index": 1})

// Count chunks for a page
db.page_chunks.countDocuments({"source_page_id": source_page_id, "status": "active"})
```

### View Crawl Runs
```javascript
// View all crawl runs
db.crawl_runs.find().pretty()

// Find crawl run by start URL
db.crawl_runs.findOne({"start_url": "https://example.com"})
```

### Count Source Pages by Crawl Run
```javascript
crawl_run_id = "<crawl_run_id>"
db.source_pages.countDocuments({"crawl_run_id": crawl_run_id})
```

### Find Chunks for a Source Page
```javascript
source_page_id = "<source_page_id>"
db.page_chunks.find({"source_page_id": source_page_id}).sort({chunk_index: 1})
```

### Verify Content Was Scraped
```javascript
// Step 1: Find source page
source_page = db.source_pages.findOne({"url": "https://example.com"})
source_page_id = source_page._id

// Step 2: Check if chunks exist (content is stored here)
chunk_count = db.page_chunks.countDocuments({"source_page_id": source_page_id, "status": "active"})
print(`Found ${chunk_count} chunks for this page`)

// Step 3: View actual content
if (chunk_count > 0) {
  db.page_chunks.find(
    {"source_page_id": source_page_id},
    {"chunk_index": 1, "content": 1}
  ).sort({"chunk_index": 1}).limit(3)
} else {
  print("No chunks found. Enable chunking in config to store content.")
}
```

---

## Next Steps

After completing these tests:
1. Test with real websites (with permission)
2. Test error scenarios (invalid URLs, timeouts, etc.)
3. Test performance with larger crawls
4. Test authentication scenarios
5. Monitor logs for issues
6. Verify data quality in MongoDB

---

## Quick Reference

### Single Page Crawl
```bash
POST /crawl
{"url": "https://example.com", "config_override": {...}}
```

### Multi-Page Crawl
```bash
POST /crawl/batch
{"start_url": "https://example.com", "use_strategy": true, "config_override": {...}}
```

### Health Check
```bash
GET /health
```

### View API Docs
```
http://localhost:8000/docs
```

---

## Key Points for Content Verification

### ✅ To Verify Scraped Content is Stored:

1. **Enable chunking in your request**:
   ```json
   {
     "chunking": {
       "enabled": true,
       "chunk_size_tokens": 512
     }
   }
   ```

2. **Check the correct collections**:
   - `source_pages` - Contains metadata (title, links, headers) but NOT text content
   - `page_chunks` - Contains actual scraped text content (only if chunking enabled)

3. **Query example**:
   ```bash
   # Get source_page_id from API response
   source_page_id="<from_api_response>"
   
   # View actual content
   mongosh crawler_db
   db.page_chunks.find(
     {"source_page_id": source_page_id},
     {"chunk_index": 1, "content": 1}
   ).sort({"chunk_index": 1})
   ```

### ❌ Common Mistakes:

- Looking for content in `source_pages` collection (only has metadata)
- Not enabling chunking and expecting to see content
- Using old collection names (`crawled_pages`, `documents`) - these are for legacy architecture
- Forgetting to get `source_page_id` from API response before querying

