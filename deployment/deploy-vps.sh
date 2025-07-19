#!/bin/bash

# Gravity Video Downloader - VPS 一键部署脚本
# 适用于有端口冲突的服务器环境

set -e

echo "🌌 Gravity Video Downloader - VPS 一键部署脚本"
echo "=================================================="
echo "部署端口: 8080(HTTP), 8443(HTTPS), 18001(API), 16379(Redis)"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
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

# 检查命令是否存在
check_command() {
    if ! command -v $1 &> /dev/null; then
        log_error "$1 未安装或不在PATH中"
        return 1
    fi
    return 0
}

# 检查 Docker 和 Docker Compose
log_info "检查依赖..."
if ! check_command docker; then
    log_error "请先安装 Docker"
    exit 1
fi

if ! check_command docker-compose; then
    log_error "请先安装 Docker Compose"
    exit 1
fi

# 检查 Docker 服务状态
if ! systemctl is-active --quiet docker; then
    log_warning "Docker 服务未运行，尝试启动..."
    sudo systemctl start docker || {
        log_error "无法启动 Docker 服务"
        exit 1
    }
fi

log_success "依赖检查完成"

# 检查端口冲突
log_info "检查端口占用情况..."
PORTS=(8080 8443 18001 16379)
PORT_CONFLICTS=()

for port in "${PORTS[@]}"; do
    if netstat -tlnp 2>/dev/null | grep -q ":$port "; then
        PORT_CONFLICTS+=($port)
    fi
done

if [ ${#PORT_CONFLICTS[@]} -gt 0 ]; then
    log_warning "发现端口冲突: ${PORT_CONFLICTS[*]}"
    read -p "是否继续部署? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "部署已取消"
        exit 1
    fi
fi

# 创建环境变量文件
log_info "配置环境变量..."
if [ ! -f ".env" ]; then
    log_info "创建 .env 文件..."
    cat > .env << 'ENV_EOF'
# Redis 密码 (请修改为更安全的密码)
REDIS_PASSWORD=GravitySecure2024!

# 应用配置
APP_NAME=Gravity Video Downloader
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO

# 安全配置 (请修改为随机字符串)
SECRET_KEY=GravityVideoDownloader2024SecureKey123456789

# 代理配置 (如果需要访问 YouTube，请取消注释并配置)
# HTTP_PROXY=http://proxy.example.com:8080
# HTTPS_PROXY=https://proxy.example.com:8080
ENV_EOF
    log_success ".env 文件已创建"
else
    log_info ".env 文件已存在，跳过创建"
fi

# 清理旧环境
log_info "清理旧环境..."
docker-compose -f docker-compose.production.yml down -v 2>/dev/null || true
docker system prune -f 2>/dev/null || true

# 构建镜像
log_info "构建应用镜像..."
if ! docker-compose -f docker-compose.production.yml build --no-cache; then
    log_error "镜像构建失败"
    exit 1
fi

log_success "镜像构建完成"

# 启动服务
log_info "启动服务..."
if ! docker-compose -f docker-compose.production.yml up -d; then
    log_error "服务启动失败"
    exit 1
fi

# 等待服务启动
log_info "等待服务启动..."
sleep 15

# 检查服务状态
log_info "检查服务状态..."
docker-compose -f docker-compose.production.yml ps

# 健康检查
log_info "执行健康检查..."
HEALTH_CHECK_PASSED=true

# 检查 Redis
log_info "检查 Redis 连接..."
if docker exec gravity-redis redis-cli -a $(grep REDIS_PASSWORD .env | cut -d'=' -f2) ping >/dev/null 2>&1; then
    log_success "Redis: 健康"
else
    log_error "Redis: 不健康"
    HEALTH_CHECK_PASSED=false
fi

# 检查 API
log_info "检查 API 服务..."
for i in {1..10}; do
    if curl -f http://localhost:18001/api/v1/health >/dev/null 2>&1; then
        log_success "API: 健康"
        break
    fi
    if [ $i -eq 10 ]; then
        log_error "API: 不健康"
        HEALTH_CHECK_PASSED=false
    else
        log_info "API 启动中... ($i/10)"
        sleep 5
    fi
done

# 检查前端
log_info "检查前端服务..."
if curl -f http://localhost:8080/health >/dev/null 2>&1; then
    log_success "前端: 健康"
else
    log_error "前端: 不健康"
    HEALTH_CHECK_PASSED=false
fi

# 显示结果
echo ""
echo "=================================================="
if [ "$HEALTH_CHECK_PASSED" = true ]; then
    log_success "🎉 部署成功！"
    echo ""
    echo "访问地址:"
    echo "🌐 前端界面: http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR-SERVER-IP'):8080"
    echo "📚 API 文档: http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR-SERVER-IP'):18001/docs"
    echo "🔍 健康检查: http://$(curl -s ifconfig.me 2>/dev/null || echo 'YOUR-SERVER-IP'):8080/health"
    echo ""
    echo "管理命令:"
    echo "📊 查看状态: ./manage.sh status"
    echo "📋 查看日志: ./manage.sh logs"
    echo "🔄 重启服务: ./manage.sh restart"
    echo "🛑 停止服务: ./manage.sh stop"
    echo "💾 备份数据: ./manage.sh backup"
else
    log_error "❌ 部署失败！请检查日志"
    echo ""
    echo "故障排除命令:"
    echo "📋 查看日志: docker-compose -f docker-compose.production.yml logs"
    echo "📊 查看状态: docker-compose -f docker-compose.production.yml ps"
    echo "🔧 重新部署: $0"
fi
echo "=================================================="