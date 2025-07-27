#!/bin/bash

# 🍪 YouTube Cookies 自动上传脚本
# 用于从Mac导出cookies并上传到VPS

# 配置变量
VPS_HOST="your-vps-ip-or-domain"  # 替换为你的VPS地址
VPS_PORT="8018"                   # FastAPI端口
VPS_URL="http://${VPS_HOST}:${VPS_PORT}"
TEMP_COOKIES_FILE="/tmp/cookies_$(date +%s).txt"
LOG_FILE="/tmp/cookies_upload.log"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "${BLUE}[$(date '+%Y-%m-%d %H:%M:%S')]${NC} $1" | tee -a "$LOG_FILE"
}

success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

# 检查依赖
check_dependencies() {
    log "检查依赖..."
    
    if ! command -v yt-dlp &> /dev/null; then
        error "yt-dlp 未安装，请先安装: pip install yt-dlp"
        exit 1
    fi
    
    if ! command -v curl &> /dev/null; then
        error "curl 未安装"
        exit 1
    fi
    
    success "依赖检查通过"
}

# 测试VPS连接
test_vps_connection() {
    log "测试VPS连接..."
    
    if curl -s --connect-timeout 10 "$VPS_URL/health" > /dev/null; then
        success "VPS连接正常"
        return 0
    else
        error "无法连接到VPS: $VPS_URL"
        return 1
    fi
}

# 导出cookies
export_cookies() {
    log "从Chrome导出cookies..."
    
    # 尝试从Chrome导出cookies
    if yt-dlp --cookies-from-browser chrome --cookies "$TEMP_COOKIES_FILE" "https://www.youtube.com/watch?v=dQw4w9WgXcQ" > /dev/null 2>&1; then
        if [ -f "$TEMP_COOKIES_FILE" ] && [ -s "$TEMP_COOKIES_FILE" ]; then
            success "cookies导出成功: $(wc -l < "$TEMP_COOKIES_FILE") 行"
            return 0
        else
            error "cookies文件为空或不存在"
            return 1
        fi
    else
        error "从Chrome导出cookies失败"
        return 1
    fi
}

# 验证cookies
validate_cookies() {
    log "验证cookies有效性..."
    
    if yt-dlp --cookiefile "$TEMP_COOKIES_FILE" --quiet "https://www.youtube.com/watch?v=dQw4w9WgXcQ" > /dev/null 2>&1; then
        success "cookies验证通过"
        return 0
    else
        warning "cookies验证失败，但继续上传"
        return 1
    fi
}

# 上传cookies到VPS
upload_cookies() {
    log "上传cookies到VPS..."
    
    # 上传文件
    response=$(curl -s -w "\n%{http_code}" \
        -X POST \
        -F "file=@$TEMP_COOKIES_FILE" \
        "$VPS_URL/upload-cookies")
    
    # 分离响应体和状态码
    http_code=$(echo "$response" | tail -n1)
    response_body=$(echo "$response" | head -n -1)
    
    if [ "$http_code" = "200" ]; then
        success "cookies上传成功"
        echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body"
        return 0
    else
        error "cookies上传失败 (HTTP $http_code)"
        echo "$response_body"
        return 1
    fi
}

# 验证VPS上的cookies状态
check_vps_cookies_status() {
    log "检查VPS上的cookies状态..."
    
    response=$(curl -s "$VPS_URL/cookies-status")
    
    if echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); exit(0 if data.get('status')=='valid' else 1)" 2>/dev/null; then
        success "VPS上的cookies状态正常"
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
        return 0
    else
        warning "VPS上的cookies状态异常"
        echo "$response" | python3 -m json.tool 2>/dev/null || echo "$response"
        return 1
    fi
}

# 清理临时文件
cleanup() {
    if [ -f "$TEMP_COOKIES_FILE" ]; then
        rm -f "$TEMP_COOKIES_FILE"
        log "清理临时文件: $TEMP_COOKIES_FILE"
    fi
}

# 主函数
main() {
    echo "🍪 YouTube Cookies 自动上传工具"
    echo "=================================="
    
    # 设置错误处理
    trap cleanup EXIT
    
    # 检查依赖
    check_dependencies || exit 1
    
    # 测试VPS连接
    test_vps_connection || exit 1
    
    # 导出cookies
    export_cookies || exit 1
    
    # 验证cookies
    validate_cookies
    
    # 上传cookies
    upload_cookies || exit 1
    
    # 检查VPS状态
    check_vps_cookies_status
    
    success "🎉 cookies更新完成！"
    log "详细日志已保存到: $LOG_FILE"
}

# 显示帮助信息
show_help() {
    echo "使用方法: $0 [选项]"
    echo ""
    echo "选项:"
    echo "  -h, --help     显示此帮助信息"
    echo "  -v, --version  显示版本信息"
    echo "  -c, --config   显示当前配置"
    echo ""
    echo "配置说明:"
    echo "  请编辑脚本开头的配置变量:"
    echo "  - VPS_HOST: VPS的IP地址或域名"
    echo "  - VPS_PORT: FastAPI服务端口"
    echo ""
    echo "示例:"
    echo "  $0                    # 执行cookies更新"
    echo "  $0 --config           # 显示当前配置"
}

# 显示配置
show_config() {
    echo "当前配置:"
    echo "  VPS地址: $VPS_HOST"
    echo "  VPS端口: $VPS_PORT"
    echo "  API地址: $VPS_URL"
    echo "  临时文件: $TEMP_COOKIES_FILE"
    echo "  日志文件: $LOG_FILE"
}

# 解析命令行参数
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    -v|--version)
        echo "YouTube Cookies 自动上传工具 v1.0"
        exit 0
        ;;
    -c|--config)
        show_config
        exit 0
        ;;
    "")
        main
        ;;
    *)
        error "未知参数: $1"
        show_help
        exit 1
        ;;
esac 