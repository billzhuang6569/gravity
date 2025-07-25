"""
统一视频下载器 - 管理多个下载引擎
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from app.models.schemas import VideoInfo, DownloadRequest
from app.core.base_engine import VideoDownloaderEngine
from app.core.you_get_engine import YouGetEngine
from app.core.yt_dlp_engine import YtDlpEngine

logger = logging.getLogger(__name__)


class UnifiedDownloader:
    """统一视频下载器"""
    
    def __init__(self):
        self.engines: List[VideoDownloaderEngine] = [
            YouGetEngine(),
            YtDlpEngine()
        ]
        logger.info(f"初始化统一下载器，可用引擎: {[engine.name for engine in self.engines]}")
    
    def _select_engine(self, url: str, preferred_engine: Optional[str] = None) -> VideoDownloaderEngine:
        """
        选择最适合的下载引擎
        
        Args:
            url: 视频URL
            preferred_engine: 用户指定的引擎名称
            
        Returns:
            选定的下载引擎
        """
        # 如果用户指定了引擎，优先使用
        if preferred_engine:
            for engine in self.engines:
                if engine.name == preferred_engine and engine.is_supported(url):
                    logger.info(f"使用用户指定引擎: {engine.name}")
                    return engine
        
        # 获取支持该URL的所有引擎，按优先级排序
        supported_engines = [
            engine for engine in self.engines 
            if engine.is_supported(url)
        ]
        
        if not supported_engines:
            logger.error(f"没有引擎支持URL: {url}")
            # 返回第一个引擎作为默认
            return self.engines[0]
        
        # 按优先级排序
        supported_engines.sort(key=lambda e: e.get_priority(url))
        selected_engine = supported_engines[0]
        
        logger.info(f"为URL {url} 选择引擎: {selected_engine.name}")
        return selected_engine
    
    async def get_video_info(self, request: DownloadRequest, preferred_engine: Optional[str] = None) -> Dict[str, Any]:
        """
        获取视频信息 - 带引擎回退机制
        
        Args:
            request: 下载请求
            preferred_engine: 首选引擎
            
        Returns:
            包含视频信息和使用的引擎信息
        """
        url = str(request.url)
        
        # 获取支持该URL的引擎列表，按优先级排序
        supported_engines = [
            engine for engine in self.engines 
            if engine.is_supported(url)
        ]
        
        if preferred_engine:
            # 如果指定了引擎，把它放在最前面
            preferred = next((e for e in supported_engines if e.name == preferred_engine), None)
            if preferred:
                supported_engines.remove(preferred)
                supported_engines.insert(0, preferred)
        else:
            # 按优先级排序
            supported_engines.sort(key=lambda e: e.get_priority(url))
        
        if not supported_engines:
            raise Exception(f"没有可用的引擎支持URL: {url}")
        
        # 尝试每个引擎直到成功
        last_error = None
        for engine in supported_engines:
            try:
                logger.info(f"尝试使用 {engine.name} 获取视频信息")
                video_info = await engine.get_video_info(request)
                
                return {
                    "video_info": video_info,
                    "engine_used": engine.name,
                    "success": True,
                    "available_engines": [e.name for e in supported_engines]
                }
                
            except Exception as e:
                last_error = e
                logger.warning(f"{engine.name} 获取视频信息失败: {str(e)}")
                continue
        
        # 所有引擎都失败了
        error_msg = f"所有引擎都无法获取视频信息。最后错误: {str(last_error)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    async def download_video(self, request: DownloadRequest, preferred_engine: Optional[str] = None) -> Dict[str, Any]:
        """
        下载视频 - 带引擎回退机制
        
        Args:
            request: 下载请求
            preferred_engine: 首选引擎
            
        Returns:
            包含下载结果和使用的引擎信息
        """
        url = str(request.url)
        
        # 获取支持该URL的引擎列表，按优先级排序
        supported_engines = [
            engine for engine in self.engines 
            if engine.is_supported(url)
        ]
        
        if preferred_engine:
            # 如果指定了引擎，把它放在最前面
            preferred = next((e for e in supported_engines if e.name == preferred_engine), None)
            if preferred:
                supported_engines.remove(preferred)
                supported_engines.insert(0, preferred)
        else:
            # 按优先级排序
            supported_engines.sort(key=lambda e: e.get_priority(url))
        
        if not supported_engines:
            raise Exception(f"没有可用的引擎支持URL: {url}")
        
        # 尝试每个引擎直到成功
        last_error = None
        for engine in supported_engines:
            try:
                logger.info(f"尝试使用 {engine.name} 下载视频")
                file_path, video_info, download_options = await engine.download_video(request)
                
                return {
                    "file_path": file_path,
                    "video_info": video_info,
                    "download_options": download_options,
                    "engine_used": engine.name,
                    "success": True,
                    "available_engines": [e.name for e in supported_engines]
                }
                
            except Exception as e:
                last_error = e
                logger.warning(f"{engine.name} 下载失败: {str(e)}")
                continue
        
        # 所有引擎都失败了
        error_msg = f"所有引擎都无法下载视频。最后错误: {str(last_error)}"
        logger.error(error_msg)
        raise Exception(error_msg)
    
    def get_supported_sites(self) -> Dict[str, List[str]]:
        """获取所有引擎支持的网站信息"""
        sites_info = {}
        for engine in self.engines:
            # 这里可以扩展每个引擎的支持网站列表
            if engine.name == "you-get":
                sites_info[engine.name] = [
                    "YouTube", "Bilibili", "iQiyi", "Youku", "QQ Video",
                    "Sina Weibo", "Twitter", "Facebook", "Instagram", "Vimeo"
                ]
            elif engine.name == "yt-dlp":
                sites_info[engine.name] = [
                    "YouTube", "Vimeo", "Twitch", "Twitter", "Facebook",
                    "Instagram", "TikTok", "Reddit", "SoundCloud", "Bilibili"
                ]
        
        return sites_info
    
    def get_engine_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有引擎的状态信息"""
        status = {}
        for engine in self.engines:
            status[engine.name] = {
                "name": engine.name,
                "available": True,  # 这里可以添加健康检查
                "priority_sites": self._get_priority_sites(engine)
            }
        
        return status
    
    def _get_priority_sites(self, engine: VideoDownloaderEngine) -> List[str]:
        """获取引擎的优先处理网站"""
        test_urls = [
            "https://youtube.com/test",
            "https://bilibili.com/test", 
            "https://vimeo.com/test",
            "https://twitter.com/test"
        ]
        
        priority_sites = []
        for url in test_urls:
            if engine.is_supported(url) and engine.get_priority(url) == 1:
                site_name = url.split("//")[1].split("/")[0].replace("www.", "")
                priority_sites.append(site_name)
        
        return priority_sites 