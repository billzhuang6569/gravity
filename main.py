import os
import tempfile
import asyncio
import json
import time
import hashlib
import uuid
import re
import signal
import threading
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse

import yt_dlp
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Request, Header
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, field_validator
import aiofiles
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 代理配置
HTTP_PROXY = os.getenv('HTTP_PROXY', '').strip()
HTTPS_PROXY = os.getenv('HTTPS_PROXY', '').strip()
PROXY_DOMAINS = os.getenv('PROXY_DOMAINS', '').strip().split(',') if os.getenv('PROXY_DOMAINS') else []

# Cookies配置
COOKIES_BROWSER = os.getenv('COOKIES_BROWSER', '').strip()
COOKIES_FILE = os.getenv('COOKIES_FILE', '').strip()

def should_use_proxy(url: str) -> bool:
    """判断是否需要使用代理"""
    if not HTTP_PROXY or not HTTPS_PROXY:
        return False
    
    try:
        domain = urlparse(url).netloc.lower()
        # 移除www前缀
        if domain.startswith('www.'):
            domain = domain[4:]
        
        # 检查是否在代理域名列表中
        for proxy_domain in PROXY_DOMAINS:
            if proxy_domain.strip() and proxy_domain.strip().lower() in domain:
                return True
        return False
    except:
        return False

def setup_proxy_env(url: str):
    """根据URL设置代理环境变量"""
    if should_use_proxy(url):
        os.environ['http_proxy'] = HTTP_PROXY
        os.environ['https_proxy'] = HTTPS_PROXY
        print(f"🌐 使用代理访问: {urlparse(url).netloc}")
    else:
        # 清除代理环境变量
        os.environ.pop('http_proxy', None)
        os.environ.pop('https_proxy', None)
        print(f"🔗 直连访问: {urlparse(url).netloc}")

def get_ydl_opts(base_opts: dict = None) -> dict:
    """获取yt-dlp配置选项，包括cookies设置"""
    if base_opts is None:
        base_opts = {}
    
    # 添加cookies配置
    if COOKIES_FILE and os.path.exists(COOKIES_FILE):
        base_opts['cookiefile'] = COOKIES_FILE
        print(f"🍪 使用cookies文件: {COOKIES_FILE}")
    elif COOKIES_BROWSER:
        base_opts['cookiesfrombrowser'] = (COOKIES_BROWSER,)
        print(f"🍪 使用{COOKIES_BROWSER}浏览器cookies")
    
    return base_opts

