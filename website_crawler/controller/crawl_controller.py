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
        description="Optional configuration overrides. Can override any section: crawler, engine, storage, extraction, strategy, auth, or logging.",
        examples=[
            None,
            {
                "crawler": {
                    "max_depth": 2,
                    "max_pages": 50,
                    "delay": 2.0
                },
                "engine": {
                    "headless": True,
                    "wait_for": ".content-loaded"
                }
            },
            {
                "crawler": {
                    "max_depth": 1,
                    "timeout": 60
                },
                "extraction": {
                    "extract_images": True,
                    "selectors": {
                        "title": "h1",
                        "content": ".main-content"
                    }
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
                        "max_pages": 50
                    },
                    "engine": {
                        "headless": True
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
    summary="Crawl a URL",
    description="""
    Crawl a URL and store the results in the configured storage backend.
    
    This endpoint accepts a URL and optional configuration overrides to customize
    the crawling behavior. The configuration overrides can modify any section of
    the default configuration including:
    
    - **crawler**: max_depth, max_pages, delay, timeout, retries, etc.
    - **engine**: headless mode, browser type, viewport size, wait conditions
    - **storage**: storage backend settings (only affects if storage is reinitialized)
    - **extraction**: extractors, selectors, content extraction options
    - **strategy**: crawling strategy type and parameters
    - **auth**: headers, cookies, proxies, user agent, basic auth
    - **logging**: logging level and format
    
    The configuration overrides are merged with the default configuration and
    only apply to this specific crawl request.
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
                # Deep copy original config to restore later
                original_config = copy.deepcopy(orchestrator.config)
                # Deep merge config overrides with existing config
                orchestrator.config = deep_merge(orchestrator.config, request.config_override)
                request_logger.info("[CrawlController] Config overrides applied")
                request_logger.log_exit("apply_config_overrides", status="applied")
            
            # Crawl the URL
            request_logger.log_entry("orchestrator.crawl_url", url=url_str)
            document = await orchestrator.crawl_url(url_str)
            request_logger.log_exit("orchestrator.crawl_url", 
                                   document_id=document.document_id,
                                   status="success")
            
            # Restore original config if overrides were applied
            if request.config_override:
                request_logger.log_entry("restore_config")
                orchestrator.config = original_config
                request_logger.log_state_change("config_overridden", "config_restored")
                request_logger.log_exit("restore_config", status="restored")
            
            response = CrawlResponse(
                success=True,
                document_id=document.document_id,
                url=document.url,
                message="Crawl completed successfully",
                warnings=warnings
            )
            request_logger.log_state_change("request_pending", "request_completed", 
                                         document_id=document.document_id)
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

