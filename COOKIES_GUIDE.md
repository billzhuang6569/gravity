# 🍪 Cookies完整使用指南

## 什么是Cookies？为什么需要它？

Cookies是浏览器存储的小型数据文件，用于保持登录状态和个人设置。对于视频下载：

- **YouTube**: 登录后可以下载更多视频，避免某些限制
- **Bilibili**: 需要登录才能下载720P+高清视频
- **其他网站**: 会员内容、私人视频等

## 🛠️ 获取Chrome浏览器Cookies的方法

### 方法1：使用浏览器扩展（最简单）

1. **安装扩展**：
   - 在Chrome应用商店搜索 **"Get cookies.txt"** 
   - 安装并启用扩展

2. **导出Cookies**：
   ```bash
   # 1. 访问并登录目标网站（如bilibili.com）
   # 2. 点击扩展图标 
   # 3. 选择"Export" → "cookies.txt format"
   # 4. 保存文件到 cookies/ 目录
   ```

### 方法2：使用我们提供的导出工具

```bash
# 进入tools目录并运行导出工具
cd tools
python3 export_chrome_cookies.py

# 按照提示选择网站并导出
```

### 方法3：手动从开发者工具获取

1. 打开Chrome开发者工具 (F12)
2. 访问目标网站并登录
3. 转到 `Application` → `Storage` → `Cookies`
4. 找到关键cookies (如SESSDATA, bili_jct等)
5. 手动创建cookies.txt文件

## 📁 Cookies文件格式和位置

### 标准Netscape格式 (cookies.txt)
```
# Netscape HTTP Cookie File
# domain    flag    path    secure    expires    name    value
.bilibili.com	TRUE	/	FALSE	1756281600	SESSDATA	your_session_data
.bilibili.com	TRUE	/	FALSE	1756281600	bili_jct	your_csrf_token
bilibili.com	FALSE	/	FALSE	1756281600	DedeUserID	12345678
```

### 文件命名规范
```
cookies/
├── bilibili_cookies.txt     # Bilibili登录cookies
├── youtube_cookies.txt      # YouTube登录cookies  
├── twitter_cookies.txt      # Twitter登录cookies
└── general_cookies.txt      # 通用cookies
```

## 🚀 API使用示例

### 基础使用

```bash
# 使用cookies获取高清视频信息
curl -X POST "http://localhost:8002/api/v1/info" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.bilibili.com/video/BV1xx411c7XD",
    "cookies_file": "cookies/bilibili_cookies.txt"
  }'
```

### 高级使用（结合所有功能）

```bash
# 使用cookies + 代理 + 指定格式下载高清视频
curl -X POST "http://localhost:8002/api/v1/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.bilibili.com/video/BV1xx411c7XD",
    "cookies_file": "cookies/bilibili_cookies.txt",
    "format": "dash-flv720",
    "http_proxy": "127.0.0.1:1087",
    "output_filename": "high_quality_video",
    "timeout": 120,
    "debug": true
  }'
```

### Python客户端示例

```python
import requests

# 高清视频下载
response = requests.post(
    'http://localhost:8002/api/v1/download',
    json={
        'url': 'https://www.bilibili.com/video/BV1xx411c7XD',
        'cookies_file': 'cookies/bilibili_cookies.txt',
        'format': 'dash-flv720',  # 720P高清
        'mode': 'stream'
    }
)

if response.status_code == 200:
    with open('video.mp4', 'wb') as f:
        f.write(response.content)
```

## 🔧 Cookies管理API

### 1. 上传Cookies文件
```bash
curl -X POST "http://localhost:8002/api/v1/cookies/upload?site=bilibili" \
  -F "file=@/path/to/bilibili_cookies.txt"
```

### 2. 列出所有Cookies
```bash
curl -s "http://localhost:8002/api/v1/cookies/list" | python3 -m json.tool
```

### 3. 获取建议的Cookies
```bash
curl -s "http://localhost:8002/api/v1/cookies/suggest/bilibili"
```

### 4. 删除Cookies
```bash
curl -X DELETE "http://localhost:8002/api/v1/cookies/bilibili"
```

## 🎯 针对不同网站的Cookies策略

### Bilibili (哔哩哔哩)
**关键Cookies:**
- `SESSDATA`: 会话数据（最重要）
- `bili_jct`: CSRF令牌
- `DedeUserID`: 用户ID

**获取方法:**
1. 登录 bilibili.com
2. 导出cookies
3. 测试：能否看到720P+格式选项

### YouTube
**关键Cookies:**
- `SID`, `HSID`, `SSID`: Google账户会话
- `LOGIN_INFO`: 登录信息

**注意事项:**
- YouTube反爬虫严格，cookies也可能无法完全解决
- 建议结合代理使用

## 🔒 安全最佳实践

### 保护你的Cookies
```bash
# 设置适当的文件权限
chmod 600 cookies/*.txt

# 不要提交到版本控制
echo "cookies/*.txt" >> .gitignore
```

### 定期更新
- Cookies通常7-30天过期
- 网站更改后可能需要重新登录
- 定期检查cookies是否仍然有效

### 安全存储
```bash
# 使用环境变量存储敏感cookies路径
export BILIBILI_COOKIES="/secure/path/bilibili_cookies.txt"

# API中使用
{
  "url": "...",
  "cookies_file": "$BILIBILI_COOKIES"
}
```

## 🧪 测试Cookies是否工作

### 1. 基础测试
```bash
# 不使用cookies
curl -X POST "http://localhost:8002/api/v1/info" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.bilibili.com/video/BV1xx411c7XD"}'

# 使用cookies（应该看到更多格式选项）
curl -X POST "http://localhost:8002/api/v1/info" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.bilibili.com/video/BV1xx411c7XD",
    "cookies_file": "cookies/bilibili_cookies.txt"
  }'
```

### 2. 验证指标
- ✅ 更多视频格式选项 (720P, 1080P等)
- ✅ 无"需要登录"错误消息
- ✅ 可以访问会员或私人内容

## 🔍 故障排除

### 常见问题

1. **"cookies文件不存在"**
   ```bash
   ls -la cookies/  # 检查文件是否存在
   ```

2. **"仍然无法获取高清"**
   - 检查cookies是否过期
   - 确认浏览器中能正常访问高清视频
   - 重新导出最新的cookies

3. **"格式错误"**
   - 确保使用Netscape格式
   - 检查文件编码为UTF-8

### 调试模式
```bash
# 启用调试模式查看详细信息
{
  "url": "...",
  "cookies_file": "cookies/bilibili_cookies.txt",
  "debug": true
}
```

## 🎉 成功案例

使用正确的cookies后，你应该能够：

- ✅ **Bilibili**: 下载720P/1080P高清视频
- ✅ **YouTube**: 访问更多视频内容
- ✅ **会员内容**: 下载需要登录的视频
- ✅ **私人视频**: 访问仅好友可见的内容

---

💡 **提示**: 如果你不熟悉技术细节，推荐使用浏览器扩展方法获取cookies，这是最简单可靠的方式！ 