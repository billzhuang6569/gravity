# Gravity V5 - 生产环境部署指南

## 系统要求
- Ubuntu 20.04+ 或 CentOS 7+
- Python 3.8+
- Git
- 至少 2GB RAM
- 10GB 可用磁盘空间

## 快速部署

### 1. 克隆项目
```bash
git clone https://github.com/billzhuang6569/gravity.git
cd gravity
git checkout gravity-v5-production
```

### 2. 安装系统依赖
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git curl

# CentOS/RHEL
sudo yum install -y python3 python3-venv python3-pip git curl
```

### 3. 创建虚拟环境
```bash
python3 -m venv venv
source venv/bin/activate
```

### 4. 安装Python依赖
```bash
pip install -r requirements.txt
```

### 5. 配置环境变量
```bash
cp .env.example .env
# 编辑 .env 文件，设置你的配置
nano .env
```

### 6. 启动服务
```bash
# 开发模式
python main.py

# 生产模式 (推荐)
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# 使用Docker (可选)
chmod +x run.sh
./run.sh
```

## Docker 部署

### 使用 docker-compose（推荐）
```bash
docker-compose up -d
```

### 手动Docker部署
```bash
# 构建镜像
docker build -t gravity-v5 .

# 运行容器
docker run -d \
  --name gravity-v5 \
  -p 8000:8000 \
  -v $(pwd)/downloads:/app/downloads \
  -v $(pwd)/cookies:/app/cookies \
  gravity-v5
```

## 服务管理

### 使用 systemd（推荐生产环境）
创建服务文件：
```bash
sudo nano /etc/systemd/system/gravity-v5.service
```

内容：
```ini
[Unit]
Description=Gravity V5 Video Downloader API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/gravity
Environment=PATH=/path/to/gravity/venv/bin
ExecStart=/path/to/gravity/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

启动服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable gravity-v5
sudo systemctl start gravity-v5
sudo systemctl status gravity-v5
```

## 反向代理配置

### Nginx 配置示例
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 100M;
    }
}
```

## 防火墙配置
```bash
# Ubuntu (ufw)
sudo ufw allow 8000/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# CentOS (firewalld)
sudo firewall-cmd --permanent --add-port=8000/tcp
sudo firewall-cmd --permanent --add-port=80/tcp
sudo firewall-cmd --permanent --add-port=443/tcp
sudo firewall-cmd --reload
```

## 监控和日志
```bash
# 查看应用日志
tail -f app.log

# 查看系统服务日志
sudo journalctl -u gravity-v5 -f

# 查看Docker日志
docker logs -f gravity-v5
```

## 性能优化

### 1. 调整Worker数量
根据CPU核心数调整uvicorn workers：
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --workers $(nproc)
```

### 2. 配置文件上传限制
在`.env`中设置：
```
MAX_FILE_SIZE=104857600  # 100MB
MAX_CONCURRENT_DOWNLOADS=10
```

### 3. 磁盘空间管理
定期清理下载目录：
```bash
# 删除7天前的文件
find downloads/ -type f -mtime +7 -delete
```

## 故障排除

### 常见问题
1. **端口被占用**: 使用 `lsof -i :8000` 检查端口使用情况
2. **权限问题**: 确保下载目录有写入权限
3. **内存不足**: 监控内存使用，必要时增加swap
4. **网络问题**: 检查防火墙和网络连接

### 测试API
```bash
# 健康检查
curl http://localhost:8000/

# 测试视频信息获取
curl -X POST "http://localhost:8000/api/v1/info" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.bilibili.com/video/BV1xx411c7mu"}'
```

## 安全建议

1. 使用非root用户运行服务
2. 配置防火墙只开放必要端口
3. 定期更新系统和依赖包
4. 使用HTTPS（配置SSL证书）
5. 限制API访问频率
6. 定期备份配置和重要数据

## 支持与联系

如有问题，请查看：
- GitHub Issues: https://github.com/billzhuang6569/gravity/issues
- 项目文档: README.md
- API文档: http://your-domain.com/docs 