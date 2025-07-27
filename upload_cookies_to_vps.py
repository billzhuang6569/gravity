#!/usr/bin/env python3
"""
🍪 YouTube Cookies 自动上传工具 (Python版本)
用于从Mac导出cookies并上传到VPS
"""

import os
import sys
import json
import time
import subprocess
import requests
from pathlib import Path
from datetime import datetime
import tempfile
import shutil

# 颜色输出
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    NC = '\033[0m'  # No Color

def colored(text, color):
    """添加颜色到文本"""
    return f"{color}{text}{Colors.NC}"

def log(message):
    """日志输出"""
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print(colored(f"[{timestamp}] {message}", Colors.BLUE))

def success(message):
    """成功消息"""
    print(colored(f"✅ {message}", Colors.GREEN))

def error(message):
    """错误消息"""
    print(colored(f"❌ {message}", Colors.RED))

def warning(message):
    """警告消息"""
    print(colored(f"⚠️  {message}", Colors.YELLOW))

def info(message):
    """信息消息"""
    print(colored(f"ℹ️  {message}", Colors.CYAN))

class CookiesUploader:
    def __init__(self):
        self.vps_host = None
        self.vps_port = "8018"
        self.vps_url = None
        self.temp_cookies_file = None
        self.log_file = "/tmp/cookies_upload.log"
        
    def get_vps_config(self):
        """交互式获取VPS配置"""
        print(colored("🍪 YouTube Cookies 自动上传工具", Colors.PURPLE))
        print("=" * 50)
        
        # 获取VPS地址
        while True:
            vps_host = input(colored("请输入VPS IP地址或域名: ", Colors.CYAN)).strip()
            if vps_host:
                self.vps_host = vps_host
                break
            else:
                error("VPS地址不能为空")
        
        # 获取端口 (可选)
        port_input = input(colored(f"请输入FastAPI端口 (默认 {self.vps_port}): ", Colors.CYAN)).strip()
        if port_input:
            self.vps_port = port_input
        
        self.vps_url = f"http://{self.vps_host}:{self.vps_port}"
        
        # 确认配置
        print(f"\n📋 当前配置:")
        print(f"   VPS地址: {self.vps_host}")
        print(f"   VPS端口: {self.vps_port}")
        print(f"   API地址: {self.vps_url}")
        
        confirm = input(colored("\n确认配置正确吗? (y/N): ", Colors.YELLOW)).strip().lower()
        if confirm not in ['y', 'yes']:
            print("配置已取消")
            return False
        
        return True
    
    def check_dependencies(self):
        """检查依赖"""
        log("检查依赖...")
        
        # 检查yt-dlp
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                success(f"yt-dlp 已安装 (版本: {result.stdout.strip()})")
            else:
                error("yt-dlp 未安装或无法运行")
                info("请安装: pip install yt-dlp")
                return False
        except (subprocess.TimeoutExpired, FileNotFoundError):
            error("yt-dlp 未安装")
            info("请安装: pip install yt-dlp")
            return False
        
        # 检查requests
        try:
            import requests
            success("requests 已安装")
        except ImportError:
            error("requests 未安装")
            info("请安装: pip install requests")
            return False
        
        return True
    
    def test_vps_connection(self):
        """测试VPS连接"""
        log("测试VPS连接...")
        
        try:
            response = requests.get(f"{self.vps_url}/health", timeout=10)
            if response.status_code == 200:
                success("VPS连接正常")
                return True
            else:
                error(f"VPS响应异常 (HTTP {response.status_code})")
                return False
        except requests.exceptions.ConnectionError:
            error(f"无法连接到VPS: {self.vps_url}")
            info("请检查:")
            info("1. VPS地址和端口是否正确")
            info("2. VPS防火墙设置")
            info("3. FastAPI服务是否正在运行")
            return False
        except requests.exceptions.Timeout:
            error("VPS连接超时")
            return False
        except Exception as e:
            error(f"连接测试失败: {e}")
            return False
    
    def export_cookies(self):
        """从Chrome导出cookies"""
        log("从Chrome导出cookies...")
        
        # 创建临时文件
        timestamp = int(time.time())
        self.temp_cookies_file = f"/tmp/cookies_{timestamp}.txt"
        
        # 尝试多种方法导出cookies
        methods = [
            {
                'name': 'Chrome',
                'cmd': [
                    'yt-dlp',
                    '--cookies-from-browser', 'chrome',
                    '--cookies', self.temp_cookies_file,
                    '--no-download',
                    '--quiet',
                    'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
                ]
            },
            {
                'name': 'Firefox',
                'cmd': [
                    'yt-dlp',
                    '--cookies-from-browser', 'firefox',
                    '--cookies', self.temp_cookies_file,
                    '--no-download',
                    '--quiet',
                    'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
                ]
            },
            {
                'name': 'Safari',
                'cmd': [
                    'yt-dlp',
                    '--cookies-from-browser', 'safari',
                    '--cookies', self.temp_cookies_file,
                    '--no-download',
                    '--quiet',
                    'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
                ]
            }
        ]
        
        for method in methods:
            try:
                info(f"尝试从{method['name']}导出cookies...")
                result = subprocess.run(method['cmd'], capture_output=True, text=True, timeout=20)
                
                if os.path.exists(self.temp_cookies_file) and os.path.getsize(self.temp_cookies_file) > 0:
                    with open(self.temp_cookies_file, 'r') as f:
                        line_count = len(f.readlines())
                    success(f"从{method['name']}导出cookies成功: {line_count} 行")
                    return True
                else:
                    warning(f"从{method['name']}导出失败")
                    if result.stderr:
                        warning(f"错误信息: {result.stderr}")
                        
            except subprocess.TimeoutExpired:
                warning(f"从{method['name']}导出超时")
                continue
            except Exception as e:
                warning(f"从{method['name']}导出失败: {e}")
                continue
        
        error("所有浏览器都无法导出cookies")
        info("请确保:")
        info("1. 至少有一个浏览器已登录YouTube")
        info("2. 浏览器没有在运行其他重要进程")
        info("3. 网络连接正常")
        return False
    
    def validate_cookies(self):
        """验证cookies有效性 - 使用get info方式"""
        log("验证cookies有效性...")
        
        try:
            # 使用get info方式验证，更快速
            cmd = [
                'yt-dlp',
                '--cookies', self.temp_cookies_file,  # 修正参数名
                '--no-download',  # 只获取信息
                '--quiet',        # 静默模式
                '--print', 'title',  # 只打印标题
                'https://www.youtube.com/watch?v=dQw4w9WgXcQ'
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            
            if result.returncode == 0 and result.stdout.strip():
                success("cookies验证通过")
                info(f"测试视频标题: {result.stdout.strip()}")
                return True
            else:
                warning("cookies验证失败，但继续上传")
                if result.stderr:
                    warning(f"验证错误: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            warning("cookies验证超时，但继续上传")
            return False
        except Exception as e:
            warning(f"cookies验证异常: {e}")
            return False
    
    def upload_cookies(self):
        """上传cookies到VPS"""
        log("上传cookies到VPS...")
        
        try:
            with open(self.temp_cookies_file, 'rb') as f:
                files = {'file': f}
                response = requests.post(
                    f"{self.vps_url}/upload-cookies",
                    files=files,
                    timeout=30
                )
            
            if response.status_code == 200:
                success("cookies上传成功")
                try:
                    result = response.json()
                    print(json.dumps(result, indent=2, ensure_ascii=False))
                except:
                    print(response.text)
                return True
            else:
                error(f"cookies上传失败 (HTTP {response.status_code})")
                try:
                    error_info = response.json()
                    print(json.dumps(error_info, indent=2, ensure_ascii=False))
                except:
                    print(response.text)
                return False
                
        except requests.exceptions.ConnectionError:
            error("上传时连接失败")
            return False
        except requests.exceptions.Timeout:
            error("上传超时")
            return False
        except Exception as e:
            error(f"上传失败: {e}")
            return False
    
    def check_vps_cookies_status(self):
        """检查VPS上的cookies状态"""
        log("检查VPS上的cookies状态...")
        
        try:
            response = requests.get(f"{self.vps_url}/cookies-status", timeout=10)
            
            if response.status_code == 200:
                try:
                    status_data = response.json()
                    if status_data.get('status') == 'valid':
                        success("VPS上的cookies状态正常")
                    else:
                        warning("VPS上的cookies状态异常")
                    print(json.dumps(status_data, indent=2, ensure_ascii=False))
                    return True
                except:
                    print(response.text)
                    return False
            else:
                error(f"获取cookies状态失败 (HTTP {response.status_code})")
                return False
                
        except requests.exceptions.ConnectionError:
            error("检查状态时连接失败")
            return False
        except requests.exceptions.Timeout:
            error("检查状态超时")
            return False
        except Exception as e:
            error(f"检查状态失败: {e}")
            return False
    
    def cleanup(self):
        """清理临时文件"""
        if self.temp_cookies_file and os.path.exists(self.temp_cookies_file):
            try:
                os.remove(self.temp_cookies_file)
                log(f"清理临时文件: {self.temp_cookies_file}")
            except Exception as e:
                warning(f"清理临时文件失败: {e}")
    
    def run(self):
        """主运行函数"""
        try:
            # 获取配置
            if not self.get_vps_config():
                return False
            
            # 检查依赖
            if not self.check_dependencies():
                return False
            
            # 测试VPS连接
            if not self.test_vps_connection():
                return False
            
            # 导出cookies
            if not self.export_cookies():
                return False
            
            # 验证cookies
            self.validate_cookies()
            
            # 上传cookies
            if not self.upload_cookies():
                return False
            
            # 检查VPS状态
            self.check_vps_cookies_status()
            
            success("🎉 cookies更新完成！")
            return True
            
        except KeyboardInterrupt:
            print("\n" + colored("操作已取消", Colors.YELLOW))
            return False
        except Exception as e:
            error(f"运行过程中出现错误: {e}")
            return False
        finally:
            self.cleanup()

def main():
    """主函数"""
    uploader = CookiesUploader()
    success = uploader.run()
    
    if success:
        print(colored("\n🎉 所有操作已完成！", Colors.GREEN))
    else:
        print(colored("\n❌ 操作失败，请检查错误信息", Colors.RED))
    
    input(colored("\n按回车键退出...", Colors.CYAN))

if __name__ == "__main__":
    main() 