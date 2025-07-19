#!/bin/bash

# 端口冲突检查脚本 - 使用不常见端口

echo "🔍 检查 Gravity 项目端口占用情况..."
echo "使用端口: 19280(HTTP), 19281(HTTPS), 19282(API), 19283(Redis)"
echo "================================"

# 检查的端口列表
PORTS=(19280 19281 19282 19283)
SERVICE_NAMES=("HTTP前端" "HTTPS前端" "API服务" "Redis数据库")

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

for i in "${!PORTS[@]}"; do
    check_port "${PORTS[$i]}" "${SERVICE_NAMES[$i]}" || all_clear=false
done

echo "================================"

if $all_clear; then
    echo "🎉 所有端口都可用，可以安全部署！"
    echo ""
    echo "运行部署命令:"
    echo "  ./deploy-vps.sh"
    exit 0
else
    echo "⚠️  有端口被占用"
    echo ""
    echo "解决方案："
    echo "1. 停止占用端口的服务"
    echo "2. 修改 docker-compose.production.yml 中的端口映射"
    echo "3. 选择其他端口进行部署"
    echo ""
    echo "这些端口(19280-19283)被设计为不常见端口，"
    echo "如果仍有冲突，建议检查是否有其他应用使用了这些端口。"
    exit 1
fi