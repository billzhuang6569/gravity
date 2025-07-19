const express = require('express');
const cors = require('cors');
const { v4: uuidv4 } = require('uuid');
const { spawn } = require('child_process');
const fs = require('fs-extra');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 8088;

// 中间件
app.use(cors());
app.use(express.json());

// 确保下载目录存在
const DOWNLOAD_DIR = path.join(__dirname, '../downloads');
fs.ensureDirSync(DOWNLOAD_DIR);

// 模拟任务存储
const tasks = [];

// 健康检查
app.get('/health', (req, res) => {
  res.json({ 
    status: 'ok', 
    timestamp: new Date().toISOString(),
    version: '1.0.0'
  });
});

// 获取视频信息
function getVideoInfo(url) {
  return new Promise((resolve, reject) => {
    const ytdlp = spawn('yt-dlp', [
      '--dump-json',
      '--no-playlist',
      url
    ]);

    let stdout = '';
    let stderr = '';

    ytdlp.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    ytdlp.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    ytdlp.on('close', (code) => {
      if (code === 0) {
        try {
          const info = JSON.parse(stdout);
          resolve(info);
        } catch (error) {
          reject(new Error('Failed to parse video info'));
        }
      } else {
        reject(new Error(`yt-dlp failed: ${stderr}`));
      }
    });

    ytdlp.on('error', (error) => {
      reject(new Error(`Failed to start yt-dlp: ${error.message}`));
    });
  });
}

// 下载视频
function downloadVideo(taskId, url, format, type) {
  return new Promise((resolve, reject) => {
    const taskDir = path.join(DOWNLOAD_DIR, taskId);
    fs.ensureDirSync(taskDir);

    const args = [
      '--output', path.join(taskDir, '%(title)s.%(ext)s'),
      '--no-playlist'
    ];

    // 根据类型选择格式
    if (type === 'audio') {
      args.push('--extract-audio');
      args.push('--audio-format', 'mp3');
      args.push('--audio-quality', '0');
    } else {
      // 视频格式
      if (format === 'best') {
        args.push('--format', 'best');
      } else if (format === 'worst') {
        args.push('--format', 'worst');
      } else if (format === '720p') {
        args.push('--format', 'best[height<=720]');
      } else if (format === '1080p') {
        args.push('--format', 'best[height<=1080]');
      } else {
        args.push('--format', 'best');
      }
    }

    args.push(url);

    console.log('Running yt-dlp with args:', args);

    const ytdlp = spawn('yt-dlp', args);
    let stderr = '';

    ytdlp.stderr.on('data', (data) => {
      stderr += data.toString();
      console.log('yt-dlp stderr:', data.toString());
    });

    ytdlp.on('close', (code) => {
      console.log('yt-dlp process closed with code:', code);
      if (code === 0) {
        // 查找下载的文件
        const files = fs.readdirSync(taskDir);
        console.log('Files in task directory:', files);
        if (files.length > 0) {
          const fileName = files[0];
          resolve(fileName);
        } else {
          reject(new Error('No file downloaded'));
        }
      } else {
        reject(new Error(`Download failed: ${stderr}`));
      }
    });

    ytdlp.on('error', (error) => {
      reject(new Error(`Failed to start download: ${error.message}`));
    });
  });
}

// 创建下载任务
app.post('/api/tasks', async (req, res) => {
  try {
    const { url, format = 'best', type = 'video' } = req.body;

    if (!url) {
      return res.status(400).json({
        error: 'URL is required'
      });
    }

    const taskId = uuidv4();
    
    // 创建任务
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

    // 异步处理下载
    (async () => {
      try {
        // 更新状态为处理中
        const taskIndex = tasks.findIndex(t => t.id === taskId);
        if (taskIndex !== -1) {
          tasks[taskIndex].status = 'processing';
          tasks[taskIndex].progress = 10;
          tasks[taskIndex].updated_at = new Date().toISOString();
        }

        // 获取视频信息
        const videoInfo = await getVideoInfo(url);
        
        // 更新任务标题
        if (taskIndex !== -1) {
          tasks[taskIndex].title = videoInfo.title || `Video from ${url}`;
          tasks[taskIndex].progress = 30;
          tasks[taskIndex].updated_at = new Date().toISOString();
        }

        // 下载视频
        const fileName = await downloadVideo(taskId, url, format, type);
        
        // 更新任务状态为完成
        if (taskIndex !== -1) {
          tasks[taskIndex].status = 'completed';
          tasks[taskIndex].progress = 100;
          tasks[taskIndex].file_name = fileName;
          tasks[taskIndex].file_path = `/downloads/${taskId}/${fileName}`;
          tasks[taskIndex].updated_at = new Date().toISOString();
        }
      } catch (error) {
        console.error('Download error:', error);
        // 更新任务状态为失败
        const taskIndex = tasks.findIndex(t => t.id === taskId);
        if (taskIndex !== -1) {
          tasks[taskIndex].status = 'failed';
          tasks[taskIndex].error = error.message;
          tasks[taskIndex].updated_at = new Date().toISOString();
        }
      }
    })();

    res.status(201).json({
      success: true,
      task
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to create task',
      details: error.message
    });
  }
});

// 获取任务状态
app.get('/api/tasks/:id', (req, res) => {
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
      details: error.message
    });
  }
});

// 获取所有任务
app.get('/api/tasks', (req, res) => {
  try {
    const limit = parseInt(req.query.limit) || 50;
    const offset = parseInt(req.query.offset) || 0;
    
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
      details: error.message
    });
  }
});

// 删除任务
app.delete('/api/tasks/:id', (req, res) => {
  try {
    const { id } = req.params;
    const taskIndex = tasks.findIndex(t => t.id === id);
    
    if (taskIndex === -1) {
      return res.status(404).json({
        error: 'Task not found'
      });
    }

    // 删除下载的文件
    const task = tasks[taskIndex];
    if (task.file_path) {
      const taskDir = path.join(DOWNLOAD_DIR, id);
      if (fs.existsSync(taskDir)) {
        fs.removeSync(taskDir);
      }
    }

    tasks.splice(taskIndex, 1);
    
    res.json({
      success: true,
      message: 'Task deleted successfully'
    });
  } catch (error) {
    res.status(500).json({
      error: 'Failed to delete task',
      details: error.message
    });
  }
});

// 下载文件
app.get('/api/downloads/:taskId', (req, res) => {
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

    const taskDir = path.join(DOWNLOAD_DIR, taskId);
    const files = fs.readdirSync(taskDir);
    
    if (files.length === 0) {
      return res.status(404).json({
        error: 'File not found'
      });
    }

    const fileName = files[0];
    const filePath = path.join(taskDir, fileName);
    const stats = fs.statSync(filePath);

    // 设置响应头
    res.setHeader('Content-Type', 'application/octet-stream');
    res.setHeader('Content-Disposition', `attachment; filename="${fileName}"`);
    res.setHeader('Content-Length', stats.size);
    
    // 发送文件
    const fileStream = fs.createReadStream(filePath);
    fileStream.pipe(res);
  } catch (error) {
    res.status(500).json({
      error: 'Failed to download file',
      details: error.message
    });
  }
});

// 404 处理
app.use('*', (req, res) => {
  res.status(404).json({ 
    error: 'API endpoint not found'
  });
});

// 启动服务器
app.listen(PORT, () => {
  console.log(`🚀 Real server started on port ${PORT}`);
  console.log(`📊 Health check: http://localhost:${PORT}/health`);
  console.log(`🌐 API base: http://localhost:${PORT}/api`);
  console.log(`📁 Download directory: ${DOWNLOAD_DIR}`);
}); 