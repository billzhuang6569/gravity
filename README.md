# 🌌 Gravity Video Downloader

一个功能强大的多平台视频下载工具，支持实时进度跟踪和文件管理。

## ✨ 功能特色

- **多平台支持**: 支持 Bilibili 和 YouTube 视频下载
- **实时进度跟踪**: 基于 WebSocket 的实时下载进度显示
- **多种格式支持**: 视频下载、音频提取（MP3、M4A、WAV）
- **质量选择**: 支持不同清晰度选择（最佳质量、720p、1080p等）
- **智能文件管理**: 自动文件命名、存储管理和清理
- **任务队列**: 基于 Celery 的分布式任务处理
- **下载历史**: 完整的下载历史记录和重新下载功能
- **响应式界面**: 现代化的纯 JavaScript 前端界面
- **错误处理**: 全面的错误处理和重试机制

## 🏗️ 技术架构

### 后端技术栈
- **FastAPI**: 现代化的 Python Web 框架
- **Celery**: 分布式任务队列系统
- **Redis**: 数据缓存和任务代理
- **yt-dlp**: 强大的视频下载库
- **Pydantic**: 数据验证和序列化

### 前端技术栈
- **纯 JavaScript**: 无框架依赖的现代化前端
- **HTML5 + CSS3**: 响应式设计
- **Fetch API**: 现代化的 HTTP 请求

### 支持的平台
- **Bilibili**: 哔哩哔哩视频平台
- **YouTube**: 谷歌视频平台

基于 yt-dlp 2023.12.30 版本，理论上支持 [1000+ 网站](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)，但本项目专门针对 Bilibili 和 YouTube 进行了优化。

## 📦 快速开始

### 环境要求
- Python 3.8+
- Node.js 14+ (可选，用于开发)
- Redis 服务器
- 系统依赖: `ffmpeg`（用于视频处理）

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/billzhuang6569/gravity.git
   cd gravity
   ```

2. **后端设置**
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或 venv\Scripts\activate  # Windows
   pip install -r requirements.txt
   ```

3. **环境配置**
   ```bash
   cp .env.example .env
   # 编辑 .env 文件，配置 Redis 连接等
   ```

4. **启动服务**
   ```bash
   # 方式1: 使用 Docker Compose（推荐）
   cd deployment
   docker-compose up -d
   
   # 方式2: 手动启动各服务
   # 终端1: 启动 Redis
   redis-server
   
   # 终端2: 启动 API 服务器
   cd backend
   source venv/bin/activate
   uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
   
   # 终端3: 启动 Celery Worker
   cd backend
   source venv/bin/activate
   python worker.py
   
   # 终端4: 启动 Celery Beat（定时任务）
   cd backend
   source venv/bin/activate
   python beat.py
   
   # 终端5: 启动前端服务器
   cd frontend
   python -m http.server 8080
   ```

5. **访问应用**
   - 前端界面: http://localhost:8080
   - API 文档: http://localhost:8001/docs

## 🔧 配置说明

### 环境变量
```bash
# Redis 配置
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=
REDIS_DB=0

# 应用配置
DEBUG=false
APP_NAME=Gravity Video Downloader
APP_VERSION=1.0.0

# 文件路径配置
DOWNLOADS_PATH=/opt/gravity/downloads
TEMP_PATH=/opt/gravity/temp

# 代理配置（可选）
HTTP_PROXY=http://proxy.example.com:8080
HTTPS_PROXY=https://proxy.example.com:8080
```

### Celery 配置
- **队列**: `downloads`（主要）、`maintenance`（维护）、`health`（健康检查）
- **并发**: 基于 CPU 核心数动态调整（cores × 2）
- **重试策略**: 3次重试，指数退避
- **超时**: 30分钟软超时，31分钟硬超时

## 🎯 使用指南

