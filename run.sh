#!/bin/bash

# 视频下载API服务启动脚本

echo "🎬 视频下载API服务启动脚本"
echo "================================"

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker未安装，请先安装Docker"
    exit 1
fi

# 检查docker-compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose未安装，请先安装docker-compose"
    exit 1
fi

# 创建必要的目录
echo "📁 创建必要的目录..."
mkdir -p downloads
mkdir -p logs

# 复制环境变量文件
if [ ! -f .env ]; then
    echo "📝 复制环境变量文件..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件，请根据需要修改配置"
fi

# 构建和启动服务
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
if curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo "✅ 服务启动成功！"
    echo ""
    echo "📚 服务信息："
    echo "   - API文档: http://localhost:8000/docs"
    echo "   - 健康检查: http://localhost:8000/api/v1/health"
    echo "   - 服务状态: docker-compose ps"
    echo "   - 查看日志: docker-compose logs -f"
    echo "   - 停止服务: docker-compose down"
else
    echo "❌ 服务启动失败，请检查日志："
    echo "   docker-compose logs"
fi 