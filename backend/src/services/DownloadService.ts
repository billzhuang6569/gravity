import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs-extra';
import { v4 as uuidv4 } from 'uuid';
import { Database } from '../database/Database';

export interface VideoInfo {
  id: string;
  title: string;
  duration: number;
  thumbnail: string;
  formats: Array<{
    format_id: string;
    ext: string;
    resolution: string;
    filesize: number;
  }>;
}

export interface DownloadOptions {
  url: string;
  format: string;
  type: 'video' | 'audio';
  outputPath: string;
}

export class DownloadService {
  private static downloadPath = process.env['DOWNLOAD_PATH'] || './downloads';

  // 获取视频信息
  public static async getVideoInfo(url: string): Promise<VideoInfo> {
    return new Promise((resolve, reject) => {
      const args = [
        '--dump-json',
        '--no-playlist',
        url
      ];

      const ytdlp = spawn('yt-dlp', args);
      let output = '';
      let error = '';

      ytdlp.stdout.on('data', (data) => {
        output += data.toString();
      });

      ytdlp.stderr.on('data', (data) => {
        error += data.toString();
      });

      ytdlp.on('close', (code) => {
        if (code === 0) {
          try {
            const info = JSON.parse(output);
            resolve({
              id: info.id,
              title: info.title,
              duration: info.duration || 0,
              thumbnail: info.thumbnail || '',
              formats: info.formats || []
            });
          } catch (parseError) {
            reject(new Error('解析视频信息失败'));
          }
        } else {
          reject(new Error(`获取视频信息失败: ${error}`));
        }
      });
    });
  }

  // 下载视频
  public static async downloadVideo(
    taskId: string,
    url: string,
    format: string = 'best',
    type: 'video' | 'audio' = 'video'
  ): Promise<string> {
    // 确保下载目录存在
    await fs.ensureDir(this.downloadPath);

    // 生成输出文件名
    const outputTemplate = path.join(this.downloadPath, `${taskId}.%(ext)s`);
    
    const args = [
      '--format', format,
      '--output', outputTemplate,
      '--no-playlist',
      '--write-thumbnail',
      '--write-description',
      '--write-info-json'
    ];

    // 如果是音频下载，添加音频转换参数
    if (type === 'audio') {
      args.push('--extract-audio');
      args.push('--audio-format', 'mp3');
      args.push('--audio-quality', '0');
    }

    args.push(url);

    return new Promise((resolve, reject) => {
      const ytdlp = spawn('yt-dlp', args);
      let progress = 0;

      ytdlp.stdout.on('data', (data) => {
        const output = data.toString();
        
        // 解析下载进度
        const progressMatch = output.match(/(\d+\.?\d*)%/);
        if (progressMatch) {
          progress = parseFloat(progressMatch[1]);
          this.updateTaskProgress(taskId, progress);
        }
      });

      ytdlp.stderr.on('data', (data) => {
        const error = data.toString();
        console.error(`下载错误: ${error}`);
      });

      ytdlp.on('close', async (code) => {
        if (code === 0) {
          try {
            // 查找下载的文件
            const files = await fs.readdir(this.downloadPath);
            const downloadedFile = files.find(file => file.startsWith(taskId));
            
            if (downloadedFile) {
              const filePath = path.join(this.downloadPath, downloadedFile);
              const stats = await fs.stat(filePath);
              
              // 更新数据库中的文件信息
              await this.updateTaskFileInfo(taskId, filePath, stats.size);
              
              resolve(filePath);
            } else {
              reject(new Error('下载完成但找不到文件'));
            }
          } catch (error) {
            reject(error);
          }
        } else {
          reject(new Error(`下载失败，退出码: ${code}`));
        }
      });
    });
  }

  // 更新任务进度
  private static async updateTaskProgress(taskId: string, progress: number): Promise<void> {
    const db = Database.getDatabase();
    await db.run(`
      UPDATE tasks 
      SET progress = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `, [progress, taskId]);
  }

  // 更新任务文件信息
  private static async updateTaskFileInfo(taskId: string, filePath: string, fileSize: number): Promise<void> {
    const db = Database.getDatabase();
    await db.run(`
      UPDATE tasks 
      SET file_path = ?, file_size = ?, updated_at = CURRENT_TIMESTAMP
      WHERE id = ?
    `, [filePath, fileSize, taskId]);
  }

  // 获取可用的格式列表
  public static async getAvailableFormats(url: string): Promise<any[]> {
    return new Promise((resolve, reject) => {
      const args = [
        '--list-formats',
        '--no-playlist',
        url
      ];

      const ytdlp = spawn('yt-dlp', args);
      let output = '';

      ytdlp.stdout.on('data', (data) => {
        output += data.toString();
      });

      ytdlp.stderr.on('data', (data) => {
        output += data.toString();
      });

      ytdlp.on('close', (code) => {
        if (code === 0) {
          // 解析格式列表
          const formats = this.parseFormats(output);
          resolve(formats);
        } else {
          reject(new Error('获取格式列表失败'));
        }
      });
    });
  }

  // 解析格式列表
  private static parseFormats(output: string): any[] {
    const lines = output.split('\n');
    const formats: any[] = [];
    
    for (const line of lines) {
      // 匹配格式信息行
      const match = line.match(/^(\d+)\s+(\w+)\s+(\d+x\d+|\w+)\s+(\d+\.?\d*\w*)\s+(.+)$/);
      if (match) {
        formats.push({
          format_id: match[1],
          ext: match[2],
          resolution: match[3],
          filesize: match[4],
          note: match[5].trim()
        });
      }
    }
    
    return formats;
  }

  // 删除下载的文件
  public static async deleteFile(filePath: string): Promise<void> {
    try {
      await fs.remove(filePath);
    } catch (error) {
      console.error('删除文件失败:', error);
    }
  }

  // 清理过期的下载文件
  public static async cleanupOldFiles(maxAge: number = 7 * 24 * 60 * 60 * 1000): Promise<void> {
    try {
      const files = await fs.readdir(this.downloadPath);
      const now = Date.now();
      
      for (const file of files) {
        const filePath = path.join(this.downloadPath, file);
        const stats = await fs.stat(filePath);
        
        if (now - stats.mtime.getTime() > maxAge) {
          await fs.remove(filePath);
          console.log(`清理过期文件: ${file}`);
        }
      }
    } catch (error) {
      console.error('清理文件失败:', error);
    }
  }
} 