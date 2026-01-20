# TASK 03: Sitemap Strategy

## Objective
Implement a sitemap-based crawling strategy that uses XML sitemaps to discover and prioritize URLs.

## Prerequisites
- TASK_01 completed (Strategy Base Interface)

## Steps

### 1. Implement Sitemap Parser
- Parse XML sitemap files
- Support sitemap index files
- Support regular sitemap files
- Extract URLs from sitemap
- Extract metadata (lastmod, changefreq, priority)
- Handle compressed sitemaps (gzip) if needed

### 2. Implement Sitemap Strategy (crawler/crawl_strategy/sitemap.py)
- Create SitemapStrategy class inheriting from BaseCrawlStrategy
- Implement sitemap discovery:
  - Try robots.txt for sitemap location
  - Try common sitemap locations (/sitemap.xml, /sitemap_index.xml)
  - Support multiple sitemap files
- Implement required abstract methods
- Add priority handling:
  - Use sitemap priority for URL ordering
  - Use lastmod for freshness
  - Use changefreq for scheduling hints

### 3. Add Sitemap Caching
- Cache parsed sitemaps
- Handle sitemap updates
- Support sitemap refresh

### 4. Integrate with URL Filtering
- Filter URLs from sitemap
- Respect robots.txt
- Apply domain filters

## Files to Create/Modify
- `crawler/crawl_strategy/sitemap.py` - Sitemap strategy implementation
- `crawler/crawl_strategy/__init__.py` - Update exports

## Source Task
- Original: TASK_17_SITEMAP_STRATEGY.md

## Sitemap Discovery
1. Check robots.txt for sitemap location
2. Try /sitemap.xml
3. Try /sitemap_index.xml
4. Parse sitemap index to get individual sitemaps
5. Parse all sitemaps and extract URLs

## Validation
- [ ] Sitemaps are discovered correctly
- [ ] Sitemap parsing works
- [ ] URLs are extracted correctly
- [ ] Priority ordering works
- [ ] Sitemap index files work

## Notes
- Use xml.etree.ElementTree or lxml for parsing
- Handle both sitemap and sitemap index formats
- Support compressed sitemaps
- Cache sitemaps to avoid repeated fetches

