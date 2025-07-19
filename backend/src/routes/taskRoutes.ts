import { Router, Request, Response } from 'express';
import { body, validationResult } from 'express-validator';
import { v4 as uuidv4 } from 'uuid';
import { Database } from '../database/Database';
import { QueueManager, DownloadTask } from '../services/QueueManager';
import { DownloadService } from '../services/DownloadService';

const router = Router();

// 创建下载任务
router.post('/', [
  body('url').isURL().withMessage('请输入有效的URL'),
  body('format').optional().isString().withMessage('格式必须是字符串'),
  body('type').optional().isIn(['video', 'audio']).withMessage('类型必须是video或audio')
], async (req: Request, res: Response) => {
  try {
    // 验证输入
    const errors = validationResult(req);
    if (!errors.isEmpty()) {
      return res.status(400).json({
        error: '输入验证失败',
        details: errors.array()
      });
    }

    const { url, format = 'best', type = 'video' } = req.body;

    // 生成任务ID
    const taskId = uuidv4();

    // 获取视频信息
    let videoInfo;
    try {
      videoInfo = await DownloadService.getVideoInfo(url);
    } catch (error) {
      return res.status(400).json({
        error: '无法获取视频信息',
        details: error instanceof Error ? error.message : '未知错误'
      });
    }

    // 创建任务记录
    const db = Database.getDatabase();
    await db.run(`
      INSERT INTO tasks (id, url, title, format, type, status, thumbnail, duration)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    `, [
      taskId,
      url,
      videoInfo.title,
      format,
      type,
      'pending',
      videoInfo.thumbnail,
      videoInfo.duration
    ]);

    // 添加到下载队列
    const downloadTask: DownloadTask = {
      id: taskId,
      url,
      format,
      type
    };

    await QueueManager.addDownloadTask(downloadTask);

    res.status(201).json({
      success: true,
      task: {
        id: taskId,
        url,
        title: videoInfo.title,
        format,
        type,
        status: 'pending',
        progress: 0,
        thumbnail: videoInfo.thumbnail,
        duration: videoInfo.duration,
        created_at: new Date().toISOString()
      }
    });
  } catch (error) {
    console.error('创建任务失败:', error);
    res.status(500).json({
      error: '创建任务失败',
      details: error instanceof Error ? error.message : '未知错误'
    });
  }
});

// 获取任务状态
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    
    const task = await QueueManager.getTaskStatus(id);
    
    if (!task) {
      return res.status(404).json({
        error: '任务不存在'
      });
    }

    res.json({
      success: true,
      task
    });
  } catch (error) {
    console.error('获取任务状态失败:', error);
    res.status(500).json({
      error: '获取任务状态失败',
      details: error instanceof Error ? error.message : '未知错误'
    });
  }
});

// 获取所有任务
router.get('/', async (req: Request, res: Response) => {
  try {
    const limit = parseInt(req.query.limit as string) || 50;
    const offset = parseInt(req.query.offset as string) || 0;
    
    const tasks = await QueueManager.getAllTasks(limit, offset);
    
    res.json({
      success: true,
      tasks,
      pagination: {
        limit,
        offset,
        total: tasks.length
      }
    });
  } catch (error) {
    console.error('获取任务列表失败:', error);
    res.status(500).json({
      error: '获取任务列表失败',
      details: error instanceof Error ? error.message : '未知错误'
    });
  }
});

// 删除任务
router.delete('/:id', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    
    const db = Database.getDatabase();
    
    // 获取任务信息
    const task = await db.get('SELECT * FROM tasks WHERE id = ?', [id]);
    
    if (!task) {
      return res.status(404).json({
        error: '任务不存在'
      });
    }

    // 如果任务已完成且有文件，删除文件
    if (task.file_path) {
      await DownloadService.deleteFile(task.file_path);
    }

    // 删除任务记录
    await db.run('DELETE FROM tasks WHERE id = ?', [id]);
    
    res.json({
      success: true,
      message: '任务删除成功'
    });
  } catch (error) {
    console.error('删除任务失败:', error);
    res.status(500).json({
      error: '删除任务失败',
      details: error instanceof Error ? error.message : '未知错误'
    });
  }
});

// 获取视频格式列表
router.get('/:id/formats', async (req: Request, res: Response) => {
  try {
    const { id } = req.params;
    
    // 获取任务信息
    const task = await QueueManager.getTaskStatus(id);
    
    if (!task) {
      return res.status(404).json({
        error: '任务不存在'
      });
    }

    // 获取可用格式
    const formats = await DownloadService.getAvailableFormats(task.url);
    
    res.json({
      success: true,
      formats
    });
  } catch (error) {
    console.error('获取格式列表失败:', error);
    res.status(500).json({
      error: '获取格式列表失败',
      details: error instanceof Error ? error.message : '未知错误'
    });
  }
});

export { router as taskRoutes }; 