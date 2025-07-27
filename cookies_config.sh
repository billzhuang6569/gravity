#!/bin/bash

# 🍪 YouTube Cookies 配置文件
# 复制此文件并修改配置，然后重命名为 upload_cookies_to_vps.sh

# VPS配置
VPS_HOST="your-vps-ip-or-domain"  # 替换为你的VPS IP地址或域名
VPS_PORT="8018"                   # FastAPI服务端口

# 可选配置
VPS_URL="http://${VPS_HOST}:${VPS_PORT}"
TEMP_COOKIES_FILE="/tmp/cookies_$(date +%s).txt"
LOG_FILE="/tmp/cookies_upload.log"

# 浏览器配置 (可选)
BROWSER="chrome"  # 可选: chrome, firefox, safari, edge

# 网络配置 (可选)
CURL_TIMEOUT="10"  # 连接超时时间(秒)
RETRY_COUNT="3"    # 重试次数

echo "请修改此文件中的配置，然后重命名为 upload_cookies_to_vps.sh"
echo "主要需要修改:"
echo "1. VPS_HOST: 你的VPS IP地址或域名"
echo "2. VPS_PORT: FastAPI服务端口 (默认8018)"
echo "3. 其他可选配置" 