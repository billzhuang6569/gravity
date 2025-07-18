"""Download tasks for Celery workers."""

import logging
from typing import Dict, Any
from celery import current_task
from celery.exceptions import Retry

from app.celery_app import celery_app
from app.services.task_storage_service import TaskStorage
from app.services.downloader import DownloaderService
from app.models.schemas import TaskStatus, DownloadOptions

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_kwargs={'max_retries': 3, 'countdown': 60})
def download_video_task(self, task_id: str, url: str, options: Dict[str, Any]) -> Dict[str, Any]:
    """
    Download video task with progress tracking and error handling.
    
    Args:
        task_id: Unique task identifier
        url: Video URL to download
        options: Download options (quality, format, etc.)
        
    Returns:
        Dict containing task result information
        
    Raises:
        Retry: When task should be retried
        Exception: When task fails permanently
    """
    task_storage = TaskStorage()
    downloader = DownloaderService()
    
    try:
        logger.info(f"Starting download task {task_id} for URL: {url}")
        
        # Update task status to DOWNLOADING
        task_storage.update_task_status(
            task_id, 
            TaskStatus.DOWNLOADING,
            progress="开始下载..."
        )
        
        # Define progress callback
        def progress_callback(d):
            """Progress callback for yt-dlp."""
            try:
                if d['status'] == 'downloading':
                    # Extract progress information
                    percent = d.get('_percent_str', 'N/A')
                    speed = d.get('_speed_str', 'N/A')
                    eta = d.get('_eta_str', 'N/A')
                    
                    progress_msg = f"下载中 {percent} - 速度: {speed} - 剩余时间: {eta}"
                    
                    # Update task progress in Redis
                    task_storage.update_task_progress(task_id, progress_msg)
                    
                elif d['status'] == 'finished':
                    logger.info(f"Download finished for task {task_id}: {d['filename']}")
                    
            except Exception as e:
                logger.error(f"Error in progress callback for task {task_id}: {e}")
        
        # Convert options dict to DownloadOptions object
        download_options = DownloadOptions(**options)
        
        # Perform the download
        result = downloader.download_video(url, download_options, progress_callback, task_id)
        
        # Update task status to COMPLETED
        task_storage.update_task_status(
            task_id,
            TaskStatus.COMPLETED,
            progress="下载完成",
            file_path=result['file_path'],
            download_url=result['download_url'],
            title=result.get('title', '')
        )
        
        # Add to download history
        task_storage.add_to_history(task_id)
        
        logger.info(f"Download task {task_id} completed successfully")
        
        return {
            'task_id': task_id,
            'status': 'completed',
            'file_path': result['file_path'],
            'download_url': result['download_url'],
            'title': result.get('title', '')
        }
        
    except Exception as e:
        logger.error(f"Download task {task_id} failed: {str(e)}")
        
        # Update task status to FAILED
        try:
            task_storage.update_task_status(
                task_id,
                TaskStatus.FAILED,
                error_message=str(e)
            )
        except Exception as storage_error:
            logger.error(f"Failed to update task status for {task_id}: {storage_error}")
        
        # Check if we should retry
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying download task {task_id} (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60 * (2 ** self.request.retries))  # Exponential backoff
        
        # Max retries reached, task failed permanently
        raise e


@celery_app.task(bind=True)
def get_video_info_task(self, url: str) -> Dict[str, Any]:
    """
    Get video information task (for async info retrieval if needed).
    
    Args:
        url: Video URL to get info for
        
    Returns:
        Dict containing video information
    """
    downloader = DownloaderService()
    
    try:
        logger.info(f"Getting video info for URL: {url}")
        
        info = downloader.get_video_info(url)
        
        logger.info(f"Video info retrieved successfully for URL: {url}")
        
        return {
            'status': 'success',
            'info': info
        }
        
    except Exception as e:
        logger.error(f"Failed to get video info for URL {url}: {str(e)}")
        
        return {
            'status': 'error',
            'error': str(e)
        }


@celery_app.task(bind=True)
def health_check_task(self) -> Dict[str, Any]:
    """
    Health check task for monitoring worker status.
    
    Returns:
        Dict containing health status information
    """
    import psutil
    import time
    
    try:
        # Get system information
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        return {
            'status': 'healthy',
            'timestamp': time.time(),
            'worker_id': self.request.id,
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': disk.percent,
                'available_memory_mb': memory.available // (1024 * 1024),
                'available_disk_gb': disk.free // (1024 * 1024 * 1024)
            }
        }
        
    except Exception as e:
        logger.error(f"Health check task failed: {str(e)}")
        
        return {
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': time.time()
        }