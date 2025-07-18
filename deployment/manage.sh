#!/bin/bash

# Gravity Video Downloader - 管理脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

show_usage() {
    echo "🌌 Gravity Video Downloader - 管理脚本"
    echo "=========================================="
    echo "用法: $0 [命令]"
    echo ""
    echo "可用命令:"
    echo "  start        启动所有服务"
    echo "  stop         停止所有服务"
    echo "  restart      重启所有服务"
    echo "  status       查看服务状态"
    echo "  logs         查看实时日志"
    echo "  logs [服务]  查看指定服务日志"
    echo "  update       更新并重启服务"
    echo "  backup       备份数据"
    echo "  restore      恢复数据"
    echo "  shell        进入 API 容器"
    echo "  clean        清理未使用的镜像和容器"
    echo "  ssl          生成 SSL 证书"
    echo "  monitor      监控资源使用"
    echo ""
    echo "示例:"
    echo "  $0 start"
    echo "  $0 logs api"
    echo "  $0 backup"
}

start_services() {
    echo "🚀 启动服务..."
    docker-compose up -d
    echo "✅ 服务已启动"
}

stop_services() {
    echo "🛑 停止服务..."
    docker-compose down
    echo "✅ 服务已停止"
}

restart_services() {
    echo "🔄 重启服务..."
    docker-compose restart
    echo "✅ 服务已重启"
}

show_status() {
    echo "📊 服务状态:"
    docker-compose ps
    echo ""
    echo "🔍 健康检查:"
    
    # 检查 API
    if curl -f http://localhost:8001/api/v1/health > /dev/null 2>&1; then
        echo "✅ API 服务: 健康"
    else
        echo "❌ API 服务: 不健康"
    fi
    
    # 检查前端
    if curl -f http://localhost > /dev/null 2>&1; then
        echo "✅ 前端服务: 健康"
    else
        echo "❌ 前端服务: 不健康"
    fi
    
    # 检查 Redis
    if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
        echo "✅ Redis 服务: 健康"
    else
        echo "❌ Redis 服务: 不健康"
    fi
}

show_logs() {
    if [ -n "$1" ]; then
        echo "📋 查看 $1 服务日志:"
        docker-compose logs -f "$1"
    else
        echo "📋 查看所有服务日志:"
        docker-compose logs -f
    fi
}

update_services() {
    echo "🔄 更新服务..."
    docker-compose pull
    docker-compose build
    docker-compose up -d
    echo "✅ 服务已更新"
}

backup_data() {
    echo "💾 备份数据..."
    BACKUP_DIR="backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$BACKUP_DIR"
    
    # 备份数据卷
    docker run --rm -v gravity_downloads_data:/data -v "$PWD/$BACKUP_DIR":/backup alpine tar czf /backup/downloads.tar.gz -C /data .
    docker run --rm -v gravity_redis_data:/data -v "$PWD/$BACKUP_DIR":/backup alpine tar czf /backup/redis.tar.gz -C /data .
    docker run --rm -v gravity_logs_data:/data -v "$PWD/$BACKUP_DIR":/backup alpine tar czf /backup/logs.tar.gz -C /data .
    
    echo "✅ 数据已备份到 $BACKUP_DIR"
}

restore_data() {
    echo "🔄 恢复数据..."
    if [ -z "$1" ]; then
        echo "❌ 请指定备份目录"
        echo "用法: $0 restore [backup_directory]"
        return 1
    fi
    
    BACKUP_DIR="$1"
    if [ ! -d "$BACKUP_DIR" ]; then
        echo "❌ 备份目录不存在: $BACKUP_DIR"
        return 1
    fi
    
    # 停止服务
    docker-compose down
    
    # 恢复数据
    docker run --rm -v gravity_downloads_data:/data -v "$PWD/$BACKUP_DIR":/backup alpine tar xzf /backup/downloads.tar.gz -C /data
    docker run --rm -v gravity_redis_data:/data -v "$PWD/$BACKUP_DIR":/backup alpine tar xzf /backup/redis.tar.gz -C /data
    docker run --rm -v gravity_logs_data:/data -v "$PWD/$BACKUP_DIR":/backup alpine tar xzf /backup/logs.tar.gz -C /data
    
    # 启动服务
    docker-compose up -d
    
    echo "✅ 数据已恢复"
}

enter_shell() {
    echo "🐚 进入 API 容器..."
    docker-compose exec api bash
}

clean_docker() {
    echo "🧹 清理 Docker 资源..."
    docker system prune -f
    docker volume prune -f
    echo "✅ 清理完成"
}

generate_ssl() {
    echo "🔐 生成 SSL 证书..."
    mkdir -p ssl
    openssl req -x509 -newkey rsa:4096 -keyout ssl/key.pem -out ssl/cert.pem -days 365 -nodes -subj "/CN=localhost"
    echo "✅ SSL 证书已生成"
}

monitor_resources() {
    echo "📊 监控资源使用:"
    echo "按 Ctrl+C 退出监控"
    echo ""
    
    while true; do
        clear
        echo "🌌 Gravity Video Downloader - 资源监控"
        echo "时间: $(date)"
        echo "=========================================="
        
        # 容器状态
        echo "📦 容器状态:"
        docker-compose ps
        echo ""
        
        # 资源使用
        echo "💻 资源使用:"
        docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
        echo ""
        
        # 磁盘使用
        echo "💾 磁盘使用:"
        docker system df
        echo ""
        
        sleep 5
    done
}

# 主逻辑
case "$1" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        restart_services
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs "$2"
        ;;
    update)
        update_services
        ;;
    backup)
        backup_data
        ;;
    restore)
        restore_data "$2"
        ;;
    shell)
        enter_shell
        ;;
    clean)
        clean_docker
        ;;
    ssl)
        generate_ssl
        ;;
    monitor)
        monitor_resources
        ;;
    *)
        show_usage
        ;;
esac