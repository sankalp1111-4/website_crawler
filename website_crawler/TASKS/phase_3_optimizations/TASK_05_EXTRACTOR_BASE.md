# TASK 05: Extractor Base Interface

## Objective
Create the abstract base class for content extractors, defining the interface that all extractors must implement.

## Prerequisites
- Phase 1 completed (Data models, HTML Parser)

## Steps

### 1. Implement Extractor Base (crawler/extraction/base.py)
- Create BaseExtractor abstract class
- Define abstract methods:
  - **extract(html: str, url: str, config: Dict[str, Any]) -> ExtractedContent**: Extract content from HTML
  - **validate_config(config: Dict[str, Any]) -> bool**: Validate extractor configuration
- Define common methods:
  - **clean_text(text: str) -> str**: Clean extracted text
  - **extract_links(html: str, base_url: str) -> List[str]**: Extract links from HTML
  - **extract_title(html: str) -> Optional[str]**: Extract page title
  - **extract_metadata(html: str) -> Dict[str, Any]**: Extract metadata
- Add type hints and docstrings

### 2. Define Extractor Interface
- All extractors must implement the interface
- Support different extraction methods (CSS, XPath, LLM)
- Support configuration-driven extraction
- Support error handling

### 3. Add Extractor Configuration
- Extractor-specific configuration
- Common configuration (selectors, options)
- Validation rules

## Files to Create/Modify
- `crawler/extraction/base.py` - Base extractor interface
- `crawler/extraction/__init__.py` - Update exports

## Source Task
- Original: TASK_19_EXTRACTOR_BASE.md

## Extractor Interface
```python
class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, html: str, url: str, config: Dict[str, Any]) -> ExtractedContent:
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> bool:
        pass
    
    def clean_text(self, text: str) -> str
    def extract_links(self, html: str, base_url: str) -> List[str]
    def extract_title(self, html: str) -> Optional[str]
    def extract_metadata(self, html: str) -> Dict[str, Any]
```

## Validation
- [ ] Base class cannot be instantiated
- [ ] Abstract methods must be implemented
- [ ] Interface is clear and well-documented
- [ ] Type hints are correct

## Notes
- Use ABC from abc module
- Make interface flexible for different extractors
- Document expected behavior

