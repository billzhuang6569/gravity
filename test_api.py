#!/usr/bin/env python3
import requests
import time
import json

# API基础URL
BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查"""
    print("🔍 测试健康检查...")
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        if response.status_code == 200:
            print("✅ 健康检查通过")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
            return True
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 健康检查异常: {e}")
        return False

def test_video_info(url):
    """测试获取视频信息"""
    print(f"\n🔍 测试获取视频信息: {url}")
    try:
        response = requests.get(f"{BASE_URL}/info", params={"url": url}, timeout=60)
        if response.status_code == 200:
            print("✅ 获取视频信息成功")
            data = response.json()
            print(f"📹 视频标题: {data.get('title', 'N/A')}")
            print(f"⏱️ 时长: {data.get('duration', 'N/A')} 秒")
            print(f"👤 上传者: {data.get('uploader', 'N/A')}")
            print(f"👀 观看次数: {data.get('view_count', 'N/A')}")
            return True
        else:
            print(f"❌ 获取视频信息失败: {response.status_code}")
            print(response.text)
            return False
    except requests.exceptions.Timeout:
        print("⏰ 请求超时，可能需要更长时间...")
        return False
    except Exception as e:
        print(f"❌ 获取视频信息异常: {e}")
        return False

def test_formats(url):
    """测试获取格式信息"""
    print(f"\n🔍 测试获取格式信息: {url}")
    try:
        response = requests.get(f"{BASE_URL}/formats", params={"url": url}, timeout=60)
        if response.status_code == 200:
            print("✅ 获取格式信息成功")
            data = response.json()
            print(f"📹 视频标题: {data.get('title', 'N/A')}")
            formats = data.get('formats', [])
            print(f"📋 可用格式数量: {len(formats)}")
            
            # 显示前5个格式
            for i, fmt in enumerate(formats[:5]):
                print(f"  {i+1}. {fmt.get('format_id', 'N/A')} - {fmt.get('resolution', 'N/A')} - {fmt.get('ext', 'N/A')}")
            
            return True
        else:
            print(f"❌ 获取格式信息失败: {response.status_code}")
            print(response.text)
            return False
    except requests.exceptions.Timeout:
        print("⏰ 请求超时，可能需要更长时间...")
        return False
    except Exception as e:
        print(f"❌ 获取格式信息异常: {e}")
        return False

def test_download(url):
    """测试下载功能"""
    print(f"\n🔍 测试下载功能: {url}")
    try:
        # 先获取视频信息
        info_response = requests.get(f"{BASE_URL}/info", params={"url": url}, timeout=60)
        if info_response.status_code != 200:
            print("❌ 无法获取视频信息，跳过下载测试")
            return False
        
        video_info = info_response.json()
        video_id = video_info.get('id', 'unknown')
        
        # 开始下载（使用最佳格式）
        download_data = {
            "url": url,
            "format": "best",
            "extract_audio": False
        }
        
        print("📥 开始下载音频...")
        response = requests.post(f"{BASE_URL}/download", json=download_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ 下载任务已启动")
            print(f"🎵 视频ID: {result.get('video_id', 'N/A')}")
            print(f"📝 标题: {result.get('title', 'N/A')}")
            print(f"🔗 进度URL: {result.get('progress_url', 'N/A')}")
            
            # 监控下载进度
            video_id = result.get('video_id')
            if video_id:
                print("\n⏳ 监控下载进度...")
                for i in range(10):  # 最多等待10次
                    time.sleep(3)
                    try:
                        progress_response = requests.get(f"{BASE_URL}/progress/{video_id}", timeout=10)
                        if progress_response.status_code == 200:
                            progress = progress_response.json()
                            status = progress.get('status', 'unknown')
                            print(f"  状态: {status}")
                            
                            if status == 'downloading':
                                print(f"  进度: {progress.get('progress', 'N/A')}")
                                print(f"  速度: {progress.get('speed', 'N/A')}")
                            elif status == 'completed':
                                print(f"  ✅ 下载完成: {progress.get('filename', 'N/A')}")
                                print(f"  📁 文件大小: {progress.get('file_size', 'N/A')} 字节")
                                return True
                            elif status == 'failed':
                                print(f"  ❌ 下载失败: {progress.get('error', 'N/A')}")
                                return False
                        else:
                            print(f"  ⚠️ 无法获取进度信息: {progress_response.status_code}")
                    except Exception as e:
                        print(f"  ⚠️ 获取进度异常: {e}")
                
                print("⏰ 下载超时")
                return False
            
            return True
        else:
            print(f"❌ 下载失败: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.Timeout:
        print("⏰ 请求超时")
        return False
    except Exception as e:
        print(f"❌ 下载测试异常: {e}")
        return False

def test_supported_sites():
    """测试获取支持的网站列表"""
    print("\n🔍 测试获取支持的网站列表...")
    try:
        response = requests.get(f"{BASE_URL}/supported-sites", timeout=30)
        if response.status_code == 200:
            print("✅ 获取支持的网站列表成功")
            data = response.json()
            print(f"🌐 支持网站数量: {data.get('count', 'N/A')}")
            
            popular_sites = data.get('popular_sites', [])
            print(f"⭐ 热门网站: {', '.join(popular_sites)}")
            return True
        else:
            print(f"❌ 获取支持的网站列表失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 获取支持的网站列表异常: {e}")
        return False

def main():
    """主测试函数"""
    print("🚀 开始测试 YT-DLP API 服务")
    print("=" * 50)
    
    # 测试健康检查
    if not test_health():
        print("❌ 健康检查失败，停止测试")
        return
    
    # 测试获取支持的网站列表
    test_supported_sites()
    
    # 测试YouTube视频
    youtube_url = "https://www.youtube.com/watch?v=qaYO4A8Zf5E"
    
    # 测试获取视频信息
    test_video_info(youtube_url)
    
    # 测试获取格式信息
    test_formats(youtube_url)
    
    # 测试下载功能
    test_download(youtube_url)
    
    print("\n" + "=" * 50)
    print("🎉 测试完成！")
    print(f"📚 API文档: {BASE_URL}/docs")
    print(f"📖 ReDoc文档: {BASE_URL}/redoc")

if __name__ == "__main__":
    main() 