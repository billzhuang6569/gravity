"""Configuration settings for Gravity Video Downloader."""

import os
import secrets
import multiprocessing
from typing import Optional, Dict, Any
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Application
    app_name: str = "Gravity Video Downloader"
    app_version: str = "0.1.0"
    debug: bool = False
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # Redis
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_password: Optional[str] = None
    redis_db: int = 0
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5
    redis_max_connections: int = 20
    
    @property
    def redis_url(self) -> str:
        """Build Redis URL from components."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    @property
    def celery_broker_url(self) -> str:
        """Build Celery broker URL from Redis components."""
        return self.redis_url
    
    @property
    def celery_result_backend(self) -> str:
        """Build Celery result backend URL from Redis components."""
        return self.redis_url
    celery_task_soft_time_limit: int = 1800  # 30 minutes
    celery_task_time_limit: int = 1860  # 31 minutes
    celery_worker_concurrency: Optional[int] = None  # Auto-calculate based on CPU cores
    celery_max_retries: int = 3
    celery_default_retry_delay: int = 60  # 1 minute
    celery_security_key: str = os.environ.get("CELERY_SECURITY_KEY", secrets.token_hex(16))
    celery_worker_max_tasks_per_child: int = 50
    celery_worker_max_memory_per_child: int = 200000  # 200MB
    celery_broker_pool_limit: int = 10
    celery_task_queue_max_priority: int = 10
    celery_task_default_priority: int = 5
    celery_beat_max_loop_interval: int = 300  # 5 minutes
    
    # File Storage
    downloads_path: str = "/opt/gravity/downloads"
    temp_path: str = "/opt/gravity/temp"
    logs_path: str = "/opt/gravity/logs"
    beat_path: str = "/opt/gravity/beat"
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Use local directories for development if /opt/gravity doesn't exist
        if not os.path.exists("/opt/gravity"):
            self.downloads_path = os.path.join(os.getcwd(), "downloads")
            self.temp_path = os.path.join(os.getcwd(), "temp")
            self.logs_path = os.path.join(os.getcwd(), "logs")
            self.beat_path = os.path.join(os.getcwd(), "beat")
    
    # Download Configuration
    max_concurrent_downloads: int = 4
    download_timeout: int = 1800  # 30 minutes
    file_retention_days: int = 7
    
    # Calculated properties
    @property
    def default_worker_concurrency(self) -> int:
        """Calculate default worker concurrency based on CPU cores."""
        return multiprocessing.cpu_count() * 2
    
    @property
    def broker_transport_options(self) -> Dict[str, Any]:
        """Get Redis broker transport options."""
        return {
            "visibility_timeout": 3600,
            "fanout_prefix": True,
            "fanout_patterns": True,
            "retry_on_timeout": True,
            "health_check_interval": 30,
            "socket_keepalive": True,
            "socket_keepalive_options": {
                "TCP_KEEPIDLE": 1,
                "TCP_KEEPINTVL": 3,
                "TCP_KEEPCNT": 5,
            },
            "max_connections": self.redis_max_connections,
            "socket_timeout": self.redis_socket_timeout,
            "socket_connect_timeout": self.redis_socket_connect_timeout,
        }
    
    @property
    def result_backend_transport_options(self) -> Dict[str, Any]:
        """Get Redis result backend transport options."""
        return {
            "visibility_timeout": 3600,
            "retry_on_timeout": True,
            "health_check_interval": 30,
            "max_connections": self.redis_max_connections,
            "socket_timeout": self.redis_socket_timeout,
            "socket_connect_timeout": self.redis_socket_connect_timeout,
        }
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Global settings instance
settings = Settings()