import express from 'express';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import dotenv from 'dotenv';

import { errorHandler } from './middleware/errorHandler';
import { taskRoutes } from './routes/taskRoutes';
import { downloadRoutes } from './routes/downloadRoutes';
import { Database } from './database/Database';
import { QueueManager } from './services/QueueManager';

// 加载环境变量
dotenv.config();

const app = express();
const PORT = process.env['PORT'] || 8000;

// 安全中间件
app.use(helmet());

// CORS 配置
app.use(cors({
  origin: process.env['NODE_ENV'] === 'production' 
    ? ['http://localhost:3000'] 
    : true,
  credentials: true
}));

// 请求限制
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15分钟
  max: 100, // 限制每个IP 15分钟内最多100个请求
  message: '请求过于频繁，请稍后再试'
});
app.use('/api/', limiter);

// 日志中间件
app.use(morgan('combined'));

// 压缩中间件
app.use(compression());

// 解析 JSON
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true, limit: '10mb' }));

// 静态文件服务
app.use('/downloads', express.static('downloads'));

// API 路由
app.use('/api/tasks', taskRoutes);
app.use('/api/downloads', downloadRoutes);

// 健康检查
app.get('/health', (_req, res) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

// 错误处理中间件
app.use(errorHandler);

// 404 处理
app.use('*', (_req, res) => {
      res.status(404).json({ 
      error: '接口不存在',
      path: _req.originalUrl 
    });
});

// 启动服务器
async function startServer() {
  try {
    // 初始化数据库
    await Database.initialize();
    console.log('✅ 数据库初始化成功');

    // 初始化任务队列
    await QueueManager.initialize();
    console.log('✅ 任务队列初始化成功');

    // 启动服务器
    app.listen(PORT, () => {
      console.log(`🚀 服务器启动成功，端口: ${PORT}`);
      console.log(`📊 健康检查: http://localhost:${PORT}/health`);
    });
  } catch (error) {
    console.error('❌ 服务器启动失败:', error);
    process.exit(1);
  }
}

// 优雅关闭
process.on('SIGTERM', async () => {
  console.log('🔄 正在关闭服务器...');
  await QueueManager.close();
  await Database.close();
  process.exit(0);
});

process.on('SIGINT', async () => {
  console.log('🔄 正在关闭服务器...');
  await QueueManager.close();
  await Database.close();
  process.exit(0);
});

startServer(); 