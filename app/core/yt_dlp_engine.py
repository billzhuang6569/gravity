"""
yt-dlp 下载引擎实现
"""
import os
import asyncio
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any
from datetime import datetime

from app.config import settings
from app.models.schemas import VideoInfo, DownloadRequest
from app.core.base_engine import VideoDownloaderEngine

logger = logging.getLogger(__name__)


class YtDlpEngine(VideoDownloaderEngine):
    """yt-dlp 下载引擎"""
    
    def __init__(self):
        super().__init__("yt-dlp")
        self.default_proxies = {
            'http': 'http://127.0.0.1:1087',
            'socks5': 'socks5://127.0.0.1:1080'
        }
    
    def is_supported(self, url: str) -> bool:
        """检查是否支持该URL - yt-dlp支持更多国外网站"""
        supported_domains = [
            'youtube.com', 'youtu.be', 'vimeo.com', 'dailymotion.com',
            'twitch.tv', 'twitter.com', 'facebook.com', 'instagram.com',
            'tiktok.com', 'reddit.com', 'soundcloud.com', 'bandcamp.com',
            'bilibili.com'  # 也支持B站
        ]
        return any(domain in url for domain in supported_domains)
    
    def get_priority(self, url: str) -> int:
        """获取优先级 - yt-dlp对国外网站优先级高"""
        if 'youtube.com' in url or 'youtu.be' in url:
            return 1  # YouTube优先使用yt-dlp
        elif 'vimeo.com' in url:
            return 1  # Vimeo优先使用yt-dlp
        elif any(domain in url for domain in ['twitter.com', 'facebook.com', 'instagram.com']):
            return 1  # 社交媒体优先使用yt-dlp
        elif any(domain in url for domain in ['bilibili.com', 'iqiyi.com', 'youku.com']):
            return 2  # 中文网站备用
        else:
            return 2  # 其他网站备用
    
    def _build_command(self, request: DownloadRequest, info_only: bool = False) -> List[str]:
        """构建yt-dlp命令"""
        url = str(request.url)
        cmd = ['yt-dlp']
        
        # 基本设置
        cmd.extend(['--no-warnings', '--ignore-errors'])
        
        if info_only:
            cmd.extend(['--dump-json', '--no-download'])
        else:
            cmd.extend(['-o', f'{self.download_dir}/%(title)s.%(ext)s'])
            
            # 格式选择 - yt-dlp使用不同的格式语法
            if request.format:
                if request.format == 'best':
                    cmd.extend(['-f', 'best'])
                elif 'quality' in request.format.lower():
                    # 处理质量选择
                    cmd.extend(['-f', 'best[height<=720]'])
                else:
                    cmd.extend(['-f', request.format])
            else:
                cmd.extend(['-f', 'best'])
        
        # 输出选项
        if request.output_filename:
            cmd.extend(['-o', f'{self.download_dir}/{request.output_filename}.%(ext)s'])
        
        # 各种选项
        if request.no_merge:
            cmd.append('--keep-video')
        if request.force_overwrite:
            cmd.append('--force-overwrites')
        if request.insecure:
            cmd.append('--no-check-certificates')
        
        # 播放列表选项
        if request.playlist:
            cmd.append('--yes-playlist')
        else:
            cmd.append('--no-playlist')
            
        if request.first and request.last:
            cmd.extend(['--playlist-items', f'{request.first}-{request.last}'])
        elif request.first:
            cmd.extend(['--playlist-start', str(request.first)])
        elif request.last:
            cmd.extend(['--playlist-end', str(request.last)])
        
        # 超时设置
        if request.timeout:
            cmd.extend(['--socket-timeout', str(request.timeout)])
        
        # Cookies
        if request.cookies_file:
            cookies_path = Path(f"cookies/{request.cookies_file}")
            if cookies_path.exists():
                cmd.extend(['--cookies', str(cookies_path)])
        
        # 代理设置
        proxy_used = self._setup_proxy(cmd, url, request)
        
        # 用户代理
        cmd.extend(['--user-agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'])
        
        cmd.append(url)
        return cmd
    
    def _setup_proxy(self, cmd: List[str], url: str, request: DownloadRequest) -> Optional[str]:
        """设置代理配置"""
        if request.no_proxy:
            cmd.append('--no-proxy')
            return "no-proxy"
        
        proxy_url = None
        if request.http_proxy:
            proxy_url = f"http://{request.http_proxy}"
        elif request.socks_proxy:
            proxy_url = f"socks5://{request.socks_proxy}"
        elif request.extractor_proxy:
            proxy_url = f"http://{request.extractor_proxy}"
        else:
            # 自动代理选择
            if any(domain in url for domain in ['youtube.com', 'youtu.be', 'vimeo.com']):
                proxy_url = self.default_proxies['http']
            elif any(domain in url for domain in ['twitter.com', 'facebook.com', 'instagram.com']):
                proxy_url = self.default_proxies['socks5']
        
        if proxy_url:
            cmd.extend(['--proxy', proxy_url])
            return proxy_url
        
        return None
    
    async def get_video_info(self, request: DownloadRequest) -> VideoInfo:
        """获取视频信息"""
        try:
            cmd = self._build_command(request, info_only=True)
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"yt-dlp info failed: {error_msg}")
                raise Exception(f"获取视频信息失败: {error_msg}")
            
            # 解析JSON输出
            output = stdout.decode('utf-8', errors='ignore')
            return self._parse_video_info(output, str(request.url))
            
        except Exception as e:
            logger.error(f"yt-dlp get_video_info error: {str(e)}")
            raise Exception(f"获取视频信息失败: {str(e)}")
    
    def _parse_video_info(self, output: str, url: str) -> VideoInfo:
        """解析yt-dlp的JSON输出"""
        try:
            # yt-dlp输出JSON格式
            lines = output.strip().split('\n')
            for line in lines:
                if line.strip().startswith('{'):
                    data = json.loads(line)
                    
                    title = data.get('title', 'Unknown')
                    site = data.get('extractor', 'Unknown')
                    
                    # 解析可用格式
                    formats_available = []
                    if 'formats' in data:
                        for fmt in data['formats']:
                            format_info = {
                                'format_id': fmt.get('format_id', ''),
                                'ext': fmt.get('ext', ''),
                                'resolution': fmt.get('resolution', ''),
                                'filesize': fmt.get('filesize', 0),
                                'quality': fmt.get('quality', 0)
                            }
                            formats_available.append(format_info)
                    
                    return VideoInfo(
                        title=title,
                        url=url,
                        site=site,
                        formats_available=formats_available
                    )
            
            # 如果没有找到JSON，尝试解析普通输出
            return VideoInfo(
                title="Unknown",
                url=url,
                site="Unknown",
                formats_available=[]
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse yt-dlp JSON output: {e}")
            return VideoInfo(
                title="Unknown",
                url=url,
                site="Unknown",
                formats_available=[]
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
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"yt-dlp download failed: {error_msg}")
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
            logger.error(f"yt-dlp download error: {str(e)}")
            raise Exception(f"下载失败: {str(e)}")
    
    def _find_downloaded_files(self, title: str) -> List[Path]:
        """查找下载的文件"""
        downloaded_files = []
        
        # 搜索可能的文件扩展名
        extensions = ['.mp4', '.webm', '.mkv', '.avi', '.mov', '.m4v', '.flv']
        
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
            return f"http://{request.extractor_proxy}"
        else:
            return self._setup_proxy([], url, request) 