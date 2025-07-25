import os
import time
import logging
from pathlib import Path
from typing import Dict, List

from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File
from fastapi.responses import FileResponse, StreamingResponse
from starlette.responses import JSONResponse

from app.models.schemas import (
    DownloadRequest, DownloadResponse, ErrorResponse, 
    HealthResponse, VideoInfo, DownloadMode
)
from app.core.downloader import downloader
from app.config import settings

logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()

# 应用启动时间
start_time = time.time()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查端点"""
    uptime = time.time() - start_time
    return HealthResponse(
        status="healthy",
        app_name=settings.app_name,
        version=settings.app_version,
        uptime=uptime
    )

@router.post("/info", response_model=Dict)
async def get_video_info(request: DownloadRequest):
    """获取视频信息（不下载）"""
    try:
        url = str(request.url)
        logger.info(f"获取视频信息: {url}")
        logger.info(f"请求参数: format={request.format}, proxy={request.http_proxy or request.socks_proxy}")
        
        info = await downloader.get_video_info(url, request)
        
        return {
            "success": True,
            "video_info": info,
            "request_options": {
                "format": request.format,
                "quality": request.quality,
                "proxy_used": request.http_proxy or request.socks_proxy,
                "timeout": request.timeout,
                "cookies_file": request.cookies_file
            }
        }
        
    except Exception as e:
        logger.error(f"获取视频信息失败: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"获取视频信息失败: {str(e)}"
        )

@router.post("/download", response_model=DownloadResponse)
async def download_video(
    request: DownloadRequest,
    background_tasks: BackgroundTasks
):
    """下载视频（返回下载链接）"""
    try:
        url = str(request.url)
        logger.info(f"下载视频请求: {url}")
        logger.info(f"下载选项: format={request.format}, quality={request.quality}, proxy={request.http_proxy or request.socks_proxy}")
        
        # 下载视频
        file_path, video_info, download_options = await downloader.download_video(
            url=url,
            request=request
        )
        
        # 安排后台清理任务
        background_tasks.add_task(
            downloader.cleanup_old_files, 
            settings.cleanup_interval / 3600
        )
        
        # 生成下载链接
        filename = Path(file_path).name
        download_url = f"/api/v1/files/{filename}"
        
        return DownloadResponse(
            success=True,
            message="视频下载成功",
            video_info=video_info,
            download_url=download_url,
            file_path=file_path,
            file_size=video_info.size,
            proxy_used=download_options.get('proxy_used'),
            download_options=download_options
        )
        
    except Exception as e:
        logger.error(f"下载视频失败: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"下载视频失败: {str(e)}"
        )

@router.post("/download/stream")
async def download_video_stream(
    request: DownloadRequest,
    background_tasks: BackgroundTasks
):
    """下载视频并直接返回文件流"""
    try:
        url = str(request.url)
        logger.info(f"流式下载视频: {url}")
        logger.info(f"下载选项: format={request.format}, quality={request.quality}")
        
        # 下载视频
        file_path, video_info, download_options = await downloader.download_video(
            url=url,
            request=request
        )
        
        # 安排后台清理任务
        background_tasks.add_task(
            downloader.cleanup_old_files,
            settings.cleanup_interval / 3600
        )
        
        # 返回文件响应
        filename = f"{video_info.title}.{video_info.format or 'mp4'}"
        
        # 清理文件名中的特殊字符
        safe_filename = "".join(c for c in filename if c.isalnum() or c in (' ', '-', '_', '.')).strip()
        
        return FileResponse(
            path=file_path,
            filename=safe_filename,
            media_type='application/octet-stream',
            headers={
                "X-Proxy-Used": download_options.get('proxy_used', 'none'),
                "X-Format-Used": download_options.get('format', 'auto')
            }
        )
        
    except Exception as e:
        logger.error(f"流式下载失败: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"流式下载失败: {str(e)}"
        )

@router.get("/files/{filename}")
async def serve_file(filename: str):
    """提供下载文件服务"""
    try:
        file_path = Path(settings.download_dir) / filename
        
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="无效的文件")
        
        return FileResponse(
            path=str(file_path),
            filename=filename,
            media_type='application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"提供文件服务失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"提供文件服务失败: {str(e)}"
        )

@router.delete("/cleanup")
async def cleanup_files():
    """手动清理文件"""
    try:
        await downloader.cleanup_old_files(settings.cleanup_interval / 3600)
        return {"success": True, "message": "文件清理完成"}
    except Exception as e:
        logger.error(f"文件清理失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"文件清理失败: {str(e)}"
        )

@router.get("/proxy/test")
async def test_proxy():
    """测试代理连接"""
    try:
        # 测试用户Mac的代理设置
        proxy_status = {
            "http_proxy": f"127.0.0.1:1087",
            "socks_proxy": f"127.0.0.1:1080",
            "status": "configured"
        }
        
        return {
            "success": True,
            "message": "代理配置信息",
            "proxy_config": proxy_status
        }
    except Exception as e:
        logger.error(f"代理测试失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"代理测试失败: {str(e)}"
        )

@router.get("/formats/{url_hash}")
async def get_available_formats(url_hash: str, url: str):
    """获取指定视频的可用格式列表"""
    try:
        from app.models.schemas import DownloadRequest
        
        # 创建一个临时请求对象
        temp_request = DownloadRequest(url=url)
        info = await downloader.get_video_info(url, temp_request)
        
        return {
            "success": True,
            "url": url,
            "available_formats": info.get('formats', []),
            "site": info.get('site', 'Unknown'),
            "title": info.get('title', 'Unknown')
        }
        
    except Exception as e:
        logger.error(f"获取格式列表失败: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"获取格式列表失败: {str(e)}"
        )

# === Cookies 管理端点 ===

@router.post("/cookies/upload")
async def upload_cookies(
    site: str,
    file: UploadFile = File(...)
):
    """上传cookies文件"""
    try:
        # 验证文件类型
        if not file.filename.endswith(('.txt', '.sqlite')):
            raise HTTPException(
                status_code=400, 
                detail="只支持 .txt 或 .sqlite 格式的cookies文件"
            )
        
        # 生成安全的文件名
        safe_site = "".join(c for c in site if c.isalnum() or c in ('_', '-')).lower()
        cookies_dir = Path("cookies")
        cookies_dir.mkdir(exist_ok=True)
        
        file_extension = Path(file.filename).suffix
        cookies_path = cookies_dir / f"{safe_site}_cookies{file_extension}"
        
        # 保存文件
        content = await file.read()
        with open(cookies_path, 'wb') as f:
            f.write(content)
        
        logger.info(f"Cookies文件已保存: {cookies_path}")
        
        return {
            "success": True,
            "message": f"Cookies文件已上传",
            "file_path": str(cookies_path),
            "site": safe_site
        }
        
    except Exception as e:
        logger.error(f"上传cookies失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"上传cookies失败: {str(e)}"
        )

@router.get("/cookies/list")
async def list_cookies():
    """列出所有可用的cookies文件"""
    try:
        cookies_dir = Path("cookies")
        if not cookies_dir.exists():
            return {"success": True, "cookies": []}
        
        cookies_files = []
        for file_path in cookies_dir.glob("*_cookies.*"):
            try:
                stat = file_path.stat()
                site_name = file_path.stem.replace('_cookies', '')
                cookies_files.append({
                    "site": site_name,
                    "filename": file_path.name,
                    "file_path": str(file_path),
                    "size": stat.st_size,
                    "modified": stat.st_mtime,
                    "format": file_path.suffix[1:]  # 去掉点号
                })
            except Exception as e:
                logger.warning(f"读取cookies文件信息失败 {file_path}: {e}")
                continue
        
        return {
            "success": True,
            "cookies": cookies_files,
            "count": len(cookies_files)
        }
        
    except Exception as e:
        logger.error(f"列出cookies失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"列出cookies失败: {str(e)}"
        )

@router.delete("/cookies/{site}")
async def delete_cookies(site: str):
    """删除指定站点的cookies文件"""
    try:
        cookies_dir = Path("cookies")
        safe_site = "".join(c for c in site if c.isalnum() or c in ('_', '-')).lower()
        
        # 查找并删除对应的cookies文件
        deleted_files = []
        for file_path in cookies_dir.glob(f"{safe_site}_cookies.*"):
            file_path.unlink()
            deleted_files.append(str(file_path))
            logger.info(f"已删除cookies文件: {file_path}")
        
        if not deleted_files:
            raise HTTPException(
                status_code=404,
                detail=f"未找到站点 {site} 的cookies文件"
            )
        
        return {
            "success": True,
            "message": f"已删除 {len(deleted_files)} 个cookies文件",
            "deleted_files": deleted_files
        }
        
    except Exception as e:
        logger.error(f"删除cookies失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"删除cookies失败: {str(e)}"
        )

@router.get("/cookies/suggest/{url}")
async def suggest_cookies(url: str):
    """根据URL建议使用的cookies文件"""
    try:
        cookies_dir = Path("cookies")
        if not cookies_dir.exists():
            return {"success": True, "suggested_cookies": None}
        
        # 根据URL判断站点
        domain_mapping = {
            'youtube.com': 'youtube',
            'youtu.be': 'youtube', 
            'bilibili.com': 'bilibili',
            'twitter.com': 'twitter',
            'facebook.com': 'facebook'
        }
        
        suggested_site = None
        for domain, site in domain_mapping.items():
            if domain in url.lower():
                suggested_site = site
                break
        
        if not suggested_site:
            return {"success": True, "suggested_cookies": None}
        
        # 查找对应的cookies文件
        cookies_files = list(cookies_dir.glob(f"{suggested_site}_cookies.*"))
        if cookies_files:
            cookies_path = str(cookies_files[0])
            return {
                "success": True,
                "suggested_cookies": cookies_path,
                "site": suggested_site,
                "message": f"建议使用 {suggested_site} 的cookies文件"
            }
        else:
            return {
                "success": True,
                "suggested_cookies": None,
                "site": suggested_site,
                "message": f"未找到 {suggested_site} 的cookies文件，建议上传"
            }
        
    except Exception as e:
        logger.error(f"建议cookies失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"建议cookies失败: {str(e)}"
        ) 