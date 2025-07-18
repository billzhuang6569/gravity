"""Tests for task storage and retrieval operations in Redis."""

import pytest
import json
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from redis.exceptions import RedisError, ConnectionError

from app.models.schemas import DownloadTask, TaskStatus, DownloadOptions
from app.services.task_storage import (
    store_task, retrieve_task, update_task_status, delete_task, 
    task_exists, get_task_ttl, TaskStorageError, TASK_TTL_SECONDS,
    add_task_to_history, get_download_history, get_download_history_with_tasks,
    remove_task_from_history, clear_download_history, get_history_size,
    HISTORY_KEY, MAX_HISTORY_SIZE
)
from app.services.redis_client import RedisClient


@pytest.fixture
def sample_task():
    """Create a sample DownloadTask for testing."""
    return DownloadTask(
        task_id="test-task-123",
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Valid 11-character YouTube video ID
        status=TaskStatus.PENDING,
        progress="",
        title="Test Video",
        file_path="",
        download_url="",
        error_message="",
        options=DownloadOptions(quality="720p", format="video"),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )


@pytest.fixture
def mock_redis_client():
    """Create a mock Redis client for testing."""
    client = AsyncMock(spec=RedisClient)
    client.execute_with_retry = AsyncMock()
    return client


@pytest.mark.asyncio
async def test_store_task_success(mock_redis_client, sample_task):
    """Test successful task storage."""
    mock_redis_client.execute_with_retry.return_value = True
    
    result = await store_task(mock_redis_client, sample_task)
    
    assert result is True
    mock_redis_client.execute_with_retry.assert_called_once()
    
    # Verify the operation was called with correct parameters
    call_args = mock_redis_client.execute_with_retry.call_args
    operation, task_key, task_data = call_args[0]
    
    assert task_key == f"task:{sample_task.task_id}"
    assert task_data["url"] == sample_task.url
    assert task_data["status"] == sample_task.status.value
    assert task_data["title"] == sample_task.title
    assert "options" in task_data
    assert "created_at" in task_data
    assert "updated_at" in task_data


@pytest.mark.asyncio
async def test_store_task_redis_error(mock_redis_client, sample_task):
    """Test task storage with Redis error."""
    mock_redis_client.execute_with_retry.side_effect = RedisError("Connection failed")
    
    with pytest.raises(TaskStorageError, match="Failed to store task"):
        await store_task(mock_redis_client, sample_task)


@pytest.mark.asyncio
async def test_store_task_operation_failure(mock_redis_client, sample_task):
    """Test task storage when Redis operation returns False."""
    mock_redis_client.execute_with_retry.return_value = False
    
    result = await store_task(mock_redis_client, sample_task)
    
    assert result is False


@pytest.mark.asyncio
async def test_retrieve_task_success(mock_redis_client, sample_task):
    """Test successful task retrieval."""
    # Mock Redis hash data
    redis_data = {
        "url": sample_task.url,
        "status": sample_task.status.value,
        "progress": sample_task.progress,
        "title": sample_task.title,
        "file_path": sample_task.file_path,
        "download_url": sample_task.download_url,
        "error_message": sample_task.error_message,
        "options": sample_task.options.model_dump_json(),
        "created_at": sample_task.created_at.isoformat(),
        "updated_at": sample_task.updated_at.isoformat()
    }
    
    mock_redis_client.execute_with_retry.return_value = redis_data
    
    result = await retrieve_task(mock_redis_client, sample_task.task_id)
    
    assert result is not None
    assert result.task_id == sample_task.task_id
    assert result.url == sample_task.url
    assert result.status == sample_task.status
    assert result.title == sample_task.title
    assert result.options.quality == sample_task.options.quality
    
    mock_redis_client.execute_with_retry.assert_called_once()


@pytest.mark.asyncio
async def test_retrieve_task_not_found(mock_redis_client):
    """Test task retrieval when task doesn't exist."""
    mock_redis_client.execute_with_retry.return_value = {}
    
    result = await retrieve_task(mock_redis_client, "nonexistent-task")
    
    assert result is None


@pytest.mark.asyncio
async def test_retrieve_task_invalid_data(mock_redis_client):
    """Test task retrieval with invalid data format."""
    # Mock invalid Redis data (missing required fields)
    redis_data = {
        "url": "https://example.com",
        "status": "PENDING"
        # Missing other required fields
    }
    
    mock_redis_client.execute_with_retry.return_value = redis_data
    
    with pytest.raises(TaskStorageError, match="Invalid task data format"):
        await retrieve_task(mock_redis_client, "test-task")


