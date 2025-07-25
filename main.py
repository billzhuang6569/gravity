import os
import tempfile
import asyncio
import json
import time
from typing import Optional, List, Dict, Any, Union
from pathlib import Path
from datetime import datetime

import yt_dlp
from fastapi import FastAPI, HTTPException, Query, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, HttpUrl, field_validator
import aiofiles

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

# 创建临时目录用于存储下载的文件
TEMP_DIR = Path(tempfile.gettempdir()) / "ytdlp_api"
TEMP_DIR.mkdir(exist_ok=True)

# 存储下载进度
download_progress = {}

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
    def __init__(self, video_id: str):
        self.video_id = video_id
        
    def __call__(self, d):
        if d['status'] == 'downloading':
            download_progress[self.video_id] = {
                'status': 'downloading',
                'progress': d.get('_percent_str', '0%'),
                'speed': d.get('_speed_str', 'N/A'),
                'eta': d.get('_eta_str', 'N/A'),
                'filename': d.get('filename', ''),
                'timestamp': time.time()
            }
        elif d['status'] == 'finished':
            download_progress[self.video_id] = {
                'status': 'completed',
                'filename': d.get('filename', ''),
                'timestamp': time.time()
            }

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
        "temp_dir": str(TEMP_DIR),
        "temp_dir_exists": TEMP_DIR.exists()
    }

@app.get("/info")
async def get_video_info(url: str = Query(..., description="视频URL")):
    """获取视频信息"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
        }
        
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
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            sanitized_info = ydl.sanitize_info(info)
            
            formats = sanitized_info.get('formats', [])
            
            # 简化格式信息并按质量排序
            simplified_formats = []
            for fmt in formats:
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
async def download_video(request: DownloadRequest, background_tasks: BackgroundTasks):
    """下载视频"""
    try:
        # 先获取视频信息
        ydl_opts_info = {'quiet': True, 'no_warnings': True}
        with yt_dlp.YoutubeDL(ydl_opts_info) as ydl:
            info = ydl.extract_info(str(request.url), download=False)
            video_id = info.get('id', 'unknown')
            title = info.get('title', 'video')
            
            # 清理文件名中的非法字符
            safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).rstrip()
            
            # 设置输出模板
            if request.extract_audio:
                ext = request.audio_format
                output_template = f"{safe_title}.%(ext)s"
            else:
                ext = info.get('ext', 'mp4')
                output_template = f"{safe_title}.%(ext)s"
            
            # 创建下载选项
            ydl_opts = {
                'format': request.format,
                'outtmpl': str(TEMP_DIR / output_template),
                'quiet': True,
                'no_warnings': True,
                'progress_hooks': [ProgressHook(video_id)],
            }
            
            # 如果请求提取音频
            if request.extract_audio:
                ydl_opts['postprocessors'] = [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': request.audio_format,
                }]
            
            # 如果请求下载字幕
            if request.write_subs:
                ydl_opts['writesubtitles'] = True
                ydl_opts['writeautomaticsub'] = True
                ydl_opts['subtitleslangs'] = [request.sub_langs]
            
            # 如果请求下载指定时间段
            if request.download_sections:
                ydl_opts['download_sections'] = request.download_sections
            
            # 初始化下载进度
            download_progress[video_id] = {
                'status': 'starting',
                'timestamp': time.time()
            }
            
            # 在后台执行下载
            background_tasks.add_task(download_video_task, str(request.url), ydl_opts, video_id, safe_title, ext)
            
            return {
                "status": "started",
                "video_id": video_id,
                "title": title,
                "message": "下载已开始，请使用 /progress/{video_id} 查看进度",
                "progress_url": f"/progress/{video_id}"
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"下载失败: {str(e)}")

async def download_video_task(url: str, ydl_opts: dict, video_id: str, title: str, ext: str):
    """后台下载任务"""
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
            
            # 查找下载的文件
            final_filename = f"{title}.{ext}"
            final_path = TEMP_DIR / final_filename
            
            if not final_path.exists():
                # 查找实际下载的文件
                for file in TEMP_DIR.glob(f"*{ext}"):
                    if file.exists():
                        final_path = file
                        final_filename = file.name
                        break
            
            if final_path.exists():
                download_progress[video_id] = {
                    'status': 'completed',
                    'filename': final_filename,
                    'file_size': final_path.stat().st_size,
                    'download_url': f"/download/{video_id}?filename={final_filename}",
                    'timestamp': time.time()
                }
            else:
                download_progress[video_id] = {
                    'status': 'failed',
                    'error': '文件未找到',
                    'timestamp': time.time()
                }
                
    except Exception as e:
        download_progress[video_id] = {
            'status': 'failed',
            'error': str(e),
            'timestamp': time.time()
        }

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
        file_path = TEMP_DIR / filename
        
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
        for file in TEMP_DIR.glob("*"):
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
        temp_files = list(TEMP_DIR.glob("*"))
        total_size = sum(f.stat().st_size for f in temp_files if f.is_file())
        
        return {
            "temp_files_count": len(temp_files),
            "temp_dir_size_bytes": total_size,
            "temp_dir_size_mb": round(total_size / (1024 * 1024), 2),
            "active_downloads": len([p for p in download_progress.values() if p.get('status') == 'downloading']),
            "completed_downloads": len([p for p in download_progress.values() if p.get('status') == 'completed']),
            "failed_downloads": len([p for p in download_progress.values() if p.get('status') == 'failed'])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取统计信息失败: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 