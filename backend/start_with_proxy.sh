#!/bin/bash
# 启动带代理的后端服务器

# 设置代理环境变量
export HTTP_PROXY=http://127.0.0.1:1087
export HTTPS_PROXY=http://127.0.0.1:1087
export http_proxy=http://127.0.0.1:1087
export https_proxy=http://127.0.0.1:1087

# 显示代理设置
echo "🌐 代理设置:"
echo "HTTP_PROXY: $HTTP_PROXY"
echo "HTTPS_PROXY: $HTTPS_PROXY"
echo "http_proxy: $http_proxy"
echo "https_proxy: $https_proxy"

# 激活虚拟环境
source venv/bin/activate

# 启动服务器
echo "🚀 启动FastAPI服务器..."
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload