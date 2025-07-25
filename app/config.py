import os
from pathlib import Path
from typing import List, Optional
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 应用基础配置
    app_name: str = "Video Downloader API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 服务器配置
    host: str = "0.0.0.0"
    port: int = 8000
    
    # 下载配置
    download_dir: str = "./downloads"
    max_file_size: int = 1024 * 1024 * 1024  # 1GB
    cleanup_interval: int = 3600  # 1小时后清理文件
    max_concurrent_downloads: int = 5
    
    # 安全配置
    allowed_domains: Optional[str] = ""  # 改为字符串类型，空字符串表示允许所有域名
    max_url_length: int = 2048
    
    class Config:
        env_file = ".env"
        case_sensitive = False
    
    def get_allowed_domains_list(self) -> List[str]:
        """获取允许的域名列表"""
        if not self.allowed_domains:
            return []  # 空列表表示允许所有域名
        return [domain.strip() for domain in self.allowed_domains.split(",") if domain.strip()]

# 创建全局设置实例
settings = Settings()

# 确保下载目录存在
download_path = Path(settings.download_dir)
download_path.mkdir(exist_ok=True) 