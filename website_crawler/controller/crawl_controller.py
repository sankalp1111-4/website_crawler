"""
Crawl controller for handling crawl API requests.
"""
import logging
import copy
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl, ConfigDict

from crawler.orchestrator import CrawlOrchestrator
from config.loader import load_config, deep_merge
from config.schema import MainConfig
from controller.models import ClientBatchCrawlRequest, ClientCrawlRequest
from controller.policy_resolver import CrawlPolicyResolver
from crawler.exceptions import (
    CrawlError,
    ValidationError,
    StorageError
)
from utils.logging_config import ComponentLoggerAdapter, get_component_logger

logger: ComponentLoggerAdapter = get_component_logger("CrawlController", __name__)

router = APIRouter(prefix="/crawl", tags=["crawl"])


class CrawlRequest(BaseModel):
    """Request model for crawl endpoint."""
    url: HttpUrl = Field(
        ...,
        description="URL to crawl",
        examples=["https://example.com", "https://www.example.com/page"]
    )
    config_override: Optional[Dict[str, Any]] = Field(
        None,
        description="""
        Optional configuration overrides. Can override any section:
        
        - **crawler**: max_depth, max_pages, delay, timeout, retries, rate_limit, respect_robots_txt, 
          follow_redirects, max_redirects, max_html_size, reject_empty_content, allowed_domains, 
          blocked_domains, exclude_patterns
        - **engine**: headless, browser_type (chromium/firefox/webkit), viewport_width, viewport_height, 
          wait_for, wait_timeout, js_enabled, images_enabled, css_enabled
        - **storage**: type, connection_string, database, collection, username, password, auth_source, 
          max_pool_size, max_document_size
        - **extraction**: type (css/xpath/llm), selectors, extract_text, extract_links, extract_images, 
          extract_metadata, clean_html, generate_markdown
        - **strategy**: type (bfs/sitemap/adaptive), max_depth, max_pages, priority_patterns, exclude_patterns
        - **auth**: headers, cookies, proxies, user_agent, basic_auth
        - **chunking**: enabled, chunk_size, chunk_overlap, strategy (sentence/paragraph/token), preserve_boundaries
        - **batching**: batch_size, max_concurrent, fail_fast
        - **logging**: level, format, file_path, console_enabled, file_enabled
        """,
        examples=[
            None,
            {
                "crawler": {
                    "max_depth": 2,
                    "max_pages": 50,
                    "delay": 2.0,
                    "timeout": 30,
                    "respect_robots_txt": True
                },
                "engine": {
                    "headless": True,
                    "wait_for": ".content-loaded",
                    "browser_type": "chromium"
                }
            },
            {
                "extraction": {
                    "type": "css",
                    "extract_images": True,
                    "selectors": {
                        "title": "h1",
                        "content": ".main-content"
                    }
                },
                "chunking": {
                    "enabled": True,
                    "chunk_size": 1000,
                    "chunk_overlap": 200
                }
            },
            {
                "extraction": {
                    "type": "xpath",
                    "selectors": {
                        "title": "//h1",
                        "content": "//div[@class='content']"
                    }
                },
                "strategy": {
                    "type": "bfs",
                    "max_depth": 3
                }
            }
        ]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "url": "https://example.com",
                "config_override": {
                    "crawler": {
                        "max_depth": 2,
                        "max_pages": 50,
                        "timeout": 30
                    },
                    "extraction": {
                        "type": "css",
                        "selectors": {
                            "title": "h1",
                            "content": ".main-content"
                        }
                    },
                    "engine": {
                        "headless": True,
                        "wait_for": ".content-loaded"
                    }
                }
            }
        }
    )


class CrawlResponse(BaseModel):
    """Response model for crawl endpoint."""
    success: bool = Field(
        ...,
        description="Whether the crawl was successful",
        examples=[True, False]
    )
    document_id: Optional[str] = Field(
        None,
        description="Document ID if successful. This ID can be used to retrieve the crawled document from storage.",
        examples=["507f1f77bcf86cd799439011", "doc_abc123xyz"]
    )
    url: str = Field(
        ...,
        description="Crawled URL",
        examples=["https://example.com", "https://www.example.com/page"]
    )
    message: str = Field(
        ...,
        description="Response message",
        examples=["Crawl completed successfully", "Crawl failed"]
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Any warnings encountered during the crawl process",
        examples=[[], ["Empty content detected", "Timeout occurred"]]
    )


