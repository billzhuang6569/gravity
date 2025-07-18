"""
Task storage service class that provides a clean interface for task operations.

This module provides a TaskStorage class that wraps the async task storage functions
to provide a clean interface for API endpoints and other services.
"""

import asyncio
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

from app.models.schemas import DownloadTask, TaskStatus, DownloadOptions
from app.services.redis_client import get_redis_client_sync
from app.services import task_storage

logger = logging.getLogger(__name__)


class TaskStorage:
    """
    Task storage service that provides a clean interface for task operations.
    
    This class wraps the async task storage functions to provide synchronous
    methods that can be used in API endpoints and other services.
    """
    
    def __init__(self):
        """Initialize the TaskStorage service."""
        self.redis_client = get_redis_client_sync()
    
    def create_task(
        self, 
        task_id: str, 
        url: str, 
        options: Dict[str, Any]
    ) -> DownloadTask:
        """
        Create a new download task.
        
        Args:
            task_id: Unique task identifier
            url: Video URL to download
            options: Download options
            
        Returns:
            DownloadTask: Created task object
        """
        try:
            # Create download options
            download_options = DownloadOptions(**options)
            
            # Create task object
            task = DownloadTask(
                task_id=task_id,
                url=url,
                status=TaskStatus.PENDING,
                progress="排队中...",
                title="",
                file_path="",
                download_url="",
                error_message="",
                options=download_options,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Store task in Redis - use threading to avoid event loop conflicts
            try:
                import threading
                import time
                
                def store_task_sync():
                    try:
                        # Create a new event loop for this operation
                        async def store_task_async():
                            from app.services.redis_client import RedisClient
                            redis_client = RedisClient()
                            await redis_client.connect()
                            try:
                                result = await task_storage.store_task(redis_client, task)
                                return result
                            finally:
                                await redis_client.disconnect()
                        
                        # Create new event loop in thread
                        new_loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(new_loop)
                        try:
                            result = new_loop.run_until_complete(store_task_async())
                            return result
                        finally:
                            new_loop.close()
                    except Exception as e:
                        logger.error(f"Error in store_task_sync: {e}")
                        return False
                
                # Run in a separate thread
                result = [False]
                thread = threading.Thread(target=lambda: result.__setitem__(0, store_task_sync()))
                thread.start()
                thread.join(timeout=10)  # 10 second timeout
                
                if not result[0]:
                    raise Exception("Failed to store task in Redis")
                    
            except Exception as e:
                logger.error(f"Failed to store task in Redis: {e}")
                raise Exception(f"Failed to store task in Redis: {e}")
            
            logger.info(f"Task {task_id} created successfully")
            return task
            
        except Exception as e:
            logger.error(f"Failed to create task {task_id}: {str(e)}")
            raise
    
    def get_task(self, task_id: str) -> Optional[DownloadTask]:
        """
        Get a task by its ID.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            DownloadTask or None: Task object if found, None otherwise
        """
        try:
            import threading
            
            def get_task_sync():
                try:
                    # Create a new event loop for this operation
                    async def get_task_async():
                        from app.services.redis_client import RedisClient
                        redis_client = RedisClient()
                        await redis_client.connect()
                        try:
                            result = await task_storage.get_task(redis_client, task_id)
                            return result
                        finally:
                            await redis_client.disconnect()
                    
                    # Create new event loop in thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result = new_loop.run_until_complete(get_task_async())
                        return result
                    finally:
                        new_loop.close()
                except Exception as e:
                    logger.error(f"Error in get_task_sync: {e}")
                    return None
            
            # Run in a separate thread
            result = [None]
            thread = threading.Thread(target=lambda: result.__setitem__(0, get_task_sync()))
            thread.start()
            thread.join(timeout=5)  # 5 second timeout
            
            return result[0]
        except Exception as e:
            logger.error(f"Failed to get task {task_id}: {str(e)}")
            return None
    
    def update_task_status(
        self,
        task_id: str,
        status: TaskStatus,
        progress: Optional[str] = None,
        error_message: Optional[str] = None,
        title: Optional[str] = None,
        file_path: Optional[str] = None,
        download_url: Optional[str] = None
    ) -> bool:
        """
        Update task status and related fields.
        
        Args:
            task_id: Unique task identifier
            status: New task status
            progress: Progress information (optional)
            error_message: Error message for failed tasks (optional)
            title: Video title (optional)
            file_path: Local file path (optional)
            download_url: Public download URL (optional)
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new event loop for this operation
                import threading
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            task_storage.update_task_status(
                                self.redis_client,
                                task_id,
                                status,
                                progress,
                                error_message,
                                title,
                                file_path,
                                download_url
                            )
                        )
                    finally:
                        new_loop.close()
                
                result = [False]
                thread = threading.Thread(target=lambda: result.__setitem__(0, run_async()))
                thread.start()
                thread.join()
                return result[0]
            else:
                return loop.run_until_complete(
                    task_storage.update_task_status(
                        self.redis_client,
                        task_id,
                        status,
                        progress,
                        error_message,
                        title,
                        file_path,
                        download_url
                    )
                )
                
        except Exception as e:
            logger.error(f"Failed to update task {task_id}: {str(e)}")
            return False
    
    def update_task_progress(self, task_id: str, progress: str) -> bool:
        """
        Update task progress information.
        
        Args:
            task_id: Unique task identifier
            progress: Progress information
            
        Returns:
            bool: True if updated successfully, False otherwise
        """
        return self.update_task_status(task_id, TaskStatus.DOWNLOADING, progress=progress)
    
    def add_to_history(self, task_id: str) -> bool:
        """
        Add a completed task to download history.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            bool: True if added successfully, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new event loop for this operation
                import threading
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            task_storage.add_to_history(self.redis_client, task_id)
                        )
                    finally:
                        new_loop.close()
                
                result = [False]
                thread = threading.Thread(target=lambda: result.__setitem__(0, run_async()))
                thread.start()
                thread.join()
                return result[0]
            else:
                return loop.run_until_complete(
                    task_storage.add_to_history(self.redis_client, task_id)
                )
                
        except Exception as e:
            logger.error(f"Failed to add task {task_id} to history: {str(e)}")
            return False
    
    def get_history(self) -> List[DownloadTask]:
        """
        Get download history (most recent 20 tasks).
        
        Returns:
            List[DownloadTask]: List of recent download tasks
        """
        try:
            import threading
            
            def get_history_sync():
                try:
                    # Create a new event loop for this operation
                    async def get_history_async():
                        from app.services.redis_client import RedisClient
                        redis_client = RedisClient()
                        await redis_client.connect()
                        try:
                            result = await task_storage.get_history(redis_client)
                            return result
                        finally:
                            await redis_client.disconnect()
                    
                    # Create new event loop in thread
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        result = new_loop.run_until_complete(get_history_async())
                        return result
                    finally:
                        new_loop.close()
                except Exception as e:
                    logger.error(f"Error in get_history_sync: {e}")
                    return []
            
            # Run in a separate thread
            result = [[]]
            thread = threading.Thread(target=lambda: result.__setitem__(0, get_history_sync()))
            thread.start()
            thread.join(timeout=5)  # 5 second timeout
            
            return result[0] or []
        except Exception as e:
            logger.error(f"Failed to get history: {str(e)}")
            return []
    
    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.
        
        Returns:
            bool: True if healthy, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new event loop for this operation
                import threading
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            self.redis_client.health_check()
                        )
                    finally:
                        new_loop.close()
                
                result = [False]
                thread = threading.Thread(target=lambda: result.__setitem__(0, run_async()))
                thread.start()
                thread.join()
                return result[0]
            else:
                return loop.run_until_complete(self.redis_client.health_check())
                
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return False
    
    def delete_task(self, task_id: str) -> bool:
        """
        Delete a task from storage.
        
        Args:
            task_id: Unique task identifier
            
        Returns:
            bool: True if deleted successfully, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new event loop for this operation
                import threading
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            task_storage.delete_task(self.redis_client, task_id)
                        )
                    finally:
                        new_loop.close()
                
                result = [False]
                thread = threading.Thread(target=lambda: result.__setitem__(0, run_async()))
                thread.start()
                thread.join()
                return result[0]
            else:
                return loop.run_until_complete(
                    task_storage.delete_task(self.redis_client, task_id)
                )
                
        except Exception as e:
            logger.error(f"Failed to delete task {task_id}: {str(e)}")
            return False
    
    def get_all_task_ids(self) -> List[str]:
        """
        Get all task IDs from storage.
        
        Returns:
            List[str]: List of task IDs
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new event loop for this operation
                import threading
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            task_storage.get_all_task_ids(self.redis_client)
                        )
                    finally:
                        new_loop.close()
                
                result = [None]
                thread = threading.Thread(target=lambda: result.__setitem__(0, run_async()))
                thread.start()
                thread.join()
                return result[0] or []
            else:
                return loop.run_until_complete(
                    task_storage.get_all_task_ids(self.redis_client)
                ) or []
                
        except Exception as e:
            logger.error(f"Failed to get all task IDs: {str(e)}")
            return []
    
    def trim_history(self) -> bool:
        """
        Trim history to keep only recent entries.
        
        Returns:
            bool: True if trimmed successfully, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new event loop for this operation
                import threading
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            task_storage.trim_history(self.redis_client)
                        )
                    finally:
                        new_loop.close()
                
                result = [False]
                thread = threading.Thread(target=lambda: result.__setitem__(0, run_async()))
                thread.start()
                thread.join()
                return result[0]
            else:
                return loop.run_until_complete(
                    task_storage.trim_history(self.redis_client)
                )
                
        except Exception as e:
            logger.error(f"Failed to trim history: {str(e)}")
            return False
    
    def cleanup_expired_keys(self) -> int:
        """
        Clean up expired keys from Redis.
        
        Returns:
            int: Number of keys cleaned up
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new event loop for this operation
                import threading
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            task_storage.cleanup_expired_keys(self.redis_client)
                        )
                    finally:
                        new_loop.close()
                
                result = [0]
                thread = threading.Thread(target=lambda: result.__setitem__(0, run_async()))
                thread.start()
                thread.join()
                return result[0]
            else:
                return loop.run_until_complete(
                    task_storage.cleanup_expired_keys(self.redis_client)
                )
                
        except Exception as e:
            logger.error(f"Failed to cleanup expired keys: {str(e)}")
            return 0
    
    def get_redis_info(self) -> Dict[str, Any]:
        """
        Get Redis server information.
        
        Returns:
            Dict[str, Any]: Redis server information
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new event loop for this operation
                import threading
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            task_storage.get_redis_info(self.redis_client)
                        )
                    finally:
                        new_loop.close()
                
                result = [{}]
                thread = threading.Thread(target=lambda: result.__setitem__(0, run_async()))
                thread.start()
                thread.join()
                return result[0]
            else:
                return loop.run_until_complete(
                    task_storage.get_redis_info(self.redis_client)
                )
                
        except Exception as e:
            logger.error(f"Failed to get Redis info: {str(e)}")
            return {}
    
    def compact_memory(self) -> bool:
        """
        Compact Redis memory.
        
        Returns:
            bool: True if compacted successfully, False otherwise
        """
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Create a new event loop for this operation
                import threading
                
                def run_async():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(
                            task_storage.compact_memory(self.redis_client)
                        )
                    finally:
                        new_loop.close()
                
                result = [False]
                thread = threading.Thread(target=lambda: result.__setitem__(0, run_async()))
                thread.start()
                thread.join()
                return result[0]
            else:
                return loop.run_until_complete(
                    task_storage.compact_memory(self.redis_client)
                )
                
        except Exception as e:
            logger.error(f"Failed to compact memory: {str(e)}")
            return False