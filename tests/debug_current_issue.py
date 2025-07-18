#!/usr/bin/env python3
"""快速诊断当前问题"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.downloader import DownloaderService
from app.services.validation import URLValidator

def test_current_issue():
    """测试当前问题"""
    print("🔍 诊断当前问题...")
    
    # 测试URLs
    test_urls = [
        ("Bilibili", "https://www.bilibili.com/video/BV11g411F7Fp/"),
        ("YouTube", "https://www.youtube.com/watch?v=CoQ4mPp5qAw"),
        ("YouTube Simple", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
    ]
    
    print("\n1. 测试URL验证...")
    validator = URLValidator()
    
    for name, url in test_urls:
        try:
            is_valid, platform, error = validator.validate_url(url)
            print(f"  {name}: ✅ 有效={is_valid}, 平台={platform}")
        except Exception as e:
            print(f"  {name}: ❌ 验证失败: {e}")
    
    print("\n2. 测试视频信息获取...")
    downloader = DownloaderService()
    
    for name, url in test_urls:
        print(f"\n测试 {name}: {url}")
        try:
            info = downloader.get_video_info(url)
            print(f"  ✅ 成功: {info.get('title', 'N/A')}")
        except Exception as e:
            print(f"  ❌ 失败: {e}")
            # 显示详细错误
            import traceback
            traceback.print_exc()
            print()

def test_proxy_status():
    """测试代理状态"""
    print("\n3. 检查代理状态...")
    
    import os
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy']
    
    for var in proxy_vars:
        value = os.environ.get(var)
        print(f"  {var}: {value}")
    
    # 检测实际使用的代理
    proxy_url = (os.environ.get('HTTP_PROXY') or 
                os.environ.get('http_proxy') or 
                os.environ.get('HTTPS_PROXY') or 
                os.environ.get('https_proxy'))
    
    print(f"  实际检测到的代理: {proxy_url}")

if __name__ == "__main__":
    print("🌌 快速诊断")
    print("=" * 50)
    
    test_proxy_status()
    test_current_issue()
    
    print("\n" + "=" * 50)
    print("诊断完成！")