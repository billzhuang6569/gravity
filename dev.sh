#!/bin/bash

echo "🔧 启动 Gravity Video Downloader 开发环境..."

# 检查 Node.js 是否安装
if ! command -v node &> /dev/null; then
    echo "❌ Node.js 未安装，请先安装 Node.js"
    exit 1
fi

# 检查 npm 是否安装
if ! command -v npm &> /dev/null; then
    echo "❌ npm 未安装，请先安装 npm"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p downloads data

# 安装后端依赖
echo "📦 安装后端依赖..."
cd backend
npm install
cd ..

# 安装前端依赖
echo "📦 安装前端依赖..."
cd frontend
npm install
cd ..

# 启动 Redis（如果使用 Docker）
echo "🔴 启动 Redis..."
docker run -d --name gravity-redis -p 6379:6379 redis:7-alpine

# 启动后端服务
echo "🔄 启动后端服务..."
cd backend
npm run dev &
BACKEND_PID=$!
cd ..

# 等待后端启动
echo "⏳ 等待后端服务启动..."
sleep 5

# 启动前端服务
echo "🔄 启动前端服务..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

echo ""
echo "✅ 开发环境启动成功！"
echo ""
echo "🌐 前端地址: http://localhost:3000"
echo "🔧 后端地址: http://localhost:8000"
echo "📊 健康检查: http://localhost:8000/health"
echo ""
echo "📝 使用说明:"
echo "1. 打开浏览器访问 http://localhost:3000"
echo "2. 粘贴视频链接，选择格式"
echo "3. 点击开始下载"
echo ""
echo "🛑 停止服务:"
echo "   - 按 Ctrl+C 停止所有服务"
echo "   - 或运行: docker stop gravity-redis"
echo ""
echo "📋 查看日志:"
echo "   - 后端日志: cd backend && npm run dev"
echo "   - 前端日志: cd frontend && npm start"

# 等待用户中断
trap "echo '🛑 正在停止服务...'; kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; docker stop gravity-redis 2>/dev/null; exit" INT
wait 