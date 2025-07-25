# YT-DLP API 服务

基于 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 的 FastAPI 封装服务，提供 RESTful API 接口用于下载各大视频网站的视频。

## 功能特性

- 🎥 支持 1000+ 个视频网站（YouTube、Bilibili、Vimeo、Twitter等）
- 📊 获取视频信息和可用格式
- ⬇️ 异步下载视频和音频
- 🎵 音频提取（支持多种格式）
- 📝 字幕下载
- ⏱️ 实时下载进度跟踪
- 🔧 灵活的格式和质量选择
- 🐳 Docker 容器化部署
- 📚 自动生成的 API 文档

## 快速开始

### 使用 Docker（推荐）

1. 克隆项目：
```bash
git clone <repository-url>
cd ytdlp-api
```

2. 使用简化版 Docker Compose 启动：
```bash
docker-compose -f docker-compose.simple.yml up -d
```

3. 或者使用完整版（包含 Nginx）：
```bash
docker-compose up -d
```

4. 访问 API 文档：
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

### 本地开发

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 安装 FFmpeg（必需）：
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# macOS
brew install ffmpeg

# Windows
# 下载并安装 FFmpeg，添加到 PATH
```

3. 启动服务：
```bash
python main.py
```

## API 使用指南

### 1. 获取视频信息

```bash
curl "http://localhost:8000/info?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### 2. 获取可用格式

```bash
curl "http://localhost:8000/formats?url=https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

### 3. 下载视频

```bash
curl -X POST "http://localhost:8000/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "format": "best",
    "extract_audio": false
  }'
```

### 4. 下载音频

```bash
curl -X POST "http://localhost:8000/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "extract_audio": true,
    "audio_format": "mp3"
  }'
```

### 5. 查看下载进度

```bash
curl "http://localhost:8000/progress/{video_id}"
```

### 6. 下载文件

```bash
curl "http://localhost:8000/download/{video_id}?filename={filename}"
```

## API 端点详解

### 基础端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/` | API 信息 |
| GET | `/health` | 健康检查 |
| GET | `/docs` | Swagger 文档 |
| GET | `/redoc` | ReDoc 文档 |

### 视频信息

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/info` | 获取视频信息 |
| GET | `/formats` | 获取可用格式 |
| GET | `/supported-sites` | 获取支持的网站列表 |

### 下载功能

| 方法 | 端点 | 描述 |
|------|------|------|
| POST | `/download` | 开始下载视频 |
| GET | `/download/{video_id}` | 下载文件 |
| GET | `/progress/{video_id}` | 获取下载进度 |

### 管理功能

| 方法 | 端点 | 描述 |
|------|------|------|
| DELETE | `/cleanup` | 清理临时文件 |
| GET | `/stats` | 获取服务统计信息 |

## 请求参数

### 下载请求 (POST /download)

```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "format": "best",
  "quality": "best",
  "extract_audio": false,
  "audio_format": "mp3",
  "output_template": "%(title)s.%(ext)s",
  "download_sections": null,
  "write_subs": false,
  "sub_langs": "en"
}
```

#### 参数说明

- `url` (必需): 视频URL
- `format` (可选): 视频格式，默认为 "best"
  - `best`: 最佳质量
  - `worst`: 最低质量
  - `bv*+ba/b`: 最佳视频+音频
  - `bv*[height<=720]+ba/b`: 720p以下最佳
- `extract_audio` (可选): 是否提取音频，默认 false
- `audio_format` (可选): 音频格式，支持 mp3, m4a, wav, flac, opus
- `write_subs` (可选): 是否下载字幕，默认 false
- `sub_langs` (可选): 字幕语言，默认 "en"

### 格式选择示例

```bash
# 下载最佳质量
"format": "best"

# 下载最佳视频+音频
"format": "bv*+ba/b"

# 下载MP4格式
"format": "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/b"

# 下载720p以下
"format": "bv*[height<=720]+ba/b[height<=720]/b"

# 下载音频
"format": "ba"
```

## 部署到 Ubuntu 服务器

### 1. 安装 Docker 和 Docker Compose

```bash
# 更新系统
sudo apt update && sudo apt upgrade -y

# 安装 Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# 安装 Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/download/v2.20.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 将用户添加到 docker 组
sudo usermod -aG docker $USER
```

### 2. 部署应用

```bash
# 克隆项目
git clone <repository-url>
cd ytdlp-api

# 启动服务
docker-compose -f docker-compose.simple.yml up -d

# 查看日志
docker-compose -f docker-compose.simple.yml logs -f
```

### 3. 配置防火墙

```bash
# 开放端口
sudo ufw allow 8000
sudo ufw allow 80
sudo ufw allow 443

# 启用防火墙
sudo ufw enable
```

### 4. 配置反向代理（可选）

如果需要使用域名访问，可以配置 Nginx 反向代理：

```bash
# 安装 Nginx
sudo apt install nginx

# 创建配置文件
sudo nano /etc/nginx/sites-available/ytdlp-api
```

配置文件内容：
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# 启用站点
sudo ln -s /etc/nginx/sites-available/ytdlp-api /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

## 使用示例

### Python 客户端示例

```python
import requests
import time

# API 基础URL
BASE_URL = "http://localhost:8000"

# 1. 获取视频信息
def get_video_info(url):
    response = requests.get(f"{BASE_URL}/info", params={"url": url})
    return response.json()

