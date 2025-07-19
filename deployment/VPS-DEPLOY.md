# 🚀 VPS 一键部署指南

## 📋 部署前准备

### 1. 服务器要求
- **操作系统**: Ubuntu 20.04+ / CentOS 8+ / Debian 11+
- **CPU**: 2核以上
- **内存**: 2GB+ (推荐 4GB)
- **磁盘**: 20GB+
- **端口**: 19280, 19282, 19283 (不常见端口，避免冲突)

### 2. 安装 Docker 和 Docker Compose

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

# 启动 Docker 服务
sudo systemctl enable docker
sudo systemctl start docker

# 重新登录生效权限
exit
# 重新连接服务器
```

## 🎯 一键部署

### 1. 下载项目

```bash
# 克隆项目
git clone https://github.com/billzhuang6569/gravity.git
cd gravity/deployment
```

### 2. 执行一键部署

```bash
# 运行部署脚本
./deploy-vps.sh
```

**部署过程**：
1. ✅ 检查依赖和端口
2. ✅ 创建环境配置
3. ✅ 构建应用镜像
4. ✅ 启动所有服务
5. ✅ 执行健康检查

### 3. 访问应用

部署成功后，你将看到访问地址：

```
🎉 部署成功！

访问地址:
🌐 前端界面: http://YOUR-SERVER-IP:19280
📚 API 文档: http://YOUR-SERVER-IP:19282/docs
🔍 健康检查: http://YOUR-SERVER-IP:19280/health
```

## 🛠️ 管理命令

### 日常管理

```bash
# 查看服务状态
./manage.sh status

# 查看实时日志
./manage.sh logs

# 查看特定服务日志
./manage.sh logs api

# 重启服务
./manage.sh restart

# 停止服务
./manage.sh stop

# 启动服务
./manage.sh start
```

### 健康检查

```bash
# 执行健康检查
./manage.sh health
```

输出示例：
```
🔍 健康检查:
  ✅ Redis (19283): 健康
  ✅ API (19282): 健康  
  ✅ 前端 (19280): 健康
```

### 调试命令

```bash
# 进入 API 容器
./manage.sh shell

# 进入 Redis 命令行
./manage.sh redis-cli
```

## 🔧 配置说明

### 端口配置

| 服务 | 内部端口 | 外部端口 | 说明 |
|------|----------|----------|------|
| 前端 | 80 | 19280 | Web 界面 |
| API | 8000 | 19282 | REST API |
| Redis | 6379 | 19283 | 数据库 |

### 环境变量

部署脚本会自动创建 `.env` 文件：

```bash
# Redis 密码 (建议修改)
REDIS_PASSWORD=GravitySecure2024!

# 应用配置
APP_NAME=Gravity Video Downloader
APP_VERSION=1.0.0
DEBUG=false
LOG_LEVEL=INFO

# 安全密钥 (建议修改)
SECRET_KEY=GravityVideoDownloader2024SecureKey123456789

# 代理配置 (可选，用于 YouTube 访问)
# HTTP_PROXY=http://proxy.example.com:8080
# HTTPS_PROXY=https://proxy.example.com:8080
```

### 数据持久化

以下数据会持久化存储：

- 📁 **下载文件**: `/opt/gravity/downloads`
- 🗃️ **Redis 数据**: 任务队列和历史记录
- 📝 **应用日志**: 系统运行日志
- ⏰ **定时任务**: Celery Beat 调度数据

## 🔥 防火墙配置

```bash
# 开放必要端口
sudo ufw allow 19280/tcp  # HTTP 前端
sudo ufw allow 19282/tcp  # API 服务
sudo ufw allow 22/tcp     # SSH 连接
sudo ufw enable

# 查看防火墙状态
sudo ufw status
```

## 🚨 故障排除

### 常见问题

#### 1. 端口被占用
```bash
# 检查端口占用
netstat -tlnp | grep -E "(19280|19282|19283)"

# 如果有冲突，修改 docker-compose.production.yml 中的端口
```

#### 2. 服务启动失败
```bash
# 查看详细日志
./manage.sh logs

# 查看特定服务日志
./manage.sh logs api
```

#### 3. 容器重启循环
```bash
# 检查容器状态
docker-compose -f docker-compose.production.yml ps

# 查看容器日志
docker-compose -f docker-compose.production.yml logs api
```

#### 4. API 无法访问
```bash
# 检查 API 健康状态
curl http://localhost:19282/api/v1/health

# 检查防火墙
sudo ufw status

# 检查端口监听
netstat -tlnp | grep 19282
```

#### 5. 前端无法访问
```bash
# 检查前端健康状态
curl http://localhost:19280/health

# 检查 Nginx 配置
./manage.sh logs frontend
```

### 完全重置

如果需要完全重新部署：

```bash
# 停止并删除所有容器和数据
docker-compose -f docker-compose.production.yml down -v

# 清理 Docker 资源
docker system prune -af
docker volume prune -f

# 重新部署
./deploy-vps.sh
```

## 🎯 性能优化

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

编辑 `docker-compose.production.yml`：

```yaml
# 为服务添加资源限制
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 2G
    reservations:
      cpus: '1.0'
      memory: 1G
```

## 📊 监控建议

### 日志监控

```bash
# 设置日志轮转
sudo nano /etc/logrotate.d/gravity-docker

# 添加以下内容：
/var/lib/docker/containers/*/*.log {
    rotate 7
    daily
    compress
    size=10M
    missingok
    delaycompress
    copytruncate
}
```

### 定期维护

```bash
# 添加到 crontab
crontab -e

# 每周清理 Docker 资源
0 3 * * 0 cd /opt/gravity/deployment && docker system prune -f

# 每天检查服务健康状态
0 6 * * * cd /opt/gravity/deployment && ./manage.sh health
```

## 🆘 获取帮助

1. **查看状态**: `./manage.sh status`
2. **查看日志**: `./manage.sh logs`
3. **健康检查**: `./manage.sh health`
4. **GitHub Issues**: https://github.com/billzhuang6569/gravity/issues

---

🎉 现在你可以在任何 VPS 上一键部署 Gravity Video Downloader 了！