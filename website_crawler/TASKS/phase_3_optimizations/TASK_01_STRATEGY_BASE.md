# TASK 01: Strategy Base Interface

## Objective
Create the abstract base class for crawling strategies, defining the interface that all strategies must implement.

## Prerequisites
- Phase 1 completed (Data models, Orchestrator)
- Phase 2 completed (Enhanced Error Handling)

## Steps

### 1. Implement Strategy Base (crawler/crawl_strategy/base.py)
- Create BaseCrawlStrategy abstract class
- Define abstract methods:
  - **get_next_urls(visited: Set[str], queue: List[str]) -> List[str]**: Get next URLs to crawl
  - **should_continue(visited_count: int, max_pages: int) -> bool**: Check if crawling should continue
  - **initialize(start_url: str, config: Dict[str, Any]) -> None**: Initialize strategy
  - **add_urls(urls: List[str], metadata: Optional[Dict] = None) -> None**: Add URLs to crawl queue
- Define common methods:
  - **get_priority(url: str) -> int**: Get URL priority (for priority-based strategies)
  - **update_metadata(url: str, metadata: Dict[str, Any]) -> None**: Update URL metadata
- Add type hints and docstrings

### 2. Define Strategy Interface
- All strategies must implement the interface
- Support different crawling patterns (BFS, DFS, priority-based)
- Support metadata tracking
- Support URL prioritization

### 3. Add Strategy Configuration
- Strategy-specific configuration
- Common configuration (max_depth, max_pages)
- URL filtering integration

## Files to Create/Modify
- `crawler/crawl_strategy/base.py` - Base strategy interface
- `crawler/crawl_strategy/__init__.py` - Update exports

## Source Task
- Original: TASK_15_STRATEGY_BASE.md

## Strategy Interface
```python
class BaseCrawlStrategy(ABC):
    @abstractmethod
    def get_next_urls(self, visited: Set[str], queue: List[str], max_count: int = 1) -> List[str]
    
    @abstractmethod
    def should_continue(self, visited_count: int, max_pages: int) -> bool
    
    @abstractmethod
    def initialize(self, start_url: str, config: Dict[str, Any]) -> None
    
    @abstractmethod
    def add_urls(self, urls: List[str], metadata: Optional[Dict] = None) -> None
    
    def get_priority(self, url: str) -> int
    def update_metadata(self, url: str, metadata: Dict[str, Any]) -> None
```

## Validation
- [ ] Base class cannot be instantiated
- [ ] Abstract methods must be implemented
- [ ] Interface is clear and well-documented
- [ ] Type hints are correct

## Notes
- Use ABC from abc module
- Make interface flexible for different strategies
- Document expected behavior

