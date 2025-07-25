"""
you-get 下载引擎实现
"""
import os
import asyncio
import subprocess
import json
import tempfile
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any
from datetime import datetime
import hashlib

from app.config import settings
from app.models.schemas import VideoInfo, DownloadResponse, DownloadRequest
from app.core.base_engine import VideoDownloaderEngine

logger = logging.getLogger(__name__)


class YouGetEngine(VideoDownloaderEngine):
    """you-get 下载引擎"""
    
    def __init__(self):
        super().__init__("you-get")
        self.default_proxies = {
            'http': '127.0.0.1:1087',
            'socks5': '127.0.0.1:1080'
        }
    
    def is_supported(self, url: str) -> bool:
        """检查是否支持该URL - you-get支持大多数网站"""
        supported_domains = [
            'youtube.com', 'youtu.be', 'bilibili.com', 'iqiyi.com',
            'youku.com', 'tudou.com', 'qq.com', 'sina.com.cn',
            'weibo.com', 'twitter.com', 'facebook.com', 'instagram.com',
            'vimeo.com', 'dailymotion.com'
        ]
        return any(domain in url for domain in supported_domains)
    
    def get_priority(self, url: str) -> int:
        """获取优先级 - you-get对中文网站优先级高"""
        if any(domain in url for domain in ['bilibili.com', 'iqiyi.com', 'youku.com']):
            return 1  # 中文网站优先使用you-get
        elif 'youtube.com' in url or 'youtu.be' in url:
            return 2  # YouTube使用yt-dlp优先
        else:
            return 3  # 其他网站中等优先级
    
    def _build_command(self, request: DownloadRequest, info_only: bool = False) -> List[str]:
        """构建you-get命令"""
        url = str(request.url)
        cmd = ['you-get']
        
        if info_only:
            cmd.append('--info')
        else:
            cmd.extend(['-o', str(self.download_dir)])
        
        # 格式选择
        if request.format:
            cmd.extend(['--format', request.format])
        
        # 输出文件名
        if request.output_filename:
            cmd.extend(['-O', request.output_filename])
        elif request.prefix:
            cmd.extend(['-P', request.prefix])
        
        # 各种选项
        if request.no_merge:
            cmd.append('--no-merge')
        if request.no_caption:
            cmd.append('--no-caption')
        if request.force_overwrite:
            cmd.append('--force')
        if request.auto_rename:
            cmd.append('--auto-rename')
        if request.insecure:
            cmd.append('--insecure')
        if request.debug:
            cmd.append('--debug')
        if request.m3u8:
            cmd.append('--m3u8')
        
        # 播放列表选项
        if request.playlist:
            cmd.append('--playlist')
        if request.first:
            cmd.extend(['--first', str(request.first)])
        if request.last:
            cmd.extend(['--last', str(request.last)])
        
        # 超时设置
        if request.timeout:
            cmd.extend(['--timeout', str(request.timeout)])
        
        # Cookies
        if request.cookies_file:
            cookies_path = Path(f"cookies/{request.cookies_file}")
            if cookies_path.exists():
                cmd.extend(['--cookies', str(cookies_path)])
        
        # 代理设置
        self._setup_proxy(cmd, url, request)
        
        cmd.append(url)
        return cmd
    
    def _setup_proxy(self, cmd: List[str], url: str, request: DownloadRequest) -> Optional[str]:
        """设置代理配置"""
        if request.no_proxy:
            cmd.append('--no-proxy')
            return "no-proxy"
        
        if request.http_proxy:
            cmd.extend(['-x', request.http_proxy])
            return f"http://{request.http_proxy}"
        elif request.socks_proxy:
            cmd.extend(['-s', request.socks_proxy])
            return f"socks5://{request.socks_proxy}"
        elif request.extractor_proxy:
            cmd.extend(['-y', request.extractor_proxy])
            return f"extractor://{request.extractor_proxy}"
        else:
            # 自动代理选择
            if 'youtube.com' in url or 'youtu.be' in url:
                cmd.extend(['-x', self.default_proxies['http']])
                return f"auto-http://{self.default_proxies['http']}"
            elif any(domain in url for domain in ['twitter.com', 'facebook.com', 'instagram.com']):
                cmd.extend(['-s', self.default_proxies['socks5']])
                return f"auto-socks5://{self.default_proxies['socks5']}"
        
        return None
    
    async def get_video_info(self, request: DownloadRequest) -> VideoInfo:
        """获取视频信息"""
        try:
            cmd = self._build_command(request, info_only=True)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.download_dir)
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"you-get info failed: {error_msg}")
                raise Exception(f"获取视频信息失败: {error_msg}")
            
            # 解析输出
            output = stdout.decode('utf-8', errors='ignore')
            return self._parse_video_info(output, str(request.url))
            
        except Exception as e:
            logger.error(f"you-get get_video_info error: {str(e)}")
            raise Exception(f"获取视频信息失败: {str(e)}")
    
    def _parse_video_info(self, output: str, url: str) -> VideoInfo:
        """解析you-get输出的视频信息"""
        lines = output.strip().split('\n')
        title = "Unknown"
        site = "Unknown"
        formats_available = []
        
        for line in lines:
            if 'title:' in line:
                title = line.split('title:', 1)[1].strip()
            elif 'site:' in line:
                site = line.split('site:', 1)[1].strip()
            elif line.strip().startswith('-'):
                # 格式信息行
                format_info = line.strip()
                if format_info:
                    formats_available.append({"format": format_info})
        
        return VideoInfo(
            title=title,
            url=url,
            site=site,
            formats_available=formats_available
        )
    
    async def download_video(self, request: DownloadRequest) -> Tuple[str, VideoInfo, Dict[str, Any]]:
        """下载视频"""
        try:
            # 先获取视频信息
            video_info = await self.get_video_info(request)
            
            # 构建下载命令
            cmd = self._build_command(request, info_only=False)
            
            # 执行下载
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.download_dir)
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"you-get download failed: {error_msg}")
                raise Exception(f"下载失败: {error_msg}")
            
            # 查找下载的文件
            downloaded_files = self._find_downloaded_files(video_info.title)
            if not downloaded_files:
                raise Exception("未找到下载的文件")
            
            file_path = downloaded_files[0]
            
            # 构建下载选项信息
            download_options = {
                "engine": self.name,
                "format": request.format,
                "proxy_used": self._get_proxy_from_request(str(request.url), request),
                "cookies_used": bool(request.cookies_file)
            }
            
            return str(file_path), video_info, download_options
            
        except Exception as e:
            logger.error(f"you-get download error: {str(e)}")
            raise Exception(f"下载失败: {str(e)}")
    
    def _find_downloaded_files(self, title: str) -> List[Path]:
        """查找下载的文件"""
        downloaded_files = []
        
        # 搜索可能的文件扩展名
        extensions = ['.mp4', '.flv', '.mkv', '.webm', '.avi', '.mov', '.m4v']
        
        for file_path in self.download_dir.glob('*'):
            if file_path.is_file():
                # 检查是否是最近创建的视频文件
                if any(file_path.name.endswith(ext) for ext in extensions):
                    downloaded_files.append(file_path)
        
        # 按修改时间排序，返回最新的文件
        downloaded_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        return downloaded_files
    
    def _get_proxy_from_request(self, url: str, request: DownloadRequest) -> Optional[str]:
        """从请求中获取代理信息"""
        if request.no_proxy:
            return "no-proxy"
        if request.http_proxy:
            return f"http://{request.http_proxy}"
        elif request.socks_proxy:
            return f"socks5://{request.socks_proxy}"
        elif request.extractor_proxy:
            return f"extractor://{request.extractor_proxy}"
        else:
            return self._setup_proxy([], url, request) 