#!/bin/bash

# Gravity Video Downloader - 主部署脚本
# 使用不常见端口: 19280-19283 避免冲突

set -e

echo "🌌 Gravity Video Downloader - 主部署脚本"
echo "=================================================="
echo ""

# 检查是否为 root 用户
if [[ $EUID -eq 0 ]]; then
   echo "⚠️  不建议使用 root 用户运行此脚本"
   echo "   建议创建普通用户并添加到 docker 组"
   read -p "是否继续? (y/N): " -n 1 -r
   echo
   if [[ ! $REPLY =~ ^[Yy]$ ]]; then
       exit 1
   fi
fi

# 检查部署方式
echo "请选择部署方式:"
echo "1. VPS 完整部署 (推荐)"
echo "2. 仅检查端口冲突"
echo "3. 查看部署文档"
echo ""
read -p "请输入选项 (1-3): " -n 1 -r
echo

case $REPLY in
    1)
        echo "🚀 执行 VPS 完整部署..."
        if [ -f "deploy-vps.sh" ]; then
            ./deploy-vps.sh
        else
            echo "❌ deploy-vps.sh 文件不存在"
            exit 1
        fi
        ;;
    2)
        echo "🔍 检查端口冲突..."
        if [ -f "check-ports.sh" ]; then
            ./check-ports.sh
        else
            echo "❌ check-ports.sh 文件不存在"
            exit 1
        fi
        ;;
    3)
        echo "📚 部署文档..."
        if [ -f "VPS-DEPLOY.md" ]; then
            echo "文档位置: VPS-DEPLOY.md"
            echo "在线查看: https://github.com/billzhuang6569/gravity/blob/main/deployment/VPS-DEPLOY.md"
        else
            echo "❌ VPS-DEPLOY.md 文件不存在"
            exit 1
        fi
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac