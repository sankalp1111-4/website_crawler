# TASK 02: BFS Strategy

## Objective
Implement a Breadth-First Search (BFS) crawling strategy that crawls URLs level by level.

## Prerequisites
- TASK_01 completed (Strategy Base Interface)

## Steps

### 1. Implement BFS Strategy (crawler/crawl_strategy/bfs.py)
- Create BFSStrategy class inheriting from BaseCrawlStrategy
- Implement queue-based BFS algorithm:
  - Use collections.deque for queue
  - Track visited URLs
  - Track current depth
  - Process URLs level by level
- Implement required abstract methods
- Add depth tracking:
  - Track depth for each URL
  - Respect max_depth configuration
  - Increment depth when processing new level

### 2. Add URL Management
- Maintain queue of URLs to crawl
- Track visited URLs to avoid duplicates
- Track depth for each URL
- Filter URLs based on depth limit

### 3. Integrate with URL Filtering
- Use URL filter before adding to queue
- Respect robots.txt
- Apply domain filters
- Apply pattern filters

## Files to Create/Modify
- `crawler/crawl_strategy/bfs.py` - BFS strategy implementation
- `crawler/crawl_strategy/__init__.py` - Update exports

## Source Task
- Original: TASK_16_BFS_STRATEGY.md

## BFS Algorithm
1. Initialize queue with start URL (depth 0)
2. While queue not empty and limits not reached:
   - Dequeue next URL (FIFO)
   - If not visited and within depth limit:
     - Mark as visited
     - Crawl URL
     - Extract links
     - Add links to queue with depth + 1
3. Stop when max_pages or max_depth reached

## Validation
- [ ] URLs are processed in breadth-first order
- [ ] Depth is tracked correctly
- [ ] Max depth limit is respected
- [ ] Max pages limit is respected
- [ ] Duplicate URLs are avoided

## Notes
- Use collections.deque for efficient queue operations
- Track depth separately for each URL
- Consider memory usage for large sites

