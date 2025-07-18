#!/bin/bash

# Gravity Video Downloader - 一键部署脚本

set -e

echo "🌌 Gravity Video Downloader - 部署脚本"
echo "=========================================="

# 检查 Docker 和 Docker Compose
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装。请先安装 Docker"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose 未安装。请先安装 Docker Compose"
    exit 1
fi

# 检查环境变量文件
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，复制默认配置..."
    cp .env.example .env
    echo "✅ 已创建 .env 文件，请根据实际情况修改配置"
    echo "📝 请编辑 .env 文件，然后重新运行此脚本"
    exit 1
fi

# 创建SSL证书目录
mkdir -p ssl
if [ ! -f "ssl/cert.pem" ] || [ ! -f "ssl/key.pem" ]; then
    echo "🔐 生成自签名 SSL 证书..."
    openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes -subj "/CN=localhost"
    echo "✅ SSL 证书已生成 (自签名)"
    echo "💡 生产环境请使用 Let's Encrypt 或购买 SSL 证书"
fi

# 拉取最新镜像
echo "📦 拉取最新镜像..."
docker-compose pull

# 构建应用镜像
echo "🔨 构建应用镜像..."
docker-compose build

# 启动服务
echo "🚀 启动服务..."
docker-compose up -d

# 等待服务启动
echo "⏳ 等待服务启动..."
sleep 10

# 检查服务状态
echo "🔍 检查服务状态..."
docker-compose ps

# 检查健康状态
echo "💊 检查健康状态..."
for i in {1..10}; do
    if curl -f http://localhost:8001/api/v1/health > /dev/null 2>&1; then
        echo "✅ API 服务健康"
        break
    fi
    echo "⏳ 等待 API 服务启动... ($i/10)"
    sleep 5
done

if curl -f http://localhost > /dev/null 2>&1; then
    echo "✅ 前端服务健康"
else
    echo "⚠️  前端服务可能未正常启动"
fi

echo ""
echo "🎉 部署完成！"
echo "=========================================="
echo "🌐 前端地址: http://localhost (或 https://localhost)"
echo "🔗 API 地址: http://localhost:8001"
echo "📊 API 文档: http://localhost:8001/docs"
echo "🔍 服务状态: docker-compose ps"
echo "📋 查看日志: docker-compose logs -f"
echo "🛑 停止服务: docker-compose down"
echo "=========================================="