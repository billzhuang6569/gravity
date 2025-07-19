import React from 'react';
import { motion } from 'framer-motion';
import { Download, Globe, Zap, Shield } from 'lucide-react';
import DownloadForm from './components/DownloadForm';
import TaskList from './components/TaskList';
import Header from './components/Header';

const App: React.FC = () => {
  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-600 via-purple-600 to-pink-600">
      {/* 背景装饰 */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-white/5 rounded-full blur-3xl animate-float"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-white/5 rounded-full blur-3xl animate-float-delayed"></div>
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-96 h-96 bg-white/5 rounded-full blur-3xl animate-float-delayed-2"></div>
      </div>

      <div className="relative z-10">
        <Header />
        
        <main className="container mx-auto px-4 py-8">
          {/* 英雄区域 */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8 }}
            className="text-center mb-12"
          >
            <h1 className="text-5xl md:text-7xl font-bold text-white text-shadow-lg mb-6">
              Gravity
            </h1>
            <p className="text-xl md:text-2xl text-white/90 text-shadow mb-8 max-w-3xl mx-auto">
              世界上最友好、最好用的视频下载器
            </p>
            
            {/* 特性展示 */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-4xl mx-auto mb-12">
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.2 }}
                className="glass-card p-6 text-center"
              >
                <Globe className="w-12 h-12 text-blue-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">支持数百个网站</h3>
                <p className="text-white/70">YouTube、Bilibili、Twitter 等主流平台</p>
              </motion.div>
              
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.4 }}
                className="glass-card p-6 text-center"
              >
                <Zap className="w-12 h-12 text-purple-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">极速下载</h3>
                <p className="text-white/70">直接粘贴链接，一键开始下载</p>
              </motion.div>
              
              <motion.div 
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.8, delay: 0.6 }}
                className="glass-card p-6 text-center"
              >
                <Shield className="w-12 h-12 text-pink-300 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-white mb-2">安全可靠</h3>
                <p className="text-white/70">本地部署，数据安全有保障</p>
              </motion.div>
            </div>
          </motion.div>

          {/* 下载表单 */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 0.8 }}
            className="max-w-4xl mx-auto mb-12"
          >
            <DownloadForm />
          </motion.div>

          {/* 任务列表 */}
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, delay: 1.0 }}
            className="max-w-6xl mx-auto"
          >
            <TaskList />
          </motion.div>
        </main>

        {/* 页脚 */}
        <footer className="text-center py-8 text-white/60">
          <p className="text-sm">
            © 2024 Gravity Video Downloader. 仅供学习和个人使用，请遵守相关法律法规。
          </p>
        </footer>
      </div>
    </div>
  );
};

export default App; 