"""
Crawl controller for handling crawl API requests.
"""
import copy
from contextlib import contextmanager
from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, status

from crawler.orchestrator import CrawlOrchestrator
from config.loader import load_config
from config.schema import MainConfig
from controller.models import (
    CrawlResponse,
    BatchCrawlResponse,
    ClientCrawlRequest
)
from controller.policy_resolver import CrawlPolicyResolver
from crawler.exceptions import (
    CrawlError,
    ValidationError,
    StorageError
)
from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("CrawlController", __name__)

router = APIRouter(prefix="/crawl", tags=["crawl"])


# Global orchestrator instance (initialized on first request)
_orchestrator: Optional[CrawlOrchestrator] = None


def get_orchestrator() -> CrawlOrchestrator:
    """
    Get or create orchestrator instance.
    
    Returns:
        CrawlOrchestrator instance
    """
    global _orchestrator
    
    if _orchestrator is None:
        logger.log_entry("get_orchestrator", action="initializing")
        config = load_config()
        config_dict = config.model_dump()
        _orchestrator = CrawlOrchestrator(config_dict)
        _orchestrator.initialize()
        logger.log_state_change("orchestrator_not_initialized", "orchestrator_initialized")
        logger.log_exit("get_orchestrator", status="initialized")
    else:
        logger.log_decision("ORCHESTRATOR_REUSED", "Using existing orchestrator instance")
    
    return _orchestrator


# ============================================================================
# Helper Functions
# ============================================================================

async def _resolve_request_config(
    request: ClientCrawlRequest,
    orchestrator: CrawlOrchestrator,
    request_logger: ComponentLoggerAdapter
) -> Dict[str, Any]:
    """
    Resolve client request to internal configuration dictionary.
    
    Args:
        request: Client crawl request
        orchestrator: Orchestrator instance
        request_logger: Logger for the request
        
    Returns:
        Configuration dictionary ready for orchestrator
    """
    request_logger.log_entry("resolve_client_intent")
    base_config = MainConfig.model_validate(orchestrator.config)
    resolver = CrawlPolicyResolver(base_config)
    internal_config = await resolver.resolve(request)
    request_logger.log_exit("resolve_client_intent", status="resolved")
    
    # Convert MainConfig to dict
    config_dict = internal_config.model_dump()
    
    # Handle chunking if requested (not in MainConfig schema)
    if request.enable_chunking:
        chunking_config = orchestrator.config.get('chunking', {}).copy()
        chunking_config['enabled'] = True
        config_dict['chunking'] = chunking_config
    
    return config_dict


@contextmanager
def isolated_config(orchestrator: CrawlOrchestrator, config_dict: Dict[str, Any]):
    """
    Context manager for temporarily applying config to orchestrator.
    
    Ensures config is always restored, even if an exception occurs.
    
    Args:
        orchestrator: Orchestrator instance
        config_dict: Configuration dictionary to apply
    """
    original_config = copy.deepcopy(orchestrator.config)
    try:
        orchestrator.config = config_dict
        orchestrator._reinitialize_components()
        yield
    finally:
        orchestrator.config = original_config
        orchestrator._reinitialize_components()


def _handle_crawl_exception(
    e: Exception,
    url_str: str,
    request_logger: ComponentLoggerAdapter
) -> HTTPException:
    """
    Handle exceptions and return appropriate HTTPException.
    
    Args:
        e: Exception that occurred
        url_str: URL being crawled
        request_logger: Logger for the request
        
    Returns:
        HTTPException with appropriate status code and details
    """
    if isinstance(e, ValidationError):
        request_logger.log_decision("VALIDATION_ERROR", reason=str(e))
        request_logger.error(f"[CrawlController] Validation error: {str(e)}", exc_info=True)
        request_logger.log_state_change("request_pending", "request_failed", error_type="ValidationError")
        status_code = status.HTTP_400_BAD_REQUEST
        error_msg = "Validation failed"
        message = str(e)
    elif isinstance(e, CrawlError):
        request_logger.log_decision("CRAWL_ERROR", reason=str(e))
        request_logger.error(f"[CrawlController] Crawl error: {str(e)}", exc_info=True)
        request_logger.log_state_change("request_pending", "request_failed", error_type="CrawlError")
        status_code = status.HTTP_502_BAD_GATEWAY
        error_msg = "Crawl failed"
        message = str(e)
    elif isinstance(e, StorageError):
        request_logger.log_decision("STORAGE_ERROR", reason=str(e))
        request_logger.error(f"[CrawlController] Storage error: {str(e)}", exc_info=True)
        request_logger.log_state_change("request_pending", "request_failed", error_type="StorageError")
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_msg = "Storage failed"
        message = str(e)
    else:
        request_logger.log_decision("UNEXPECTED_ERROR", reason=str(e))
        request_logger.exception(f"[CrawlController] Unexpected error: {str(e)}")
        request_logger.log_state_change("request_pending", "request_failed", error_type="Exception")
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        error_msg = "Internal server error"
        message = "An unexpected error occurred"
    
    return HTTPException(
        status_code=status_code,
        detail={
            "error": error_msg,
            "message": message,
            "url": url_str
        }
    )


