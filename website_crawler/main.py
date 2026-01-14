"""
Main application entry point for the website crawler service.
"""
import os
import sys
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
import uvicorn

from controller import router as crawl_router
from config.loader import load_config
from utils.logging_config import configure_logger_from_config

# Load configuration and initialize logging
_config = load_config()
config_dict = _config.model_dump() if hasattr(_config, 'model_dump') else dict(_config)
configure_logger_from_config(config_dict)

# Initialize FastAPI app
app = FastAPI(
    title="Website Crawler Service",
    description="A comprehensive web crawling service for structured data extraction",
    version="1.0.0"
)

# Include routers
app.include_router(crawl_router)


@app.get("/")
async def root() -> Dict[str, str]:
    """Root endpoint."""
    return {
        "service": "Website Crawler Service",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/health")
async def health() -> Dict[str, Any]:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "website-crawler",
        "version": "1.0.0"
    }


def main():
    """Main entry point for the application."""
    # Get port from environment variable or default to 8000
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    # Run the server
    uvicorn.run(
        "main:app",
        host=host,
        port=port,
        log_level=os.getenv("LOG_LEVEL", "info").lower(),
        reload=False
    )


if __name__ == "__main__":
    main()

