import logging
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from app.config import settings
from app.api.routes import router
from app.core.downloader import downloader

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时执行
    logger.info("启动视频下载API服务...")
    logger.info(f"下载目录: {settings.download_dir}")
    
    # 清理启动时的旧文件
    await downloader.cleanup_old_files(settings.cleanup_interval / 3600)
    
    yield
    
    # 关闭时执行
    logger.info("关闭视频下载API服务...")

# 创建FastAPI应用实例
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="基于you-get的视频下载API服务",
    lifespan=lifespan
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(router, prefix="/api/v1")

# 根路径
@app.get("/")
async def root():
    """根路径，返回API信息"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "基于you-get的视频下载API服务",
        "docs_url": "/docs",
        "health_check": "/api/v1/health"
    }

# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"未处理的异常: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "error": "内部服务器错误",
            "detail": str(exc) if settings.debug else "请联系管理员"
        }
    )

if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    ) 