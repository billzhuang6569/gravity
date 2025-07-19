import { Router, Request, Response } from 'express';
import path from 'path';
import fs from 'fs-extra';
import { Database } from '../database/Database';

const router = Router();

// 下载文件
router.get('/:taskId', async (req: Request, res: Response) => {
  try {
    const { taskId } = req.params;
    
    // 获取任务信息
    const db = Database.getDatabase();
    const task = await db.get('SELECT * FROM tasks WHERE id = ?', [taskId]);
    
    if (!task) {
      return res.status(404).json({
        error: '任务不存在'
      });
    }

    if (task.status !== 'completed') {
      return res.status(400).json({
        error: '任务尚未完成',
        status: task.status
      });
    }

    if (!task.file_path || !await fs.pathExists(task.file_path)) {
      return res.status(404).json({
        error: '文件不存在'
      });
    }

    // 获取文件信息
    const stats = await fs.stat(task.file_path);
    const fileName = path.basename(task.file_path);

    // 设置响应头
    res.setHeader('Content-Type', 'application/octet-stream');
    res.setHeader('Content-Disposition', `attachment; filename="${fileName}"`);
    res.setHeader('Content-Length', stats.size);

    // 创建文件流并发送
    const fileStream = fs.createReadStream(task.file_path);
    fileStream.pipe(res);

    // 记录下载历史
    await db.run(`
      INSERT INTO download_history (task_id, file_path, file_size)
      VALUES (?, ?, ?)
    `, [taskId, task.file_path, stats.size]);

  } catch (error) {
    console.error('下载文件失败:', error);
    res.status(500).json({
      error: '下载文件失败',
      details: error instanceof Error ? error.message : '未知错误'
    });
  }
});

// 获取下载历史
router.get('/history/:taskId', async (req: Request, res: Response) => {
  try {
    const { taskId } = req.params;
    
    const db = Database.getDatabase();
    const history = await db.all(`
      SELECT * FROM download_history 
      WHERE task_id = ? 
      ORDER BY downloaded_at DESC
    `, [taskId]);
    
    res.json({
      success: true,
      history
    });
  } catch (error) {
    console.error('获取下载历史失败:', error);
    res.status(500).json({
      error: '获取下载历史失败',
      details: error instanceof Error ? error.message : '未知错误'
    });
  }
});

// 获取所有下载历史
router.get('/history', async (req: Request, res: Response) => {
  try {
    const limit = parseInt(req.query.limit as string) || 50;
    const offset = parseInt(req.query.offset as string) || 0;
    
    const db = Database.getDatabase();
    const history = await db.all(`
      SELECT h.*, t.title, t.url 
      FROM download_history h
      JOIN tasks t ON h.task_id = t.id
      ORDER BY h.downloaded_at DESC
      LIMIT ? OFFSET ?
    `, [limit, offset]);
    
    res.json({
      success: true,
      history,
      pagination: {
        limit,
        offset,
        total: history.length
      }
    });
  } catch (error) {
    console.error('获取下载历史失败:', error);
    res.status(500).json({
      error: '获取下载历史失败',
      details: error instanceof Error ? error.message : '未知错误'
    });
  }
});

export { router as downloadRoutes }; 