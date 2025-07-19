#\!/bin/bash

# Gravity Video Downloader - 管理脚本

COMPOSE_FILE="docker-compose.production.yml"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

show_usage() {
    echo "🌌 Gravity Video Downloader - 管理脚本"
    echo "端口配置: 19280(HTTP), 19281(HTTPS), 19282(API), 19283(Redis)"
    echo "=========================================="
    echo "用法: $0 [命令]"
    echo ""
    echo "可用命令:"
    echo "  start        启动所有服务"
    echo "  stop         停止所有服务"
    echo "  restart      重启所有服务"
    echo "  status       查看服务状态和健康检查"
    echo "  logs         查看实时日志"
    echo "  logs [服务]  查看指定服务日志 (api|worker|beat|redis|frontend)"
    echo "  health       执行健康检查"
    echo "  shell        进入 API 容器"
    echo "  redis-cli    进入 Redis 命令行"
    echo ""
    echo "示例:"
    echo "  $0 start"
    echo "  $0 logs api"
    echo "  $0 health"
}

start_services() {
    log_info "启动服务..."
    docker-compose -f $COMPOSE_FILE up -d
    sleep 5
    log_success "服务已启动"
    show_status
}

stop_services() {
    log_info "停止服务..."
    docker-compose -f $COMPOSE_FILE down
    log_success "服务已停止"
}

restart_services() {
    log_info "重启服务..."
    docker-compose -f $COMPOSE_FILE restart
    sleep 5
    log_success "服务已重启"
    show_status
}

show_status() {
    echo ""
    log_info "📊 容器状态:"
    docker-compose -f $COMPOSE_FILE ps
    
    echo ""
    log_info "🔍 健康检查:"
    health_check
    
    echo ""
    log_info "🌐 访问地址:"
    SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || echo "YOUR-SERVER-IP")
    echo "  前端界面: http://$SERVER_IP:19280"
    echo "  API 文档: http://$SERVER_IP:19282/docs"
    echo "  健康检查: http://$SERVER_IP:19280/health"
}

health_check() {
    # 检查 Redis
    if docker exec gravity-redis redis-cli -a $(grep REDIS_PASSWORD .env | cut -d'=' -f2) ping >/dev/null 2>&1; then
        echo "  ✅ Redis (19283): 健康"
    else
        echo "  ❌ Redis (19283): 不健康"
    fi
    
    # 检查 API
    if curl -f http://localhost:19282/api/v1/health >/dev/null 2>&1; then
        echo "  ✅ API (19282): 健康"
    else
        echo "  ❌ API (19282): 不健康"
    fi
    
    # 检查前端
    if curl -f http://localhost:19280/health >/dev/null 2>&1; then
        echo "  ✅ 前端 (19280): 健康"
    else
        echo "  ❌ 前端 (19280): 不健康"
    fi
}

show_logs() {
    if [ -n "$1" ]; then
        case $1 in
            api|worker|beat|redis|frontend)
                log_info "📋 查看 $1 服务日志 (Ctrl+C 退出):"
                docker-compose -f $COMPOSE_FILE logs -f "$1"
                ;;
            *)
                log_error "无效的服务名称。可用服务: api, worker, beat, redis, frontend"
                ;;
        esac
    else
        log_info "📋 查看所有服务日志 (Ctrl+C 退出):"
        docker-compose -f $COMPOSE_FILE logs -f
    fi
}

enter_shell() {
    log_info "进入 API 容器 (exit 退出)..."
    docker-compose -f $COMPOSE_FILE exec api bash
}

redis_cli() {
    log_info "进入 Redis 命令行 (exit 退出)..."
    REDIS_PASSWORD=$(grep REDIS_PASSWORD .env | cut -d'=' -f2)
    docker-compose -f $COMPOSE_FILE exec redis redis-cli -a $REDIS_PASSWORD
}

# 主逻辑
case "${1:-}" in
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
    health)
        health_check
        ;;
    shell)
        enter_shell
        ;;
    redis-cli)
        redis_cli
        ;;
    "")
        show_usage
        ;;
    *)
        log_error "未知命令: $1"
        show_usage
        exit 1
        ;;
esac
EOF < /dev/null