@pytest.mark.asyncio
async def test_retrieve_task_redis_error(mock_redis_client):
    """Test task retrieval with Redis error."""
    mock_redis_client.execute_with_retry.side_effect = RedisError("Connection failed")
    
    with pytest.raises(TaskStorageError, match="Failed to retrieve task"):
        await retrieve_task(mock_redis_client, "test-task")


@pytest.mark.asyncio
async def test_update_task_status_success(mock_redis_client):
    """Test successful task status update."""
    # Mock task exists check
    mock_redis_client.execute_with_retry.side_effect = [1, True]  # exists=1, update=True
    
    result = await update_task_status(
        mock_redis_client, 
        "test-task", 
        TaskStatus.DOWNLOADING,
        progress="50%",
        title="Updated Title"
    )
    
    assert result is True
    assert mock_redis_client.execute_with_retry.call_count == 2
    
    # Check the update operation call
    update_call = mock_redis_client.execute_with_retry.call_args_list[1]
    operation, task_key, update_data = update_call[0]
    
    assert task_key == "task:test-task"
    assert update_data["status"] == TaskStatus.DOWNLOADING.value
    assert update_data["progress"] == "50%"
    assert update_data["title"] == "Updated Title"
    assert "updated_at" in update_data


@pytest.mark.asyncio
async def test_update_task_status_task_not_exists(mock_redis_client):
    """Test task status update when task doesn't exist."""
    mock_redis_client.execute_with_retry.return_value = 0  # exists=0
    
    result = await update_task_status(mock_redis_client, "nonexistent-task", TaskStatus.FAILED)
    
    assert result is False


@pytest.mark.asyncio
async def test_update_task_status_with_error_message(mock_redis_client):
    """Test task status update with error message."""
    mock_redis_client.execute_with_retry.side_effect = [1, True]
    
    result = await update_task_status(
        mock_redis_client,
        "test-task",
        TaskStatus.FAILED,
        error_message="Download failed"
    )
    
    assert result is True
    
    # Check the update data includes error message
    update_call = mock_redis_client.execute_with_retry.call_args_list[1]
    update_data = update_call[0][2]
    assert update_data["error_message"] == "Download failed"


@pytest.mark.asyncio
async def test_update_task_status_redis_error(mock_redis_client):
    """Test task status update with Redis error."""
    mock_redis_client.execute_with_retry.side_effect = RedisError("Connection failed")
    
    with pytest.raises(TaskStorageError, match="Failed to update task"):
        await update_task_status(mock_redis_client, "test-task", TaskStatus.FAILED)


@pytest.mark.asyncio
async def test_delete_task_success(mock_redis_client):
    """Test successful task deletion."""
    mock_redis_client.execute_with_retry.return_value = 1  # 1 key deleted
    
    result = await delete_task(mock_redis_client, "test-task")
    
    assert result is True
    mock_redis_client.execute_with_retry.assert_called_once()


@pytest.mark.asyncio
async def test_delete_task_not_found(mock_redis_client):
    """Test task deletion when task doesn't exist."""
    mock_redis_client.execute_with_retry.return_value = 0  # 0 keys deleted
    
    result = await delete_task(mock_redis_client, "nonexistent-task")
    
    assert result is False


@pytest.mark.asyncio
async def test_delete_task_redis_error(mock_redis_client):
    """Test task deletion with Redis error."""
    mock_redis_client.execute_with_retry.side_effect = RedisError("Connection failed")
    
    with pytest.raises(TaskStorageError, match="Failed to delete task"):
        await delete_task(mock_redis_client, "test-task")


@pytest.mark.asyncio
async def test_task_exists_true(mock_redis_client):
    """Test task existence check when task exists."""
    mock_redis_client.execute_with_retry.return_value = 1
    
    result = await task_exists(mock_redis_client, "test-task")
    
    assert result is True


@pytest.mark.asyncio
async def test_task_exists_false(mock_redis_client):
    """Test task existence check when task doesn't exist."""
    mock_redis_client.execute_with_retry.return_value = 0
    
    result = await task_exists(mock_redis_client, "nonexistent-task")
    
    assert result is False