def _get_document_ids(orchestrator: CrawlOrchestrator, crawl_run_id: str) -> List[str]:
    """
    Fetch document IDs for a crawl run from storage.
    
    Args:
        orchestrator: Orchestrator instance
        crawl_run_id: Crawl run ID
        
    Returns:
        List of document IDs
    """
    try:
        if hasattr(orchestrator.storage, 'source_pages_collection') and orchestrator.storage.source_pages_collection:
            source_pages = list(orchestrator.storage.source_pages_collection.find(
                {'crawl_run_id': crawl_run_id}
            ))
            return [str(sp.get('_id', sp.get('source_page_id', ''))) for sp in source_pages]
    except Exception:
        pass
    return []


# ============================================================================
# API Endpoints
# ============================================================================

@router.post(
    "",
    response_model=CrawlResponse,
    status_code=status.HTTP_200_OK,
    summary="Crawl a single URL",
    description="""
    Crawl a single URL and store the results in the configured storage backend.
    
    This endpoint uses intent-based configuration - just tell us what you want.
    Backend handles all infrastructure settings (storage, logging, rate limits, etc.).
    
    This endpoint performs a single-page crawl with the following pipeline:
    1. URL validation and normalization
    2. URL filtering (robots.txt, domain restrictions, pattern matching)
    3. Page crawling using Crawl4AI engine
    4. Content extraction using configured extractor (CSS/XPath/LLM)
    5. Optional markdown conversion
    6. Optional content chunking
    7. Document storage in MongoDB
    
    **Client-Controlled Parameters:**
    
    - **max_pages**: Maximum number of pages to crawl (1-10000)
    - **max_depth**: Maximum crawling depth (1-10)
    - **strategy**: Crawl strategy (auto/sitemap/bfs/dfs)
    - **render_js**: Enable JavaScript rendering
    - **extract**: What to extract (text, links, images, metadata)
    - **selectors**: CSS selectors for content extraction
    - **allowed_domains**: List of allowed domains
    - **exclude_patterns**: URL patterns to exclude
    - **enable_chunking**: Enable document chunking
    
    **Backend-Controlled (Not Exposed):**
    
    - Storage configuration (connection strings, credentials, database settings)
    - Engine infrastructure (browser type, viewport dimensions)
    - Rate limiting, timeouts, retries
    - Logging configuration
    
    All backend settings are configured via backend config files and environment variables.
    """,
    responses={
        200: {
            "description": "Crawl completed successfully",
            "content": {
                "application/json": {
                    "example": {
                        "success": True,
                        "document_id": "507f1f77bcf86cd799439011",
                        "url": "https://example.com",
                        "message": "Crawl completed successfully",
                        "warnings": []
                    }
                }
            }
        },
        400: {
            "description": "Validation error - Invalid request parameters",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "error": "Validation failed",
                            "message": "Invalid URL format",
                            "url": "https://example.com"
                        }
                    }
                }
            }
        },
        502: {
            "description": "Crawl error - Failed to crawl the URL",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "error": "Crawl failed",
                            "message": "Timeout while loading page",
                            "url": "https://example.com"
                        }
                    }
                }
            }
        },
        500: {
            "description": "Internal server error - Storage or unexpected error",
            "content": {
                "application/json": {
                    "example": {
                        "detail": {
                            "error": "Storage failed",
                            "message": "Failed to save document to database",
                            "url": "https://example.com"
                        }
                    }
                }
            }
        }
    }
)
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


@router.post(
    "/batch",
    response_model=BatchCrawlResponse,
    status_code=status.HTTP_200_OK,
    summary="Crawl multiple URLs",
    description="""
    Simplified intent-based crawling API.
    
    Just tell us what you want - we handle the rest automatically.
    
    **Example:**
    
    {
      "url": "https://docs.crawl4ai.com/",
      "max_pages": 20,
      "strategy": "sitemap",
      "extract": {
        "text": true,
        "links": true,
        "images": true,
        "metadata": true
      },
      "enable_chunking": true
    }
    
    """)
async def crawl_batch(request: ClientCrawlRequest) -> BatchCrawlResponse:
    """Simplified batch crawl endpoint - intent-based configuration."""
    url_str = str(request.url)
    request_logger = logger.with_url(url_str)
    
    with request_logger.component_flow("crawl_batch", url=url_str):
        try:
            # Get orchestrator
            orchestrator = get_orchestrator()
            
            # Resolve client intent to internal config
            config_dict = await _resolve_request_config(request, orchestrator, request_logger)
            
            # Use isolated config context
            with isolated_config(orchestrator, config_dict):
                # Perform crawl
                crawl_run = await orchestrator.crawl_with_strategy_unified(url_str)
                
                # Query document IDs from storage
                document_ids = _get_document_ids(orchestrator, crawl_run.crawl_run_id)
                
                response = BatchCrawlResponse(
                    success=True,
                    documents_count=crawl_run.total_pages_crawled,
                    document_ids=document_ids,
                    start_url=url_str,
                    message=f"Crawl completed successfully. Crawled {crawl_run.total_pages_crawled} documents.",
                    warnings=[]
                )
                return response
            
        except (ValidationError, CrawlError, StorageError, Exception) as e:
            raise _handle_crawl_exception(e, url_str, request_logger)

