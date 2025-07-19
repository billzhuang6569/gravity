# Gravity Video Downloader

一个基于 yt-dlp 的现代化网页视频下载器，提供简洁美观的用户界面和强大的下载功能。

## ✨ 功能特性

- 🎯 **支持数百个网站**：基于 yt-dlp，支持 YouTube、Bilibili、Twitter 等主流平台
- 🎨 **现代界面设计**：类似 Mac Downie 的简约风格，支持渐变和毛玻璃效果
- ⚡ **快速下载**：直接粘贴 URL 即可开始下载，无需复杂配置
- 📱 **响应式设计**：完美支持桌面和移动端
- 🔄 **实时进度**：实时显示下载进度和状态
- 🎛️ **格式选择**：支持选择视频质量和格式（视频/音频）
- 🚀 **并发下载**：支持多任务同时下载
- 📦 **容器化部署**：一键部署到 VPS，每个人都可以拥有自己的下载站

## 🛠 技术栈

### 前端
- React 18 + TypeScript
- Tailwind CSS
- Framer Motion
- Lucide React
- React Query

### 后端
- Node.js + Express + TypeScript
- SQLite
- Bull Queue
- yt-dlp

### 部署
- Docker + Docker Compose
- Nginx (可选)

## 🚀 快速开始

### 使用 Docker 部署

1. 克隆项目
```bash
git clone https://github.com/your-username/gravity-video-downloader.git
cd gravity-video-downloader
```

2. 启动服务
```bash
docker-compose up -d
```

3. 访问应用
打开浏览器访问 `http://localhost:3000`

### 开发环境

1. 安装依赖
```bash
# 安装前端依赖
cd frontend
npm install

# 安装后端依赖
cd ../backend
npm install
```

2. 启动开发服务器
```bash
# 启动后端服务
cd backend
npm run dev

# 启动前端服务
cd frontend
npm run dev
```

## 📖 API 文档

### 创建下载任务
```http
POST /api/tasks
Content-Type: application/json

{
  "url": "https://www.youtube.com/watch?v=example",
  "format": "best",
  "type": "video"
}
```

### 获取任务状态
```http
GET /api/tasks/:id
```

### 下载文件
```http
GET /api/tasks/:id/download
```

## 🔧 配置说明

### 环境变量

```env
# 服务器配置
PORT=3000
NODE_ENV=production

# 数据库配置
DATABASE_URL=./data/downloads.db

# 下载配置
DOWNLOAD_PATH=./downloads
MAX_CONCURRENT_DOWNLOADS=3
MAX_FILE_SIZE=1073741824  # 1GB

# Redis 配置（用于任务队列）
REDIS_URL=redis://localhost:6379
```

## 📝 使用说明

1. **开始下载**：在主页直接粘贴视频 URL
2. **选择格式**：选择视频质量或音频格式
3. **监控进度**：实时查看下载进度
4. **下载文件**：完成后点击下载按钮获取文件

## 🤝 贡献指南

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## ⚠️ 免责声明

本工具仅供学习和个人使用，请遵守相关网站的条款和版权法律。使用者需自行承担使用风险。 