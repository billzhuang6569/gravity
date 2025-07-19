import React from 'react';
import { motion } from 'framer-motion';
import { Download, Settings } from 'lucide-react';

const Header: React.FC = () => {
  return (
    <motion.header 
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.6 }}
      className="glass-card mx-4 mt-4 p-4"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Download className="w-8 h-8 text-white" />
          <h1 className="text-2xl font-bold text-white">Gravity</h1>
        </div>
        
        <div className="flex items-center space-x-4">
          <button className="btn-secondary flex items-center space-x-2">
            <Settings className="w-5 h-5" />
            <span>设置</span>
          </button>
        </div>
      </div>
    </motion.header>
  );
};

export default Header; 