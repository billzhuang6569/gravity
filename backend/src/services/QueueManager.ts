import Queue from 'bull';
import { Database } from '../database/Database';

export interface DownloadTask {
  id: string;
  url: string;
  format: string;
  type: 'video' | 'audio';
}

export interface TaskProgress {
  taskId: string;
  progress: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error?: string;
}

export class QueueManager {
  private static instance: QueueManager;
  private downloadQueue: Queue.Queue | null = null;

  private constructor() {}

  public static getInstance(): QueueManager {
    if (!QueueManager.instance) {
      QueueManager.instance = new QueueManager();
    }
    return QueueManager.instance;
  }

  public static async initialize(): Promise<void> {
    const instance = QueueManager.getInstance();
    await instance.init();
  }

  public static async close(): Promise<void> {
    const instance = QueueManager.getInstance();
    await instance.closeQueue();
  }

  public static getQueue(): Queue.Queue {
    const instance = QueueManager.getInstance();
    if (!instance.downloadQueue) {
      throw new Error('任务队列未初始化');
    }
    return instance.downloadQueue;
  }

  private async init(): Promise<void> {
    // 创建下载队列
    this.downloadQueue = new Queue('download-queue', process.env.REDIS_URL || 'redis://localhost:6379');

    // 设置并发处理数量
    const maxConcurrent = parseInt(process.env.MAX_CONCURRENT_DOWNLOADS || '3');
    this.downloadQueue.process(maxConcurrent, async (job) => {
      return await this.processDownloadJob(job);
    });

    // 监听任务完成事件
    this.downloadQueue.on('completed', async (job, result) => {
      console.log(`✅ 任务完成: ${job.data.id}`);
      await this.updateTaskStatus(job.data.id, 'completed', 100);
    });

    // 监听任务失败事件
    this.downloadQueue.on('failed', async (job, err) => {
      console.error(`❌ 任务失败: ${job.data.id}`, err.message);
      await this.updateTaskStatus(job.data.id, 'failed', 0, err.message);
    });

    // 监听任务进度事件
    this.downloadQueue.on('progress', async (job, progress) => {
      await this.updateTaskProgress(job.data.id, progress);
    });

    console.log('📋 任务队列初始化成功');
  }

  private async processDownloadJob(job: Queue.Job): Promise<any> {
    const { id, url, format, type } = job.data as DownloadTask;
    
    try {
      console.log(`🔄 开始处理任务: ${id}`);
      
      // 更新任务状态为处理中
      await this.updateTaskStatus(id, 'processing', 0);

      // 这里将调用 yt-dlp 进行实际下载
      // 具体实现将在 DownloadService 中完成
      
      return { success: true, taskId: id };
    } catch (error) {
      console.error(`❌ 任务处理失败: ${id}`, error);
      throw error;
    }
  }

  private async updateTaskStatus(taskId: string, status: string, progress: number, errorMessage?: string): Promise<void> {
    const db = Database.getDatabase();
    
    await db.run(`
      UPDATE tasks 
      SET status = ?, progress = ?, updated_at = CURRENT_TIMESTAMP, error_message = ?
      WHERE id = ?
    `, [status, progress, errorMessage || null, taskId]);
  }

  private async updateTaskProgress(taskId: string, progress: number): Promise<void> {
    const db = Database.getDatabase();
    
    await db.run(`
      UPDATE tasks 
      SET progress = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `, [progress, taskId]);
  }

  private async closeQueue(): Promise<void> {
    if (this.downloadQueue) {
      await this.downloadQueue.close();
      this.downloadQueue = null;
    }
  }

  // 添加下载任务到队列
  public static async addDownloadTask(task: DownloadTask): Promise<void> {
    const queue = QueueManager.getQueue();
    await queue.add(task, {
      jobId: task.id,
      attempts: 3,
      backoff: {
        type: 'exponential',
        delay: 2000
      }
    });
  }

  // 获取任务状态
  public static async getTaskStatus(taskId: string): Promise<any> {
    const db = Database.getDatabase();
    const task = await db.get('SELECT * FROM tasks WHERE id = ?', [taskId]);
    return task;
  }

  // 获取所有任务
  public static async getAllTasks(limit: number = 50, offset: number = 0): Promise<any[]> {
    const db = Database.getDatabase();
    const tasks = await db.all(`
      SELECT * FROM tasks 
      ORDER BY created_at DESC 
      LIMIT ? OFFSET ?
    `, [limit, offset]);
    return tasks;
  }
} 