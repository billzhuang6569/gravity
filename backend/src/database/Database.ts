import sqlite3 from 'sqlite3';
import { open, Database as SQLiteDatabase } from 'sqlite';
import path from 'path';
import fs from 'fs-extra';

export class Database {
  private static instance: Database;
  private db: SQLiteDatabase | null = null;

  private constructor() {}

  public static getInstance(): Database {
    if (!Database.instance) {
      Database.instance = new Database();
    }
    return Database.instance;
  }

  public static async initialize(): Promise<void> {
    const instance = Database.getInstance();
    await instance.init();
  }

  public static async close(): Promise<void> {
    const instance = Database.getInstance();
    await instance.closeConnection();
  }

  public static getDatabase(): SQLiteDatabase {
    const instance = Database.getInstance();
    if (!instance.db) {
      throw new Error('数据库未初始化');
    }
    return instance.db;
  }

  private async init(): Promise<void> {
    // 确保数据目录存在
    const dataDir = path.dirname(process.env['DATABASE_URL'] || './data/downloads.db');
    await fs.ensureDir(dataDir);

    // 打开数据库连接
    this.db = await open({
      filename: process.env['DATABASE_URL'] || './data/downloads.db',
      driver: sqlite3.Database
    });

    // 创建表
    await this.createTables();
  }

  private async createTables(): Promise<void> {
    if (!this.db) return;

    // 创建任务表
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS tasks (
        id TEXT PRIMARY KEY,
        url TEXT NOT NULL,
        title TEXT,
        format TEXT DEFAULT 'best',
        type TEXT DEFAULT 'video',
        status TEXT DEFAULT 'pending',
        progress REAL DEFAULT 0,
        file_path TEXT,
        file_size INTEGER,
        duration INTEGER,
        thumbnail TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        error_message TEXT
      )
    `);

    // 创建下载历史表
    await this.db.exec(`
      CREATE TABLE IF NOT EXISTS download_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id TEXT NOT NULL,
        file_path TEXT NOT NULL,
        file_size INTEGER,
        downloaded_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (task_id) REFERENCES tasks (id)
      )
    `);

    // 创建索引
    await this.db.exec(`
      CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks (status);
      CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks (created_at);
      CREATE INDEX IF NOT EXISTS idx_download_history_task_id ON download_history (task_id);
    `);
  }

  private async closeConnection(): Promise<void> {
    if (this.db) {
      await this.db.close();
      this.db = null;
    }
  }
} 