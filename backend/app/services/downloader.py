"""
DownloaderService for yt-dlp integration.

This service encapsulates all yt-dlp functionality to provide a clean interface
for video downloading and metadata extraction while handling errors gracefully.
"""

import os
import re
import tempfile
from typing import Dict, List, Optional, Callable, Any
from pathlib import Path
import yt_dlp
from yt_dlp.utils import DownloadError as YtDlpDownloadError, ExtractorError, UnsupportedError

from app.models.schemas import VideoFormat, DownloadOptions


class VideoInfoError(Exception):
    """Exception raised when video info extraction fails."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class DownloadError(Exception):
    """Exception raised when video download fails."""
    def __init__(self, message: str, original_error: Optional[Exception] = None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


class DownloaderService:
    """
    Service class for handling video downloads and metadata extraction using yt-dlp.
    
    This class encapsulates all yt-dlp functionality and provides error handling
    with user-friendly Chinese error messages.
    """
    
    # Pinned yt-dlp version for stability
    YT_DLP_VERSION = "2023.12.30"
    
    # Error message mappings to Chinese
    ERROR_MESSAGES = {
        # Video availability errors
        "Video unavailable": "视频不存在或已被删除",
        "Private video": "视频为私有，无法访问",
        "This video is unavailable": "视频不可用",
        "Video removed": "视频已被移除",
        "This video has been removed": "视频已被删除",
        
        # Geographic and access restrictions
        "not available in your country": "视频存在地区限制，无法访问",
        "blocked in your country": "视频在您的地区被屏蔽",
        "Geographic restriction": "视频存在地区限制",
        "region locked": "视频存在地区限制",
        
        # Format and quality errors
        "Format not available": "指定格式不可用",
        "No video formats found": "未找到可用的视频格式",
        "Requested format not available": "请求的格式不可用",
        "No suitable formats": "没有合适的格式可供下载",
        
        # Network and connection errors
        "Network error": "网络连接错误，请稍后重试",
        "Connection timeout": "网络连接错误，请稍后重试",
        "HTTP Error 403": "访问被拒绝，可能需要登录或存在限制",
        "HTTP Error 404": "视频不存在或链接无效",
        "HTTP Error 429": "请求过于频繁，请稍后重试",
        "HTTP Error 500": "服务器错误，请稍后重试",
        
        # Platform-specific errors
        "Sign in to confirm your age": "需要登录确认年龄才能访问此视频",
        "This video requires payment": "此视频需要付费观看",
        "Live stream": "暂不支持直播流下载",
        
        # General errors
        "Extraction failed": "视频信息提取失败",
        "Download failed": "下载失败",
        "Unknown error": "未知错误，请稍后重试"
    }
    
    def __init__(self, download_dir: Optional[str] = None):
        """
        Initialize the DownloaderService.
        
        Args:
            download_dir: Directory where downloaded files will be stored (uses config if not provided)
        """
        if download_dir is None:
            from app.config import settings
            download_dir = settings.downloads_path
        
        self.download_dir = Path(download_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        
        # Verify yt-dlp version
        if hasattr(yt_dlp, 'version') and yt_dlp.version.__version__ != self.YT_DLP_VERSION:
            print(f"Warning: yt-dlp version mismatch. Expected {self.YT_DLP_VERSION}, got {yt_dlp.version.__version__}")
    
    def get_video_info(self, url: str) -> Dict[str, Any]:
        """
        Extract video metadata synchronously without downloading.
        
        Args:
            url: Video URL to extract info from
            
        Returns:
            Dictionary containing video metadata including title, duration, and formats
            
        Raises:
            VideoInfoError: If video info extraction fails
        """
        try:
            # Configure yt-dlp for info extraction only
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'extract_flat': False,
                'skip_download': True,
                'listformats': False,
                # Don't specify format for info extraction to avoid format errors
                'socket_timeout': 5,  # 5秒超时
                'retries': 1,  # 重试1次
                'fragment_retries': 1,  # 片段重试1次
            }
            
            # Add proxy configuration from environment variables
            import os
            proxy_url = (os.environ.get('HTTP_PROXY') or 
                        os.environ.get('http_proxy') or 
                        os.environ.get('HTTPS_PROXY') or 
                        os.environ.get('https_proxy'))
            if proxy_url:
                ydl_opts['proxy'] = proxy_url
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract video info
                info = ydl.extract_info(url, download=False)
                
                if not info:
                    raise VideoInfoError("无法获取视频信息")
                
                # Parse available formats
                formats = self._parse_formats_for_info(info.get('formats', []))
                
                # Extract duration
                duration = None
                if info.get('duration'):
                    duration = self._format_duration(info['duration'])
                
                return {
                    'title': info.get('title', '未知标题'),
                    'duration': duration,
                    'formats': formats,
                    'uploader': info.get('uploader', ''),
                    'upload_date': info.get('upload_date', ''),
                    'view_count': info.get('view_count', 0),
                    'description': info.get('description', '')[:500] if info.get('description') else ''  # Limit description length
                }
                
        except VideoInfoError:
            # Re-raise VideoInfoError as-is
            raise
        except (YtDlpDownloadError, ExtractorError) as e:
            error_msg = self._parse_error(str(e))
            raise VideoInfoError(error_msg, e)
        except UnsupportedError as e:
            raise VideoInfoError("不支持的视频平台或URL格式", e)
        except Exception as e:
            error_msg = self._parse_error(str(e))
            raise VideoInfoError(error_msg, e)
    
    def download_video(self, url: str, options: DownloadOptions, 
                      progress_callback: Optional[Callable[[Dict], None]] = None,
                      task_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Download video with progress tracking.
        
        Args:
            url: Video URL to download
            options: Download configuration options
            progress_callback: Optional callback function for progress updates
            task_id: Optional task ID for file naming
            
        Returns:
            Dictionary containing file_path, download_url, and title
            
        Raises:
            DownloadError: If download fails
        """
        try:
            # Configure yt-dlp options
            ydl_opts = self._build_download_options(options, task_id)
            
            # Add progress hook if provided
            if progress_callback:
                ydl_opts['progress_hooks'] = [progress_callback]
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info first to get title for filename
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise DownloadError("无法获取视频信息")
                
                # Generate filename with task_id
                filename = self._generate_filename(info.get('title', 'video'), task_id, options)
                ydl_opts['outtmpl'] = str(self.download_dir / filename)
                
                # Create new YDL instance with updated options
                with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                    # Download the video
                    ydl_download.download([url])
                
                # Find the actual downloaded file
                downloaded_file = self._find_downloaded_file(filename)
                if not downloaded_file or not downloaded_file.exists():
                    raise DownloadError("下载完成但无法找到文件")
                
                # Create download result with file management
                from app.services.file_manager import FileManager
                file_manager = FileManager()
                
                return file_manager.create_download_result(
                    str(downloaded_file), 
                    info.get('title', '')
                )
                
        except DownloadError:
            # Re-raise DownloadError as-is
            raise
        except (YtDlpDownloadError, ExtractorError) as e:
            error_msg = self._parse_error(str(e))
            raise DownloadError(error_msg, e)
        except UnsupportedError as e:
            raise DownloadError("不支持的视频平台或URL格式", e)
        except Exception as e:
            error_msg = self._parse_error(str(e))
            raise DownloadError(error_msg, e)
    
    def _parse_formats_for_info(self, formats: List[Dict]) -> List[Dict]:
        """
        Parse yt-dlp formats into dictionary format for API responses.
        
        Args:
            formats: List of format dictionaries from yt-dlp
            
        Returns:
            List of format dictionaries
        """
        parsed_formats = []
        seen_qualities = set()
        
        for fmt in formats:
            if not fmt.get('format_id'):
                continue
                
            # Extract quality information
            quality = self._extract_quality(fmt)
            if quality in seen_qualities:
                continue
            seen_qualities.add(quality)
            
            # Create format dictionary
            format_dict = {
                'format_id': fmt['format_id'],
                'quality': quality,
                'ext': fmt.get('ext', 'mp4'),
                'filesize': fmt.get('filesize')
            }
            parsed_formats.append(format_dict)
        
        # Sort by quality (best first)
        return sorted(parsed_formats, key=lambda x: self._quality_sort_key(x['quality']), reverse=True)
    
    def _parse_formats(self, formats: List[Dict]) -> List[VideoFormat]:
        """
        Parse yt-dlp formats into VideoFormat objects.
        
        Args:
            formats: List of format dictionaries from yt-dlp
            
        Returns:
            List of VideoFormat objects
        """
        parsed_formats = []
        seen_qualities = set()
        
        for fmt in formats:
            if not fmt.get('format_id'):
                continue
                
            # Extract quality information
            quality = self._extract_quality(fmt)
            if quality in seen_qualities:
                continue
            seen_qualities.add(quality)
            
            # Create VideoFormat object
            video_format = VideoFormat(
                format_id=fmt['format_id'],
                quality=quality,
                ext=fmt.get('ext', 'mp4'),
                filesize=fmt.get('filesize')
            )
            parsed_formats.append(video_format)
        
        # Sort by quality (best first)
        return sorted(parsed_formats, key=lambda x: self._quality_sort_key(x.quality), reverse=True)
    
    def _extract_quality(self, fmt: Dict) -> str:
        """Extract quality string from format info."""
        height = fmt.get('height')
        if height:
            return f"{height}p"
        
        # Fallback to format note or format_id
        note = fmt.get('format_note', '')
        if note:
            return note
        
        return fmt.get('format_id', 'unknown')
    
    def _quality_sort_key(self, quality: str) -> int:
        """Generate sort key for quality ordering."""
        quality_map = {
            '2160p': 2160, '1440p': 1440, '1080p': 1080, '720p': 720,
            '480p': 480, '360p': 360, '240p': 240, '144p': 144
        }
        
        # Extract numeric part
        for q, value in quality_map.items():
            if q in quality:
                return value
        
        return 0  # Unknown quality goes to end
    
    def _build_download_options(self, options: DownloadOptions, task_id: Optional[str] = None) -> Dict:
        """Build yt-dlp options dictionary from DownloadOptions."""
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'socket_timeout': 15,  # 15秒超时
            'retries': 3,  # 重试3次
        }
        
        # Add proxy configuration from environment variables
        import os
        proxy_url = (os.environ.get('HTTP_PROXY') or 
                    os.environ.get('http_proxy') or 
                    os.environ.get('HTTPS_PROXY') or 
                    os.environ.get('https_proxy'))
        if proxy_url:
            ydl_opts['proxy'] = proxy_url
        
        # Set format based on options with fallback for compatibility
        if options.format == 'audio':
            # Audio only download with multiple fallback options
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': options.audio_format or 'mp3',
                'preferredquality': '192',
            }]
        else:
            # Video download with multiple fallback options
            if options.quality == 'best':
                # Use more flexible format selection for better compatibility
                ydl_opts['format'] = 'best/bestvideo+bestaudio/bestvideo/best'
            else:
                # Try to match specific quality with fallbacks
                try:
                    quality_height = options.quality.rstrip('p')
                    ydl_opts['format'] = f'best[height<={quality_height}]/bestvideo[height<={quality_height}]+bestaudio/best'
                except (ValueError, AttributeError):
                    # Fallback to best quality if parsing fails
                    ydl_opts['format'] = 'best/bestvideo+bestaudio/bestvideo/best'
        
        return ydl_opts
    
    def _generate_filename(self, title: str, task_id: Optional[str], options: DownloadOptions) -> str:
        """
        Generate filename following the pattern: {sanitized_title}_{task_id}.{ext}
        
        Args:
            title: Video title
            task_id: Task identifier
            options: Download options
            
        Returns:
            Generated filename
        """
        # Sanitize title for filename
        sanitized_title = self._sanitize_filename(title)
        
        # Determine extension
        ext = 'mp3' if options.format == 'audio' else 'mp4'
        
        # Build filename
        if task_id:
            filename = f"{sanitized_title}_{task_id}.%(ext)s"
        else:
            filename = f"{sanitized_title}.%(ext)s"
        
        return filename
    
    def _sanitize_filename(self, filename: str) -> str:
        """Sanitize filename by removing invalid characters."""
        # Remove or replace invalid characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '', filename)
        sanitized = re.sub(r'\s+', '_', sanitized.strip())
        
        # Limit length
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        return sanitized or 'video'
    
    def _find_downloaded_file(self, filename_pattern: str) -> Optional[Path]:
        """Find the actual downloaded file matching the pattern."""
        # Remove %(ext)s placeholder and search for files
        base_name = filename_pattern.replace('.%(ext)s', '')
        
        for file_path in self.download_dir.glob(f"{base_name}.*"):
            if file_path.is_file():
                return file_path
        
        return None
    
    def _format_duration(self, duration_seconds: float) -> str:
        """Format duration from seconds to human-readable string."""
        # Convert float to int for formatting
        duration_int = int(duration_seconds)
        hours = duration_int // 3600
        minutes = (duration_int % 3600) // 60
        seconds = duration_int % 60
        
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            return f"{minutes:02d}:{seconds:02d}"
    
    def _parse_error(self, error_message: str) -> str:
        """
        Convert yt-dlp errors to user-friendly Chinese messages.
        
        Args:
            error_message: Original error message from yt-dlp
            
        Returns:
            User-friendly Chinese error message
        """
        error_lower = error_message.lower()
        
        # Check for specific error patterns
        for pattern, chinese_msg in self.ERROR_MESSAGES.items():
            if pattern.lower() in error_lower:
                return chinese_msg
        
        # Check for HTTP error codes
        if 'http error' in error_lower:
            if '403' in error_lower:
                return self.ERROR_MESSAGES["HTTP Error 403"]
            elif '404' in error_lower:
                return self.ERROR_MESSAGES["HTTP Error 404"]
            elif '429' in error_lower:
                return self.ERROR_MESSAGES["HTTP Error 429"]
            elif '500' in error_lower:
                return self.ERROR_MESSAGES["HTTP Error 500"]
        
        # Check for network-related errors
        if any(term in error_lower for term in ['timeout', 'connection', 'network']):
            return self.ERROR_MESSAGES["Network error"]
        
        # Default fallback
        return self.ERROR_MESSAGES["Unknown error"]