class BatchCrawlResponse(BaseModel):
    """Response model for batch crawl endpoint."""
    success: bool = Field(
        ...,
        description="Whether the crawl was successful",
        examples=[True, False]
    )
    documents_count: int = Field(
        ...,
        description="Number of documents crawled",
        examples=[1, 10, 50]
    )
    document_ids: list[str] = Field(
        default_factory=list,
        description="List of document IDs for crawled documents",
        examples=[["doc1", "doc2", "doc3"]]
    )
    start_url: str = Field(
        ...,
        description="Starting URL",
        examples=["https://example.com"]
    )
    message: str = Field(
        ...,
        description="Response message",
        examples=["Batch crawl completed successfully", "Batch crawl failed"]
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Any warnings encountered during the crawl process",
        examples=[[], ["Some URLs failed to crawl"]]
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "success": True,
                    "document_id": "507f1f77bcf86cd799439011",
                    "url": "https://example.com",
                    "message": "Crawl completed successfully",
                    "warnings": []
                },
                {
                    "success": True,
                    "document_id": "507f1f77bcf86cd799439012",
                    "url": "https://example.com/page",
                    "message": "Crawl completed successfully",
                    "warnings": ["Empty content detected in some pages"]
                }
            ]
        }
    )


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
        config_dict = config.model_dump() if hasattr(config, 'model_dump') else dict(config)
        _orchestrator = CrawlOrchestrator(config_dict)
        _orchestrator.initialize()
        logger.log_state_change("orchestrator_not_initialized", "orchestrator_initialized")
        logger.log_exit("get_orchestrator", status="initialized")
    else:
        logger.log_decision("ORCHESTRATOR_REUSED", "Using existing orchestrator instance")
    
    return _orchestrator


