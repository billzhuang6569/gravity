from pydantic import BaseModel, HttpUrl, validator
from typing import Optional, List, Dict, Any
from enum import Enum

class DownloadMode(str, Enum):
    """下载模式枚举"""
    STREAM = "stream"  # 返回二进制流
    LINK = "link"      # 返回下载链接
    BOTH = "both"      # 同时支持两种模式

class ProxyType(str, Enum):
    """代理类型枚举"""
    HTTP = "http"
    SOCKS5 = "socks5"
    EXTRACTOR = "extractor"  # 仅提取时使用的代理

class DownloadRequest(BaseModel):
    """下载请求模型"""
    url: HttpUrl
    mode: DownloadMode = DownloadMode.STREAM
    
    # 格式和质量控制
    format: Optional[str] = None           # -F, --format: 视频格式ID
    quality: Optional[str] = None          # 兼容性保留
    no_merge: Optional[bool] = False       # --no-merge: 不合并视频片段
    playlist: Optional[bool] = False       # -l, --playlist: 下载播放列表
    
    # 输出控制
    output_filename: Optional[str] = None  # -O, --output-filename: 输出文件名
    prefix: Optional[str] = None           # --pre, --prefix: 文件名前缀
    postfix: Optional[bool] = False        # --post, --postfix: 文件名后缀
    force_overwrite: Optional[bool] = False # -f, --force: 强制覆盖
    auto_rename: Optional[bool] = True     # -a, --auto-rename: 自动重命名
    
    # 字幕和标题控制
    no_caption: Optional[bool] = True      # --no-caption: 不下载字幕
    
    # 代理设置
    http_proxy: Optional[str] = None       # -x, --http-proxy: HTTP代理
    socks_proxy: Optional[str] = None      # -s, --socks-proxy: SOCKS5代理
    extractor_proxy: Optional[str] = None  # -y, --extractor-proxy: 提取器代理
    no_proxy: Optional[bool] = False       # --no-proxy: 禁用代理
    
    # 认证和安全
    cookies_file: Optional[str] = None     # -c, --cookies: cookies文件路径
    password: Optional[str] = None         # -P, --password: 访问密码
    insecure: Optional[bool] = False       # -k, --insecure: 忽略SSL错误
    
    # 网络设置
    timeout: Optional[int] = 30            # -t, --timeout: 超时时间(秒)
    
    # 播放列表选项
    first: Optional[int] = None            # --first: 播放列表开始编号
    last: Optional[int] = None             # --last: 播放列表结束编号
    page_size: Optional[int] = None        # --size, --page-size: 页面大小
    
    # 高级选项
    m3u8: Optional[bool] = False           # -m, --m3u8: 使用m3u8下载
    debug: Optional[bool] = False          # -d, --debug: 调试模式
    
    @validator('url')
    def validate_url_length(cls, v):
        if len(str(v)) > 2048:
            raise ValueError('URL长度不能超过2048字符')
        return v
    
    @validator('http_proxy', 'socks_proxy', 'extractor_proxy')
    def validate_proxy_format(cls, v):
        if v and ':' not in v:
            raise ValueError('代理格式应为 HOST:PORT 或 USERNAME:PASSWORD@HOST:PORT')
        return v

class VideoInfo(BaseModel):
    """视频信息模型"""
    title: str
    url: str
    size: Optional[int] = None
    duration: Optional[str] = None
    format: Optional[str] = None
    quality: Optional[str] = None
    thumbnail: Optional[str] = None
    site: Optional[str] = None
    formats_available: Optional[List[Dict]] = None  # 可用格式列表

class DownloadResponse(BaseModel):
    """下载响应模型"""
    success: bool
    message: str
    video_info: Optional[VideoInfo] = None
    download_url: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    proxy_used: Optional[str] = None       # 使用的代理信息
    download_options: Optional[Dict] = None # 使用的下载选项

class ErrorResponse(BaseModel):
    """错误响应模型"""
    success: bool = False
    error: str
    detail: Optional[str] = None

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    app_name: str
    version: str
    uptime: float 