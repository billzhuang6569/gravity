#!/usr/bin/env python3
"""测试代理设置"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.downloader import DownloaderService

def test_proxy_env():
    """测试代理环境变量"""
    print("🌐 检查代理环境变量...")
    
    http_proxy = os.environ.get('HTTP_PROXY')
    https_proxy = os.environ.get('HTTPS_PROXY')
    http_proxy_lower = os.environ.get('http_proxy')
    https_proxy_lower = os.environ.get('https_proxy')
    
    print(f"HTTP_PROXY: {http_proxy}")
    print(f"HTTPS_PROXY: {https_proxy}")
    print(f"http_proxy: {http_proxy_lower}")
    print(f"https_proxy: {https_proxy_lower}")
    
    # 测试代理检测逻辑
    proxy_url = http_proxy or http_proxy_lower
    print(f"检测到的代理: {proxy_url}")
    
    return proxy_url

def test_youtube_with_proxy():
    """测试YouTube与代理"""
    print("\n🎬 测试YouTube代理...")
    
    # 设置代理
    proxy_url = test_proxy_env()
    
    if not proxy_url:
        print("❌ 未检测到代理设置")
        return
    
    # 测试YouTube URLs
    test_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=1jn_RpbPbEc",
    ]
    
    downloader = DownloaderService()
    
    for url in test_urls:
        print(f"\n测试: {url}")
        try:
            info = downloader.get_video_info(url)
            print(f"✅ 成功: {info.get('title', 'N/A')}")
        except Exception as e:
            print(f"❌ 失败: {e}")
            # 显示详细错误信息
            import traceback
            traceback.print_exc()

def test_yt_dlp_proxy():
    """直接测试yt-dlp代理"""
    print("\n🔧 直接测试yt-dlp代理...")
    
    import yt_dlp
    
    proxy_url = os.environ.get('HTTP_PROXY') or os.environ.get('http_proxy')
    
    if not proxy_url:
        print("❌ 未检测到代理设置")
        return
    
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'proxy': proxy_url,
    }
    
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"✅ yt-dlp代理成功: {info.get('title', 'N/A')}")
    except Exception as e:
        print(f"❌ yt-dlp代理失败: {e}")

if __name__ == "__main__":
    print("🌌 代理测试")
    print("=" * 50)
    
    test_youtube_with_proxy()
    test_yt_dlp_proxy()
    
    print("\n" + "=" * 50)
    print("代理测试完成！")