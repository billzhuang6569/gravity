#!/usr/bin/env python3
"""调试Celery任务问题"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.models.schemas import DownloadRequest, DownloadOptions
from app.tasks.download_tasks import download_video_task

def test_celery_serialization():
    """测试Celery序列化问题"""
    print("🔧 测试Celery序列化...")
    
    # 创建测试请求
    request = DownloadRequest(
        url="https://www.bilibili.com/video/BV11g411F7Fp/",
        quality="best",
        format="video",
        audio_format="mp3"
    )
    
    print(f"原始请求: {request}")
    print(f"模型转储: {request.model_dump()}")
    
    # 测试选项创建
    options_dict = request.model_dump()
    print(f"选项字典: {options_dict}")
    
    try:
        # 测试DownloadOptions创建
        download_options = DownloadOptions(**options_dict)
        print(f"✅ DownloadOptions创建成功: {download_options}")
    except Exception as e:
        print(f"❌ DownloadOptions创建失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 测试Celery任务参数
    task_id = "test-task-123"
    url = request.url
    options = request.model_dump()
    
    print(f"\nCelery任务参数:")
    print(f"  task_id: {task_id} (类型: {type(task_id)})")
    print(f"  url: {url} (类型: {type(url)})")
    print(f"  options: {options} (类型: {type(options)})")
    
    # 检查每个参数
    for key, value in options.items():
        print(f"    {key}: {value} (类型: {type(value)})")
    
    return True

def test_celery_task_direct():
    """直接测试Celery任务"""
    print("\n🎯 直接测试Celery任务...")
    
    if not test_celery_serialization():
        print("❌ 序列化测试失败，跳过任务测试")
        return
    
    # 准备参数
    task_id = "test-task-direct"
    url = "https://www.bilibili.com/video/BV11g411F7Fp/"
    options = {
        'url': url,
        'quality': 'best',
        'format': 'video',
        'audio_format': 'mp3'
    }
    
    print(f"准备调用任务:")
    print(f"  download_video_task({task_id}, {url}, {options})")
    
    try:
        # 注意：这里不会实际执行下载，只是测试参数转换
        print("✅ 参数准备成功，可以调用任务")
    except Exception as e:
        print(f"❌ 任务调用失败: {e}")
        import traceback
        traceback.print_exc()

def test_api_data_flow():
    """测试API数据流"""
    print("\n🌊 测试API数据流...")
    
    # 模拟前端发送的数据
    frontend_data = {
        "url": "https://www.bilibili.com/video/BV11g411F7Fp/",
        "quality": "best",
        "format": "video",
        "audio_format": "mp3"
    }
    
    print(f"1. 前端数据: {frontend_data}")
    
    # 模拟API端点处理
    try:
        request = DownloadRequest(**frontend_data)
        print(f"2. DownloadRequest创建成功: {request}")
        
        dumped = request.model_dump()
        print(f"3. 模型转储: {dumped}")
        
        # 检查转储的数据类型
        print("4. 转储数据类型检查:")
        for key, value in dumped.items():
            print(f"   {key}: {value} ({type(value)})")
            if isinstance(value, str) and key in ['quality']:
                # 检查是否可能被误解为数字
                try:
                    int(value)
                    print(f"   ⚠️ {key} 的值 '{value}' 可以被转换为整数")
                except ValueError:
                    print(f"   ✅ {key} 的值 '{value}' 不能被转换为整数")
        
        # 测试最终的选项创建
        final_options = DownloadOptions(**dumped)
        print(f"5. ✅ 最终选项创建成功: {final_options}")
        
    except Exception as e:
        print(f"❌ 数据流测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🌌 Celery任务调试")
    print("=" * 50)
    
    test_api_data_flow()
    test_celery_task_direct()
    
    print("\n" + "=" * 50)
    print("调试完成！")