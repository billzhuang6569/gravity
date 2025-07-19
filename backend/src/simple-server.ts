import express from 'express';
import cors from 'cors';
import { v4 as uuidv4 } from 'uuid';

const app = express();
const PORT = process.env['PORT'] || 8088;

// 中间件
app.use(cors());
app.use(express.json());

// 模拟任务存储
const tasks: any[] = [];

// 健康检查
app.get('/health', (_req: any, res: any) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

// 创建下载任务
app.post('/api/tasks', (req: any, res: any) => {
  try {
    const { url, format = 'best', type = 'video' } = req.body;

    if (!url) {
      return res.status(400).json({
        error: 'URL is required'
      });
    }

    const taskId = uuidv4();
    const task = {
      id: taskId,
      url,
      title: `Video from ${url}`,
      format,
      type,
      status: 'pending',
      progress: 0,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };

    tasks.push(task);

    // 模拟下载过程
    setTimeout(() => {
      const taskIndex = tasks.findIndex(t => t.id === taskId);
      if (taskIndex !== -1) {
        tasks[taskIndex].status = 'processing';
        tasks[taskIndex].progress = 50;
        tasks[taskIndex].updated_at = new Date().toISOString();
      }
    }, 2000);

    setTimeout(() => {
      const taskIndex = tasks.findIndex(t => t.id === taskId);
      if (taskIndex !== -1) {
        tasks[taskIndex].status = 'completed';
        tasks[taskIndex].progress = 100;
        tasks[taskIndex].file_path = `/downloads/${taskId}.mp4`;
        tasks[taskIndex].file_size = 1024 * 1024 * 10; // 10MB
        tasks[taskIndex].updated_at = new Date().toISOString();
      }
    }, 5000);

    res.status(201).json({
      success: true,
      task
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to create task',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// 获取任务状态
app.get('/api/tasks/:id', (req: any, res: any) => {
  try {
    const { id } = req.params;
    const task = tasks.find(t => t.id === id);
    
    if (!task) {
      return res.status(404).json({
        error: 'Task not found'
      });
    }

    res.json({
      success: true,
      task
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to get task',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// 获取所有任务
app.get('/api/tasks', (req: any, res: any) => {
  try {
    const limit = parseInt(req.query['limit'] as string) || 50;
    const offset = parseInt(req.query['offset'] as string) || 0;
    
    const paginatedTasks = tasks.slice(offset, offset + limit);
    
    res.json({
      success: true,
      tasks: paginatedTasks,
      pagination: {
        limit,
        offset,
        total: tasks.length
      }
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to get tasks',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// 删除任务
app.delete('/api/tasks/:id', (req: any, res: any) => {
  try {
    const { id } = req.params;
    const taskIndex = tasks.findIndex(t => t.id === id);
    
    if (taskIndex === -1) {
      return res.status(404).json({
        error: 'Task not found'
      });
    }

    tasks.splice(taskIndex, 1);
    
    res.json({
      success: true,
      message: 'Task deleted successfully'
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to delete task',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// 下载文件（模拟）
app.get('/api/downloads/:taskId', (req: any, res: any) => {
  try {
    const { taskId } = req.params;
    const task = tasks.find(t => t.id === taskId);
    
    if (!task) {
      return res.status(404).json({
        error: 'Task not found'
      });
    }

    if (task.status !== 'completed') {
      return res.status(400).json({
        error: 'Task not completed',
        status: task.status
      });
    }

    // 模拟文件下载
    res.setHeader('Content-Type', 'application/octet-stream');
    res.setHeader('Content-Disposition', `attachment; filename="${task.title}.mp4"`);
    res.setHeader('Content-Length', task.file_size || 1024 * 1024);
    
    // 发送一个简单的响应
    res.send('Mock video file content');
  } catch (error) {
    res.status(500).json({
      error: 'Failed to download file',
      details: error instanceof Error ? error.message : 'Unknown error'
    });
  }
});

// 404 处理
app.use('*', (_req: any, res: any) => {
  res.status(404).json({ 
    error: 'API endpoint not found'
  });
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`🚀 Simple server started on port ${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
  console.log(`🌐 API base: http://localhost:${PORT}/api`);
}); 