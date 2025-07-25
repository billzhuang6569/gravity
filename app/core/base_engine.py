"""
视频下载引擎基类
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Tuple, List, Any
from pathlib import Path
from app.models.schemas import VideoInfo, DownloadRequest


class VideoDownloaderEngine(ABC):
    """视频下载引擎抽象基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.download_dir = Path("downloads")
        self.download_dir.mkdir(exist_ok=True)
    
    @abstractmethod
    async def get_video_info(self, request: DownloadRequest) -> VideoInfo:
        """获取视频信息"""
        pass
    
    @abstractmethod
    async def download_video(self, request: DownloadRequest) -> Tuple[str, VideoInfo, Dict[str, Any]]:
        """
        下载视频
        返回: (文件路径, 视频信息, 下载选项)
        """
        pass
    
    @abstractmethod
    def is_supported(self, url: str) -> bool:
        """检查是否支持该URL"""
        pass
    
    @abstractmethod
    def get_priority(self, url: str) -> int:
        """
        获取处理该URL的优先级
        数字越小优先级越高
        """
        pass 