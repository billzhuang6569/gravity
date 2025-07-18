#!/bin/bash

# 端口冲突检查脚本

echo "🔍 检查端口占用情况..."
echo "================================"

# 检查的端口列表
PORTS=(80 443 8001 6379)

# 检查函数
check_port() {
    local port=$1
    local service_name=$2
    
    if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        echo "❌ 端口 $port ($service_name) 已被占用:"
        netstat -tlnp 2>/dev/null | grep ":$port " | head -1
        return 1
    else
        echo "✅ 端口 $port ($service_name) 可用"
        return 0
    fi
}

# 检查所有端口
all_clear=true

check_port 80 "HTTP/前端" || all_clear=false
check_port 443 "HTTPS/前端" || all_clear=false
check_port 8001 "API服务" || all_clear=false
check_port 6379 "Redis" || all_clear=false

echo "================================"

if $all_clear; then
    echo "🎉 所有端口都可用，可以安全部署！"
    exit 0
else
    echo "⚠️  有端口被占用，请解决冲突后再部署"
    echo ""
    echo "解决方案："
    echo "1. 停止占用端口的服务"
    echo "2. 修改 docker-compose.yml 中的端口映射"
    echo "3. 使用自定义端口部署"
    exit 1
fi