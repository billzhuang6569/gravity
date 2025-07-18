#!/usr/bin/env python3
"""
直接测试后端API的脚本，绕过网络代理问题
"""

import asyncio
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.downloader import DownloaderService
from app.services.validation import URLValidator
from app.models.schemas import DownloadOptions

async def test_url_validation():
    """测试URL验证"""
    print("🔍 测试URL验证...")
    
    validator = URLValidator()
    
    test_urls = [
        "https://www.bilibili.com/video/BV11g411F7Fp/",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=1jn_RpbPbEc",
        "https://invalid-url.com/video"
    ]
    
    for url in test_urls:
        try:
            is_valid, platform, error = validator.validate_url(url)
            print(f"URL: {url}")
            print(f"  有效: {is_valid}, 平台: {platform}, 错误: {error}")
        except Exception as e:
            print(f"URL: {url}")
            print(f"  ❌ 验证失败: {e}")
        print()

async def test_video_info_direct():
    """直接测试视频信息获取"""
    print("🎬 测试视频信息获取...")
    
    downloader = DownloaderService()
    
    # 测试不同的URLs
    test_urls = [
        ("YouTube简单视频", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
        ("Bilibili视频", "https://www.bilibili.com/video/BV11g411F7Fp/"),
    ]
    
    for name, url in test_urls:
        print(f"\n测试 {name}: {url}")
        try:
            info = downloader.get_video_info(url)
            print(f"  ✅ 成功获取信息:")
            print(f"    标题: {info.get('title', 'N/A')}")
            print(f"    时长: {info.get('duration', 'N/A')}")
            print(f"    上传者: {info.get('uploader', 'N/A')}")
            print(f"    格式数量: {len(info.get('formats', []))}")
        except Exception as e:
            print(f"  ❌ 获取失败: {e}")
            print(f"    错误类型: {type(e).__name__}")

async def test_with_proxy():
    """测试带代理的情况"""
    print("\n🌐 测试代理设置...")
    
    import os
    # 设置代理环境变量
    os.environ['HTTP_PROXY'] = 'http://127.0.0.1:1087'
    os.environ['HTTPS_PROXY'] = 'http://127.0.0.1:1087'
    
    downloader = DownloaderService()
    
    try:
        # 测试YouTube（需要代理）
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        print(f"使用代理测试: {url}")
        info = downloader.get_video_info(url)
        print(f"  ✅ 代理下成功: {info.get('title', 'N/A')}")
    except Exception as e:
        print(f"  ❌ 代理下失败: {e}")

async def test_yt_dlp_direct():
    """直接测试yt-dlp"""
    print("\n🔧 直接测试yt-dlp...")
    
    import yt_dlp
    
    # 测试不同配置
    configs = [
        {
            "name": "基本配置",
            "opts": {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
            }
        },
        {
            "name": "带代理配置",
            "opts": {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'proxy': 'http://127.0.0.1:1087',
            }
        }
    ]
    
    test_urls = [
        ("Bilibili", "https://www.bilibili.com/video/BV11g411F7Fp/"),
        ("YouTube", "https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
    ]
    
    for config in configs:
        print(f"\n{config['name']}:")
        for platform, url in test_urls:
            try:
                with yt_dlp.YoutubeDL(config['opts']) as ydl:
                    info = ydl.extract_info(url, download=False)
                    print(f"  ✅ {platform}: {info.get('title', 'N/A')}")
            except Exception as e:
                print(f"  ❌ {platform}: {str(e)[:100]}...")

async def test_api_endpoints():
    """测试API端点逻辑"""
    print("\n🛠️ 测试API端点逻辑...")
    
    from app.services.validation import URLValidator
    
    validator = URLValidator()
    downloader = DownloaderService()
    
    # 模拟API端点的处理逻辑
    test_url = "https://www.bilibili.com/video/BV11g411F7Fp/"
    
    print(f"测试URL: {test_url}")
    
    # 第1步：验证URL
    is_valid, platform, error_msg = validator.validate_url(test_url)
    print(f"  URL验证: 有效={is_valid}, 平台={platform}, 错误={error_msg}")
    
    if not is_valid:
        print(f"  ❌ URL验证失败，API会返回400错误")
        return
    
    # 第2步：获取视频信息
    try:
        video_info = downloader.get_video_info(test_url)
        print(f"  ✅ 视频信息获取成功: {video_info.get('title', 'N/A')}")
        
        # 第3步：模拟下载选项
        options = DownloadOptions(
            url=test_url,
            quality="best",
            format="video"
        )
        print(f"  下载选项: {options}")
        
    except Exception as e:
        print(f"  ❌ 视频信息获取失败: {e}")
        print(f"  API会返回422错误")

async def main():
    """主函数"""
    print("🌌 Gravity Video Downloader - 直接API测试")
    print("=" * 60)
    
    await test_url_validation()
    await test_video_info_direct()
    await test_with_proxy()
    await test_yt_dlp_direct()
    await test_api_endpoints()
    
    print("\n" + "=" * 60)
    print("测试完成！")

if __name__ == "__main__":
    asyncio.run(main())