# 2. 开始下载
def download_video(url, format="best", extract_audio=False):
    data = {
        "url": url,
        "format": format,
        "extract_audio": extract_audio
    }
    response = requests.post(f"{BASE_URL}/download", json=data)
    return response.json()

# 3. 监控下载进度
def monitor_progress(video_id):
    while True:
        response = requests.get(f"{BASE_URL}/progress/{video_id}")
        progress = response.json()
        print(f"状态: {progress['status']}")
        
        if progress['status'] == 'downloading':
            print(f"进度: {progress.get('progress', 'N/A')}")
            print(f"速度: {progress.get('speed', 'N/A')}")
        elif progress['status'] == 'completed':
            print(f"下载完成: {progress['filename']}")
            return progress['download_url']
        elif progress['status'] == 'failed':
            print(f"下载失败: {progress.get('error', '未知错误')}")
            return None
        
        time.sleep(2)

# 使用示例
if __name__ == "__main__":
    url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    
    # 获取信息
    info = get_video_info(url)
    print(f"视频标题: {info['title']}")
    
    # 开始下载
    result = download_video(url, extract_audio=True)
    video_id = result['video_id']
    
    # 监控进度
    download_url = monitor_progress(video_id)
    if download_url:
        print(f"下载链接: {download_url}")
```

### JavaScript 客户端示例

```javascript
// 使用 fetch API
const BASE_URL = 'http://localhost:8000';

// 获取视频信息
async function getVideoInfo(url) {
    const response = await fetch(`${BASE_URL}/info?url=${encodeURIComponent(url)}`);
    return await response.json();
}

// 下载视频
async function downloadVideo(url, options = {}) {
    const response = await fetch(`${BASE_URL}/download`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            url,
            format: options.format || 'best',
            extract_audio: options.extractAudio || false,
            audio_format: options.audioFormat || 'mp3'
        })
    });
    return await response.json();
}

// 监控下载进度
async function monitorProgress(videoId) {
    return new Promise((resolve, reject) => {
        const checkProgress = async () => {
            try {
                const response = await fetch(`${BASE_URL}/progress/${videoId}`);
                const progress = await response.json();
                
                console.log(`状态: ${progress.status}`);
                
                if (progress.status === 'downloading') {
                    console.log(`进度: ${progress.progress || 'N/A'}`);
                    setTimeout(checkProgress, 2000);
                } else if (progress.status === 'completed') {
                    console.log(`下载完成: ${progress.filename}`);
                    resolve(progress.download_url);
                } else if (progress.status === 'failed') {
                    console.log(`下载失败: ${progress.error || '未知错误'}`);
                    reject(new Error(progress.error));
                }
            } catch (error) {
                reject(error);
            }
        };
        
        checkProgress();
    });
}

// 使用示例
async function main() {
    try {
        const url = 'https://www.youtube.com/watch?v=dQw4w9WgXcQ';
        
        // 获取信息
        const info = await getVideoInfo(url);
        console.log(`视频标题: ${info.title}`);
        
        // 开始下载
        const result = await downloadVideo(url, { extractAudio: true });
        const videoId = result.video_id;
        
        // 监控进度
        const downloadUrl = await monitorProgress(videoId);
        console.log(`下载链接: ${downloadUrl}`);
    } catch (error) {
        console.error('错误:', error);
    }
}

main();
```

## 故障排除

### 常见问题

1. **FFmpeg 未找到**
   - 确保已安装 FFmpeg
   - Docker 镜像已包含 FFmpeg

2. **下载失败**
   - 检查视频URL是否有效
   - 确认网络连接正常
   - 查看服务日志：`docker-compose logs ytdlp-api`

3. **内存不足**
   - 增加服务器内存
   - 限制并发下载数量

4. **磁盘空间不足**
   - 定期清理临时文件：`DELETE /cleanup`
   - 增加磁盘空间

### 日志查看

```bash
# 查看容器日志
docker-compose logs ytdlp-api

# 实时查看日志
docker-compose logs -f ytdlp-api

# 查看特定时间段的日志
docker-compose logs --since="2023-01-01T00:00:00" ytdlp-api
```

## 性能优化

### 服务器配置建议

- **CPU**: 2+ 核心
- **内存**: 4GB+ RAM
- **存储**: SSD 推荐，至少 20GB 可用空间
- **网络**: 稳定的网络连接

### 配置优化

1. **增加并发下载数**：
   ```python
   # 在 main.py 中修改
   ydl_opts['concurrent_fragments'] = 8
   ```

2. **设置下载限制**：
   ```python
   ydl_opts['limit_rate'] = '10M'  # 限制下载速度
   ```

3. **启用缓存**：
   ```python
   ydl_opts['cachedir'] = '/tmp/ytdlp_cache'
   ```

## 安全考虑

1. **生产环境部署**：
   - 使用 HTTPS
   - 配置防火墙
   - 限制访问IP
   - 定期更新依赖

2. **API 安全**：
   - 添加身份验证
   - 限制请求频率
   - 监控异常访问

3. **文件安全**：
   - 定期清理临时文件
   - 限制文件大小
   - 扫描恶意文件

## 许可证

本项目基于 MIT 许可证开源。

## 贡献

欢迎提交 Issue 和 Pull Request！

## 更新日志

### v1.0.0
- 初始版本发布
- 支持基本的视频下载功能
- 提供 RESTful API 接口
- Docker 容器化部署 