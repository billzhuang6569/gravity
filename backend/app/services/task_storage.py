"""
Task storage and retrieval operations using Redis.

This module provides functions to store, retrieve, and manage DownloadTask
objects in Redis using hash data structures with proper TTL management.
It also provides download history management using Redis sorted sets.
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from redis.exceptions import RedisError

from app.models.schemas import DownloadTask, TaskStatus, DownloadOptions
from app.services.redis_client import RedisClient

logger = logging.getLogger(__name__)

# TTL for task data (7 days in seconds)
TASK_TTL_SECONDS = 7 * 24 * 60 * 60

# History management constants
HISTORY_KEY = "history:downloads"
HISTORY_SET_KEY = "history:downloads:set"
MAX_HISTORY_SIZE = 20


class TaskStorageError(Exception):
    """Exception raised for task storage operations."""
    pass


async def store_task(redis_client: RedisClient, task: DownloadTask) -> bool:
    """
    Store a DownloadTask object as a Redis hash with TTL.
    
    Args:
        redis_client: Redis client instance
        task: DownloadTask object to store
        
    Returns:
        bool: True if stored successfully, False otherwise
        
    Raises:
        TaskStorageError: If storage operation fails
    """
    try:
        task_key = f"task:{task.task_id}"
        
        # Convert task to hash fields
        task_data = {
            "url": task.url,
            "status": task.status.value,
            "progress": task.progress,
            "title": task.title,
            "file_path": task.file_path,
            "download_url": task.download_url,
            "error_message": task.error_message,
            "options": task.options.model_dump_json(),
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat()
        }
        
        async def _store_operation(client, key: str, data: Dict[str, str]):
            # Store as hash
            await client.hset(key, mapping=data)
            # Set TTL
            await client.expire(key, TASK_TTL_SECONDS)
            return True
        
        result = await redis_client.execute_with_retry(_store_operation, task_key, task_data)
        
        if result:
            logger.info(f"Task {task.task_id} stored successfully")
            return True
        else:
            logger.error(f"Failed to store task {task.task_id}")
            return False
            
    except RedisError as e:
        logger.error(f"Redis error storing task {task.task_id}: {e}")
        raise TaskStorageError(f"Failed to store task: {e}")
    except Exception as e:
        logger.error(f"Unexpected error storing task {task.task_id}: {e}")
        raise TaskStorageError(f"Unexpected error storing task: {e}")


async def retrieve_task(redis_client: RedisClient, task_id: str) -> Optional[DownloadTask]:
    """
    Retrieve a DownloadTask object by task_id from Redis.
    
    Args:
        redis_client: Redis client instance
        task_id: Unique task identifier
        
    Returns:
        DownloadTask object if found, None otherwise
        
    Raises:
        TaskStorageError: If retrieval operation fails
    """
    try:
        task_key = f"task:{task_id}"
        
        async def _retrieve_operation(client, key: str):
            return await client.hgetall(key)
        
        task_data = await redis_client.execute_with_retry(_retrieve_operation, task_key)
        
        if not task_data:
            logger.debug(f"Task {task_id} not found")
            return None
        
        # Convert bytes to strings if necessary
        if task_data and isinstance(next(iter(task_data.keys())), bytes):
            task_data = {k.decode('utf-8'): v.decode('utf-8') for k, v in task_data.items()}
        
        # Convert hash data back to DownloadTask
        try:
            options_data = json.loads(task_data.get("options", "{}"))
            options = DownloadOptions(**options_data)
            
            task = DownloadTask(
                task_id=task_id,
                url=task_data["url"],
                status=TaskStatus(task_data["status"]),
                progress=task_data.get("progress", ""),
                title=task_data.get("title", ""),
                file_path=task_data.get("file_path", ""),
                download_url=task_data.get("download_url", ""),
                error_message=task_data.get("error_message", ""),
                options=options,
                created_at=datetime.fromisoformat(task_data["created_at"]),
                updated_at=datetime.fromisoformat(task_data["updated_at"])
            )
            
            logger.debug(f"Task {task_id} retrieved successfully")
            return task
            
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Error parsing task data for {task_id}: {e}")
            raise TaskStorageError(f"Invalid task data format: {e}")
            
    except RedisError as e:
        logger.error(f"Redis error retrieving task {task_id}: {e}")
        raise TaskStorageError(f"Failed to retrieve task: {e}")
    except TaskStorageError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving task {task_id}: {e}")
        raise TaskStorageError(f"Unexpected error retrieving task: {e}")


async def update_task_status(
    redis_client: RedisClient, 
    task_id: str, 
    status: TaskStatus,
    progress: Optional[str] = None,
    error_message: Optional[str] = None,
    title: Optional[str] = None,
    file_path: Optional[str] = None,
    download_url: Optional[str] = None
) -> bool:
    """
    Update task status and related fields with timestamp tracking.
    
    Args:
        redis_client: Redis client instance
        task_id: Unique task identifier
        status: New task status
        progress: Progress information (optional)
        error_message: Error message for failed tasks (optional)
        title: Video title (optional)
        file_path: Local file path (optional)
        download_url: Public download URL (optional)
        
    Returns:
        bool: True if updated successfully, False otherwise
        
    Raises:
        TaskStorageError: If update operation fails
    """
    try:
        task_key = f"task:{task_id}"
        
        # Check if task exists first
        async def _check_exists(client, key: str):
            return await client.exists(key)
        
        exists = await redis_client.execute_with_retry(_check_exists, task_key)
        if not exists:
            logger.warning(f"Attempted to update non-existent task {task_id}")
            return False
        
        # Prepare update data
        update_data = {
            "status": status.value,
            "updated_at": datetime.now().isoformat()
        }
        
        if progress is not None:
            update_data["progress"] = progress
        if error_message is not None:
            update_data["error_message"] = error_message
        if title is not None:
            update_data["title"] = title
        if file_path is not None:
            update_data["file_path"] = file_path
        if download_url is not None:
            update_data["download_url"] = download_url
        
        async def _update_operation(client, key: str, data: Dict[str, str]):
            await client.hset(key, mapping=data)
            # Refresh TTL
            await client.expire(key, TASK_TTL_SECONDS)
            return True
        
        result = await redis_client.execute_with_retry(_update_operation, task_key, update_data)
        
        if result:
            logger.info(f"Task {task_id} status updated to {status.value}")
            return True
        else:
            logger.error(f"Failed to update task {task_id}")
            return False
            
    except RedisError as e:
        logger.error(f"Redis error updating task {task_id}: {e}")
        raise TaskStorageError(f"Failed to update task: {e}")
    except Exception as e:
        logger.error(f"Unexpected error updating task {task_id}: {e}")
        raise TaskStorageError(f"Unexpected error updating task: {e}")


async def delete_task(redis_client: RedisClient, task_id: str) -> bool:
    """
    Delete a task from Redis storage.
    
    Args:
        redis_client: Redis client instance
        task_id: Unique task identifier
        
    Returns:
        bool: True if deleted successfully, False if task didn't exist
        
    Raises:
        TaskStorageError: If deletion operation fails
    """
    try:
        task_key = f"task:{task_id}"
        
        async def _delete_operation(client, key: str):
            return await client.delete(key)
        
        deleted_count = await redis_client.execute_with_retry(_delete_operation, task_key)
        
        if deleted_count > 0:
            logger.info(f"Task {task_id} deleted successfully")
            return True
        else:
            logger.debug(f"Task {task_id} not found for deletion")
            return False
            
    except RedisError as e:
        logger.error(f"Redis error deleting task {task_id}: {e}")
        raise TaskStorageError(f"Failed to delete task: {e}")
    except Exception as e:
        logger.error(f"Unexpected error deleting task {task_id}: {e}")
        raise TaskStorageError(f"Unexpected error deleting task: {e}")


async def task_exists(redis_client: RedisClient, task_id: str) -> bool:
    """
    Check if a task exists in Redis storage.
    
    Args:
        redis_client: Redis client instance
        task_id: Unique task identifier
        
    Returns:
        bool: True if task exists, False otherwise
        
    Raises:
        TaskStorageError: If check operation fails
    """
    try:
        task_key = f"task:{task_id}"
        
        async def _exists_operation(client, key: str):
            return await client.exists(key)
        
        exists = await redis_client.execute_with_retry(_exists_operation, task_key)
        return bool(exists)
        
    except RedisError as e:
        logger.error(f"Redis error checking task existence {task_id}: {e}")
        raise TaskStorageError(f"Failed to check task existence: {e}")
    except Exception as e:
        logger.error(f"Unexpected error checking task existence {task_id}: {e}")
        raise TaskStorageError(f"Unexpected error checking task existence: {e}")


async def get_task_ttl(redis_client: RedisClient, task_id: str) -> Optional[int]:
    """
    Get the remaining TTL for a task in seconds.
    
    Args:
        redis_client: Redis client instance
        task_id: Unique task identifier
        
    Returns:
        int: Remaining TTL in seconds, None if task doesn't exist or has no TTL
        
    Raises:
        TaskStorageError: If TTL check operation fails
    """
    try:
        task_key = f"task:{task_id}"
        
        async def _ttl_operation(client, key: str):
            return await client.ttl(key)
        
        ttl = await redis_client.execute_with_retry(_ttl_operation, task_key)
        
        # Redis returns -2 if key doesn't exist, -1 if key exists but has no TTL
        if ttl == -2:
            return None  # Task doesn't exist
        elif ttl == -1:
            return None  # Task exists but has no TTL (shouldn't happen in our case)
        else:
            return ttl
            
    except RedisError as e:
        logger.error(f"Redis error getting task TTL {task_id}: {e}")
        raise TaskStorageError(f"Failed to get task TTL: {e}")
    except Exception as e:
        logger.error(f"Unexpected error getting task TTL {task_id}: {e}")
        raise TaskStorageError(f"Unexpected error getting task TTL: {e}")


# Download History Management Functions

async def add_task_to_history(redis_client: RedisClient, task_id: str) -> bool:
    """
    Add a completed task to the download history using Redis sorted set.
    Automatically trims the history to keep only the most recent MAX_HISTORY_SIZE records.
    
    Args:
        redis_client: Redis client instance
        task_id: Unique task identifier to add to history
        
    Returns:
        bool: True if added successfully, False otherwise
        
    Raises:
        TaskStorageError: If history operation fails
    """
    try:
        current_timestamp = datetime.now().timestamp()
        
        async def _add_to_history_operation(client, history_key: str, task_id: str, timestamp: float):
            # Add task to sorted set with timestamp as score
            await client.zadd(history_key, {task_id: timestamp})
            
            # Trim to keep only the most recent MAX_HISTORY_SIZE records
            # Keep elements with highest scores (most recent timestamps)
            total_count = await client.zcard(history_key)
            if total_count > MAX_HISTORY_SIZE:
                # Remove oldest records (lowest scores)
                remove_count = total_count - MAX_HISTORY_SIZE
                await client.zremrangebyrank(history_key, 0, remove_count - 1)
            
            return True
        
        result = await redis_client.execute_with_retry(
            _add_to_history_operation, 
            HISTORY_KEY, 
            task_id, 
            current_timestamp
        )
        
        if result:
            logger.info(f"Task {task_id} added to download history")
            return True
        else:
            logger.error(f"Failed to add task {task_id} to history")
            return False
            
    except RedisError as e:
        logger.error(f"Redis error adding task {task_id} to history: {e}")
        raise TaskStorageError(f"Failed to add task to history: {e}")
    except Exception as e:
        logger.error(f"Unexpected error adding task {task_id} to history: {e}")
        raise TaskStorageError(f"Unexpected error adding task to history: {e}")


async def get_download_history(redis_client: RedisClient, limit: Optional[int] = None) -> List[str]:
    """
    Retrieve download history task IDs sorted by most recent first.
    
    Args:
        redis_client: Redis client instance
        limit: Maximum number of records to return (defaults to MAX_HISTORY_SIZE)
        
    Returns:
        List[str]: List of task IDs sorted by most recent first
        
    Raises:
        TaskStorageError: If history retrieval fails
    """
    try:
        if limit is None:
            limit = MAX_HISTORY_SIZE
        
        async def _get_history_operation(client, history_key: str, limit: int):
            # Get task IDs sorted by score (timestamp) in descending order (most recent first)
            # ZREVRANGE returns elements in reverse order (highest to lowest score)
            return await client.zrevrange(history_key, 0, limit - 1)
        
        task_ids = await redis_client.execute_with_retry(_get_history_operation, HISTORY_KEY, limit)
        
        # Convert bytes to strings if necessary
        if task_ids and isinstance(task_ids[0], bytes):
            task_ids = [task_id.decode('utf-8') for task_id in task_ids]
        
        logger.debug(f"Retrieved {len(task_ids)} tasks from download history")
        return task_ids
        
    except RedisError as e:
        logger.error(f"Redis error retrieving download history: {e}")
        raise TaskStorageError(f"Failed to retrieve download history: {e}")
    except Exception as e:
        logger.error(f"Unexpected error retrieving download history: {e}")
        raise TaskStorageError(f"Unexpected error retrieving download history: {e}")


async def get_download_history_with_tasks(redis_client: RedisClient, limit: Optional[int] = None) -> List[DownloadTask]:
    """
    Retrieve download history with full task details sorted by most recent first.
    
    Args:
        redis_client: Redis client instance
        limit: Maximum number of records to return (defaults to MAX_HISTORY_SIZE)
        
    Returns:
        List[DownloadTask]: List of DownloadTask objects sorted by most recent first
        
    Raises:
        TaskStorageError: If history retrieval fails
    """
    try:
        # Get task IDs from history
        task_ids = await get_download_history(redis_client, limit)
        
        if not task_ids:
            return []
        
        # Retrieve full task details for each task ID
        tasks = []
        for task_id in task_ids:
            try:
                task = await retrieve_task(redis_client, task_id)
                if task:
                    tasks.append(task)
                else:
                    # Task no longer exists, remove from history
                    logger.warning(f"Task {task_id} in history but not found in storage, removing from history")
                    await remove_task_from_history(redis_client, task_id)
            except TaskStorageError as e:
                logger.warning(f"Error retrieving task {task_id} from history: {e}")
                continue
        
        logger.info(f"Retrieved {len(tasks)} complete tasks from download history")
        return tasks
        
    except TaskStorageError:
        raise
    except Exception as e:
        logger.error(f"Unexpected error retrieving download history with tasks: {e}")
        raise TaskStorageError(f"Unexpected error retrieving download history with tasks: {e}")


async def remove_task_from_history(redis_client: RedisClient, task_id: str) -> bool:
    """
    Remove a specific task from the download history.
    
    Args:
        redis_client: Redis client instance
        task_id: Unique task identifier to remove from history
        
    Returns:
        bool: True if removed successfully, False if task wasn't in history
        
    Raises:
        TaskStorageError: If history operation fails
    """
    try:
        async def _remove_from_history_operation(client, history_key: str, task_id: str):
            return await client.zrem(history_key, task_id)
        
        removed_count = await redis_client.execute_with_retry(
            _remove_from_history_operation, 
            HISTORY_KEY, 
            task_id
        )
        
        if removed_count > 0:
            logger.info(f"Task {task_id} removed from download history")
            return True
        else:
            logger.debug(f"Task {task_id} not found in download history")
            return False
            
    except RedisError as e:
        logger.error(f"Redis error removing task {task_id} from history: {e}")
        raise TaskStorageError(f"Failed to remove task from history: {e}")
    except Exception as e:
        logger.error(f"Unexpected error removing task {task_id} from history: {e}")
        raise TaskStorageError(f"Unexpected error removing task from history: {e}")


async def clear_download_history(redis_client: RedisClient) -> bool:
    """
    Clear all download history records.
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        bool: True if cleared successfully, False otherwise
        
    Raises:
        TaskStorageError: If clear operation fails
    """
    try:
        async def _clear_history_operation(client, history_key: str):
            return await client.delete(history_key)
        
        deleted_count = await redis_client.execute_with_retry(_clear_history_operation, HISTORY_KEY)
        
        if deleted_count > 0:
            logger.info("Download history cleared successfully")
            return True
        else:
            logger.debug("Download history was already empty")
            return True  # Consider empty history as successfully cleared
            
    except RedisError as e:
        logger.error(f"Redis error clearing download history: {e}")
        raise TaskStorageError(f"Failed to clear download history: {e}")
    except Exception as e:
        logger.error(f"Unexpected error clearing download history: {e}")
        raise TaskStorageError(f"Unexpected error clearing download history: {e}")


async def get_task(redis_client: RedisClient, task_id: str) -> Optional[DownloadTask]:
    """
    Get a task by task_id (alias for retrieve_task).
    
    Args:
        redis_client: Redis client instance
        task_id: Unique task identifier
        
    Returns:
        DownloadTask object if found, None otherwise
        
    Raises:
        TaskStorageError: If retrieval operation fails
    """
    return await retrieve_task(redis_client, task_id)


async def get_history(redis_client: RedisClient, limit: int = 20) -> List[DownloadTask]:
    """
    Get download history (most recent tasks).
    
    Args:
        redis_client: Redis client instance
        limit: Maximum number of tasks to return (default: 20)
        
    Returns:
        List of DownloadTask objects sorted by creation time (newest first)
    """
    try:
        async with redis_client.get_client() as client:
            # Get recent task IDs from sorted set (newest first)
            task_ids = await client.zrevrange(
                HISTORY_KEY, 
                0, 
                limit - 1,  # Redis uses 0-based indexing
                withscores=False
            )
            
            if not task_ids:
                logger.info("No tasks found in history")
                return []
            
            # Get task data for each ID
            history_tasks = []
            for task_id in task_ids:
                task_id_str = task_id.decode('utf-8') if isinstance(task_id, bytes) else task_id
                task = await get_task(redis_client, task_id_str)
                if task:
                    history_tasks.append(task)
            
            logger.info(f"Retrieved {len(history_tasks)} tasks from history")
            return history_tasks
            
    except RedisError as e:
        logger.error(f"Redis error while getting history: {e}")
        return []
    except Exception as e:
        logger.error(f"Error getting history: {e}")
        return []


async def add_to_history(redis_client: RedisClient, task_id: str) -> bool:
    """
    Add a task to download history (alias for add_task_to_history).
    
    Args:
        redis_client: Redis client instance
        task_id: Unique task identifier
        
    Returns:
        bool: True if added successfully, False otherwise
        
    Raises:
        TaskStorageError: If history operation fails
    """
    return await add_task_to_history(redis_client, task_id)


async def get_history_size(redis_client: RedisClient) -> int:
    """
    Get the current size of the download history.
    
    Args:
        redis_client: Redis client instance
        
    Returns:
        int: Number of records in download history
        
    Raises:
        TaskStorageError: If size check operation fails
    """
    try:
        async def _get_history_size_operation(client, history_key: str):
            return await client.zcard(history_key)
        
        size = await redis_client.execute_with_retry(_get_history_size_operation, HISTORY_KEY)
        
        logger.debug(f"Download history contains {size} records")
        return size
        
    except RedisError as e:
        logger.error(f"Redis error getting download history size: {e}")
        raise TaskStorageError(f"Failed to get download history size: {e}")
    except Exception as e:
        logger.error(f"Unexpected error getting download history size: {e}")
        raise TaskStorageError(f"Unexpected error getting download history size: {e}")