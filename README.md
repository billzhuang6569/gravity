# 视频下载API服务

基于 [you-get](https://github.com/soimort/you-get) 的FastAPI视频下载服务，支持多种视频网站的视频下载，提供简单易用的REST API接口。

## 功能特性

- 🎬 支持多种视频网站（Bilibili、YouTube、优酷等）
- 📡 RESTful API接口，易于集成
- 📦 两种下载模式：直接文件流 / 下载链接
- 🐳 Docker容器化部署
- 🔄 自动文件清理机制
- 📊 健康检查和监控
- 📝 详细的日志记录
- 🚀 异步处理，高性能

## 支持的网站

基于you-get，支持以下网站（部分）：
- Bilibili (哔哩哔哩)
- YouTube
- 优酷 (Youku)
- 土豆 (Tudou)
- 爱奇艺 (iQIYI)
- 腾讯视频
- 网易云音乐
- 更多网站请参考 [you-get支持列表](https://github.com/soimort/you-get#supported-sites)

## 快速开始

### 使用Docker (推荐)

1. 克隆项目：
```bash
git clone <repository-url>
cd video-downloader-api
```

2. 启动服务：
```bash
docker-compose up -d
```

3. 访问API文档：
```
http://localhost:8000/docs
```

### 本地开发

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 安装you-get：
```bash
pip install you-get
```

3. 启动服务：
```bash
python main.py
```

## API接口

### 基础信息

- **基础URL**: `http://localhost:8000/api/v1`
- **文档地址**: `http://localhost:8000/docs`

### 主要端点

#### 1. 健康检查
```bash
GET /api/v1/health
```

#### 2. 获取视频信息
```bash
POST /api/v1/info
Content-Type: application/json

{
    "url": "https://www.bilibili.com/video/BV1xx411c7XD"
}
```

#### 3. 下载视频（返回下载链接）
```bash
POST /api/v1/download
Content-Type: application/json

{
    "url": "https://www.bilibili.com/video/BV1xx411c7XD",
    "mode": "link",
    "quality": "720p"
}
```

#### 4. 下载视频（直接返回文件流）
```bash
POST /api/v1/download/stream
Content-Type: application/json

{
    "url": "https://www.bilibili.com/video/BV1xx411c7XD",
    "quality": "720p"
}
```

#### 5. 获取下载文件
```bash
GET /api/v1/files/{filename}
```

#### 6. 清理文件
```bash
DELETE /api/v1/cleanup
```

## 请求参数

### DownloadRequest

| 参数 | 类型 | 必须 | 说明 |
|------|------|------|------|
| url | string | 是 | 视频URL |
| mode | string | 否 | 下载模式：stream/link/both |
| quality | string | 否 | 视频质量 |
| format | string | 否 | 视频格式 |

## 配置选项

### 环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

主要配置项：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| HOST | 0.0.0.0 | 服务监听地址 |
| PORT | 8000 | 服务端口 |
| DOWNLOAD_DIR | ./downloads | 下载目录 |
| CLEANUP_INTERVAL | 3600 | 文件清理间隔(秒) |
| MAX_FILE_SIZE | 1073741824 | 最大文件大小(字节) |

## 部署到VPS

### 1. 使用Docker Compose

```bash
# 上传项目文件到VPS
scp -r . user@your-vps:/path/to/app

# SSH到VPS
ssh user@your-vps

# 进入项目目录
cd /path/to/app

# 启动服务
docker-compose up -d

# 查看日志
docker-compose logs -f
```

### 2. 使用systemd (Ubuntu/CentOS)

创建systemd服务文件：

```bash
sudo tee /etc/systemd/system/video-downloader.service << EOF
[Unit]
Description=Video Downloader API
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/path/to/app
ExecStart=/usr/bin/python3 main.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动服务
sudo systemctl enable video-downloader
sudo systemctl start video-downloader
sudo systemctl status video-downloader
```

### 3. 使用Nginx反向代理

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
    }
}
```

## 使用示例

### Python客户端

```python
import requests

# 获取视频信息
response = requests.post(
    'http://localhost:8000/api/v1/info',
    json={'url': 'https://www.bilibili.com/video/BV1xx411c7XD'}
)
print(response.json())

# 下载视频
response = requests.post(
    'http://localhost:8000/api/v1/download',
    json={
        'url': 'https://www.bilibili.com/video/BV1xx411c7XD',
        'mode': 'link'
    }
)
result = response.json()
if result['success']:
    download_url = result['download_url']
    print(f"下载链接: {download_url}")
```

### curl示例

```bash
# 获取视频信息
curl -X POST "http://localhost:8000/api/v1/info" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.bilibili.com/video/BV1xx411c7XD"}'

# 下载视频
curl -X POST "http://localhost:8000/api/v1/download" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.bilibili.com/video/BV1xx411c7XD", "mode": "link"}'

# 直接下载到文件
curl -X POST "http://localhost:8000/api/v1/download/stream" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://www.bilibili.com/video/BV1xx411c7XD"}' \
     --output "video.mp4"
```

## 注意事项

1. **依赖you-get**: 确保you-get能正常工作并支持目标网站
2. **存储空间**: 下载的视频会临时存储，注意磁盘空间
3. **网络环境**: 某些网站可能需要特定的网络环境
4. **版权问题**: 请遵守相关网站的使用条款和版权法律
5. **性能**: 大文件下载可能耗时较长，建议设置合理的超时时间

## 故障排除

### 常见问题

1. **you-get命令不存在**
   ```bash
   pip install you-get
   ```

2. **下载失败**
   - 检查URL是否有效
   - 检查网络连接
   - 查看日志文件：`docker-compose logs`

3. **权限问题**
   ```bash
   chmod -R 755 downloads/
   ```

4. **端口被占用**
   - 修改`.env`中的`PORT`配置
   - 或使用`docker-compose.yml`中的端口映射

## 开发

### 项目结构

```
.
├── app/
│   ├── __init__.py
│   ├── config.py              # 配置管理
│   ├── api/
│   │   └── routes.py          # API路由
│   ├── core/
│   │   └── downloader.py      # 下载核心逻辑
│   └── models/
│       └── schemas.py         # 数据模型
├── main.py                    # 应用入口
├── requirements.txt           # 依赖包
├── Dockerfile                 # Docker配置
├── docker-compose.yml         # 服务编排
└── README.md                  # 项目文档
```

### 贡献

欢迎提交Issue和Pull Request！

## 许可证

MIT License

## 相关链接

- [you-get GitHub](https://github.com/soimort/you-get)
- [FastAPI文档](https://fastapi.tiangolo.com/)
- [Docker文档](https://docs.docker.com/) 