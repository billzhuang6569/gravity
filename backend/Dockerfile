FROM node:18-alpine

# 安装系统依赖
RUN apk add --no-cache \
    python3 \
    py3-pip \
    ffmpeg \
    && pip3 install yt-dlp

# 设置工作目录
WORKDIR /app

# 复制 package.json 和 package-lock.json
COPY package*.json ./

# 安装依赖
RUN npm ci --only=production

# 复制源代码
COPY . .

# 创建必要的目录
RUN mkdir -p downloads data

# 编译 TypeScript
RUN npm run build

# 暴露端口
EXPOSE 8000

# 启动应用
CMD ["npm", "start"] 