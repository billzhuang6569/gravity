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
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
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

class ProgressMonitor:
    """基于文件大小监控和定时器的进度跟踪系统"""
    
    def __init__(self, task_id: str, expected_size: int = None):
        self.task_id = task_id
        self.expected_size = expected_size
        self.monitor_thread = None
        self.stop_monitoring = False
        self.download_file_path = None
        self.start_time = time.time()
        self.last_size = 0
        self.last_update_time = time.time()
        self.speed_samples = []
        
    def start_monitoring(self, file_path: Path):
        """开始监控下载进度"""
        self.download_file_path = file_path
        self.stop_monitoring = False
        
        def monitor_progress():
            print(f"🔧 [ProgressMonitor] 开始监控: {self.task_id} -> {file_path}")
            while not self.stop_monitoring:
                try:
                    if file_path.exists():
                        current_size = file_path.stat().st_size
                        current_time = time.time()
                        
                        # 计算下载速度
                        if self.last_size > 0 and hasattr(self, 'last_update_time'):
                            time_diff = current_time - self.last_update_time
                            size_diff = current_size - self.last_size
                            if time_diff > 0 and size_diff > 0:
                                speed_bps = size_diff / time_diff
                                self.speed_samples.append(speed_bps)
                                # 保持最近10个样本
                                if len(self.speed_samples) > 10:
                                    self.speed_samples.pop(0)
                        elif self.last_size == 0 and current_size > 0:
                            # 第一次检测到文件，初始化
                            elapsed_time = current_time - self.start_time
                            if elapsed_time > 0:
                                initial_speed = current_size / elapsed_time
                                self.speed_samples.append(initial_speed)
                        
                        # 计算平均速度
                        avg_speed = sum(self.speed_samples) / len(self.speed_samples) if self.speed_samples else 0
                        
                        # 格式化速度
                        if avg_speed > 1024 * 1024:
                            speed_str = f"{avg_speed / (1024 * 1024):.1f}MB/s"
                        elif avg_speed > 1024:
                            speed_str = f"{avg_speed / 1024:.1f}KB/s"
                        else:
                            speed_str = f"{avg_speed:.0f}B/s"
                        
                        # 动态调整预期大小 - 如果实际大小超过预期，调整预期大小
                        if self.expected_size and current_size > self.expected_size:
                            # 预期大小明显不准确，根据当前进度动态调整
                            if current_size > self.expected_size * 1.2:  # 超出20%以上才调整
                                old_expected = self.expected_size
                                # 估算最终大小：假设当前是80%进度
                                self.expected_size = int(current_size / 0.8)
                                print(f"🔧 [ProgressMonitor] 动态调整预期大小: {old_expected} -> {self.expected_size} bytes ({self.expected_size / (1024*1024):.1f}MB)")
                        
                        # 计算进度
                        if self.expected_size and self.expected_size > 0:
                            progress_decimal = min(current_size / self.expected_size, 1.0)
                            progress_percentage = progress_decimal * 100
                            
                            # 计算ETA
                            if avg_speed > 0 and current_size < self.expected_size:
                                remaining_bytes = self.expected_size - current_size
                                eta_seconds = remaining_bytes / avg_speed
                                eta_str = f"{int(eta_seconds // 60):02d}:{int(eta_seconds % 60):02d}"
                            else:
                                eta_str = "未知"
                        else:
                            progress_decimal = 0.0
                            progress_percentage = 0.0
                            eta_str = "未知"
                        
                        # 更新progress信息
                        current_info = download_progress.get(self.task_id, {})
                        download_progress[self.task_id] = {
                            **current_info,
                            'status': 'downloading',
                            'progress_decimal': round(progress_decimal, 4),
                            'progress_percentage': round(progress_percentage, 2),
                            'speed': speed_str,
                            'eta': eta_str,
                            'downloaded_bytes': current_size,
                            'total_bytes': self.expected_size or 0,
                            'timestamp': current_time
                        }
                        
                        self.last_size = current_size
                        self.last_update_time = current_time
                        
                        print(f"🔧 [ProgressMonitor] 进度更新: {self.task_id} -> {progress_percentage:.1f}% ({speed_str})")
                        
                    time.sleep(2)  # 每2秒更新一次
                except Exception as e:
                    print(f"🔧 [ProgressMonitor] 监控错误: {e}")
                    time.sleep(2)
                    
        self.monitor_thread = threading.Thread(target=monitor_progress, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring_progress(self):
        """停止监控"""
        self.stop_monitoring = True
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=1)
            print(f"🔧 [ProgressMonitor] 停止监控: {self.task_id}")

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
    """后台下载任务"""
    current_thread = threading.current_thread()
    progress_monitor = None
    
    try:
        print(f"🔧 [BACKGROUND] 后台任务开始: {temp_video_id} (thread: {current_thread.name})")
        
        # 设置代理
        setup_proxy_env(url)
        print(f"🔧 [BACKGROUND] 代理设置完成")
        
        # 更新状态：正在获取视频信息（保留已有的详细进度信息）
        current_progress = download_progress[temp_video_id]
        download_progress[temp_video_id] = {
            **current_progress,  # 保留已有信息
            'status': 'extracting_info',
            'message': '正在获取视频信息...'
        }
        
        # 获取视频信息
        ydl_opts_info = get_ydl_opts({'quiet': True, 'no_warnings': True})
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(url, download=False)
            real_video_id = info.get('id', temp_video_id)
            title = info.get('title', 'video')
            
            # 检查可用格式，排除mhtml等非视频格式
            formats = info.get('formats', [])
            valid_formats = [f for f in formats if f.get('ext') not in ['mhtml', 'html', 'json']]
            
            if not valid_formats:
                current_progress = download_progress[temp_video_id]
                download_progress[temp_video_id] = {
                    **current_progress,  # 保留已有的详细进度信息
                    'status': 'failed',
                    'error': '该视频没有可下载的视频格式',
                    'timestamp': time.time()
                }
                return
            
            # 清理文件名中的非法字符
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            
            # 获取预期文件大小用于进度计算
            expected_size = None
            
            # 尝试从所有格式中获取最大的文件大小信息
            print(f"🔧 [DEBUG] 共找到 {len(valid_formats)} 个有效格式")
            max_filesize = 0
            for i, fmt in enumerate(valid_formats):
                fmt_size = fmt.get('filesize') or fmt.get('filesize_approx') or 0
                if fmt_size > max_filesize:
                    max_filesize = fmt_size
                print(f"🔧 [DEBUG] 格式{i}: {fmt.get('format_id', 'unknown')} - 大小: {fmt_size} bytes - 扩展名: {fmt.get('ext', 'unknown')}")
                
            if max_filesize > 0:
                expected_size = max_filesize
                print(f"🔧 [DEBUG] 使用最大格式大小: {expected_size} bytes")
            else:
                # 如果没有找到大小信息，使用改进的估算
                duration = info.get('duration', 0)
                width = info.get('width', 0)
                height = info.get('height', 0)
                
                if duration and width and height:
                    # 根据分辨率估算更合理的码率
                    if width >= 1920:  # 1080p及以上
                        bitrate_kbps = 5000  # 5Mbps
                    elif width >= 1280:  # 720p
                        bitrate_kbps = 2500  # 2.5Mbps
                    elif width >= 854:   # 480p
                        bitrate_kbps = 1200  # 1.2Mbps
                    else:  # 360p及以下
                        bitrate_kbps = 800   # 0.8Mbps
                    
                    expected_size = int(duration * bitrate_kbps * 125)  # 转换为字节 (kbps * 125 = bytes/s)
                    print(f"🔧 [DEBUG] 基于分辨率({width}x{height})和时长({duration}s)估算: {expected_size} bytes (码率: {bitrate_kbps}kbps)")
                elif duration:
                    # 保守估算：使用更高的默认码率
                    expected_size = int(duration * 2000 * 125)  # 2Mbps
                    print(f"🔧 [DEBUG] 基于时长({duration}s)估算: {expected_size} bytes (默认码率: 2Mbps)")
                else:
                    # 最后的备选方案
                    expected_size = 100 * 1024 * 1024  # 100MB
                    print(f"🔧 [DEBUG] 使用默认大小: {expected_size} bytes (100MB)")
                    
            print(f"🔧 [BACKGROUND] 视频信息: {title}, 预期大小: {expected_size} bytes ({expected_size / (1024*1024):.1f}MB)")
            
            # 创建进度监控器
            progress_monitor = ProgressMonitor(temp_video_id, expected_size)
            
            # 智能选择格式
            download_format = request_dict.get('format', 'best')
            if download_format == "best":
                download_format = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
            elif download_format == "bestaudio":
                download_format = "ba[ext=m4a]/ba"
            
            # 设置输出模板
            if request_dict.get('extract_audio', False):
                ext = request_dict.get('audio_format', 'mp3')
                output_template = f"{safe_title}.%(ext)s"
            else:
                ext = "mp4"
                output_template = f"{safe_title}.%(ext)s"
            
            # 更新进度：开始下载（保留已有的详细进度信息）
            current_progress = download_progress[temp_video_id]
            download_progress[temp_video_id] = {
                **current_progress,  # 保留已有信息
                'status': 'downloading',
                'message': f'正在下载: {title}',
                'title': title,
                'video_id': real_video_id
            }
            
            # 计算预期的文件路径
            expected_file_path = DOWNLOAD_DIR / f"{safe_title}.{ext}"
            
            # 启动进度监控
            if progress_monitor:
                progress_monitor.start_monitoring(expected_file_path)
                print(f"🔧 [DEBUG] 进度监控已启动: {temp_video_id} -> {expected_file_path}")
            
            # 创建下载选项 - 使用简化的设置
            ydl_opts = get_ydl_opts({
                'format': download_format,
                'outtmpl': str(DOWNLOAD_DIR / output_template),
                'quiet': True,  # 安静模式，减少输出
                'no_warnings': True,
            })
            
            # 如果请求提取音频
            if request_dict.get('extract_audio', False):
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': request_dict.get('audio_format', 'mp3'),
                }]
            
            # 如果请求下载字幕
            if request_dict.get('write_subs', False):
                ydl_opts['writesubtitles'] = True
                ydl_opts['writeautomaticsub'] = True
                ydl_opts['subtitleslangs'] = [request_dict.get('sub_langs', 'en')]
            
            # 如果请求下载指定时间段
            if request_dict.get('download_sections'):
                ydl_opts['download_sections'] = request_dict['download_sections']
        
        # 执行下载
        print(f"🔧 [DEBUG] 开始下载，进度监控已启动: {temp_video_id}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"🔧 [DEBUG] 下载完成: {temp_video_id}")
        
        # 停止进度监控
        if progress_monitor:
            progress_monitor.stop_monitoring_progress()
        
        # 查找下载的文件
        final_filename = f"{safe_title}.{ext}"
        final_path = DOWNLOAD_DIR / final_filename
        
        if not final_path.exists():
            # 查找实际下载的文件
            for file in DOWNLOAD_DIR.glob(f"*{ext}"):
                if file.exists():
                    final_path = file
                    final_filename = file.name
                    break
        
        if final_path.exists():
            current_progress = download_progress[temp_video_id]
            download_progress[temp_video_id] = {
                **current_progress,  # 保留已有的详细进度信息
                'status': 'completed',
                'title': title,
                'video_id': real_video_id,
                'filename': final_filename,
                'file_size': final_path.stat().st_size,
                'download_url': f"/download/{temp_video_id}?filename={final_filename}",
                'timestamp': time.time()
            }
        else:
            current_progress = download_progress[temp_video_id]
            download_progress[temp_video_id] = {
                **current_progress,  # 保留已有的详细进度信息
                'status': 'failed',
                'error': '下载完成但找不到文件',
                'timestamp': time.time()
            }
                
    except Exception as e:
        current_progress = download_progress.get(temp_video_id, {})
        download_progress[temp_video_id] = {
            **current_progress,  # 保留已有的详细进度信息
            'status': 'failed',
            'error': str(e),
            'timestamp': time.time()
        }
    finally:
        # 确保停止进度监控
        if progress_monitor:
            progress_monitor.stop_monitoring_progress()
        # 清理线程引用
        active_download_threads.discard(current_thread)
        print(f"🔧 [BACKGROUND] 任务结束，清理线程: {temp_video_id} (thread: {current_thread.name})")

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
    stream: bool = Query(False, description="是否流式传输")
):
    """下载文件"""
    try:
        file_path = DOWNLOAD_DIR / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if stream:
            # 流式传输
            def iterfile():
                with open(file_path, mode="rb") as file_like:
                    yield from file_like
            
            return StreamingResponse(
                iterfile(),
                media_type="application/octet-stream",
                headers={"Content-Disposition": f"attachment; filename={filename}"}
            )
        else:
            # 直接文件响应
            return FileResponse(
                path=file_path,
                filename=filename,
                media_type="application/octet-stream"
            )
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"文件下载失败: {str(e)}")

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