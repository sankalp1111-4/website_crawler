"""
Crawl controller for handling crawl API requests.
"""
import logging
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl

from crawler.orchestrator import CrawlOrchestrator
from config.loader import load_config
from crawler.exceptions import (
    CrawlError,
    ValidationError,
    StorageError
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/crawl", tags=["crawl"])


class CrawlRequest(BaseModel):
    """Request model for crawl endpoint."""
    url: HttpUrl = Field(..., description="URL to crawl")
    config_override: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional configuration overrides"
    )


class CrawlResponse(BaseModel):
    """Response model for crawl endpoint."""
    success: bool = Field(..., description="Whether the crawl was successful")
    document_id: Optional[str] = Field(None, description="Document ID if successful")
    url: str = Field(..., description="Crawled URL")
    message: str = Field(..., description="Response message")
    warnings: list[str] = Field(default_factory=list, description="Any warnings")


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
        config = load_config()
        config_dict = config.model_dump() if hasattr(config, 'model_dump') else dict(config)
        _orchestrator = CrawlOrchestrator(config_dict)
        _orchestrator.initialize()
        logger.info("Orchestrator initialized")
    
    return _orchestrator


@router.post("", response_model=CrawlResponse, status_code=status.HTTP_200_OK)
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
    warnings = []
    
    try:
        # Get orchestrator
        orchestrator = get_orchestrator()
        
        # Apply config overrides if provided
        if request.config_override:
            # Merge config overrides with existing config
            original_config = orchestrator.config.copy()
            orchestrator.config = {**original_config, **request.config_override}
            logger.info(f"Applied config overrides: {request.config_override}")
        
        # Crawl the URL
        url_str = str(request.url)
        logger.info(f"Starting crawl for URL: {url_str}")
        
        document = await orchestrator.crawl_url(url_str)
        
        # Restore original config if overrides were applied
        if request.config_override:
            orchestrator.config = original_config
        
        return CrawlResponse(
            success=True,
            document_id=document.document_id,
            url=document.url,
            message="Crawl completed successfully",
            warnings=warnings
        )
        
    except ValidationError as e:
        logger.error(f"Validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "Validation failed",
                "message": str(e),
                "url": str(request.url)
            }
        )
    except CrawlError as e:
        logger.error(f"Crawl error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "error": "Crawl failed",
                "message": str(e),
                "url": str(request.url)
            }
        )
    except StorageError as e:
        logger.error(f"Storage error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Storage failed",
                "message": str(e),
                "url": str(request.url)
            }
        )
    except Exception as e:
        logger.exception(f"Unexpected error during crawl: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "Internal server error",
                "message": "An unexpected error occurred",
                "url": str(request.url)
            }
        )

