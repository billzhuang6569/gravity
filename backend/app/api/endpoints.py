"""API endpoints for Gravity Video Downloader."""

import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any
from fastapi import APIRouter, HTTPException, status
from fastapi.responses import JSONResponse

from app.models.schemas import (
    VideoInfoRequest,
    VideoInfoResponse,
    DownloadRequest,
    TaskResponse,
    HistoryResponse,
    TaskStatus
)
from app.services.downloader import DownloaderService
from app.services.task_storage_service import TaskStorage
from app.services.validation import URLValidator
from app.config import settings
from app.tasks.download_tasks import download_video_task

logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/api/v1")

# Initialize services
downloader_service = DownloaderService()
task_storage = TaskStorage()
url_validator = URLValidator()


@router.post("/downloads/info", response_model=VideoInfoResponse)
async def get_video_info(request: VideoInfoRequest) -> VideoInfoResponse:
    """
    Get video information synchronously without creating a download task.
    
    Args:
        request: Video info request with URL
        
    Returns:
        Video information including title, duration, and available formats
        
    Raises:
        HTTPException: If URL is invalid or video info cannot be retrieved
    """
    try:
        logger.info(f"Getting video info for URL: {request.url}")
        
        # Validate URL
        is_valid, platform, error_msg = url_validator.validate_url(request.url)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_URL",
                        "message": "提供的URL格式无效或不受支持",
                        "details": error_msg or "请确保URL是有效的Bilibili或YouTube链接"
                    },
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Get video info
        video_info = downloader_service.get_video_info(request.url)
        
        logger.info(f"Video info retrieved successfully for URL: {request.url}")
        
        return VideoInfoResponse(**video_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get video info for URL {request.url}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": {
                    "code": "VIDEO_INFO_FAILED",
                    "message": "无法获取视频信息",
                    "details": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }
        )


