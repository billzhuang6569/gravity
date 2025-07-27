#!/bin/bash

# 🍪 YouTube Cookies 自动更新脚本
# 一键激活虚拟环境并运行cookies更新工具

echo "🍪 YouTube Cookies 自动更新工具"
echo "=================================================="

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "❌ 虚拟环境不存在，请先创建虚拟环境："
    echo "   python3 -m venv venv"
    exit 1
fi

# 激活虚拟环境
echo "📦 激活虚拟环境..."
source venv/bin/activate

# 检查Python脚本是否存在
if [ ! -f "upload_cookies_to_vps.py" ]; then
    echo "❌ upload_cookies_to_vps.py 不存在"
    exit 1
fi

# 运行cookies更新脚本
echo "🚀 启动cookies更新工具..."
python upload_cookies_to_vps.py

# 脚本结束
echo "✅ 更新脚本执行完成" 