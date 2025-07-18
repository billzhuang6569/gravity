# 🚀 VPS 部署指南

## 快速部署 (推荐)

### 1. 服务器环境准备

在 VPS 上执行以下命令：

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 重新登录以应用 Docker 用户组
exit
```

### 2. 部署应用

```bash
# 克隆项目
git clone https://github.com/billzhuang6569/gravity.git
cd gravity/deployment

# 复制并编辑环境变量
cp .env.example .env
nano .env

# 运行一键部署脚本
chmod +x deploy.sh
./deploy.sh
```

### 3. 访问应用

- 前端界面: https://your-server-ip
- API 文档: https://your-server-ip:8001/docs

## 详细配置

### 环境变量配置

编辑 `.env` 文件：

```bash
# Redis 密码（必须修改）
REDIS_PASSWORD=your_secure_redis_password

# 应用配置
APP_NAME=Gravity Video Downloader
APP_VERSION=1.0.0
DEBUG=false

# 安全密钥（必须修改）
SECRET_KEY=your_very_secure_secret_key_32_chars_min

# 域名配置
DOMAIN=your-domain.com
EMAIL=your-email@example.com

# 代理配置（如果需要访问 YouTube）
# HTTP_PROXY=http://proxy.example.com:8080
# HTTPS_PROXY=https://proxy.example.com:8080
```

### SSL 证书配置

#### 方式1: Let's Encrypt (推荐)

```bash
# 安装 certbot
sudo apt install certbot

# 获取 SSL 证书
sudo certbot certonly --standalone -d your-domain.com

# 复制证书到项目目录
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem ssl/cert.pem
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem ssl/key.pem
sudo chown $USER:$USER ssl/*.pem
```

#### 方式2: 自签名证书

```bash
# 生成自签名证书
./manage.sh ssl
```

### 防火墙配置

```bash
# 开放必要端口
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 22/tcp
sudo ufw enable
```

## 管理命令

项目提供了完整的管理脚本：

```bash
# 给脚本添加执行权限
chmod +x manage.sh

# 启动服务
./manage.sh start

# 停止服务
./manage.sh stop

# 重启服务
./manage.sh restart

# 查看状态
./manage.sh status

# 查看日志
./manage.sh logs

# 查看特定服务日志
./manage.sh logs api

# 更新应用
./manage.sh update

# 备份数据
./manage.sh backup

# 恢复数据
./manage.sh restore backup_20241201_120000

# 进入容器
./manage.sh shell

# 清理资源
./manage.sh clean

# 监控资源使用
./manage.sh monitor
```

## 服务架构

```
┌─────────────────┐    ┌─────────────────┐
│   Nginx         │    │   API Server    │
│   (Frontend)    │◄───┤   (FastAPI)     │
│   Port: 80/443  │    │   Port: 8001    │
└─────────────────┘    └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   Redis         │
                       │   (Cache/Queue) │
                       │   Port: 6379    │
                       └─────────────────┘
                                │
                    ┌─────────────┬─────────────┐
            ┌─────────────────┐  │ ┌─────────────────┐
            │   Celery        │  │ │   Celery        │
            │   Worker        │  │ │   Beat          │
            │   (Downloads)   │  │ │   (Schedule)    │
            └─────────────────┘  │ └─────────────────┘
                                │
                       ┌─────────────────┐
                       │   Volumes       │
                       │   (Persistent)  │
                       └─────────────────┘
```

## 性能优化

### 系统级优化

```bash
# 增加文件描述符限制
echo "* soft nofile 65536" | sudo tee -a /etc/security/limits.conf
echo "* hard nofile 65536" | sudo tee -a /etc/security/limits.conf

# 优化内核参数
echo "net.core.somaxconn = 1024" | sudo tee -a /etc/sysctl.conf
echo "net.core.netdev_max_backlog = 5000" | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

### 应用级优化

修改 `docker-compose.yml` 中的资源限制：

```yaml
api:
  deploy:
    resources:
      limits:
        cpus: '2.0'
        memory: 2G
      reservations:
        cpus: '1.0'
        memory: 1G
```

## 监控与维护

### 日志管理

```bash
# 查看应用日志
./manage.sh logs

# 查看系统日志
sudo journalctl -u docker

# 清理日志
docker system prune -f
```

### 定期维护

创建定时任务：

```bash
# 编辑 crontab
crontab -e

# 添加以下内容：
# 每天凌晨 2 点备份数据
0 2 * * * cd /path/to/gravity/deployment && ./manage.sh backup

# 每周清理 Docker 资源
0 3 * * 0 cd /path/to/gravity/deployment && ./manage.sh clean
```

## 故障排除

### 常见问题

1. **端口被占用**
   ```bash
   sudo netstat -tlnp | grep :80
   sudo lsof -i :80
   ```

2. **权限问题**
   ```bash
   sudo chown -R $USER:$USER /path/to/gravity
   ```

3. **内存不足**
   ```bash
   free -h
   docker stats
   ```

4. **磁盘空间不足**
   ```bash
   df -h
   docker system df
   ./manage.sh clean
   ```

### 获取帮助

- 查看服务状态: `./manage.sh status`
- 查看日志: `./manage.sh logs`
- 监控资源: `./manage.sh monitor`
- GitHub Issues: https://github.com/billzhuang6569/gravity/issues

## 安全建议

1. 修改默认密码
2. 定期更新系统和应用
3. 配置防火墙
4. 使用 HTTPS
5. 定期备份数据
6. 监控系统资源

---

🎉 现在你可以在 VPS 上轻松部署和管理 Gravity Video Downloader 了！