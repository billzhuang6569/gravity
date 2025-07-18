#!/usr/bin/env python3
"""专门调试Bilibili问题的脚本"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import yt_dlp
from app.services.downloader import DownloaderService

def test_bilibili_raw():
    """直接测试Bilibili"""
    print("🔍 直接测试Bilibili yt-dlp...")
    
    url = "https://www.bilibili.com/video/BV11g411F7Fp/"
    
    try:
        ydl_opts = {
            'quiet': False,  # 显示详细信息
            'no_warnings': False,  # 显示警告
            'skip_download': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"正在提取: {url}")
            info = ydl.extract_info(url, download=False)
            
            print(f"✅ 成功提取信息:")
            print(f"  标题: {info.get('title', 'N/A')}")
            print(f"  时长: {info.get('duration', 'N/A')}")
            print(f"  格式数量: {len(info.get('formats', []))}")
            
            # 显示前几个格式
            formats = info.get('formats', [])
            print(f"  前5个格式:")
            for i, fmt in enumerate(formats[:5]):
                print(f"    {i+1}. {fmt.get('format_id', 'N/A')} - {fmt.get('ext', 'N/A')} - {fmt.get('resolution', 'N/A')}")
            
    except Exception as e:
        print(f"❌ 直接调用失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()

def test_bilibili_with_service():
    """使用我们的服务测试Bilibili"""
    print("\n🔧 使用DownloaderService测试Bilibili...")
    
    url = "https://www.bilibili.com/video/BV11g411F7Fp/"
    
    try:
        downloader = DownloaderService()
        info = downloader.get_video_info(url)
        
        print(f"✅ 服务调用成功:")
        print(f"  标题: {info.get('title', 'N/A')}")
        print(f"  时长: {info.get('duration', 'N/A')}")
        print(f"  格式数量: {len(info.get('formats', []))}")
        
    except Exception as e:
        print(f"❌ 服务调用失败: {e}")
        print(f"错误类型: {type(e).__name__}")
        import traceback
        traceback.print_exc()

def test_bilibili_step_by_step():
    """逐步测试Bilibili处理过程"""
    print("\n🎯 逐步测试Bilibili处理...")
    
    url = "https://www.bilibili.com/video/BV11g411F7Fp/"
    
    # 第1步：基本配置
    print("第1步：基本配置")
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': False,
            'skip_download': True,
            'listformats': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            print(f"  ✅ 基本提取成功: {info.get('title', 'N/A')}")
            
            # 第2步：格式处理
            print("第2步：格式处理")
            formats = info.get('formats', [])
            print(f"  原始格式数量: {len(formats)}")
            
            # 模拟我们的格式处理逻辑
            from app.services.downloader import DownloaderService
            downloader = DownloaderService()
            
            # 调用私有方法进行格式处理
            try:
                parsed_formats = downloader._parse_formats_for_info(formats)
                print(f"  ✅ 格式处理成功: {len(parsed_formats)} 个格式")
                for fmt in parsed_formats[:3]:
                    print(f"    {fmt}")
            except Exception as e:
                print(f"  ❌ 格式处理失败: {e}")
                
            # 第3步：时长处理
            print("第3步：时长处理")
            try:
                duration = info.get('duration')
                if duration:
                    formatted_duration = downloader._format_duration(duration)
                    print(f"  ✅ 时长处理成功: {formatted_duration}")
                else:
                    print(f"  ⚠️ 无时长信息")
            except Exception as e:
                print(f"  ❌ 时长处理失败: {e}")
                
    except Exception as e:
        print(f"❌ 逐步测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🌌 Bilibili问题调试")
    print("=" * 50)
    
    test_bilibili_raw()
    test_bilibili_with_service()
    test_bilibili_step_by_step()
    
    print("\n" + "=" * 50)
    print("调试完成！")