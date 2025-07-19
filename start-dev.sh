#!/bin/bash

# Gravity Video Downloader - 开发环境启动脚本
# 此脚本会激活Python虚拟环境并启动所有服务

echo "🚀 启动 Gravity Video Downloader 开发环境..."

# 检查虚拟环境是否存在
if [ ! -d "venv" ]; then
    echo "📦 创建Python虚拟环境..."
    python3 -m venv venv
fi

# 激活虚拟环境
echo "🔧 激活Python虚拟环境..."
source venv/bin/activate

# 安装Python依赖
echo "📥 安装Python依赖..."
pip install -r requirements.txt

# 检查Redis是否运行
echo "🔍 检查Redis服务..."
if ! pgrep -x "redis-server" > /dev/null; then
    echo "⚠️  Redis服务未运行，请手动启动Redis或使用Docker:"
    echo "   docker run -d --name gravity-redis -p 6379:6379 redis:7-alpine"
    echo "   或者安装并启动本地Redis服务"
else
    echo "✅ Redis服务正在运行"
fi

# 启动后端服务
echo "🔧 启动后端服务..."
cd backend
npm run dev &
BACKEND_PID=$!
cd ..

# 等待后端启动
echo "⏳ 等待后端服务启动..."
sleep 5

# 检查后端是否启动成功
if curl -s http://localhost:8000/health > /dev/null; then
    echo "✅ 后端服务启动成功 (http://localhost:8000)"
else
    echo "❌ 后端服务启动失败"
    exit 1
fi

# 启动前端服务
echo "🎨 启动前端服务..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

# 等待前端启动
echo "⏳ 等待前端服务启动..."
sleep 10

# 检查前端是否启动成功
if curl -s http://localhost:3000 > /dev/null; then
    echo "✅ 前端服务启动成功 (http://localhost:3000)"
else
    echo "❌ 前端服务启动失败"
    exit 1
fi

echo ""
echo "🎉 Gravity Video Downloader 启动完成！"
echo ""
echo "📱 前端界面: http://localhost:3000"
echo "🔧 后端API: http://localhost:8000"
echo "📊 健康检查: http://localhost:8000/health"
echo ""
echo "按 Ctrl+C 停止所有服务"

# 等待用户中断
trap "echo ''; echo '🛑 正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; echo '✅ 服务已停止'; exit 0" INT

# 保持脚本运行
wait 