@router.post(
    "",
    response_model=CrawlResponse,
    status_code=status.HTTP_200_OK,
    summary="Crawl a single URL",
    description="""
    Crawl a single URL and store the results in the configured storage backend (MongoDB).
    
    This endpoint performs a single-page crawl with the following pipeline:
    1. URL validation and normalization
    2. URL filtering (robots.txt, domain restrictions, pattern matching)
    3. Page crawling using Crawl4AI engine
    4. Content extraction using configured extractor (CSS/XPath/LLM)
    5. Optional markdown conversion
    6. Optional content chunking
    7. Document storage in MongoDB
    
    **Configuration Overrides:**
    
    The `config_override` parameter allows you to customize any aspect of the crawl:
    
    - **crawler**: Control crawl behavior (max_depth, max_pages, delay, timeout, retries, rate_limit, 
      respect_robots_txt, follow_redirects, max_redirects, max_html_size, reject_empty_content, 
      allowed_domains, blocked_domains, exclude_patterns)
    - **engine**: Browser settings (headless, browser_type: chromium/firefox/webkit, viewport_width, 
      viewport_height, wait_for selector, wait_timeout, js_enabled, images_enabled, css_enabled)
    - **extraction**: Content extraction (type: css/xpath/llm, selectors dict, extract_text, extract_links, 
      extract_images, extract_metadata, clean_html, generate_markdown)
    - **chunking**: Text chunking (enabled, chunk_size, chunk_overlap, strategy: sentence/paragraph/token, 
      preserve_boundaries)
    - **auth**: Authentication (headers dict, cookies dict, proxies list, user_agent string, basic_auth dict)
    - **logging**: Logging settings (level, format, file_path, console_enabled, file_enabled)
    
    Configuration overrides are merged with defaults and only apply to this request.
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
async def crawl_url(request: CrawlRequest) -> CrawlResponse:
    """
    Crawl a URL and store the results.
    
    Args:
        request: Crawl request containing URL and optional config overrides
        
    Returns:
        CrawlResponse with crawl results
        
    Raises:
        HTTPException: If crawl fails
    """
    url_str = str(request.url)
    request_logger = logger.with_url(url_str)
    
    with request_logger.component_flow("crawl_url", url=url_str, has_config_override=bool(request.config_override)):
        warnings = []
        
        try:
            # Get orchestrator
            request_logger.log_entry("get_orchestrator")
            orchestrator = get_orchestrator()
            request_logger.log_exit("get_orchestrator", status="retrieved")
            
            # Apply config overrides if provided
            if request.config_override:
                request_logger.log_entry("apply_config_overrides", overrides=request.config_override)
                
                # Log strategy before override
                original_strategy = orchestrator.config.get('strategy', {}).get('type', 'unknown')
                override_strategy = request.config_override.get('strategy', {}).get('type') if isinstance(request.config_override.get('strategy'), dict) else None
                
                if override_strategy:
                    request_logger.info(f"[CrawlController] Strategy override requested: {override_strategy} (original: {original_strategy})")
                
                # Deep copy original config to restore later
                original_config = copy.deepcopy(orchestrator.config)
                # Deep merge config overrides with existing config
                orchestrator.config = deep_merge(orchestrator.config, request.config_override)
                
                # Verify strategy was merged correctly
                merged_strategy = orchestrator.config.get('strategy', {}).get('type', 'unknown')
                request_logger.info(f"[CrawlController] Strategy after merge: {merged_strategy}")
                
                if override_strategy and merged_strategy != override_strategy:
                    request_logger.warning(
                        f"[CrawlController] Strategy override failed! Requested: {override_strategy}, "
                        f"but merged to: {merged_strategy}"
                    )
                
                # Re-initialize components to use updated config
                orchestrator._reinitialize_components()
                request_logger.info("[CrawlController] Config overrides applied and components re-initialized")
                request_logger.log_exit("apply_config_overrides", status="applied")
            
            # Crawl the URL using unified architecture
            request_logger.log_entry("orchestrator.crawl_url_unified", url=url_str)
            source_page = await orchestrator.crawl_url_unified(url_str)
            request_logger.log_exit("orchestrator.crawl_url_unified", 
                                   source_page_id=source_page.source_page_id,
                                   status="success")
            
            # Restore original config if overrides were applied
            if request.config_override:
                request_logger.log_entry("restore_config")
                orchestrator.config = original_config
                # Re-initialize components to use restored config
                orchestrator._reinitialize_components()
                request_logger.log_state_change("config_overridden", "config_restored")
                request_logger.log_exit("restore_config", status="restored")
            
            response = CrawlResponse(
                success=True,
                document_id=source_page.source_page_id,  # Use source_page_id as document_id for compatibility
                url=source_page.url,
                message="Crawl completed successfully",
                warnings=warnings
            )
            request_logger.log_state_change("request_pending", "request_completed", 
                                         document_id=source_page.source_page_id)
            return response
            
        except ValidationError as e:
            request_logger.log_decision("VALIDATION_ERROR", reason=str(e))
            request_logger.error(f"[CrawlController] Validation error: {str(e)}", exc_info=True)
            request_logger.log_state_change("request_pending", "request_failed", error_type="ValidationError")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation failed",
                    "message": str(e),
                    "url": url_str
                }
            )
        except CrawlError as e:
            request_logger.log_decision("CRAWL_ERROR", reason=str(e))
            request_logger.error(f"[CrawlController] Crawl error: {str(e)}", exc_info=True)
            request_logger.log_state_change("request_pending", "request_failed", error_type="CrawlError")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error": "Crawl failed",
                    "message": str(e),
                    "url": url_str
                }
            )
        except StorageError as e:
            request_logger.log_decision("STORAGE_ERROR", reason=str(e))
            request_logger.error(f"[CrawlController] Storage error: {str(e)}", exc_info=True)
            request_logger.log_state_change("request_pending", "request_failed", error_type="StorageError")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Storage failed",
                    "message": str(e),
                    "url": url_str
                }
            )
        except Exception as e:
            request_logger.log_decision("UNEXPECTED_ERROR", reason=str(e))
            request_logger.exception(f"[CrawlController] Unexpected error during crawl: {str(e)}")
            request_logger.log_state_change("request_pending", "request_failed", error_type="Exception")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred",
                    "url": url_str
                }
            )


class BatchCrawlResponse(BaseModel):
    """Response model for batch crawl endpoint."""
    success: bool = Field(
        ...,
        description="Whether the crawl was successful",
        examples=[True, False]
    )
    documents_count: int = Field(
        ...,
        description="Number of documents crawled",
        examples=[1, 10, 50]
    )
    document_ids: list[str] = Field(
        default_factory=list,
        description="List of document IDs for crawled documents",
        examples=[["doc1", "doc2", "doc3"]]
    )
    start_url: str = Field(
        ...,
        description="Starting URL",
        examples=["https://example.com"]
    )
    message: str = Field(
        ...,
        description="Response message",
        examples=["Batch crawl completed successfully", "Batch crawl failed"]
    )
    warnings: list[str] = Field(
        default_factory=list,
        description="Any warnings encountered during the crawl process",
        examples=[[], ["Some URLs failed to crawl"]]
    )


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
async def crawl_batch(request: ClientBatchCrawlRequest) -> BatchCrawlResponse:
    """Simplified batch crawl endpoint - intent-based configuration."""
    url_str = str(request.url)
    request_logger = logger.with_url(url_str)
    
    with request_logger.component_flow("crawl_batch", url=url_str):
        warnings = []
        
        try:
            # Get orchestrator
            orchestrator = get_orchestrator()
            
            # Resolve client intent to internal config
            base_config = MainConfig.model_validate(orchestrator.config)
            resolver = CrawlPolicyResolver(base_config)
            
            # Convert ClientBatchCrawlRequest to ClientCrawlRequest for resolver
            client_request = ClientCrawlRequest(
                url=request.url,
                max_pages=request.max_pages,
                max_depth=request.max_depth,
                strategy=request.strategy,
                render_js=request.render_js,
                extract=request.extract,
                selectors=request.selectors,
                allowed_domains=request.allowed_domains,
                exclude_patterns=request.exclude_patterns,
                auth=request.auth,
                enable_chunking=request.enable_chunking
            )
            
            # Log client request strategy
            request_logger.info(f"[CrawlController] Client requested strategy: {request.strategy}")
            
            # Get base config strategy for comparison
            base_strategy = base_config.strategy.type if hasattr(base_config, 'strategy') else 'unknown'
            request_logger.info(f"[CrawlController] Base config strategy: {base_strategy}")
            
            internal_config = await resolver.resolve(client_request)
            
            # Convert MainConfig to dict and handle chunking
            config_dict = internal_config.model_dump()
            
            # Verify strategy was set correctly
            final_strategy = config_dict.get('strategy', {}).get('type', 'unknown')
            request_logger.info(f"[CrawlController] Final resolved strategy: {final_strategy}")
            
            if request.strategy != "auto" and final_strategy != request.strategy:
                request_logger.warning(
                    f"[CrawlController] Strategy mismatch! Client requested: {request.strategy}, "
                    f"but resolved to: {final_strategy}"
                )
            
            # Handle chunking (not in MainConfig schema)
            if request.enable_chunking:
                chunking_config = orchestrator.config.get('chunking', {})
                chunking_config['enabled'] = True
                config_dict['chunking'] = chunking_config
            
            # Use isolated config context
            original_config = copy.deepcopy(orchestrator.config)
            orchestrator.config = config_dict
            orchestrator._reinitialize_components()
            
            try:
                # Perform crawl
                crawl_run = await orchestrator.crawl_with_strategy_unified(url_str)
                
                # Query document IDs from storage
                document_ids = []
                try:
                    # Query source pages by crawl_run_id
                    if hasattr(orchestrator.storage, 'source_pages_collection') and orchestrator.storage.source_pages_collection:
                        source_pages = list(orchestrator.storage.source_pages_collection.find(
                            {'crawl_run_id': crawl_run.crawl_run_id}
                        ))
                        document_ids = [str(sp.get('_id', sp.get('source_page_id', ''))) for sp in source_pages]
                except Exception as e:
                    request_logger.warning(f"Could not fetch document IDs: {e}")
                
                response = BatchCrawlResponse(
                    success=True,
                    documents_count=crawl_run.total_pages_crawled,
                    document_ids=document_ids,
                    start_url=url_str,
                    message=f"Crawl completed successfully. Crawled {crawl_run.total_pages_crawled} documents.",
                    warnings=warnings
                )
                return response
            
            finally:
                # Restore config
                orchestrator.config = original_config
                orchestrator._reinitialize_components()
            
        except ValidationError as e:
            request_logger.error(f"Validation error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "Validation failed",
                    "message": str(e),
                    "url": url_str
                }
            )
        except CrawlError as e:
            request_logger.error(f"Crawl error: {str(e)}", exc_info=True)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail={
                    "error": "Crawl failed",
                    "message": str(e),
                    "url": url_str
                }
            )
        except Exception as e:
            request_logger.exception(f"Unexpected error: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred",
                    "url": url_str
                }
            )