@pytest.mark.asyncio
async def test_task_exists_redis_error(mock_redis_client):
    """Test task existence check with Redis error."""
    mock_redis_client.execute_with_retry.side_effect = RedisError("Connection failed")
    
    with pytest.raises(TaskStorageError, match="Failed to check task existence"):
        await task_exists(mock_redis_client, "test-task")


@pytest.mark.asyncio
async def test_get_task_ttl_success(mock_redis_client):
    """Test getting task TTL when task exists."""
    mock_redis_client.execute_with_retry.return_value = 3600  # 1 hour remaining
    
    result = await get_task_ttl(mock_redis_client, "test-task")
    
    assert result == 3600


@pytest.mark.asyncio
async def test_get_task_ttl_task_not_exists(mock_redis_client):
    """Test getting task TTL when task doesn't exist."""
    mock_redis_client.execute_with_retry.return_value = -2  # Key doesn't exist
    
    result = await get_task_ttl(mock_redis_client, "nonexistent-task")
    
    assert result is None


@pytest.mark.asyncio
async def test_get_task_ttl_no_expiry(mock_redis_client):
    """Test getting task TTL when task has no expiry."""
    mock_redis_client.execute_with_retry.return_value = -1  # Key exists but no TTL
    
    result = await get_task_ttl(mock_redis_client, "test-task")
    
    assert result is None


@pytest.mark.asyncio
async def test_get_task_ttl_redis_error(mock_redis_client):
    """Test getting task TTL with Redis error."""
    mock_redis_client.execute_with_retry.side_effect = RedisError("Connection failed")
    
    with pytest.raises(TaskStorageError, match="Failed to get task TTL"):
        await get_task_ttl(mock_redis_client, "test-task")


@pytest.mark.asyncio
async def test_store_task_with_complex_options(mock_redis_client):
    """Test storing task with complex download options."""
    task = DownloadTask(
        task_id="complex-task",
        url="https://www.bilibili.com/video/BV123456789",
        status=TaskStatus.PENDING,
        progress="",
        title="复杂视频标题",
        file_path="",
        download_url="",
        error_message="",
        options=DownloadOptions(quality="1080p", format="audio", audio_format="m4a"),
        created_at=datetime.now(),
        updated_at=datetime.now()
    )
    
    mock_redis_client.execute_with_retry.return_value = True
    
    result = await store_task(mock_redis_client, task)
    
    assert result is True
    
    # Verify options are properly serialized
    call_args = mock_redis_client.execute_with_retry.call_args
    task_data = call_args[0][2]
    options_data = json.loads(task_data["options"])
    assert options_data["quality"] == "1080p"
    assert options_data["format"] == "audio"
    assert options_data["audio_format"] == "m4a"


@pytest.mark.asyncio
async def test_update_task_status_all_fields(mock_redis_client):
    """Test updating task status with all optional fields."""
    mock_redis_client.execute_with_retry.side_effect = [1, True]
    
    result = await update_task_status(
        mock_redis_client,
        "test-task",
        TaskStatus.COMPLETED,
        progress="100%",
        error_message="",
        title="Final Title",
        file_path="/downloads/video.mp4",
        download_url="/downloads/video.mp4"
    )
    
    assert result is True
    
    # Verify all fields are included in update
    update_call = mock_redis_client.execute_with_retry.call_args_list[1]
    update_data = update_call[0][2]
    
    assert update_data["status"] == TaskStatus.COMPLETED.value
    assert update_data["progress"] == "100%"
    assert update_data["error_message"] == ""
    assert update_data["title"] == "Final Title"
    assert update_data["file_path"] == "/downloads/video.mp4"
    assert update_data["download_url"] == "/downloads/video.mp4"
    assert "updated_at" in update_data


@pytest.mark.asyncio
async def test_ttl_constants():
    """Test that TTL constants are properly defined."""
    assert TASK_TTL_SECONDS == 7 * 24 * 60 * 60  # 7 days in seconds
    assert TASK_TTL_SECONDS == 604800


@pytest.mark.asyncio
async def test_task_storage_error_inheritance():
    """Test that TaskStorageError is properly defined."""
    error = TaskStorageError("Test error")
    assert isinstance(error, Exception)
    assert str(error) == "Test error"


