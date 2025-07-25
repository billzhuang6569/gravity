import os
import asyncio
import subprocess
import json
import tempfile
import logging
from pathlib import Path
from typing import Dict, Optional, Tuple, List
from datetime import datetime
import hashlib

from app.config import settings
from app.models.schemas import VideoInfo, DownloadResponse, DownloadRequest

logger = logging.getLogger(__name__)

class VideoDownloader:
    """基于you-get的视频下载器"""
    
    def __init__(self):
        self.download_dir = Path(settings.download_dir)
        self.download_dir.mkdir(exist_ok=True)
        
        # Mac本地代理设置
        self.default_proxies = {
            'http': '127.0.0.1:1087',
            'socks5': '127.0.0.1:1080'
        }
        
    def _build_command(self, url: str, request: Optional[DownloadRequest] = None, info_only: bool = False) -> List[str]:
        """构建you-get命令"""
        cmd = ['you-get']
        
        if info_only:
            cmd.append('--info')
        else:
            # 输出目录设置
            cmd.extend(['-o', str(self.download_dir)])
            
            if request:
                # 格式设置
                if request.format:
                    cmd.extend(['-F', request.format])
                
                # 合并设置
                if request.no_merge:
                    cmd.append('--no-merge')
                
                # 播放列表设置
                if request.playlist:
                    cmd.append('--playlist')
                
                # 输出文件名设置
                if request.output_filename:
                    cmd.extend(['-O', request.output_filename])
                elif not request.output_filename:
                    # 生成安全的文件名
                    filename = self._generate_filename(url, "video")
                    cmd.extend(['-O', filename])
                
                # 文件名前缀和后缀
                if request.prefix:
                    cmd.extend(['--prefix', request.prefix])
                if request.postfix:
                    cmd.append('--postfix')
                
                # 文件处理选项
                if request.force_overwrite:
                    cmd.append('-f')
                if request.auto_rename:
                    cmd.append('-a')
                
                # 字幕设置
                if request.no_caption:
                    cmd.append('--no-caption')
                
                # 代理设置 - 优先级：用户指定 > YouTube自动代理 > 默认代理
                proxy_used = self._setup_proxy(cmd, url, request)
                
                # 认证设置
                if request.cookies_file:
                    cmd.extend(['-c', request.cookies_file])
                if request.password:
                    cmd.extend(['-P', request.password])
                
                # 安全设置
                if request.insecure:
                    cmd.append('-k')
                
                # 网络设置
                if request.timeout:
                    cmd.extend(['-t', str(request.timeout)])
                
                # 播放列表范围
                if request.first:
                    cmd.extend(['--first', str(request.first)])
                if request.last:
                    cmd.extend(['--last', str(request.last)])
                if request.page_size:
                    cmd.extend(['--size', str(request.page_size)])
                
                # 高级选项
                if request.m3u8:
                    cmd.append('-m')
                if request.debug:
                    cmd.append('-d')
        
        cmd.append(url)
        return cmd
    
    def _setup_proxy(self, cmd: List[str], url: str, request: DownloadRequest) -> Optional[str]:
        """设置代理配置"""
        proxy_used = None
        
        # 如果用户明确要求不使用代理
        if request.no_proxy:
            cmd.append('--no-proxy')
            return "no-proxy"
        
        # 用户指定的代理优先
        if request.http_proxy:
            cmd.extend(['-x', request.http_proxy])
            proxy_used = f"http://{request.http_proxy}"
        elif request.socks_proxy:
            cmd.extend(['-s', request.socks_proxy])
            proxy_used = f"socks5://{request.socks_proxy}"
        elif request.extractor_proxy:
            cmd.extend(['-y', request.extractor_proxy])
            proxy_used = f"extractor://{request.extractor_proxy}"
        else:
            # 自动代理策略
            if 'youtube.com' in url or 'youtu.be' in url:
                # YouTube使用HTTP代理
                cmd.extend(['-x', self.default_proxies['http']])
                proxy_used = f"auto-http://{self.default_proxies['http']}"
                logger.info(f"YouTube检测到，使用HTTP代理: {self.default_proxies['http']}")
            elif any(domain in url for domain in ['twitter.com', 'facebook.com', 'instagram.com']):
                # 其他需要代理的网站使用SOCKS5
                cmd.extend(['-s', self.default_proxies['socks5']])
                proxy_used = f"auto-socks5://{self.default_proxies['socks5']}"
                logger.info(f"海外网站检测到，使用SOCKS5代理: {self.default_proxies['socks5']}")
        
        return proxy_used
        
    async def get_video_info(self, url: str, request: Optional[DownloadRequest] = None) -> Dict:
        """获取视频信息（不下载）"""
        try:
            cmd = self._build_command(url, request, info_only=True)
            logger.info(f"执行信息获取命令: {' '.join(cmd)}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"you-get执行失败: {error_msg}")
                raise Exception(f"获取视频信息失败: {error_msg}")
            
            # 解析输出信息
            output = stdout.decode('utf-8', errors='ignore')
            logger.info(f"you-get输出: {output}")
            
            # 简单解析输出信息
            info = {
                "title": "Unknown",
                "site": "Unknown", 
                "formats": [],
                "url": url
            }
            
            lines = output.split('\n')
            current_format = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('site:'):
                    info['site'] = line.split(':', 1)[1].strip()
                elif line.startswith('title:'):
                    info['title'] = line.split(':', 1)[1].strip()
                elif line.startswith('- format:'):
                    if current_format:
                        info['formats'].append(current_format)
                    current_format = {'format': line.split(':', 1)[1].strip()}
                elif 'container:' in line and current_format:
                    current_format['container'] = line.split(':', 1)[1].strip()
                elif 'quality:' in line and current_format:
                    current_format['quality'] = line.split(':', 1)[1].strip()
                elif 'size:' in line and current_format:
                    size_part = line.split('size:', 1)[1].strip()
                    current_format['size'] = size_part
            
            if current_format:
                info['formats'].append(current_format)
            
            return info
            
        except Exception as e:
            logger.error(f"获取视频信息失败: {str(e)}")
            raise
    
    def _generate_filename(self, url: str, title: str) -> str:
        """生成安全的文件名"""
        # 使用URL的哈希值和时间戳生成唯一文件名
        url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # 清理标题中的特殊字符
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title[:50]  # 限制长度
        
        return f"{timestamp}_{url_hash}_{safe_title}"
    
    async def download_video(
        self, 
        url: str, 
        request: Optional[DownloadRequest] = None
    ) -> Tuple[str, VideoInfo, Dict]:
        """下载视频并返回文件路径、视频信息和下载选项"""
        try:
            # 先获取视频信息
            info = await self.get_video_info(url, request)
            
            # 提取视频信息
            title = info.get('title', 'Unknown')
            
            # 构建下载命令
            cmd = self._build_command(url, request, info_only=False)
            logger.info(f"执行下载命令: {' '.join(cmd)}")
            
            # 执行下载
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            stdout, stderr = await process.communicate()
            
            if process.returncode != 0:
                error_msg = stderr.decode('utf-8', errors='ignore')
                logger.error(f"下载失败: {error_msg}")
                raise Exception(f"下载失败: {error_msg}")
            
            # 查找下载的文件
            if request and request.output_filename:
                filename_pattern = request.output_filename
            else:
                filename_pattern = self._generate_filename(url, title)
            
            downloaded_files = list(self.download_dir.glob(f"{filename_pattern}*"))
            if not downloaded_files:
                # 尝试查找任何新文件
                downloaded_files = sorted(self.download_dir.glob("*"), key=lambda x: x.stat().st_mtime, reverse=True)
                if downloaded_files:
                    downloaded_file = downloaded_files[0]
                    logger.info(f"找到最新下载文件: {downloaded_file}")
                else:
                    raise Exception("下载完成但找不到文件")
            else:
                downloaded_file = downloaded_files[0]
            
            # 获取文件大小
            file_size = downloaded_file.stat().st_size
            
            # 创建视频信息对象
            video_info = VideoInfo(
                title=title,
                url=url,
                size=file_size,
                format=info.get('formats', [{}])[0].get('container', 'unknown') if info.get('formats') else 'unknown',
                site=info.get('site', 'Unknown'),
                formats_available=info.get('formats', [])
            )
            
            # 收集下载选项信息
            download_options = {
                'format': request.format if request else None,
                'quality': request.quality if request else None,
                'proxy_used': self._get_proxy_from_request(request) if request else None,
                'no_merge': request.no_merge if request else False,
                'playlist': request.playlist if request else False,
            }
            
            logger.info(f"视频下载成功: {downloaded_file}")
            return str(downloaded_file), video_info, download_options
            
        except Exception as e:
            logger.error(f"下载视频失败: {str(e)}")
            raise
    
    def _get_proxy_from_request(self, request: DownloadRequest) -> Optional[str]:
        """从请求中获取代理信息"""
        if request.no_proxy:
            return "disabled"
        elif request.http_proxy:
            return f"http://{request.http_proxy}"
        elif request.socks_proxy:
            return f"socks5://{request.socks_proxy}"
        elif request.extractor_proxy:
            return f"extractor://{request.extractor_proxy}"
        else:
            return "auto"
    
    async def cleanup_old_files(self, max_age_hours: int = 1):
        """清理旧文件"""
        try:
            current_time = datetime.now().timestamp()
            max_age_seconds = max_age_hours * 3600
            
            for file_path in self.download_dir.iterdir():
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        logger.info(f"清理旧文件: {file_path}")
                        
        except Exception as e:
            logger.error(f"清理文件失败: {str(e)}")

# 创建全局下载器实例
downloader = VideoDownloader() 