#!/usr/bin/env python3
"""
视频下载API测试脚本
用于测试API接口是否正常工作
"""

import requests
import json
import time

# API基础URL
BASE_URL = "http://localhost:8000/api/v1"

def test_health():
    """测试健康检查接口"""
    print("🔍 测试健康检查接口...")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查通过: {data['status']}")
            print(f"   应用名称: {data['app_name']}")
            print(f"   版本: {data['version']}")
            print(f"   运行时间: {data['uptime']:.2f}秒")
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {str(e)}")
        return False

def test_video_info():
    """测试获取视频信息接口"""
    print("\n📹 测试获取视频信息接口...")
    
    # 使用一个Bilibili测试URL
    test_url = "https://www.bilibili.com/video/BV1xx411c7XD"
    
    try:
        response = requests.post(
            f"{BASE_URL}/info",
            json={"url": test_url},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ 获取视频信息成功")
                video_info = data.get('video_info', {})
                print(f"   标题: {video_info.get('title', 'N/A')}")
                print(f"   格式: {video_info.get('format', 'N/A')}")
                return True
            else:
                print(f"❌ 获取视频信息失败: {data}")
                return False
        else:
            print(f"❌ 请求失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 测试失败: {str(e)}")
        return False

def test_download():
    """测试下载接口"""
    print("\n⬬ 测试下载接口...")
    
    # 使用一个简单的测试URL (如果有的话)
    test_url = "https://www.bilibili.com/video/BV1xx411c7XD"
    
    try:
        response = requests.post(
            f"{BASE_URL}/download",
            json={
                "url": test_url,
                "mode": "link"
            },
            timeout=60  # 下载可能需要更长时间
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                print("✅ 下载请求成功")
                print(f"   下载链接: {data.get('download_url', 'N/A')}")
                print(f"   文件大小: {data.get('file_size', 'N/A')} 字节")
                return True
            else:
                print(f"❌ 下载失败: {data}")
                return False
        else:
            print(f"❌ 下载请求失败: {response.status_code}")
            print(f"   响应: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ 下载测试失败: {str(e)}")
        return False

def main():
    """主测试函数"""
    print("🎬 视频下载API测试")
    print("=" * 40)
    
    # 测试健康检查
    if not test_health():
        print("\n❌ 服务未启动或无法访问，请检查服务状态")
        print("提示：运行 'docker-compose up -d' 启动服务")
        return
    
    # 等待一下
    time.sleep(1)
    
    # 测试视频信息获取
    test_video_info()
    
    # 等待一下
    time.sleep(1)
    
    # 注意：下载测试可能比较耗时，在实际环境中谨慎使用
    print("\n⚠️  下载测试可能耗时较长，是否继续？ (y/N): ", end="")
    user_input = input().strip().lower()
    
    if user_input == 'y':
        test_download()
    else:
        print("⏭️  跳过下载测试")
    
    print("\n🎉 测试完成！")
    print("\n📚 更多测试:")
    print("   - API文档: http://localhost:8000/docs")
    print("   - 交互式测试: http://localhost:8000/docs#/")

if __name__ == "__main__":
    main() 