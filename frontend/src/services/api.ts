import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data;
  },
  (error) => {
    console.error('API Error:', error);
    return Promise.reject(error);
  }
);

export interface CreateTaskRequest {
  url: string;
  format: string;
  type: 'video' | 'audio';
}

export interface Task {
  id: string;
  url: string;
  title: string;
  format: string;
  type: 'video' | 'audio';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress: number;
  file_path?: string;
  file_size?: number;
  duration?: number;
  thumbnail?: string;
  created_at: string;
  updated_at: string;
  error_message?: string;
}

export interface CreateTaskResponse {
  success: boolean;
  task: Task;
}

export interface GetTasksResponse {
  success: boolean;
  tasks: Task[];
  pagination: {
    limit: number;
    offset: number;
    total: number;
  };
}

export interface GetTaskResponse {
  success: boolean;
  task: Task;
}

// API 函数
export const createDownloadTask = async (data: CreateTaskRequest): Promise<CreateTaskResponse> => {
  return api.post('/api/tasks', data);
};

export const getTasks = async (limit: number = 50, offset: number = 0): Promise<GetTasksResponse> => {
  return api.get('/api/tasks', {
    params: { limit, offset }
  });
};

export const getTask = async (taskId: string): Promise<GetTaskResponse> => {
  return api.get(`/api/tasks/${taskId}`);
};

export const deleteTask = async (taskId: string): Promise<{ success: boolean; message: string }> => {
  return api.delete(`/api/tasks/${taskId}`);
};

export const downloadFile = async (taskId: string): Promise<Blob> => {
  const response = await axios.get(`${API_BASE_URL}/api/downloads/${taskId}`, {
    responseType: 'blob',
  });
  return response.data;
};

export const getDownloadHistory = async (taskId?: string): Promise<any> => {
  const url = taskId ? `/api/downloads/history/${taskId}` : '/api/downloads/history';
  return api.get(url);
};

export default api; 