#!/usr/bin/env python3
"""测试Celery Worker连接"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.celery_app import celery_app
from app.tasks.download_tasks import download_video_task

def test_celery_connection():
    """测试Celery连接"""
    print("🔧 测试Celery连接...")
    
    try:
        # 检查Celery配置
        print(f"Celery broker: {celery_app.conf.broker_url}")
        print(f"Celery backend: {celery_app.conf.result_backend}")
        
        # 检查worker状态
        inspect = celery_app.control.inspect()
        
        # 获取活跃节点
        active_nodes = inspect.active()
        print(f"活跃节点: {active_nodes}")
        
        # 获取已注册任务
        registered = inspect.registered()
        print(f"已注册任务: {registered}")
        
        if not active_nodes:
            print("❌ 没有活跃的Celery worker")
            return False
        
        print("✅ Celery连接正常")
        return True
        
    except Exception as e:
        print(f"❌ Celery连接失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_simple_task():
    """测试简单任务"""
    print("\n🎯 测试简单任务...")
    
    if not test_celery_connection():
        print("❌ Celery连接失败，跳过任务测试")
        return
    
    try:
        # 测试delay调用（异步）
        print("测试 delay 调用...")
        
        task_id = "test-simple-task"
        url = "https://www.bilibili.com/video/BV11g411F7Fp/"
        options = {
            'url': url,
            'quality': 'best',
            'format': 'video',
            'audio_format': 'mp3'
        }
        
        print(f"调用参数: task_id={task_id}, url={url}, options={options}")
        
        # 检查参数类型
        print("参数类型检查:")
        print(f"  task_id: {type(task_id)} - {task_id}")
        print(f"  url: {type(url)} - {url}")
        print(f"  options: {type(options)} - {options}")
        
        # 尝试调用任务
        result = download_video_task.delay(task_id, url, options)
        print(f"✅ 任务提交成功: {result}")
        print(f"任务ID: {result.id}")
        
    except Exception as e:
        print(f"❌ 任务调用失败: {e}")
        import traceback
        traceback.print_exc()

def test_apply_async():
    """测试apply_async调用"""
    print("\n🚀 测试apply_async调用...")
    
    try:
        task_id = "test-apply-async"
        url = "https://www.bilibili.com/video/BV11g411F7Fp/"
        options = {
            'url': url,
            'quality': 'best',
            'format': 'video',
            'audio_format': 'mp3'
        }
        
        result = download_video_task.apply_async(
            args=[task_id, url, options],
            countdown=1  # 1秒后执行
        )
        
        print(f"✅ apply_async成功: {result}")
        print(f"任务ID: {result.id}")
        
    except Exception as e:
        print(f"❌ apply_async失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print("🌌 Celery Worker测试")
    print("=" * 50)
    
    test_celery_connection()
    test_simple_task()
    test_apply_async()
    
    print("\n" + "=" * 50)
    print("测试完成！")