### 基本使用
1. 在输入框中粘贴视频链接
2. 点击"解析"按钮获取视频信息
3. 选择下载格式和质量
4. 点击"开始下载"
5. 实时查看下载进度
6. 下载完成后点击"下载"按钮保存文件

### 支持的 URL 格式
- **YouTube**: 
  - `https://www.youtube.com/watch?v=VIDEO_ID`
  - `https://youtu.be/VIDEO_ID`
  - `https://youtube.com/embed/VIDEO_ID`
- **Bilibili**:
  - `https://www.bilibili.com/video/BV1234567890`
  - `https://www.bilibili.com/video/av123456789`
  - `https://b23.tv/SHORT_URL`

### 下载选项
- **格式**: 视频文件或纯音频
- **质量**: 最佳质量、720p、1080p等
- **音频格式**: MP3、M4A、WAV（仅音频模式）

## 🛠️ 开发指南

### 项目结构
```
gravity/
├── backend/                 # 后端服务
│   ├── app/                # 应用代码
│   │   ├── api/           # API 端点
│   │   ├── models/        # 数据模型
│   │   ├── services/      # 业务逻辑
│   │   ├── tasks/         # Celery 任务
│   │   └── config.py      # 配置文件
│   ├── tests/             # 测试文件
│   └── requirements.txt   # 依赖管理
├── frontend/              # 前端应用
│   ├── index.html        # 主页面
│   ├── app.js            # 主应用逻辑
│   └── styles.css        # 样式文件
├── deployment/           # 部署配置
└── README.md
```

### 开发命令
```bash
# 运行测试
cd backend
pytest

# 代码格式化
black app/
isort app/

# 类型检查
mypy app/

# 启动开发服务器
uvicorn app.main:app --reload
```

### API 端点
- `POST /api/v1/downloads/info` - 获取视频信息
- `POST /api/v1/downloads` - 提交下载任务
- `GET /api/v1/downloads/{task_id}/status` - 查询任务状态
- `GET /api/v1/downloads/history` - 获取下载历史
- `GET /api/v1/downloads/{filename}` - 下载文件
- `GET /api/v1/health` - 健康检查

## 🚀 部署指南

### Docker 部署（推荐）
```bash
cd deployment
docker-compose up -d
```

### 手动部署
1. 安装依赖和配置环境
2. 配置 Nginx 反向代理
3. 使用 systemd 管理服务
4. 设置定时任务和日志轮转

### 生产环境建议
- 使用 Gunicorn 作为 WSGI 服务器
- 配置 Nginx 处理静态文件
- 使用 Redis Cluster 提高可用性
- 实施日志聚合和监控
- 定期备份下载历史

## 🔒 安全考虑

- 输入验证和 URL 白名单
- 文件路径安全检查
- 下载大小限制
- 代理配置安全
- CORS 策略配置

## 📈 性能优化

- Redis 连接池管理
- 异步任务处理
- 文件流式下载
- 自动清理机制
- 内存使用监控

## 🐛 故障排除

### 常见问题
1. **Redis 连接失败**: 检查 Redis 服务状态和配置
2. **YouTube 访问受限**: 配置 HTTP 代理
3. **下载速度慢**: 检查网络连接和代理设置
4. **文件权限错误**: 确保下载目录有写权限
5. **Celery Worker 无响应**: 重启 Worker 进程

### 日志查看
```bash
# 应用日志
tail -f logs/app.log

# Celery 日志
tail -f logs/celery.log

# Redis 日志
tail -f /var/log/redis/redis-server.log
```

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 🙏 致谢

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - 强大的视频下载库
- [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Web 框架
- [Celery](https://docs.celeryproject.org/) - 分布式任务队列
- [Redis](https://redis.io/) - 内存数据库

## 📞 联系方式

- 项目主页: https://github.com/billzhuang6569/gravity
- 问题报告: https://github.com/billzhuang6569/gravity/issues

---

⭐ 如果这个项目对你有帮助，请给它一个星标！