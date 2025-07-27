#!/usr/bin/env python3
"""
YouTube Cookies 测试脚本
用于验证cookies是否有效，避免bot验证错误
"""

import os
import sys
import yt_dlp
from pathlib import Path

def test_cookies_with_browser():
    """测试浏览器cookies"""
    print("🔍 测试浏览器cookies...")
    
    try:
        # 测试Chrome cookies
        ydl_opts = {
            'cookiesfrombrowser': ('chrome',),
            'quiet': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # 尝试获取一个简单视频的信息
            info = ydl.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False)
            print("✅ Chrome cookies 有效")
            print(f"   视频标题: {info.get('title', 'N/A')}")
            return True
            
    except Exception as e:
        print(f"❌ Chrome cookies 无效: {e}")
        
    try:
        # 测试Firefox cookies
        ydl_opts = {
            'cookiesfrombrowser': ('firefox',),
            'quiet': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False)
            print("✅ Firefox cookies 有效")
            print(f"   视频标题: {info.get('title', 'N/A')}")
            return True
            
    except Exception as e:
        print(f"❌ Firefox cookies 无效: {e}")
    
    return False

def test_cookies_file(cookies_file):
    """测试cookies文件"""
    print(f"🔍 测试cookies文件: {cookies_file}")
    
    if not os.path.exists(cookies_file):
        print(f"❌ cookies文件不存在: {cookies_file}")
        return False
    
    try:
        ydl_opts = {
            'cookiefile': cookies_file,
            'quiet': True,
            'no_warnings': True
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info("https://www.youtube.com/watch?v=dQw4w9WgXcQ", download=False)
            print("✅ cookies文件有效")
            print(f"   视频标题: {info.get('title', 'N/A')}")
            return True
            
    except Exception as e:
        print(f"❌ cookies文件无效: {e}")
        return False

def main():
    print("🍪 YouTube Cookies 测试工具")
    print("=" * 50)
    
    # 测试浏览器cookies
    browser_ok = test_cookies_with_browser()
    
    # 测试cookies文件
    cookies_file = "cookies.txt"
    file_ok = test_cookies_file(cookies_file)
    
    print("\n📊 测试结果:")
    print(f"   浏览器cookies: {'✅ 有效' if browser_ok else '❌ 无效'}")
    print(f"   cookies文件: {'✅ 有效' if file_ok else '❌ 无效'}")
    
    if not browser_ok and not file_ok:
        print("\n🚨 所有cookies都无效！需要更新cookies:")
        print("1. 重新登录YouTube")
        print("2. 使用浏览器扩展导出cookies")
        print("3. 或使用yt-dlp --cookies-from-browser导出")
    elif browser_ok and not file_ok:
        print("\n💡 建议: 将浏览器cookies导出到文件")
        print("yt-dlp --cookies-from-browser chrome --cookies-out cookies.txt")
    else:
        print("\n✅ cookies状态良好")

if __name__ == "__main__":
    main() 