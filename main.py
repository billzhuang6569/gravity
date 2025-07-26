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
import subprocess
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

class YtDlpProgressParser:
    """基于yt-dlp输出解析的进度跟踪系统"""
    
    def __init__(self, task_id: str):
        self.task_id = task_id
        self.process = None
        self.monitor_thread = None
        self.stop_monitoring = False
        
    def parse_progress_line(self, line: str):
        """解析yt-dlp的进度输出行"""
        try:
            # 典型格式: [download]  27.7% of    3.60MiB at    2.09MiB/s ETA 00:01
            if '[download]' not in line:
                return None
                
            # 移除ANSI颜色代码
            clean_line = re.sub(r'\x1b\[[0-9;]*m', '', line).strip()
            
            # 提取百分比
            progress_match = re.search(r'(\d+\.?\d*)%', clean_line)
            progress_percentage = float(progress_match.group(1)) if progress_match else 0.0
            progress_decimal = progress_percentage / 100.0
            
            # 提取文件大小
            size_match = re.search(r'of\s+([0-9.]+)(KiB|MiB|GiB|B)', clean_line)
            total_bytes = 0
            if size_match:
                size_val = float(size_match.group(1))
                size_unit = size_match.group(2)
                if size_unit == 'GiB':
                    total_bytes = int(size_val * 1024 * 1024 * 1024)
                elif size_unit == 'MiB':
                    total_bytes = int(size_val * 1024 * 1024)
                elif size_unit == 'KiB':
                    total_bytes = int(size_val * 1024)
                else:  # B
                    total_bytes = int(size_val)
            
            # 计算已下载字节数
            downloaded_bytes = int(total_bytes * progress_decimal) if total_bytes > 0 else 0
            
            # 提取速度
            speed_match = re.search(r'at\s+([0-9.]+)(KiB/s|MiB/s|GiB/s|B/s)', clean_line)
            speed_str = "0B/s"
            if speed_match:
                speed_val = float(speed_match.group(1))
                speed_unit = speed_match.group(2)
                speed_str = f"{speed_val:.1f}{speed_unit}"
            
            # 提取ETA
            eta_match = re.search(r'ETA\s+(\d{2}:\d{2})', clean_line)
            eta_str = eta_match.group(1) if eta_match else "未知"
            
            return {
                'progress_decimal': round(progress_decimal, 4),
                'progress_percentage': round(progress_percentage, 2),
                'speed': speed_str,
                'eta': eta_str,
                'downloaded_bytes': downloaded_bytes,
                'total_bytes': total_bytes,
                'timestamp': time.time()
            }
            
        except Exception as e:
            print(f"🔧 [YtDlpProgressParser] 解析错误: {e}, 行内容: {line}")
            return None
    
    def start_monitoring(self, process):
        """开始监控yt-dlp进程的输出"""
        self.process = process
        self.stop_monitoring = False
        
        def monitor_output():
            print(f"🔧 [YtDlpProgressParser] 开始监控yt-dlp输出: {self.task_id}")
            line_count = 0
            
            try:
                while not self.stop_monitoring and self.process.poll() is None:
                    # 读取stdout的一行
                    line = self.process.stdout.readline()
                    if not line:
                        print(f"🔧 [YtDlpProgressParser] 读取到空行，退出循环")
                        break
                        
                    line_str = line.decode('utf-8', errors='ignore').strip()
                    line_count += 1
                    
                    # 显示所有输出行用于调试
                    if line_str:
                        print(f"🔧 [YtDlpProgressParser] 第{line_count}行: {line_str}")
                    
                    # 解析进度信息
                    progress_info = self.parse_progress_line(line_str)
                    if progress_info:
                        # 更新progress字典
                        current_info = download_progress.get(self.task_id, {})
                        download_progress[self.task_id] = {
                            **current_info,
                            'status': 'downloading',
                            **progress_info
                        }
                        
                        print(f"🔧 [YtDlpProgressParser] ✅ 进度更新: {self.task_id} -> {progress_info['progress_percentage']}% ({progress_info['speed']})")
                    
                    # 也显示其他重要信息
                    if any(keyword in line_str.lower() for keyword in ['error', 'warning', 'finished']):
                        print(f"🔧 [YtDlpProgressParser] ⚠️ 重要输出: {line_str}")
                        
                print(f"🔧 [YtDlpProgressParser] 监控循环结束，共读取{line_count}行")
                        
            except Exception as e:
                print(f"🔧 [YtDlpProgressParser] ❌ 监控出错: {e}")
                import traceback
                traceback.print_exc()
            finally:
                print(f"🔧 [YtDlpProgressParser] 停止监控: {self.task_id}")
                
        self.monitor_thread = threading.Thread(target=monitor_output, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring_progress(self):
        """停止监控"""
        self.stop_monitoring = True
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=2)
            print(f"🔧 [YtDlpProgressParser] 监控线程已停止: {self.task_id}")

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
    progress_parser = None
    ydl_process = None
    
    try:
        print(f"🔧 [BACKGROUND] 后台任务开始: {temp_video_id} (thread: {current_thread.name})")
        
        # 设置代理
        setup_proxy_env(url)
        print(f"🔧 [BACKGROUND] 代理设置完成")
        
        # 更新状态：正在获取视频信息
        current_progress = download_progress[temp_video_id]
        download_progress[temp_video_id] = {
            **current_progress,
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
        
        # 更新进度：开始下载
        current_progress = download_progress[temp_video_id]
        download_progress[temp_video_id] = {
            **current_progress,
            'status': 'downloading',
            'message': f'正在下载: {title}',
            'title': title,
            'video_id': real_video_id
        }
        
        # 创建进度解析器
        progress_parser = YtDlpProgressParser(temp_video_id)
        
        # 检查yt-dlp是否可用
        try:
            result = subprocess.run(['yt-dlp', '--version'], capture_output=True, text=True, timeout=5)
            print(f"🔧 [DEBUG] yt-dlp版本: {result.stdout.strip()}")
        except Exception as e:
            print(f"🔧 [ERROR] yt-dlp不可用: {e}")
            # 回退到使用python -m yt_dlp
            cmd_args = ['python', '-m', 'yt_dlp']
            print(f"🔧 [DEBUG] 使用python -m yt_dlp")
        else:
            cmd_args = ['yt-dlp']
            print(f"🔧 [DEBUG] 使用yt-dlp命令")
        
        # 基本参数
        cmd_args.extend([
            '--format', download_format,
            '--output', str(DOWNLOAD_DIR / output_template),
            '--no-warnings',
            '--progress'  # 强制显示进度
        ])
        
        # cookies配置
        if COOKIES_FILE and os.path.exists(COOKIES_FILE):
            cmd_args.extend(['--cookies', COOKIES_FILE])
        elif COOKIES_BROWSER:
            cmd_args.extend(['--cookies-from-browser', COOKIES_BROWSER])
        
        # 如果请求提取音频
        if request_dict.get('extract_audio', False):
            cmd_args.extend([
                '--extract-audio',
                '--audio-format', request_dict.get('audio_format', 'mp3')
            ])
        
        # 如果请求下载字幕
        if request_dict.get('write_subs', False):
            cmd_args.extend([
                '--write-subs',
                '--write-auto-subs',
                '--sub-langs', request_dict.get('sub_langs', 'en')
            ])
        
        # 如果请求下载指定时间段
        if request_dict.get('download_sections'):
            cmd_args.extend(['--download-sections', request_dict['download_sections']])
        
        # 添加URL
        cmd_args.append(url)
        
        print(f"🔧 [DEBUG] 执行yt-dlp命令: {' '.join(cmd_args)}")
        
        # 启动yt-dlp进程
        try:
            ydl_process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=False,
                bufsize=1
            )
            print(f"🔧 [DEBUG] yt-dlp进程启动成功，PID: {ydl_process.pid}")
        except Exception as e:
            print(f"🔧 [ERROR] 启动yt-dlp进程失败: {e}")
            raise
        
        # 启动进度监控
        try:
            progress_parser.start_monitoring(ydl_process)
            print(f"🔧 [DEBUG] 进度监控启动成功")
        except Exception as e:
            print(f"🔧 [ERROR] 启动进度监控失败: {e}")
            raise
        
        # 等待进程完成
        return_code = ydl_process.wait()
        
        print(f"🔧 [DEBUG] yt-dlp进程完成，返回码: {return_code}")
        
        # 停止进度监控
        if progress_parser:
            progress_parser.stop_monitoring_progress()
        
        if return_code != 0:
            current_progress = download_progress[temp_video_id]
            download_progress[temp_video_id] = {
                **current_progress,
                'status': 'failed',
                'error': f'yt-dlp下载失败，返回码: {return_code}',
                'timestamp': time.time()
            }
            return
        
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
        if progress_parser:
            progress_parser.stop_monitoring_progress()
        # 确保进程被终止
        if ydl_process and ydl_process.poll() is None:
            ydl_process.terminate()
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