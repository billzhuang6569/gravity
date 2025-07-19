#!/bin/bash

echo "🚀 启动 Gravity Video Downloader..."

# 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，请先安装 Docker"
    exit 1
fi

# 检查 Docker Compose 是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装，请先安装 Docker Compose"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p downloads data

# 设置权限
echo "🔐 设置目录权限..."
chmod 755 downloads data

# 启动服务
echo "🔄 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "📊 检查服务状态..."
docker-compose ps

echo ""
echo "✅ Gravity Video Downloader 启动成功！"
echo ""
echo "🌐 访问地址: http://localhost:3000"
echo "📊 健康检查: http://localhost:8000/health"
echo ""
echo "📝 使用说明:"
echo "1. 打开浏览器访问 http://localhost:3000"
echo "2. 粘贴视频链接，选择格式"
echo "3. 点击开始下载"
echo ""
echo "🛑 停止服务: docker-compose down"
echo "📋 查看日志: docker-compose logs -f" 