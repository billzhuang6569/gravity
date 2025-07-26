#!/bin/bash

# YT-DLP API 服务安装脚本
# 此脚本将配置API服务为系统服务，开机自动启动

set -e

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== YT-DLP API 服务安装脚本 ===${NC}"

# 检查是否以root权限运行
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}错误: 请使用 sudo 运行此脚本${NC}"
    exit 1
fi

# 获取当前脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVICE_NAME="ytdlp-api"
INSTALL_DIR="/opt/$SERVICE_NAME"
SERVICE_FILE="/etc/systemd/system/$SERVICE_NAME.service"

echo -e "${YELLOW}1. 检查系统依赖...${NC}"

# 检查Python3
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: Python3 未安装${NC}"
    echo "请先安装 Python3: sudo apt update && sudo apt install python3 python3-pip python3-venv"
    exit 1
fi

# 检查FFmpeg
if ! command -v ffmpeg &> /dev/null; then
    echo -e "${YELLOW}FFmpeg 未安装，正在安装...${NC}"
    apt update && apt install -y ffmpeg
fi

# 检查systemd
if ! command -v systemctl &> /dev/null; then
    echo -e "${RED}错误: 此系统不支持 systemd${NC}"
    exit 1
fi

echo -e "${GREEN}✓ 系统依赖检查完成${NC}"

echo -e "${YELLOW}2. 创建安装目录和用户...${NC}"

# 创建系统用户（如果不存在）
if ! id "www-data" &>/dev/null; then
    useradd --system --no-create-home --shell /bin/false www-data
    echo -e "${GREEN}✓ 创建了用户 www-data${NC}"
else
    echo -e "${GREEN}✓ 用户 www-data 已存在${NC}"
fi

# 创建安装目录
mkdir -p "$INSTALL_DIR"
echo -e "${GREEN}✓ 创建安装目录: $INSTALL_DIR${NC}"

echo -e "${YELLOW}3. 复制项目文件...${NC}"

# 复制应用文件
cp "$SCRIPT_DIR/main.py" "$INSTALL_DIR/"
cp "$SCRIPT_DIR/requirements.txt" "$INSTALL_DIR/"

# 如果存在其他Python文件也复制
if [ -f "$SCRIPT_DIR/test_api.py" ]; then
    cp "$SCRIPT_DIR/test_api.py" "$INSTALL_DIR/"
fi

echo -e "${GREEN}✓ 项目文件复制完成${NC}"

echo -e "${YELLOW}4. 设置Python虚拟环境...${NC}"

# 创建虚拟环境
cd "$INSTALL_DIR"
python3 -m venv venv
source venv/bin/activate

# 升级pip并安装依赖
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${GREEN}✓ Python环境设置完成${NC}"

echo -e "${YELLOW}5. 设置文件权限...${NC}"

# 设置目录权限
chown -R www-data:www-data "$INSTALL_DIR"
chmod -R 755 "$INSTALL_DIR"
chmod +x "$INSTALL_DIR/main.py"

echo -e "${GREEN}✓ 文件权限设置完成${NC}"

echo -e "${YELLOW}6. 安装systemd服务...${NC}"

# 创建服务文件
cat > "$SERVICE_FILE" << EOF
[Unit]
Description=YT-DLP FastAPI Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=$INSTALL_DIR
ExecStart=$INSTALL_DIR/venv/bin/python $INSTALL_DIR/main.py
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal
SyslogIdentifier=$SERVICE_NAME

# 环境变量
Environment=PYTHONPATH=$INSTALL_DIR
Environment=PYTHONUNBUFFERED=1

# 安全设置
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=$INSTALL_DIR /tmp
PrivateTmp=true

# 资源限制
LimitNOFILE=65536
MemoryMax=2G

[Install]
WantedBy=multi-user.target
EOF

# 重新加载systemd配置
systemctl daemon-reload

# 启用服务
systemctl enable "$SERVICE_NAME"

echo -e "${GREEN}✓ Systemd服务安装完成${NC}"

echo -e "${YELLOW}7. 配置防火墙...${NC}"

# 检查防火墙状态并开放端口
if command -v ufw &> /dev/null; then
    ufw allow 8018/tcp
    echo -e "${GREEN}✓ UFW防火墙已开放端口8018${NC}"
elif command -v firewall-cmd &> /dev/null; then
    firewall-cmd --permanent --add-port=8018/tcp
    firewall-cmd --reload
    echo -e "${GREEN}✓ FirewallD已开放端口8018${NC}"
else
    echo -e "${YELLOW}⚠ 未检测到防火墙，请手动开放端口8018${NC}"
fi

echo -e "${YELLOW}8. 启动服务...${NC}"

# 启动服务
systemctl start "$SERVICE_NAME"

# 等待服务启动
sleep 3

# 检查服务状态
if systemctl is-active --quiet "$SERVICE_NAME"; then
    echo -e "${GREEN}✓ 服务启动成功${NC}"
else
    echo -e "${RED}✗ 服务启动失败${NC}"
    echo "查看日志: sudo journalctl -u $SERVICE_NAME -f"
    exit 1
fi

echo -e "${BLUE}=== 安装完成 ===${NC}"
echo ""
echo -e "${GREEN}🎉 YT-DLP API 服务安装成功！${NC}"
echo ""
echo -e "${YELLOW}服务信息:${NC}"
echo "• 服务名称: $SERVICE_NAME"
echo "• 安装目录: $INSTALL_DIR"
echo "• 服务端口: 8018"
echo "• 服务状态: $(systemctl is-active $SERVICE_NAME)"
echo "• 开机启动: $(systemctl is-enabled $SERVICE_NAME)"
echo ""
echo -e "${YELLOW}管理命令:${NC}"
echo "• 查看状态: sudo systemctl status $SERVICE_NAME"
echo "• 启动服务: sudo systemctl start $SERVICE_NAME"
echo "• 停止服务: sudo systemctl stop $SERVICE_NAME"
echo "• 重启服务: sudo systemctl restart $SERVICE_NAME"
echo "• 查看日志: sudo journalctl -u $SERVICE_NAME -f"
echo "• 禁用开机启动: sudo systemctl disable $SERVICE_NAME"
echo ""
echo -e "${YELLOW}测试API:${NC}"
echo "• API根路径: http://$(hostname -I | awk '{print $1}'):8018"
echo "• 健康检查: curl http://localhost:8018/health"
echo "• API文档: http://$(hostname -I | awk '{print $1}'):8018/docs"
echo ""
echo -e "${YELLOW}清理命令 (如需卸载):${NC}"
echo "sudo systemctl stop $SERVICE_NAME && sudo systemctl disable $SERVICE_NAME && sudo rm $SERVICE_FILE && sudo rm -rf $INSTALL_DIR && sudo systemctl daemon-reload"