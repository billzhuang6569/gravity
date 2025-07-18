"""
Test script to verify the Pydantic models work correctly.
"""

import sys
import os
from datetime import datetime
from uuid import uuid4

# Add the backend directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.models import (
    TaskStatus,
    DownloadOptions,
    DownloadTask,
    VideoFormat,
    VideoInfoRequest,
    VideoInfoResponse,
    DownloadRequest,
    TaskResponse,
    ErrorResponse
)

def test_models():
    """Test all the Pydantic models."""
    
    print("Testing TaskStatus enum...")
    assert TaskStatus.PENDING == "PENDING"
    assert TaskStatus.DOWNLOADING == "DOWNLOADING"
    assert TaskStatus.COMPLETED == "COMPLETED"
    assert TaskStatus.FAILED == "FAILED"
    print("✓ TaskStatus enum works correctly")
    
    print("\nTesting DownloadOptions model...")
    options = DownloadOptions(quality="1080p", format="video", audio_format="mp3")
    assert options.quality == "1080p"
    assert options.format == "video"
    assert options.audio_format == "mp3"
    print("✓ DownloadOptions model works correctly")
    
    print("\nTesting VideoFormat model...")
    video_format = VideoFormat(
        format_id="22",
        quality="720p",
        ext="mp4",
        filesize=1024000
    )
    assert video_format.format_id == "22"
    assert video_format.quality == "720p"
    print("✓ VideoFormat model works correctly")
    
    print("\nTesting VideoInfoRequest model...")
    info_request = VideoInfoRequest(url="https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert info_request.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print("✓ VideoInfoRequest model works correctly")
    
    print("\nTesting VideoInfoResponse model...")
    info_response = VideoInfoResponse(
        title="Test Video",
        duration="00:05:30",
        formats=[video_format]
    )
    assert info_response.title == "Test Video"
    assert len(info_response.formats) == 1
    print("✓ VideoInfoResponse model works correctly")
    
    print("\nTesting DownloadRequest model...")
    download_request = DownloadRequest(
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        quality="720p",
        format="video"
    )
    assert download_request.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert download_request.quality == "720p"
    print("✓ DownloadRequest model works correctly")
    
    print("\nTesting DownloadTask model...")
    task_id = str(uuid4())
    now = datetime.now()
    download_task = DownloadTask(
        task_id=task_id,
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        status=TaskStatus.PENDING,
        progress="",
        title="Test Video",
        file_path="",
        download_url="",
        error_message="",
        options=options,
        created_at=now,
        updated_at=now
    )
    assert download_task.task_id == task_id
    assert download_task.status == TaskStatus.PENDING
    assert download_task.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    print("✓ DownloadTask model works correctly")
    
    print("\nTesting TaskResponse model...")
    task_response = TaskResponse(
        task_id=task_id,
        url="https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        status=TaskStatus.COMPLETED,
        progress="100%",
        title="Test Video",
        download_url="/downloads/test.mp4",
        error_message=None,
        created_at=now,
        updated_at=now
    )
    assert task_response.task_id == task_id
    assert task_response.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"  # URL field included
    assert task_response.status == TaskStatus.COMPLETED
    print("✓ TaskResponse model works correctly")
    
    print("\nTesting ErrorResponse model...")
    error_response = ErrorResponse.create(
        code="INVALID_URL",
        message="The provided URL is invalid",
        details="URL format not recognized"
    )
    assert error_response.error["code"] == "INVALID_URL"
    assert error_response.error["message"] == "The provided URL is invalid"
    print("✓ ErrorResponse model works correctly")
    
    print("\nTesting validation...")
    try:
        # Test invalid format
        DownloadOptions(format="invalid")
        assert False, "Should have raised validation error"
    except ValueError as e:
        assert "Format must be either" in str(e)
        print("✓ Format validation works correctly")
    
    try:
        # Test empty URL
        VideoInfoRequest(url="")
        assert False, "Should have raised validation error"
    except ValueError as e:
        assert "URL cannot be empty" in str(e)
        print("✓ URL validation works correctly")
    
    print("\n🎉 All model tests passed!")

if __name__ == "__main__":
    test_models()