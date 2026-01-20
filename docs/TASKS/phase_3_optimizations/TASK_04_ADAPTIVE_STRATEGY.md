# TASK 04: Adaptive Strategy

## Objective
Implement an adaptive/priority-based crawling strategy that prioritizes URLs based on various factors.

## Prerequisites
- TASK_01 completed (Strategy Base Interface)

## Steps

### 1. Implement Priority Queue
- Use heapq or PriorityQueue for priority management
- Support custom priority functions
- Support priority updates

### 2. Implement Adaptive Strategy (crawler/crawl_strategy/adaptive.py)
- Create AdaptiveStrategy class inheriting from BaseCrawlStrategy
- Implement priority-based crawling:
  - Calculate priority for each URL
  - Use priority queue for URL selection
  - Support multiple priority factors
- Implement required abstract methods
- Implement priority calculation:
  - URL depth (shallower = higher priority)
  - URL path length (shorter = higher priority)
  - URL patterns (matching patterns = higher priority)
  - Custom priority scores

### 3. Add Priority Factors
- Depth-based priority
- Path-based priority
- Pattern-based priority
- Custom priority weights
- Dynamic priority updates

### 4. Integrate with URL Filtering
- Filter URLs before adding to queue
- Apply priority after filtering

## Files to Create/Modify
- `crawler/crawl_strategy/adaptive.py` - Adaptive strategy implementation
- `crawler/crawl_strategy/__init__.py` - Update exports

## Source Task
- Original: TASK_18_ADAPTIVE_STRATEGY.md

## Priority Calculation
Priority = weighted sum of:
- Depth factor (1 / (depth + 1))
- Path factor (1 / path_length)
- Pattern match factor (1.0 if matches, 0.0 otherwise)
- Custom factors

## Validation
- [ ] Priority queue works correctly
- [ ] URLs are selected by priority
- [ ] Priority calculation is correct
- [ ] Priority updates work
- [ ] Multiple priority factors work together

## Notes
- Use heapq for efficient priority queue
- Make priority calculation configurable
- Support negative priorities for deprioritization

