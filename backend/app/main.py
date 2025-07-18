"""FastAPI application entry point for Gravity Video Downloader."""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.services.redis_client import init_redis, close_redis
from app.api.endpoints import router

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Gravity Video Downloader...")
    try:
        await init_redis()
        logger.info("Application startup completed")
    except Exception as e:
        logger.error(f"Failed to start application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Shutting down Gravity Video Downloader...")
    try:
        await close_redis()
        logger.info("Application shutdown completed")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Multi-platform video downloader with real-time status tracking",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API router
app.include_router(router)

# Mount static files for backward compatibility with old download URLs
from fastapi.staticfiles import StaticFiles
app.mount("/downloads", StaticFiles(directory=settings.downloads_path), name="downloads")

# File downloads are also handled through the API endpoint /api/v1/downloads/{filename}
# This provides better control over headers and security


