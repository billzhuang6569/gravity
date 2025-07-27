# 🍪 YouTube Cookies 自动管理方案

## 📋 方案概述

这个方案解决了VPS无法直接访问Mac浏览器cookies的问题，通过自动化脚本实现cookies的导出、上传和验证。

## 🏗️ 架构设计

```
Mac (本地)                    VPS (服务器)
    │                              │
    │ 1. 导出Chrome cookies        │
    │ 2. 验证cookies有效性         │
    │ 3. 上传到VPS                │
    │                              │ 4. 接收并验证cookies
    │                              │ 5. 备份旧cookies
    │                              │ 6. 更新cookies文件
    │                              │ 7. 返回验证结果
    │                              │
    └──────────────────────────────┘
```

## 🚀 快速开始

### 1. VPS端配置

#### 1.1 更新代码
```bash
cd /opt/gravity_v6
git pull origin fastapi-fork
```

#### 1.2 重启服务
```bash
source venv/bin/activate
python main.py
```

#### 1.3 验证新端点
```bash
# 检查cookies状态
curl "http://localhost:8018/cookies-status"

# 测试上传端点 (可选)
curl -X POST -F "file=@test_cookies.txt" "http://localhost:8018/upload-cookies"
```

### 2. Mac端配置

#### 2.1 安装依赖
```bash
# 安装yt-dlp (如果未安装)
pip install yt-dlp

# 安装requests (如果未安装)
pip install requests
```

#### 2.2 运行Python脚本
```bash
# 直接运行Python脚本
python upload_cookies_to_vps.py

# 脚本会交互式地询问VPS地址和端口
```

## 📖 使用方法

### 基本使用

```bash
# 执行cookies更新
python upload_cookies_to_vps.py

# 脚本会交互式地询问:
# 1. VPS IP地址或域名
# 2. FastAPI端口 (默认8018)
# 3. 确认配置
```

### 示例输出

```
🍪 YouTube Cookies 自动上传工具
==================================
[2024-01-26 10:30:15] 检查依赖...
✅ 依赖检查通过
[2024-01-26 10:30:16] 测试VPS连接...
✅ VPS连接正常
[2024-01-26 10:30:17] 从Chrome导出cookies...
✅ cookies导出成功: 125 行
[2024-01-26 10:30:18] 验证cookies有效性...
✅ cookies验证通过
[2024-01-26 10:30:19] 上传cookies到VPS...
✅ cookies上传成功
{
  "status": "success",
  "message": "cookies文件上传成功",
  "validation": {
    "status": "valid",
    "message": "cookies文件验证成功"
  }
}
[2024-01-26 10:30:20] 检查VPS上的cookies状态...
✅ VPS上的cookies状态正常
🎉 cookies更新完成！
```

## 🔧 API端点说明

### 1. `/upload-cookies` (POST)
上传cookies文件到服务器

**请求:**
- Content-Type: `multipart/form-data`
- 参数: `file` (cookies.txt文件)

**响应:**
```json
{
  "status": "success",
  "message": "cookies文件上传成功",
  "filename": "cookies.txt",
  "file_size": 2048,
  "cookies_file": "/opt/gravity_v6/cookies.txt",
  "backup_file": "/opt/gravity_v6/cookies.txt.backup.1706254219",
  "validation": {
    "status": "valid",
    "message": "cookies文件验证成功"
  }
}
```

### 2. `/cookies-status` (GET)
检查当前cookies状态

**响应:**
```json
{
  "cookies_file": "/opt/gravity_v6/cookies.txt",
  "cookies_browser": "chrome",
  "file_exists": true,
  "status": "valid",
  "method": "file",
  "suggestion": "cookies状态良好，可以正常使用"
}
```

### 3. `/update-cookies` (POST)
从浏览器更新cookies (仅限VPS本地使用)

**参数:**
- `browser`: 浏览器名称 (chrome/firefox/safari/edge)

## 🛡️ 安全特性

### 1. 文件验证
- 只接受.txt格式文件
- 验证Netscape cookies格式
- 限制文件大小 (最大1MB)

### 2. 备份机制
- 自动备份现有cookies文件
- 验证失败时自动恢复
- 时间戳命名避免冲突

### 3. 错误处理
- 详细的错误信息
- 自动重试机制
- 日志记录

## 🔄 自动化建议

### 1. 定时任务 (可选)
```bash
# 添加到crontab，每周更新一次cookies
0 2 * * 0 cd /path/to/project && python upload_cookies_to_vps.py >> /tmp/cookies_update.log 2>&1
```

### 2. 监控脚本
```bash
# 检查cookies状态，失效时自动更新
#!/bin/bash
if ! curl -s "http://localhost:8018/cookies-status" | grep -q '"status":"valid"'; then
    echo "Cookies已失效，需要更新"
    # 发送通知或自动触发更新
fi
```

## 🐛 故障排除

### 常见问题

#### 1. "无法连接到VPS"
- 检查VPS_HOST和VPS_PORT配置
- 确认VPS防火墙设置
- 验证FastAPI服务是否运行

#### 2. "从Chrome导出cookies失败"
- 确保Chrome已登录YouTube
- 检查Chrome是否正在运行
- 尝试其他浏览器 (Firefox/Safari)

#### 3. "cookies验证失败"
- 重新登录YouTube
- 清除浏览器cookies后重新登录
- 检查网络连接

#### 4. "文件上传失败"
- 检查文件格式是否正确
- 确认文件大小不超过1MB
- 查看服务器日志

### 调试模式

```bash
# Python脚本自带详细日志输出
python upload_cookies_to_vps.py

# 查看临时日志 (如果有)
tail -f /tmp/cookies_upload.log
```

## 📝 更新日志

### v1.0 (2024-01-26)
- 初始版本
- 支持Chrome cookies导出
- 自动上传到VPS
- 完整的验证机制

## 🤝 贡献

如有问题或建议，请提交Issue或Pull Request。

## �� 许可证

MIT License 