app = FastAPI(
    title="YT-DLP API",
    description="基于yt-dlp的视频下载API服务，支持各大视频网站",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 创建下载目录用于存储下载的文件（项目内）
DOWNLOAD_DIR = Path(__file__).parent / "downloads"
DOWNLOAD_DIR.mkdir(exist_ok=True)

# 存储下载进度
download_progress = {}

# 跟踪活跃的下载线程
active_download_threads = set()

class DownloadRequest(BaseModel):
    url: HttpUrl
    format: Optional[str] = "best"
    quality: Optional[str] = "best"
    extract_audio: Optional[bool] = False
    audio_format: Optional[str] = "mp3"
    output_template: Optional[str] = "%(title)s.%(ext)s"
    download_sections: Optional[str] = None  # 下载指定时间段
    write_subs: Optional[bool] = False  # 下载字幕
    sub_langs: Optional[str] = "en"  # 字幕语言
    
    @field_validator('audio_format')
    @classmethod
    def validate_audio_format(cls, v):
        valid_formats = ['mp3', 'm4a', 'wav', 'flac', 'opus']
        if v not in valid_formats:
            raise ValueError(f'音频格式必须是以下之一: {", ".join(valid_formats)}')
        return v

class VideoInfo(BaseModel):
    id: str
    title: str
    duration: Optional[float]
    formats: List[Dict[str, Any]]
    thumbnail: Optional[str]
    description: Optional[str]
    uploader: Optional[str]
    upload_date: Optional[str]
    view_count: Optional[int]
    like_count: Optional[int]
    webpage_url: Optional[str]

class DownloadProgress(BaseModel):
    video_id: str
    status: str  # 'downloading', 'completed', 'failed'
    progress: Optional[float] = None
    speed: Optional[str] = None
    eta: Optional[str] = None
    filename: Optional[str] = None
    error: Optional[str] = None

class ProgressHook:
    """官方progress_hooks实现 - 标准且可靠的方法"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        
    def __call__(self, d):
        """yt-dlp progress hook回调函数"""
        try:
            status = d.get('status', 'unknown')
            
            if status == 'downloading':
                # 获取文件大小信息
                downloaded_bytes = d.get('downloaded_bytes', 0)
                total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                
                # 🎯 直接用字节数计算进度，更准确！
                if total_bytes > 0:
                    progress_decimal = min(downloaded_bytes / total_bytes, 1.0)
                    progress_percentage = progress_decimal * 100
                else:
                    # 备用：尝试解析_percent_str
                    progress_raw = d.get('_percent_str', '0%')
                    progress_decimal = self._parse_percent_str(progress_raw)
                    progress_percentage = progress_decimal * 100
                
                # 格式化速度信息
                speed_str = self._format_speed(d.get('speed'))
                
                # 格式化ETA
                eta_str = self._format_eta(d.get('eta'))
                
                # 更新全局进度状态 - 保留现有信息
                current_info = download_progress.get(self.task_id, {})
                download_progress[self.task_id] = {
                    **current_info,
                    'status': 'downloading',
                    'progress_decimal': round(progress_decimal, 4),
                    'progress_percentage': round(progress_percentage, 2),
                    'speed': speed_str,
                    'eta': eta_str,
                    'downloaded_bytes': downloaded_bytes,
                    'total_bytes': total_bytes,
                    'filename': d.get('filename', ''),
                    'timestamp': time.time()
                }
                
                print(f"🎯 [ProgressHook] 进度更新: {self.task_id} -> {progress_percentage:.1f}% ({speed_str})")
                
            elif status == 'finished':
                # 下载完成
                current_info = download_progress.get(self.task_id, {})
                download_progress[self.task_id] = {
                    **current_info,
                    'status': 'post_processing',
                    'progress_decimal': 1.0,
                    'progress_percentage': 100.0,
                    'message': '下载完成，正在后处理...',
                    'filename': d.get('filename', ''),
                    'timestamp': time.time()
                }
                
                print(f"🎯 [ProgressHook] 下载完成: {self.task_id}")
                
            elif status == 'error':
                # 下载错误
                current_info = download_progress.get(self.task_id, {})
                download_progress[self.task_id] = {
                    **current_info,
                    'status': 'failed',
                    'error': 'yt-dlp下载错误',
                    'timestamp': time.time()
                }
                
                print(f"🎯 [ProgressHook] 下载错误: {self.task_id}")
                
        except Exception as e:
            print(f"🎯 [ProgressHook] 回调错误: {e}")
            import traceback
            traceback.print_exc()
    
    def _parse_percent_str(self, percent_str):
        """解析百分比字符串"""
        if not percent_str:
            return 0.0
        try:
            # 移除%符号并转换为浮点数
            clean_str = percent_str.replace('%', '').strip()
            return float(clean_str) / 100.0
        except:
            return 0.0
            
    def _format_speed(self, speed):
        """格式化速度信息"""
        if not speed:
            return "0B/s"
        try:
            # speed已经是数字（字节/秒）
            if speed > 1024 * 1024:
                return f"{speed / (1024 * 1024):.1f}MB/s"
            elif speed > 1024:
                return f"{speed / 1024:.1f}KB/s"
            else:
                return f"{speed:.0f}B/s"
        except:
            return "0B/s"
            
    def _format_eta(self, eta):
        """格式化ETA信息"""
        if not eta:
            return "未知"
        try:
            # eta是秒数
            if eta > 3600:
                hours = int(eta // 3600)
                minutes = int((eta % 3600) // 60)
                return f"{hours:02d}:{minutes:02d}:00"
            else:
                minutes = int(eta // 60)
                seconds = int(eta % 60)
                return f"{minutes:02d}:{seconds:02d}"
        except:
            return "未知"

@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "message": "YT-DLP API 服务",
        "version": "1.0.0",
        "description": "基于yt-dlp的视频下载API，支持各大视频网站",
        "endpoints": {
            "GET /info": "获取视频信息",
            "GET /formats": "获取可用格式",
            "POST /download": "下载视频",
            "GET /download/{video_id}": "直接下载视频",
            "GET /progress/{video_id}": "获取下载进度",
            "GET /health": "健康检查",
            "GET /supported-sites": "获取支持的网站列表",
            "DELETE /cleanup": "清理临时文件"
        },
        "docs": "/docs"
    }

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy", 
        "service": "yt-dlp-api",
        "timestamp": datetime.now().isoformat(),
        "download_dir": str(DOWNLOAD_DIR),
        "download_dir_exists": DOWNLOAD_DIR.exists()
    }

@app.get("/info")
async def get_video_info(url: str = Query(..., description="视频URL")):
    """获取视频信息"""
    try:
        # 设置代理
        setup_proxy_env(url)
        
        ydl_opts = get_ydl_opts({
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            sanitized_info = ydl.sanitize_info(info)
            
            # 提取关键信息
            video_info = VideoInfo(
                id=sanitized_info.get('id', ''),
                title=sanitized_info.get('title', ''),
                duration=sanitized_info.get('duration'),
                formats=sanitized_info.get('formats', []),
                thumbnail=sanitized_info.get('thumbnail'),
                description=sanitized_info.get('description'),
                uploader=sanitized_info.get('uploader'),
                upload_date=sanitized_info.get('upload_date'),
                view_count=sanitized_info.get('view_count'),
                like_count=sanitized_info.get('like_count'),
                webpage_url=sanitized_info.get('webpage_url')
            )
            
            return video_info
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取视频信息失败: {str(e)}")

@app.get("/formats")
async def get_formats(url: str = Query(..., description="视频URL")):
    """获取视频的可用格式"""
    try:
        # 设置代理
        setup_proxy_env(url)
        
        ydl_opts = get_ydl_opts({
            'quiet': True,
            'no_warnings': True,
        })
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            sanitized_info = ydl.sanitize_info(info)
            
            formats = sanitized_info.get('formats', [])
            
            # 简化格式信息并按质量排序，排除非视频格式
            simplified_formats = []
            for fmt in formats:
                # 跳过mhtml等非视频格式
                if fmt.get('ext') in ['mhtml', 'html', 'json']:
                    continue
                    
                simplified_formats.append({
                    'format_id': fmt.get('format_id'),
                    'ext': fmt.get('ext'),
                    'resolution': fmt.get('resolution'),
                    'filesize': fmt.get('filesize'),
                    'vcodec': fmt.get('vcodec'),
                    'acodec': fmt.get('acodec'),
                    'fps': fmt.get('fps'),
                    'height': fmt.get('height'),
                    'width': fmt.get('width'),
                    'url': fmt.get('url'),
                    'format_note': fmt.get('format_note'),
                    'filesize_approx': fmt.get('filesize_approx')
                })
            
            # 如果没有有效格式，返回错误
            if not simplified_formats:
                raise HTTPException(status_code=400, detail="该视频没有可用的视频或音频格式")
            
            # 按分辨率排序
            simplified_formats.sort(key=lambda x: (x.get('height', 0) or 0, x.get('width', 0) or 0), reverse=True)
            
            return {
                "video_id": sanitized_info.get('id'),
                "title": sanitized_info.get('title'),
                "duration": sanitized_info.get('duration'),
                "formats": simplified_formats,
                "format_recommendations": {
                    "best_video": "bv*+ba/b",
                    "best_audio": "ba",
                    "worst": "w",
                    "best_mp4": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b",
                    "best_under_720p": "bv*[height<=720]+ba/b[height<=720]/b"
                }
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"获取格式信息失败: {str(e)}")

@app.post("/download")
async def download_video(request: DownloadRequest):
    """下载视频"""
    try:
        print(f"🔍 [DEBUG] 开始处理下载请求")
        
        # 生成完全随机的唯一task_id
        task_id = str(uuid.uuid4())[:12]
        print(f"🔍 [DEBUG] 生成随机task_id: {task_id}")
        
        # 立即初始化进度
        download_progress[task_id] = {
            'status': 'pending',
            'message': '任务已创建，准备开始...',
            'timestamp': time.time()
        }
        print(f"🔍 [DEBUG] 进度初始化完成")
        
        # 使用可控制的线程启动后台任务
        download_thread = threading.Thread(
            target=download_video_task_sync, 
            args=(str(request.url), request.model_dump(), task_id),
            daemon=True  # 设置为守护线程，主进程结束时自动结束
        )
        active_download_threads.add(download_thread)
        download_thread.start()
        print(f"🔍 [DEBUG] 后台任务已启动在独立线程 (thread: {download_thread.name})")
        
        # 立即返回响应
        response = {
            "status": "started",
            "video_id": task_id,
            "message": "下载任务已创建",
            "progress_url": f"/progress/{task_id}"
        }
        print(f"🔍 [DEBUG] 立即返回响应: {task_id}")
        return response
        
    except Exception as e:
        print(f"❌ [DEBUG] 异常: {str(e)}")
        raise HTTPException(status_code=400, detail=f"任务创建失败: {str(e)}")

def download_video_task_sync(url: str, request_dict: dict, temp_video_id: str):
    """后台下载任务 - 使用官方yt_dlp Python库和progress_hooks"""
    current_thread = threading.current_thread()
    
    try:
        print(f"🎯 [BACKGROUND] 后台任务开始: {temp_video_id} (thread: {current_thread.name})")
        
        # 设置代理
        setup_proxy_env(url)
        print(f"🎯 [BACKGROUND] 代理设置完成")
        
        # 更新状态：正在获取视频信息
        current_progress = download_progress[temp_video_id]
        download_progress[temp_video_id] = {
            **current_progress,
            'status': 'extracting_info',
            'message': '正在获取视频信息...',
            'timestamp': time.time()
        }
        
        # 快速获取视频信息（标题等）
        ydl_opts_info = get_ydl_opts({'quiet': True, 'no_warnings': True})
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
            real_video_id = info.get('id', temp_video_id)
            title = info.get('title', 'video')
            
            # 检查可用格式
            formats = info.get('formats', [])
            valid_formats = [f for f in formats if f.get('ext') not in ['mhtml', 'html', 'json']]
            
            if not valid_formats:
                download_progress[temp_video_id] = {
                    **download_progress[temp_video_id],
                    'status': 'failed',
                    'error': '该视频没有可下载的视频格式',
                    'timestamp': time.time()
                }
                return
        
        # 清理文件名
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
        
        # 智能选择格式
        download_format = request_dict.get('format', 'best')
        if download_format == "best":
            download_format = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
        elif download_format == "bestaudio":
            download_format = "ba[ext=m4a]/ba"
        
        # 🎯 设置唯一输出模板 - 加入task_id确保每次下载都有唯一文件名
        if request_dict.get('extract_audio', False):
            ext = request_dict.get('audio_format', 'mp3')
            output_template = f"{safe_title}_{temp_video_id}.%(ext)s"
        else:
            ext = "mp4"
            output_template = f"{safe_title}_{temp_video_id}.%(ext)s"
        
        # 更新进度：开始下载
        download_progress[temp_video_id] = {
            **download_progress[temp_video_id],
            'status': 'downloading',
            'message': f'正在下载: {title}',
            'title': title,
            'video_id': real_video_id,
            'timestamp': time.time()
        }
        
        # 创建进度回调Hook
        progress_hook = ProgressHook(temp_video_id)
        
        # 构建yt-dlp选项
        ydl_opts = get_ydl_opts({
            'format': download_format,
            'outtmpl': str(DOWNLOAD_DIR / output_template),
            'progress_hooks': [progress_hook],  # 🎯 使用官方progress_hooks
            'quiet': False,  # 允许进度显示
            'no_warnings': False
        })
        
        # 如果请求提取音频
        if request_dict.get('extract_audio', False):
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': request_dict.get('audio_format', 'mp3'),
                'preferredquality': '192',
            }]
        
        # 如果请求下载字幕
        if request_dict.get('write_subs', False):
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            ydl_opts['subtitleslangs'] = [request_dict.get('sub_langs', 'en')]
        
        # 如果请求下载指定时间段
        if request_dict.get('download_sections'):
            ydl_opts['download_sections'] = request_dict['download_sections']
        
        print(f"🎯 [DEBUG] 开始yt-dlp下载，使用progress_hooks")
        
        # 🎯 使用官方yt_dlp库下载
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        
        print(f"🎯 [DEBUG] yt-dlp下载完成: {temp_video_id}")
        
        # 🎯 查找下载的文件 - 使用包含task_id的唯一文件名
        final_filename = f"{safe_title}_{temp_video_id}.{ext}"
        final_path = DOWNLOAD_DIR / final_filename
        
        if not final_path.exists():
            # 查找实际下载的文件（按task_id匹配）
            for file in DOWNLOAD_DIR.glob(f"*{temp_video_id}*.{ext}"):
                if file.exists():
                    final_path = file
                    final_filename = file.name
                    break
        
        if final_path.exists():
            download_progress[temp_video_id] = {
                **download_progress[temp_video_id],
                'status': 'completed',
                'message': f'下载完成: {title}',
                'title': title,
                'video_id': real_video_id,
                'filename': final_filename,
                'file_size': final_path.stat().st_size,
                'download_url': f"/download-direct/{temp_video_id}?filename={final_filename}",
                'timestamp': time.time()
            }
        else:
            download_progress[temp_video_id] = {
                **download_progress[temp_video_id],
                'status': 'failed',
                'message': '下载失败: 找不到下载文件',
                'error': '下载完成但找不到文件',
                'timestamp': time.time()
            }
                
    except Exception as e:
        download_progress[temp_video_id] = {
            **download_progress.get(temp_video_id, {}),
            'status': 'failed',
            'message': f'下载失败: {str(e)}',
            'error': str(e),
            'timestamp': time.time()
        }
    finally:
        # 清理线程引用
        active_download_threads.discard(current_thread)
        print(f"🎯 [BACKGROUND] 任务结束，清理线程: {temp_video_id} (thread: {current_thread.name})")

@app.get("/progress/{video_id}")
async def get_download_progress(video_id: str):
    """获取下载进度"""
    if video_id not in download_progress:
        raise HTTPException(status_code=404, detail="未找到该视频的下载任务")
    
    progress = download_progress[video_id]
    return {
        "video_id": video_id,
        **progress
    }

@app.get("/download/{video_id}")
async def download_file(
    video_id: str, 
    filename: str = Query(..., description="文件名"),
    stream: bool = Query(True, description="是否流式传输")  # 默认改为True
):
    """下载文件 - 优化为适合n8n等HTTP客户端"""
    try:
        file_path = DOWNLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 获取文件大小
        file_size = file_path.stat().st_size
        
        if stream:
            # 改进的流式传输 - 适合n8n等HTTP客户端
            async def iterfile():
                chunk_size = 8192  # 8KB chunks for better streaming
                async with aiofiles.open(file_path, mode="rb") as file_like:
                    while chunk := await file_like.read(chunk_size):
                        yield chunk
            
            # 设置适合n8n的响应头
            headers = {
                "Content-Disposition": f'attachment; filename*=utf-8\'\'{filename}',
                "Content-Length": str(file_size),
                "Accept-Ranges": "bytes",
                "Cache-Control": "no-cache",
                "Connection": "keep-alive"
            }
            
            return StreamingResponse(
                iterfile(),
                media_type="application/octet-stream",
                headers=headers
            )
        else:
            # 直接文件响应 - 保持向后兼容
            return FileResponse(
                path=file_path,
                filename=filename,
                media_type="application/octet-stream"
            )
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件下载失败: {str(e)}")

@app.get("/download-binary/{video_id}")
async def download_binary_for_n8n(
    video_id: str, 
    filename: str = Query(..., description="文件名")
):
    """专门为n8n等HTTP客户端优化的二进制文件下载端点"""
    try:
        file_path = DOWNLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 获取文件大小和最后修改时间
        file_stat = file_path.stat()
        file_size = file_stat.st_size
        last_modified = datetime.fromtimestamp(file_stat.st_mtime).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # 小块流式传输，避免内存问题
        async def generate_file_chunks():
            chunk_size = 4096  # 4KB chunks - 更小的块大小
            try:
                async with aiofiles.open(file_path, mode="rb") as file_obj:
                    while True:
                        chunk = await file_obj.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk
            except Exception as e:
                print(f"🔴 文件流传输错误: {e}")
                raise
        
        # 为n8n优化的响应头
        headers = {
            "Content-Type": "application/octet-stream",
            "Content-Disposition": f'attachment; filename*=utf-8\'\'{filename}',
            "Content-Length": str(file_size),
            "Content-Transfer-Encoding": "binary",
            "Accept-Ranges": "bytes",
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "Last-Modified": last_modified,
            # ETag for caching
            "ETag": f'"{hashlib.md5(str(file_size).encode() + str(file_stat.st_mtime).encode()).hexdigest()}"'
        }
        
        return StreamingResponse(
            generate_file_chunks(),
            status_code=200,
            headers=headers,
            media_type="application/octet-stream"
        )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"🔴 下载端点错误: {e}")
        raise HTTPException(status_code=500, detail=f"文件下载失败: {str(e)}")

@app.get("/download-range/{video_id}")
async def download_with_range_support(
    video_id: str, 
    filename: str = Query(..., description="文件名"),
    range_header: Optional[str] = Header(None, alias="Range")
):
    """支持HTTP Range请求的下载端点 - 解决n8n大文件问题"""
    try:
        file_path = DOWNLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 获取文件信息
        file_stat = file_path.stat()
        file_size = file_stat.st_size
        last_modified = datetime.fromtimestamp(file_stat.st_mtime).strftime('%a, %d %b %Y %H:%M:%S GMT')
        
        # 解析Range请求
        start = 0
        end = file_size - 1
        
        if range_header:
            # 解析 "bytes=start-end" 格式
            try:
                range_match = re.match(r'bytes=(\d+)-(\d*)', range_header)
                if range_match:
                    start = int(range_match.group(1))
                    if range_match.group(2):
                        end = int(range_match.group(2))
                    else:
                        end = file_size - 1
                    
                    # 确保范围有效
                    start = max(0, min(start, file_size - 1))
                    end = max(start, min(end, file_size - 1))
            except ValueError:
                pass
        
        # 计算内容长度
        content_length = end - start + 1
        
        # 分块流式传输
        async def generate_range_chunks():
            chunk_size = 8192  # 8KB chunks
            current_pos = start
            
            async with aiofiles.open(file_path, mode="rb") as file_obj:
                await file_obj.seek(start)
                
                while current_pos <= end:
                    remaining = end - current_pos + 1
                    read_size = min(chunk_size, remaining)
                    
                    chunk = await file_obj.read(read_size)
                    if not chunk:
                        break
                        
                    current_pos += len(chunk)
                    yield chunk
        
        # 设置响应头
        headers = {
            "Content-Type": "application/octet-stream",
            "Accept-Ranges": "bytes",
            "Content-Length": str(content_length),
            "Last-Modified": last_modified,
            "ETag": f'"{hashlib.md5(str(file_size).encode() + str(file_stat.st_mtime).encode()).hexdigest()}"',
            "Cache-Control": "public, max-age=3600",
        }
        
        # 如果是Range请求，返回206 Partial Content
        if range_header:
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
            status_code = 206
        else:
            headers["Content-Disposition"] = f'attachment; filename*=utf-8\'\'{filename}'
            status_code = 200
        
        return StreamingResponse(
            generate_range_chunks(),
            status_code=status_code,
            headers=headers,
            media_type="application/octet-stream"
        )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"🔴 Range下载端点错误: {e}")
        raise HTTPException(status_code=500, detail=f"Range下载失败: {str(e)}")

@app.get("/download-direct/{video_id}")
async def download_direct_link(
    video_id: str, 
    filename: str = Query(..., description="文件名")
):
    """直接文件下载链接 - 绕过n8n二进制处理限制"""
    try:
        file_path = DOWNLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        # 对于n8n，返回一个重定向到实际文件或者文件信息
        file_stat = file_path.stat()
        file_size = file_stat.st_size
        
        # 如果文件太大（超过100MB），建议使用外部下载
        if file_size > 100 * 1024 * 1024:
            return JSONResponse({
                "status": "file_too_large_for_n8n",
                "file_size": file_size,
                "file_size_mb": round(file_size / (1024 * 1024), 2),
                "message": "文件过大，建议使用外部下载工具",
                "download_url": f"/download-range/{video_id}?filename={filename}",
                "direct_url": f"http://localhost:8018/download-range/{video_id}?filename={filename}",
                "suggestion": "请使用wget、curl或浏览器直接下载"
            })
        
        # 小文件直接返回
        return FileResponse(
            path=file_path,
            filename=filename,
            media_type="application/octet-stream"
        )
            
    except HTTPException:
        raise
    except Exception as e:
        print(f"🔴 直接下载端点错误: {e}")
        raise HTTPException(status_code=500, detail=f"直接下载失败: {str(e)}")

@app.delete("/cleanup")
async def cleanup_files():
    """清理临时文件"""
    try:
        count = 0
        for file in DOWNLOAD_DIR.glob("*"):
            if file.is_file():
                file.unlink()
                count += 1
        
        # 清理进度记录
        download_progress.clear()
        
        return {"message": f"清理了 {count} 个临时文件", "cleared_progress": True}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"清理失败: {str(e)}")

@app.get("/supported-sites")
async def get_supported_sites():
    """获取支持的网站列表"""
    try:
        # 使用yt_dlp的list_extractors函数
        extractors = yt_dlp.list_extractors()
        return {
            "supported_sites": extractors,
            "count": len(extractors),
            "popular_sites": [
                "youtube", "bilibili", "vimeo", "dailymotion", 
                "twitch", "instagram", "tiktok", "twitter"
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取支持网站列表失败: {str(e)}")

@app.get("/stats")
async def get_stats():
    """获取服务统计信息"""
    try:
        download_files = list(DOWNLOAD_DIR.glob("*"))
        total_size = sum(f.stat().st_size for f in download_files if f.is_file())
        
        return {
            "download_files_count": len(download_files),
            "download_dir_size_bytes": total_size,
            "download_dir_size_mb": round(total_size / (1024 * 1024), 2),
            "active_downloads": len([p for p in download_progress.values() if p.get('status') == 'downloading']),
            "completed_downloads": len([p for p in download_progress.values() if p.get('status') == 'completed']),
            "failed_downloads": len([p for p in download_progress.values() if p.get('status') == 'failed']),
            "active_threads": len(active_download_threads),
            "thread_names": [t.name for t in active_download_threads if t.is_alive()]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

@app.post("/stop-downloads")
async def stop_all_downloads():
    """停止所有活跃的下载任务"""
    try:
        thread_count = len(active_download_threads)
        cleanup_download_threads()
        return {
            "message": f"已停止 {thread_count} 个下载任务",
            "stopped_threads": thread_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"停止下载任务失败: {str(e)}")

def cleanup_download_threads():
    """清理所有活跃的下载线程"""
    if active_download_threads:
        print(f"🧹 正在清理 {len(active_download_threads)} 个活跃的下载线程...")
        
        # 等待所有线程完成，最多等待5秒
        for thread in list(active_download_threads):
            if thread.is_alive():
                print(f"⏳ 等待线程结束: {thread.name}")
                thread.join(timeout=5)  # 最多等待5秒
                
                if thread.is_alive():
                    print(f"⚠️  线程 {thread.name} 未能正常结束")
                else:
                    print(f"✅ 线程 {thread.name} 已结束")
        
        active_download_threads.clear()
        print("🧹 线程清理完成")

def signal_handler(signum, frame):
    """信号处理器：优雅关闭"""
    print(f"\n🛑 收到停止信号 ({signum})，正在优雅关闭...")
    cleanup_download_threads()
    print("👋 服务器已停止")
    exit(0)

if __name__ == "__main__":
    import uvicorn
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)   # Ctrl+C
    signal.signal(signal.SIGTERM, signal_handler)  # 终止信号
    
    # 从环境变量读取服务器配置
    host = os.getenv('SERVER_HOST', '0.0.0.0')
    port = int(os.getenv('SERVER_PORT', '8018'))
    
    print(f"🚀 启动服务器: {host}:{port}")
    if HTTP_PROXY and HTTPS_PROXY:
        print(f"🌐 代理配置: HTTP={HTTP_PROXY}, HTTPS={HTTPS_PROXY}")
        print(f"📡 代理域名: {', '.join(PROXY_DOMAINS)}")
    else:
        print("🔗 直连模式 (未配置代理)")
    
    if COOKIES_FILE and os.path.exists(COOKIES_FILE):
        print(f"🍪 Cookies配置: 使用cookies文件 {COOKIES_FILE}")
    elif COOKIES_BROWSER:
        print(f"🍪 Cookies配置: 使用{COOKIES_BROWSER}浏览器cookies")
    else:
        print("🚫 未配置cookies")
    
    print("💡 提示: 使用 Ctrl+C 优雅停止服务器和所有下载任务")
    
    try:
        uvicorn.run(app, host=host, port=port)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)
    finally:
        cleanup_download_threads() 

# 修复进度信息保留问题 - 2024-07-26 