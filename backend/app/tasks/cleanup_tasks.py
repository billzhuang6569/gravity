"""Cleanup and maintenance tasks for Celery workers."""

import os
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pathlib import Path

from app.celery_app import celery_app
from app.config import settings
from app.services.task_storage_service import TaskStorage

logger = logging.getLogger(__name__)


@celery_app.task(bind=True)
def cleanup_old_files(self) -> Dict[str, Any]:
    """
    Clean up old downloaded files based on retention policy.
    
    Returns:
        Dict containing cleanup results
    """
    try:
        logger.info("Starting cleanup of old files")
        
        downloads_path = Path(settings.downloads_path)
        temp_path = Path(settings.temp_path)
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=settings.file_retention_days)
        cutoff_timestamp = cutoff_date.timestamp()
        
        cleaned_files = []
        total_size_freed = 0
        
        # Clean downloads directory
        if downloads_path.exists():
            for file_path in downloads_path.rglob("*"):
                if file_path.is_file():
                    try:
                        # Check file modification time
                        if file_path.stat().st_mtime < cutoff_timestamp:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            cleaned_files.append(str(file_path))
                            total_size_freed += file_size
                            logger.info(f"Deleted old file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete file {file_path}: {e}")
        
        # Clean temp directory
        if temp_path.exists():
            for file_path in temp_path.rglob("*"):
                if file_path.is_file():
                    try:
                        # Clean all temp files older than 1 hour
                        temp_cutoff = datetime.now() - timedelta(hours=1)
                        if file_path.stat().st_mtime < temp_cutoff.timestamp():
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            cleaned_files.append(str(file_path))
                            total_size_freed += file_size
                            logger.info(f"Deleted temp file: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to delete temp file {file_path}: {e}")
        
        result = {
            'status': 'completed',
            'files_cleaned': len(cleaned_files),
            'size_freed_mb': round(total_size_freed / (1024 * 1024), 2),
            'cutoff_date': cutoff_date.isoformat(),
            'cleaned_files': cleaned_files[:10]  # Limit to first 10 for logging
        }
        
        logger.info(f"File cleanup completed: {result['files_cleaned']} files, "
                   f"{result['size_freed_mb']} MB freed")
        
        return result
        
    except Exception as e:
        logger.error(f"File cleanup task failed: {str(e)}")
        
        return {
            'status': 'failed',
            'error': str(e),
            'files_cleaned': 0,
            'size_freed_mb': 0
        }


@celery_app.task(bind=True)
def cleanup_old_tasks(self) -> Dict[str, Any]:
    """
    Clean up old task records from Redis.
    
    Returns:
        Dict containing cleanup results
    """
    try:
        logger.info("Starting cleanup of old task records")
        
        task_storage = TaskStorage()
        
        # Get all task IDs
        all_tasks = task_storage.get_all_task_ids()
        
        # Calculate cutoff date (older than retention period)
        cutoff_date = datetime.now() - timedelta(days=settings.file_retention_days)
        
        cleaned_tasks = []
        
        for task_id in all_tasks:
            try:
                task = task_storage.get_task(task_id)
                if task and task.created_at < cutoff_date:
                    task_storage.delete_task(task_id)
                    cleaned_tasks.append(task_id)
                    logger.info(f"Deleted old task record: {task_id}")
            except Exception as e:
                logger.error(f"Failed to process task {task_id}: {e}")
        
        # Clean up history records (keep only recent 20)
        try:
            task_storage.trim_history()
        except Exception as e:
            logger.error(f"Failed to trim history: {e}")
        
        result = {
            'status': 'completed',
            'tasks_cleaned': len(cleaned_tasks),
            'cutoff_date': cutoff_date.isoformat(),
            'cleaned_task_ids': cleaned_tasks[:10]  # Limit for logging
        }
        
        logger.info(f"Task cleanup completed: {result['tasks_cleaned']} tasks cleaned")
        
        return result
        
    except Exception as e:
        logger.error(f"Task cleanup failed: {str(e)}")
        
        return {
            'status': 'failed',
            'error': str(e),
            'tasks_cleaned': 0
        }


@celery_app.task(bind=True)
def system_health_check(self) -> Dict[str, Any]:
    """
    Perform system health check and resource monitoring.
    
    Returns:
        Dict containing system health information
    """
    try:
        import psutil
        
        logger.info("Performing system health check")
        
        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk_usage = psutil.disk_usage(settings.downloads_path if os.path.exists(settings.downloads_path) else '/')
        
        # Check Redis connectivity
        task_storage = TaskStorage()
        redis_healthy = task_storage.health_check()
        
        # Calculate disk space for downloads directory
        downloads_path = Path(settings.downloads_path)
        downloads_size = 0
        downloads_files = 0
        
        if downloads_path.exists():
            for file_path in downloads_path.rglob("*"):
                if file_path.is_file():
                    downloads_size += file_path.stat().st_size
                    downloads_files += 1
        
        # Determine overall health status
        health_issues = []
        
        if cpu_percent > 90:
            health_issues.append("High CPU usage")
        
        if memory.percent > 90:
            health_issues.append("High memory usage")
        
        if disk_usage.percent > 90:
            health_issues.append("Low disk space")
        
        if not redis_healthy:
            health_issues.append("Redis connectivity issues")
        
        overall_status = "healthy" if not health_issues else "warning" if len(health_issues) < 3 else "critical"
        
        result = {
            'status': overall_status,
            'timestamp': datetime.now().isoformat(),
            'issues': health_issues,
            'metrics': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': round(memory.available / (1024**3), 2),
                'disk_percent': disk_usage.percent,
                'disk_free_gb': round(disk_usage.free / (1024**3), 2),
                'downloads_size_mb': round(downloads_size / (1024**2), 2),
                'downloads_files': downloads_files
            },
            'services': {
                'redis': 'healthy' if redis_healthy else 'unhealthy'
            }
        }
        
        if health_issues:
            logger.warning(f"System health check found issues: {health_issues}")
        else:
            logger.info("System health check passed")
        
        return result
        
    except Exception as e:
        logger.error(f"System health check failed: {str(e)}")
        
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }


@celery_app.task(bind=True)
def optimize_redis_memory(self) -> Dict[str, Any]:
    """
    Optimize Redis memory usage by cleaning up expired keys and compacting data.
    
    Returns:
        Dict containing optimization results
    """
    try:
        logger.info("Starting Redis memory optimization")
        
        task_storage = TaskStorage()
        
        # Get Redis info before optimization
        redis_info_before = task_storage.get_redis_info()
        memory_before = redis_info_before.get('used_memory', 0)
        
        # Clean up expired keys
        expired_keys = task_storage.cleanup_expired_keys()
        
        # Compact Redis memory
        task_storage.compact_memory()
        
        # Get Redis info after optimization
        redis_info_after = task_storage.get_redis_info()
        memory_after = redis_info_after.get('used_memory', 0)
        
        memory_freed = memory_before - memory_after
        
        result = {
            'status': 'completed',
            'memory_before_mb': round(memory_before / (1024**2), 2),
            'memory_after_mb': round(memory_after / (1024**2), 2),
            'memory_freed_mb': round(memory_freed / (1024**2), 2),
            'expired_keys_cleaned': expired_keys,
            'timestamp': datetime.now().isoformat()
        }
        
        logger.info(f"Redis optimization completed: {result['memory_freed_mb']} MB freed, "
                   f"{expired_keys} expired keys cleaned")
        
        return result
        
    except Exception as e:
        logger.error(f"Redis optimization failed: {str(e)}")
        
        return {
            'status': 'failed',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }