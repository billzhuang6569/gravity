"""
Data models and schemas for the Gravity video downloader application.

This module contains all Pydantic models used for data validation,
serialization, and API request/response handling.
"""

from enum import Enum
from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field, HttpUrl, validator
from app.services.validation import validate_video_url, ValidationError


class TaskStatus(str, Enum):
    """Enumeration of possible task statuses."""
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DownloadOptions(BaseModel):
    """Options for video download configuration."""
    quality: str = Field(default="best", description="Video quality preference")
    format: str = Field(default="video", description="Download format: video or audio")
    audio_format: Optional[str] = Field(default="mp3", description="Audio format when downloading audio only")
    
    @validator('format')
    def validate_format(cls, v):
        if v not in ['video', 'audio']:
            raise ValueError('Format must be either "video" or "audio"')
        return v
    
    @validator('audio_format')
    def validate_audio_format(cls, v, values):
        if values.get('format') == 'audio' and v not in ['mp3', 'm4a']:
            raise ValueError('Audio format must be either "mp3" or "m4a"')
        return v


class VideoFormat(BaseModel):
    """Represents an available video format option."""
    format_id: str = Field(description="Unique format identifier")
    quality: str = Field(description="Quality description (e.g., 1080p, 720p)")
    ext: str = Field(description="File extension")
    filesize: Optional[int] = Field(default=None, description="File size in bytes")


class VideoInfoRequest(BaseModel):
    """Request model for video information parsing."""
    url: str = Field(description="Video URL to parse")
    
    @validator('url')
    def validate_url(cls, v):
        if not v or not v.strip():
            raise ValueError('URL cannot be empty')
        
        url = v.strip()
        try:
            is_valid, platform, error_msg = validate_video_url(url)
            if not is_valid:
                raise ValueError(error_msg or 'Invalid video URL')
        except ValidationError as e:
            raise ValueError(e.message)
        
        return url


class VideoInfoResponse(BaseModel):
    """Response model for video information."""
    title: str = Field(description="Video title")
    duration: Optional[str] = Field(default=None, description="Video duration")
    formats: List[VideoFormat] = Field(description="Available video formats")


class DownloadRequest(BaseModel):
    """Request model for creating a download task."""
    url: str = Field(description="Video URL to download")
    quality: str = Field(default="best", description="Preferred video quality")
    format: str = Field(default="video", description="Download format: video or audio")
    audio_format: Optional[str] = Field(default="mp3", description="Audio format for audio downloads")
    
    @validator('url')
    def validate_url(cls, v):
        if not v or not v.strip():
            raise ValueError('URL cannot be empty')
        
        url = v.strip()
        try:
            is_valid, platform, error_msg = validate_video_url(url)
            if not is_valid:
                raise ValueError(error_msg or 'Invalid video URL')
        except ValidationError as e:
            raise ValueError(e.message)
        
        return url
    
    @validator('format')
    def validate_format(cls, v):
        if v not in ['video', 'audio']:
            raise ValueError('Format must be either "video" or "audio"')
        return v


class DownloadTask(BaseModel):
    """Core model representing a download task with all required fields."""
    task_id: str = Field(description="Unique task identifier")
    url: str = Field(description="Original video URL")
    status: TaskStatus = Field(description="Current task status")
    progress: str = Field(default="", description="Progress information")
    title: str = Field(default="", description="Video title")
    file_path: str = Field(default="", description="Local file path")
    download_url: str = Field(default="", description="Public download URL")
    error_message: str = Field(default="", description="Error details if failed")
    options: DownloadOptions = Field(description="Download configuration options")
    created_at: datetime = Field(description="Task creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")
    
    @validator('url')
    def validate_url(cls, v):
        if not v or not v.strip():
            raise ValueError('URL cannot be empty')
        
        url = v.strip()
        try:
            is_valid, platform, error_msg = validate_video_url(url)
            if not is_valid:
                raise ValueError(error_msg or 'Invalid video URL')
        except ValidationError as e:
            raise ValueError(e.message)
        
        return url


class TaskResponse(BaseModel):
    """API response model for task information with URL field included."""
    task_id: str = Field(description="Unique task identifier")
    url: str = Field(description="Original video URL for self-contained data")
    status: TaskStatus = Field(description="Current task status")
    progress: Optional[str] = Field(default=None, description="Progress information")
    title: Optional[str] = Field(default=None, description="Video title")
    download_url: Optional[str] = Field(default=None, description="Download link when completed")
    error_message: Optional[str] = Field(default=None, description="Error details if failed")
    created_at: datetime = Field(description="Task creation timestamp")
    updated_at: datetime = Field(description="Last update timestamp")


class TaskCreateResponse(BaseModel):
    """Response model for task creation."""
    task_id: str = Field(description="Unique task identifier")
    status: TaskStatus = Field(description="Initial task status")
    message: str = Field(description="Success message")


class HistoryResponse(BaseModel):
    """Response model for download history."""
    tasks: List[TaskResponse] = Field(description="List of recent download tasks")
    total: int = Field(description="Total number of tasks in response")


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: dict = Field(description="Error details")
    timestamp: datetime = Field(description="Error occurrence timestamp")
    
    @classmethod
    def create(cls, code: str, message: str, details: Optional[str] = None):
        """Create a standardized error response."""
        return cls(
            error={
                "code": code,
                "message": message,
                "details": details
            },
            timestamp=datetime.now()
        )


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(description="Service health status")
    timestamp: datetime = Field(description="Health check timestamp")
    services: dict = Field(description="Individual service statuses")