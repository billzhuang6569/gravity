#!/usr/bin/env python3
"""测试YouTube超时问题"""

import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.downloader import DownloaderService

def test_youtube_timeout():
    """测试YouTube超时"""
    print("🎬 测试YouTube超时问题...")
    
    # 设置代理
    os.environ['http_proxy'] = 'http://127.0.0.1:1087'
    os.environ['https_proxy'] = 'http://127.0.0.1:1087'
    
    downloader = DownloaderService()
    
    # 测试URLs
    test_urls = [
        ("YouTube原始", "https://www.youtube.com/watch?v=CoQ4mPp5qAw&list=RDCoQ4mPp5qAw&start_radio=1"),
        ("YouTube简化", "https://www.youtube.com/watch?v=CoQ4mPp5qAw"),
        ("YouTube经典", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
    ]
    
    for name, url in test_urls:
        print(f"\n测试 {name}:")
        print(f"URL: {url}")
        
        start_time = time.time()
        try:
            info = downloader.get_video_info(url)
            end_time = time.time()
            print(f"✅ 成功 ({end_time - start_time:.2f}秒): {info.get('title', 'N/A')}")
        except Exception as e:
            end_time = time.time()
            print(f"❌ 失败 ({end_time - start_time:.2f}秒): {e}")
            import traceback
            traceback.print_exc()

def test_with_timeout():
    """测试带超时的yt-dlp"""
    print("\n🔧 测试带超时的yt-dlp...")
    
    import yt_dlp
    
    # 设置代理
    os.environ['http_proxy'] = 'http://127.0.0.1:1087'
    os.environ['https_proxy'] = 'http://127.0.0.1:1087'
    
    proxy_url = os.environ.get('http_proxy')
    
    opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
        'proxy': proxy_url,
        'socket_timeout': 10,  # 10秒超时
        'retries': 3,
    }
    
    url = "https://www.youtube.com/watch?v=CoQ4mPp5qAw&list=RDCoQ4mPp5qAw&start_radio=1"
    
    print(f"测试URL: {url}")
    print(f"代理: {proxy_url}")
    
    start_time = time.time()
    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            end_time = time.time()
            print(f"✅ 成功 ({end_time - start_time:.2f}秒): {info.get('title', 'N/A')}")
    except Exception as e:
        end_time = time.time()
        print(f"❌ 失败 ({end_time - start_time:.2f}秒): {e}")

if __name__ == "__main__":
    print("🌌 YouTube超时测试")
    print("=" * 50)
    
    test_youtube_timeout()
    test_with_timeout()
    
    print("\n" + "=" * 50)
    print("测试完成！")