# 🚀 快速开始指南

## 🚀 运行Python脚本

### 1. 安装依赖
```bash
# 安装必要的Python包
pip install yt-dlp requests
```

### 2. 运行脚本
```bash
python upload_cookies_to_vps.py
```

### 3. 交互式配置
脚本会询问：
- VPS IP地址或域名
- FastAPI端口 (默认8018)
- 确认配置

无需手动编辑配置文件！

## 📋 运行前检查清单

- [ ] 已安装 yt-dlp: `pip install yt-dlp`
- [ ] 已安装 requests: `pip install requests`
- [ ] Chrome已登录YouTube
- [ ] VPS上FastAPI服务正在运行
- [ ] 知道VPS的IP地址或域名

## 🔍 故障排除

### 如果遇到依赖问题
```bash
pip install yt-dlp requests
```

### 如果遇到连接问题
```bash
# 测试VPS连接
curl "http://你的VPS-IP:8018/health"
```

### 如果遇到Python问题
```bash
# 确保使用正确的Python版本
python3 upload_cookies_to_vps.py
```

## 📞 需要帮助？

查看详细文档: `COOKIES_SETUP.md` 