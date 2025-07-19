import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Link, Download, Video, Music } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { createDownloadTask } from '../services/api';

const DownloadForm: React.FC = () => {
  const [url, setUrl] = useState('');
  const [format, setFormat] = useState('best');
  const [type, setType] = useState<'video' | 'audio'>('video');
  const [isLoading, setIsLoading] = useState(false);
  
  const queryClient = useQueryClient();

  const createTaskMutation = useMutation({
    mutationFn: createDownloadTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setUrl('');
      setIsLoading(false);
    },
    onError: (error) => {
      console.error('创建任务失败:', error);
      setIsLoading(false);
    }
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim()) return;

    setIsLoading(true);
    createTaskMutation.mutate({
      url: url.trim(),
      format,
      type
    });
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      setUrl(text);
    } catch (error) {
      console.error('读取剪贴板失败:', error);
    }
  };

  return (
    <motion.div 
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.5 }}
      className="glass-card p-8"
    >
      <div className="text-center mb-8">
        <h2 className="text-3xl font-bold text-white mb-2">开始下载</h2>
        <p className="text-white/70">粘贴视频链接，选择格式，一键下载</p>
      </div>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* URL 输入 */}
        <div className="space-y-2">
          <label className="block text-white font-medium">视频链接</label>
          <div className="relative">
            <input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="粘贴视频链接到这里..."
              className="input-field pr-12"
              required
            />
            <button
              type="button"
              onClick={handlePaste}
              className="absolute right-3 top-1/2 transform -translate-y-1/2 text-white/60 hover:text-white transition-colors"
            >
              <Link className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* 格式选择 */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="space-y-2">
            <label className="block text-white font-medium">下载类型</label>
            <div className="flex space-x-2">
              <button
                type="button"
                onClick={() => setType('video')}
                className={`flex-1 flex items-center justify-center space-x-2 py-3 px-4 rounded-xl transition-all duration-200 ${
                  type === 'video' 
                    ? 'bg-blue-500 text-white' 
                    : 'bg-white/10 text-white/70 hover:bg-white/20'
                }`}
              >
                <Video className="w-5 h-5" />
                <span>视频</span>
              </button>
              <button
                type="button"
                onClick={() => setType('audio')}
                className={`flex-1 flex items-center justify-center space-x-2 py-3 px-4 rounded-xl transition-all duration-200 ${
                  type === 'audio' 
                    ? 'bg-blue-500 text-white' 
                    : 'bg-white/10 text-white/70 hover:bg-white/20'
                }`}
              >
                <Music className="w-5 h-5" />
                <span>音频</span>
              </button>
            </div>
          </div>

          <div className="space-y-2">
            <label className="block text-white font-medium">视频质量</label>
            <select
              value={format}
              onChange={(e) => setFormat(e.target.value)}
              className="input-field"
            >
              <option value="best">最佳质量</option>
              <option value="worst">最低质量</option>
              <option value="720p">720p</option>
              <option value="480p">480p</option>
              <option value="360p">360p</option>
            </select>
          </div>
        </div>

        {/* 提交按钮 */}
        <button
          type="submit"
          disabled={isLoading || !url.trim()}
          className="btn-primary w-full flex items-center justify-center space-x-2 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? (
            <>
              <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
              <span>处理中...</span>
            </>
          ) : (
            <>
              <Download className="w-5 h-5" />
              <span>开始下载</span>
            </>
          )}
        </button>
      </form>

      {/* 提示信息 */}
      <div className="mt-6 p-4 bg-white/5 rounded-xl">
        <p className="text-white/70 text-sm">
          💡 提示：支持 YouTube、Bilibili、Twitter、Instagram 等数百个网站的视频下载
        </p>
      </div>
    </motion.div>
  );
};

export default DownloadForm; 