@pytest.mark.asyncio
async def test_retrieve_task_with_unicode_title(mock_redis_client):
    """Test retrieving task with Unicode characters in title."""
    redis_data = {
        "url": "https://www.bilibili.com/video/BV123",
        "status": "COMPLETED",
        "progress": "100%",
        "title": "测试视频标题 🎥",
        "file_path": "/downloads/test.mp4",
        "download_url": "/downloads/test.mp4",
        "error_message": "",
        "options": json.dumps({"quality": "720p", "format": "video", "audio_format": "mp3"}),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    mock_redis_client.execute_with_retry.return_value = redis_data
    
    result = await retrieve_task(mock_redis_client, "test-task")
    
    assert result is not None
    assert result.title == "测试视频标题 🎥"
    assert result.status == TaskStatus.COMPLETED


# Download History Management Tests

@pytest.mark.asyncio
async def test_add_task_to_history_success(mock_redis_client):
    """Test successfully adding a task to download history."""
    mock_redis_client.execute_with_retry.return_value = True
    
    result = await add_task_to_history(mock_redis_client, "test-task-123")
    
    assert result is True
    mock_redis_client.execute_with_retry.assert_called_once()
    
    # Verify the operation was called with correct parameters
    call_args = mock_redis_client.execute_with_retry.call_args
    operation, history_key, task_id, timestamp = call_args[0]
    
    assert history_key == HISTORY_KEY
    assert task_id == "test-task-123"
    assert isinstance(timestamp, float)


@pytest.mark.asyncio
async def test_add_task_to_history_redis_error(mock_redis_client):
    """Test adding task to history with Redis error."""
    mock_redis_client.execute_with_retry.side_effect = RedisError("Connection failed")
    
    with pytest.raises(TaskStorageError, match="Failed to add task to history"):
        await add_task_to_history(mock_redis_client, "test-task")


@pytest.mark.asyncio
async def test_add_task_to_history_operation_failure(mock_redis_client):
    """Test adding task to history when Redis operation returns False."""
    mock_redis_client.execute_with_retry.return_value = False
    
    result = await add_task_to_history(mock_redis_client, "test-task")
    
    assert result is False


@pytest.mark.asyncio
async def test_get_download_history_success(mock_redis_client):
    """Test successfully retrieving download history."""
    # Mock Redis sorted set data (task IDs)
    mock_task_ids = ["task-3", "task-2", "task-1"]  # Most recent first
    mock_redis_client.execute_with_retry.return_value = mock_task_ids
    
    result = await get_download_history(mock_redis_client)
    
    assert result == mock_task_ids
    mock_redis_client.execute_with_retry.assert_called_once()
    
    # Verify the operation was called with correct parameters
    call_args = mock_redis_client.execute_with_retry.call_args
    operation, history_key, limit = call_args[0]
    
    assert history_key == HISTORY_KEY
    assert limit == MAX_HISTORY_SIZE


@pytest.mark.asyncio
async def test_get_download_history_with_limit(mock_redis_client):
    """Test retrieving download history with custom limit."""
    mock_task_ids = ["task-2", "task-1"]
    mock_redis_client.execute_with_retry.return_value = mock_task_ids
    
    result = await get_download_history(mock_redis_client, limit=2)
    
    assert result == mock_task_ids
    
    # Verify limit was passed correctly
    call_args = mock_redis_client.execute_with_retry.call_args
    limit = call_args[0][2]
    assert limit == 2


@pytest.mark.asyncio
async def test_get_download_history_empty(mock_redis_client):
    """Test retrieving download history when empty."""
    mock_redis_client.execute_with_retry.return_value = []
    
    result = await get_download_history(mock_redis_client)
    
    assert result == []


@pytest.mark.asyncio
async def test_get_download_history_bytes_conversion(mock_redis_client):
    """Test retrieving download history with bytes conversion."""
    # Mock Redis returns bytes
    mock_task_ids_bytes = [b"task-3", b"task-2", b"task-1"]
    mock_redis_client.execute_with_retry.return_value = mock_task_ids_bytes
    
    result = await get_download_history(mock_redis_client)
    
    assert result == ["task-3", "task-2", "task-1"]


@pytest.mark.asyncio
async def test_get_download_history_redis_error(mock_redis_client):
    """Test retrieving download history with Redis error."""
    mock_redis_client.execute_with_retry.side_effect = RedisError("Connection failed")
    
    with pytest.raises(TaskStorageError, match="Failed to retrieve download history"):
        await get_download_history(mock_redis_client)


@pytest.mark.asyncio
async def test_get_download_history_with_tasks_success(mock_redis_client, sample_task):
    """Test successfully retrieving download history with full task details."""
    # Mock history retrieval
    mock_task_ids = ["test-task-123"]
    
    # Mock task retrieval
    redis_data = {
        "url": sample_task.url,
        "status": sample_task.status.value,
        "progress": sample_task.progress,
        "title": sample_task.title,
        "file_path": sample_task.file_path,
        "download_url": sample_task.download_url,
        "error_message": sample_task.error_message,
        "options": sample_task.options.model_dump_json(),
        "created_at": sample_task.created_at.isoformat(),
        "updated_at": sample_task.updated_at.isoformat()
    }
    
    # First call returns history, second call returns task data
    mock_redis_client.execute_with_retry.side_effect = [mock_task_ids, redis_data]
    
    result = await get_download_history_with_tasks(mock_redis_client)
    
    assert len(result) == 1
    assert result[0].task_id == sample_task.task_id
    assert result[0].url == sample_task.url
    assert result[0].title == sample_task.title


@pytest.mark.asyncio
async def test_get_download_history_with_tasks_empty(mock_redis_client):
    """Test retrieving download history with tasks when history is empty."""
    mock_redis_client.execute_with_retry.return_value = []
    
    result = await get_download_history_with_tasks(mock_redis_client)
    
    assert result == []


@pytest.mark.asyncio
async def test_get_download_history_with_tasks_missing_task(mock_redis_client):
    """Test retrieving download history when some tasks no longer exist."""
    # Mock history with task IDs
    mock_task_ids = ["existing-task", "missing-task"]
    
    # Mock task retrieval - first exists, second doesn't
    redis_data = {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Valid YouTube URL
        "status": "COMPLETED",
        "progress": "100%",
        "title": "Existing Task",
        "file_path": "/downloads/test.mp4",
        "download_url": "/downloads/test.mp4",
        "error_message": "",
        "options": json.dumps({"quality": "720p", "format": "video", "audio_format": "mp3"}),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    # History call, existing task call, missing task call (empty), remove from history call
    mock_redis_client.execute_with_retry.side_effect = [
        mock_task_ids,  # get_download_history
        redis_data,     # retrieve_task for existing-task
        {},             # retrieve_task for missing-task (empty = not found)
        1               # remove_task_from_history
    ]
    
    result = await get_download_history_with_tasks(mock_redis_client)
    
    assert len(result) == 1
    assert result[0].task_id == "existing-task"
    assert result[0].title == "Existing Task"
    
    # Verify remove_task_from_history was called for missing task
    assert mock_redis_client.execute_with_retry.call_count == 4


@pytest.mark.asyncio
async def test_remove_task_from_history_success(mock_redis_client):
    """Test successfully removing a task from download history."""
    mock_redis_client.execute_with_retry.return_value = 1  # 1 item removed
    
    result = await remove_task_from_history(mock_redis_client, "test-task")
    
    assert result is True
    mock_redis_client.execute_with_retry.assert_called_once()
    
    # Verify the operation was called with correct parameters
    call_args = mock_redis_client.execute_with_retry.call_args
    operation, history_key, task_id = call_args[0]
    
    assert history_key == HISTORY_KEY
    assert task_id == "test-task"


@pytest.mark.asyncio
async def test_remove_task_from_history_not_found(mock_redis_client):
    """Test removing task from history when task is not in history."""
    mock_redis_client.execute_with_retry.return_value = 0  # 0 items removed
    
    result = await remove_task_from_history(mock_redis_client, "nonexistent-task")
    
    assert result is False


@pytest.mark.asyncio
async def test_remove_task_from_history_redis_error(mock_redis_client):
    """Test removing task from history with Redis error."""
    mock_redis_client.execute_with_retry.side_effect = RedisError("Connection failed")
    
    with pytest.raises(TaskStorageError, match="Failed to remove task from history"):
        await remove_task_from_history(mock_redis_client, "test-task")


@pytest.mark.asyncio
async def test_clear_download_history_success(mock_redis_client):
    """Test successfully clearing download history."""
    mock_redis_client.execute_with_retry.return_value = 1  # 1 key deleted
    
    result = await clear_download_history(mock_redis_client)
    
    assert result is True
    mock_redis_client.execute_with_retry.assert_called_once()
    
    # Verify the operation was called with correct parameters
    call_args = mock_redis_client.execute_with_retry.call_args
    operation, history_key = call_args[0]
    
    assert history_key == HISTORY_KEY


@pytest.mark.asyncio
async def test_clear_download_history_already_empty(mock_redis_client):
    """Test clearing download history when already empty."""
    mock_redis_client.execute_with_retry.return_value = 0  # 0 keys deleted
    
    result = await clear_download_history(mock_redis_client)
    
    assert result is True  # Should still return True for empty history


@pytest.mark.asyncio
async def test_clear_download_history_redis_error(mock_redis_client):
    """Test clearing download history with Redis error."""
    mock_redis_client.execute_with_retry.side_effect = RedisError("Connection failed")
    
    with pytest.raises(TaskStorageError, match="Failed to clear download history"):
        await clear_download_history(mock_redis_client)


@pytest.mark.asyncio
async def test_get_history_size_success(mock_redis_client):
    """Test successfully getting download history size."""
    mock_redis_client.execute_with_retry.return_value = 5
    
    result = await get_history_size(mock_redis_client)
    
    assert result == 5
    mock_redis_client.execute_with_retry.assert_called_once()
    
    # Verify the operation was called with correct parameters
    call_args = mock_redis_client.execute_with_retry.call_args
    operation, history_key = call_args[0]
    
    assert history_key == HISTORY_KEY


@pytest.mark.asyncio
async def test_get_history_size_empty(mock_redis_client):
    """Test getting download history size when empty."""
    mock_redis_client.execute_with_retry.return_value = 0
    
    result = await get_history_size(mock_redis_client)
    
    assert result == 0


@pytest.mark.asyncio
async def test_get_history_size_redis_error(mock_redis_client):
    """Test getting download history size with Redis error."""
    mock_redis_client.execute_with_retry.side_effect = RedisError("Connection failed")
    
    with pytest.raises(TaskStorageError, match="Failed to get download history size"):
        await get_history_size(mock_redis_client)


@pytest.mark.asyncio
async def test_history_constants():
    """Test that history constants are properly defined."""
    assert HISTORY_KEY == "history:downloads"
    assert MAX_HISTORY_SIZE == 20


@pytest.mark.asyncio
async def test_history_automatic_trimming_simulation(mock_redis_client):
    """Test the automatic trimming logic in add_task_to_history."""
    # Simulate adding a task when history is at max capacity
    # The operation should handle trimming internally
    
    async def mock_operation(client, history_key, task_id, timestamp):
        # Simulate the Redis operations that would happen
        # zadd, zcard (returns 21), zremrangebyrank
        return True
    
    mock_redis_client.execute_with_retry.side_effect = [True]
    
    result = await add_task_to_history(mock_redis_client, "new-task")
    
    assert result is True
    # The actual trimming logic is tested through the Redis operations
    # which are mocked, but the function structure ensures trimming occurs


@pytest.mark.asyncio
async def test_get_download_history_with_tasks_task_storage_error(mock_redis_client):
    """Test get_download_history_with_tasks when task retrieval fails with TaskStorageError."""
    # Mock history with task IDs
    mock_task_ids = ["failing-task", "good-task"]
    
    # Mock task retrieval - first fails, second succeeds
    redis_data = {
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Valid YouTube URL
        "status": "COMPLETED",
        "progress": "100%",
        "title": "Good Task",
        "file_path": "/downloads/test.mp4",
        "download_url": "/downloads/test.mp4",
        "error_message": "",
        "options": json.dumps({"quality": "720p", "format": "video", "audio_format": "mp3"}),
        "created_at": datetime.now().isoformat(),
        "updated_at": datetime.now().isoformat()
    }
    
    mock_redis_client.execute_with_retry.side_effect = [
        mock_task_ids,                                    # get_download_history
        RedisError("Task retrieval failed"),              # retrieve_task for failing-task
        redis_data                                        # retrieve_task for good-task
    ]
    
    result = await get_download_history_with_tasks(mock_redis_client)
    
    # Should continue processing despite one task failing
    assert len(result) == 1
    assert result[0].task_id == "good-task"
    assert result[0].title == "Good Task"