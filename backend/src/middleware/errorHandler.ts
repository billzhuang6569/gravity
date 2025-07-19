import { Request, Response, NextFunction } from 'express';

export interface AppError extends Error {
  statusCode?: number;
  isOperational?: boolean;
}

export const errorHandler = (
  error: AppError,
  req: Request,
  res: Response,
  _next: NextFunction
): void => {
  const statusCode = error.statusCode || 500;
  const message = error.message || '服务器内部错误';

  // 记录错误日志
  console.error(`[${new Date().toISOString()}] ${req.method} ${req.path} - ${statusCode}: ${message}`);
  
  if (error.stack) {
    console.error(error.stack);
  }

  // 开发环境返回详细错误信息
  const errorResponse: any = {
    error: message,
    statusCode
  };

  if (process.env['NODE_ENV'] === 'development') {
    errorResponse.stack = error.stack;
    errorResponse.path = req.path;
    errorResponse.method = req.method;
  }

  res.status(statusCode).json(errorResponse);
};

// 创建自定义错误类
export class ValidationError extends Error implements AppError {
  public statusCode: number;
  public isOperational: boolean;

  constructor(message: string) {
    super(message);
    this.statusCode = 400;
    this.isOperational = true;
    this.name = 'ValidationError';
  }
}

export class NotFoundError extends Error implements AppError {
  public statusCode: number;
  public isOperational: boolean;

  constructor(message: string = '资源不存在') {
    super(message);
    this.statusCode = 404;
    this.isOperational = true;
    this.name = 'NotFoundError';
  }
}

export class UnauthorizedError extends Error implements AppError {
  public statusCode: number;
  public isOperational: boolean;

  constructor(message: string = '未授权访问') {
    super(message);
    this.statusCode = 401;
    this.isOperational = true;
    this.name = 'UnauthorizedError';
  }
}

export class ForbiddenError extends Error implements AppError {
  public statusCode: number;
  public isOperational: boolean;

  constructor(message: string = '禁止访问') {
    super(message);
    this.statusCode = 403;
    this.isOperational = true;
    this.name = 'ForbiddenError';
  }
} 