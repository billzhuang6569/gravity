import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery } from '@tanstack/react-query';
import { getTasks, deleteTask, downloadFile, Task } from '../services/api';
import { 
  Play, 
  Pause, 
  CheckCircle, 
  XCircle, 
  Download, 
  Trash2, 
  Clock,
  FileVideo,
  FileAudio
} from 'lucide-react';

const TaskList: React.FC = () => {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ['tasks'],
    queryFn: () => getTasks(),
    refetchInterval: 2000, // 每2秒刷新一次
  });

  const handleDelete = async (taskId: string) => {
    try {
      await deleteTask(taskId);
      refetch();
    } catch (error) {
      console.error('删除任务失败:', error);
    }
  };

  const handleDownload = async (taskId: string, title: string) => {
    try {
      const blob = await downloadFile(taskId);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${title}.mp4`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('下载文件失败:', error);
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <Clock className="w-5 h-5 text-yellow-400" />;
      case 'processing':
        return <Play className="w-5 h-5 text-blue-400 animate-pulse" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-400" />;
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-400" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getStatusText = (status: string) => {
    switch (status) {
      case 'pending':
        return '等待中';
      case 'processing':
        return '下载中';
      case 'completed':
        return '已完成';
      case 'failed':
        return '失败';
      default:
        return '未知';
    }
  };

  const formatFileSize = (bytes?: number) => {
    if (!bytes) return '未知';
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return `${(bytes / Math.pow(1024, i)).toFixed(1)} ${sizes[i]}`;
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return '未知';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;
    
    if (hours > 0) {
      return `${hours}:${minutes.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }
    return `${minutes}:${secs.toString().padStart(2, '0')}`;
  };

  if (isLoading) {
    return (
      <div className="glass-card p-8 text-center">
        <div className="w-8 h-8 border-2 border-white/30 border-t-white rounded-full animate-spin mx-auto mb-4"></div>
        <p className="text-white/70">加载任务列表...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="glass-card p-8 text-center">
        <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
        <p className="text-white/70">加载任务列表失败</p>
      </div>
    );
  }

  const tasks = data?.tasks || [];

  return (
    <div className="glass-card p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-white">下载任务</h2>
        <button
          onClick={() => refetch()}
          className="btn-secondary"
        >
          刷新
        </button>
      </div>

      {tasks.length === 0 ? (
        <div className="text-center py-12">
          <FileVideo className="w-16 h-16 text-white/30 mx-auto mb-4" />
          <p className="text-white/70">暂无下载任务</p>
          <p className="text-white/50 text-sm">开始添加第一个下载任务吧！</p>
        </div>
      ) : (
        <div className="space-y-4">
          <AnimatePresence>
            {tasks.map((task: Task) => (
              <motion.div
                key={task.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -20 }}
                transition={{ duration: 0.3 }}
                className="bg-white/5 backdrop-blur-sm rounded-xl p-4 border border-white/10"
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-3 mb-2">
                      {task.type === 'video' ? (
                        <FileVideo className="w-5 h-5 text-blue-400" />
                      ) : (
                        <FileAudio className="w-5 h-5 text-purple-400" />
                      )}
                      <h3 className="text-white font-medium truncate">{task.title}</h3>
                    </div>
                    
                    <div className="flex items-center space-x-4 text-sm text-white/60 mb-3">
                      <span>{task.format}</span>
                      <span>{task.type === 'video' ? '视频' : '音频'}</span>
                      {task.duration && (
                        <span>{formatDuration(task.duration)}</span>
                      )}
                      {task.file_size && (
                        <span>{formatFileSize(task.file_size)}</span>
                      )}
                    </div>

                    {/* 进度条 */}
                    <div className="progress-bar mb-3">
                      <div 
                        className="progress-fill"
                        style={{ width: `${task.progress}%` }}
                      ></div>
                    </div>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        {getStatusIcon(task.status)}
                        <span className="text-white/80 text-sm">{getStatusText(task.status)}</span>
                        <span className="text-white/60 text-sm">{task.progress}%</span>
                      </div>

                      <div className="flex items-center space-x-2">
                        {task.status === 'completed' && (
                          <button
                            onClick={() => handleDownload(task.id, task.title)}
                            className="btn-secondary text-sm py-2 px-3"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                        )}
                        <button
                          onClick={() => handleDelete(task.id)}
                          className="bg-red-500/20 hover:bg-red-500/30 text-red-300 hover:text-red-200 p-2 rounded-lg transition-colors"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {task.error_message && (
                      <div className="mt-2 p-2 bg-red-500/10 border border-red-500/20 rounded-lg">
                        <p className="text-red-300 text-sm">{task.error_message}</p>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
};

export default TaskList; 