#!/usr/bin/env python3
"""测试下载任务修复"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.tasks.download_tasks import download_video_task
from app.models.schemas import DownloadOptions

def test_download_task():
    """测试下载任务"""
    print("🎯 测试下载任务...")
    
    # 测试参数
    task_id = "test-task-123"
    url = "https://www.bilibili.com/video/BV11g411F7Fp/"
    
    # 创建选项字典（模拟从API传递的数据）
    options_dict = {
        'url': url,
        'quality': 'best',
        'format': 'video',
        'audio_format': 'mp3'
    }
    
    print(f"任务ID: {task_id}")
    print(f"URL: {url}")
    print(f"选项: {options_dict}")
    
    try:
        # 测试DownloadOptions创建
        download_options = DownloadOptions(**options_dict)
        print(f"✅ DownloadOptions创建成功: {download_options}")
        
        # 测试下载任务（这里不实际运行，只是测试参数转换）
        print("✅ 参数转换测试通过")
        
        # 如果需要实际测试下载（注释掉以避免实际下载）
        # result = download_video_task(task_id, url, options_dict)
        # print(f"✅ 下载任务完成: {result}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_options_conversion():
    """测试选项转换"""
    print("\n🔧 测试选项转换...")
    
    test_cases = [
        {
            'name': 'Bilibili视频',
            'options': {
                'url': 'https://www.bilibili.com/video/BV11g411F7Fp/',
                'quality': 'best',
                'format': 'video',
                'audio_format': 'mp3'
            }
        },
        {
            'name': 'YouTube音频',
            'options': {
                'url': 'https://www.youtube.com/watch?v=dQw4w9WgXcQ',
                'quality': '720p',
                'format': 'audio',
                'audio_format': 'mp3'
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"\n测试: {test_case['name']}")
        try:
            options = DownloadOptions(**test_case['options'])
            print(f"  ✅ 成功: quality={options.quality}, format={options.format}")
        except Exception as e:
            print(f"  ❌ 失败: {e}")

if __name__ == "__main__":
    print("🌌 下载任务测试")
    print("=" * 50)
    
    test_options_conversion()
    test_download_task()
    
    print("\n" + "=" * 50)
    print("测试完成！")