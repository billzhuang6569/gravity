# Cookies 使用指南

## 为什么需要Cookies？

许多视频网站（如YouTube、Bilibili）需要登录状态才能访问高质量的视频流：
- **YouTube**: 需要登录才能下载某些视频
- **Bilibili**: 需要登录才能下载720P及以上质量
- **其他网站**: 可能需要会员身份

## 如何获取Chrome浏览器的Cookies

### 方法1: 使用浏览器扩展（推荐）

1. 安装Chrome扩展 **"Get cookies.txt"**
2. 访问目标网站并登录（如bilibili.com或youtube.com）
3. 点击扩展图标，选择"Export"
4. 保存为 `cookies.txt` 格式

### 方法2: 手动导出

1. 打开Chrome开发者工具 (F12)
2. 访问目标网站并登录
3. 转到 `Application` → `Storage` → `Cookies`
4. 复制所需的cookie值

### 方法3: 使用脚本导出（高级用户）

```python
# 可以使用browser_cookie3库
import browser_cookie3
cookies = browser_cookie3.chrome()
```

## 支持的Cookie格式

- **Netscape格式** (`cookies.txt`): 推荐，兼容性最好
- **Mozilla格式** (`cookies.sqlite`): SQLite数据库格式

## 文件放置位置

将cookies文件放在以下位置：
- `cookies/bilibili_cookies.txt` - Bilibili的cookies
- `cookies/youtube_cookies.txt` - YouTube的cookies
- `cookies/general_cookies.txt` - 通用cookies

## API使用示例

```bash
# 使用cookies下载高质量视频
curl -X POST "http://localhost:8002/api/v1/download" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://www.bilibili.com/video/BV1xx411c7XD",
    "cookies_file": "cookies/bilibili_cookies.txt",
    "format": "dash-flv720"
  }'
```

## 安全注意事项

⚠️ **重要**: Cookies包含敏感信息，请：
- 不要分享cookies文件
- 定期更新cookies（通常7-30天过期）
- 不要将cookies提交到版本控制系统 