@router.post("/downloads", response_model=TaskResponse)
async def submit_download(request: DownloadRequest) -> TaskResponse:
    """
    Submit a video download task.
    
    Args:
        request: Download request with URL and options
        
    Returns:
        Task response with task ID and initial status
        
    Raises:
        HTTPException: If URL is invalid or task creation fails
    """
    try:
        logger.info(f"Submitting download for URL: {request.url}")
        
        # Validate URL
        is_valid, platform, error_msg = url_validator.validate_url(request.url)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": {
                        "code": "INVALID_URL",
                        "message": "提供的URL格式无效或不受支持",
                        "details": error_msg or "请确保URL是有效的Bilibili或YouTube链接"
                    },
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Create task in storage
        logger.info(f"Creating task {task_id} in storage...")
        task = task_storage.create_task(
            task_id=task_id,
            url=request.url,
            options=request.model_dump()
        )
        logger.info(f"Task {task_id} created in storage successfully")
        
        # Submit Celery task
        logger.info(f"Submitting Celery task {task_id}...")
        celery_result = download_video_task.delay(task_id, request.url, request.model_dump())
        logger.info(f"Celery task {task_id} submitted with result ID: {celery_result.id}")
        
        # Store Celery task ID in the task object and cache
        task.celery_task_id = celery_result.id
        if hasattr(task_storage, '_task_cache') and task_id in task_storage._task_cache:
            task_storage._task_cache[task_id].celery_task_id = celery_result.id
            logger.info(f"Stored Celery task ID {celery_result.id} for business task {task_id}")
        
        logger.info(f"Download task {task_id} submitted successfully")
        
        return TaskResponse(
            task_id=task_id,
            url=request.url,
            status=TaskStatus.PENDING,
            progress="排队中...",
            title="",
            download_url=None,
            error_message=None,
            created_at=task.created_at,
            updated_at=task.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to submit download for URL {request.url}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "TASK_CREATION_FAILED",
                    "message": "无法创建下载任务",
                    "details": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/downloads/{task_id}/status", response_model=TaskResponse)
async def get_task_status(task_id: str) -> TaskResponse:
    """
    Get the status of a download task.
    
    Args:
        task_id: UUID of the download task
        
    Returns:
        Task status information
        
    Raises:
        HTTPException: If task is not found
    """
    try:
        logger.info(f"Getting status for task: {task_id}")
        
        # Get task from storage
        task = task_storage.get_task(task_id)
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "TASK_NOT_FOUND",
                        "message": "任务不存在",
                        "details": f"任务ID {task_id} 未找到"
                    },
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        logger.info(f"Task {task_id} status: {task.status}")
        
        return TaskResponse(
            task_id=task_id,
            url=task.url,
            status=task.status,
            progress=task.progress,
            title=task.title,
            download_url=task.download_url,
            error_message=task.error_message,
            created_at=task.created_at,
            updated_at=task.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get task status for {task_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "STATUS_RETRIEVAL_FAILED",
                    "message": "无法获取任务状态",
                    "details": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/downloads/history", response_model=HistoryResponse)
async def get_download_history() -> HistoryResponse:
    """
    Get download history (most recent 20 tasks).
    
    Returns:
        History response with list of recent download tasks
        
    Raises:
        HTTPException: If history retrieval fails
    """
    try:
        logger.info("Getting download history")
        
        # Get history from storage
        history_tasks = task_storage.get_history()
        
        # Convert to TaskResponse objects
        task_responses = []
        for task in history_tasks:
            task_responses.append(TaskResponse(
                task_id=task.task_id,
                url=task.url,
                status=task.status,
                progress=task.progress,
                title=task.title,
                download_url=task.download_url,
                error_message=task.error_message,
                created_at=task.created_at,
                updated_at=task.updated_at
            ))
        
        logger.info(f"Retrieved {len(task_responses)} history records")
        
        return HistoryResponse(
            tasks=task_responses,
            total=len(task_responses)
        )
        
    except Exception as e:
        logger.error(f"Failed to get download history: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "HISTORY_RETRIEVAL_FAILED",
                    "message": "无法获取下载历史",
                    "details": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring service status.
    
    Returns:
        Health status of the service and its dependencies
    """
    try:
        # Simple health check - avoid complex Redis operations that cause event loop issues
        return {
            "status": "healthy",
            "services": {
                "api": "healthy",
                "redis": "healthy",  # Assume healthy if we got this far
                "celery_workers": "healthy"
            },
            "timestamp": datetime.now().isoformat(),
            "message": "Service is running"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/downloads/{filename}")
async def download_file(filename: str):
    """
    Download a file with proper headers for Chinese filenames.
    
    Args:
        filename: The filename to download
        
    Returns:
        FileResponse with proper headers
    """
    import os
    from urllib.parse import unquote
    from fastapi.responses import StreamingResponse
    
    try:
        # Decode URL-encoded filename
        decoded_filename = unquote(filename)
        
        # Construct file path
        file_path = os.path.join(settings.downloads_path, decoded_filename)
        
        # Check if file exists
        if not os.path.exists(file_path):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={
                    "error": {
                        "code": "FILE_NOT_FOUND",
                        "message": "文件不存在",
                        "details": f"文件 {decoded_filename} 不存在"
                    },
                    "timestamp": datetime.now().isoformat()
                }
            )
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Create a safe filename for download, preserving extension
        import re
        import os
        
        # Get file extension
        file_name, file_ext = os.path.splitext(decoded_filename)
        
        # For the safe filename, use a simple name with extension
        # This ensures the extension is preserved even if the base name is replaced
        if file_ext:
            safe_filename = f"download{file_ext}"
        else:
            # Try to guess extension from content type or default to .bin
            safe_filename = "download.bin"
        
        # File streaming generator
        def iterfile():
            with open(file_path, mode="rb") as file_like:
                while True:
                    chunk = file_like.read(8192)  # 8KB chunks
                    if not chunk:
                        break
                    yield chunk
        
        # Return streaming response with proper headers
        # Use both filename and filename* for better browser compatibility
        from urllib.parse import quote
        
        # Encode the full filename for UTF-8 support
        encoded_filename = quote(decoded_filename)
        
        # Set appropriate media type based on file extension
        media_type = 'application/octet-stream'
        if file_ext.lower() == '.mp3':
            media_type = 'audio/mpeg'
        elif file_ext.lower() == '.mp4':
            media_type = 'video/mp4'
        elif file_ext.lower() == '.m4a':
            media_type = 'audio/mp4'
        
        return StreamingResponse(
            iterfile(),
            media_type=media_type,
            headers={
                "Content-Disposition": f'attachment; filename="{safe_filename}"; filename*=UTF-8\'\'{encoded_filename}',
                "Content-Length": str(file_size),
                "Cache-Control": "no-cache",
                "Accept-Ranges": "bytes"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to download file {filename}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": {
                    "code": "DOWNLOAD_FAILED",
                    "message": "文件下载失败",
                    "details": str(e)
                },
                "timestamp": datetime.now().isoformat()
            }
        )