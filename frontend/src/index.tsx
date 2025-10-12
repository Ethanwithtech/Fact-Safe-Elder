import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.simple';
import './index.css';

// 检查浏览器兼容性
const checkBrowserSupport = () => {
  const unsupportedFeatures = [];
  
  // 检查必需的API支持
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    unsupportedFeatures.push('音频录制 (getUserMedia)');
  }
  
  if (!window.SpeechRecognition && !window.webkitSpeechRecognition) {
    console.warn('浏览器不支持语音识别API，将使用降级方案');
  }
  
  if (!window.AudioContext && !window.webkitAudioContext) {
    unsupportedFeatures.push('音频处理 (AudioContext)');
  }
  
  if (unsupportedFeatures.length > 0) {
    const message = `您的浏览器不支持以下功能：\n${unsupportedFeatures.join('\n')}\n\n建议使用最新版本的 Chrome 或 Edge 浏览器以获得最佳体验。`;
    alert(message);
    console.error('浏览器兼容性检查失败:', unsupportedFeatures);
  }
};

// 全局错误处理
window.addEventListener('error', (event) => {
  console.error('全局错误:', event.error);
  // 可以在这里添加错误上报逻辑
});

window.addEventListener('unhandledrejection', (event) => {
  console.error('未处理的Promise拒绝:', event.reason);
  // 可以在这里添加错误上报逻辑
});

// 检查浏览器支持
checkBrowserSupport();

// 创建React应用根节点
const root = ReactDOM.createRoot(
  document.getElementById('root') as HTMLElement
);

// 渲染应用
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

// 性能监控
if (process.env.NODE_ENV === 'production') {
  // 可以在这里添加性能监控代码
  console.log('生产环境启动');
} else {
  console.log('开发环境启动');
  
  // 开发环境下的调试帮助
  (window as any).debugInfo = {
    version: '1.0.0',
    build: 'development',
    features: {
      audioSupport: !!(navigator.mediaDevices && navigator.mediaDevices.getUserMedia),
      speechRecognition: !!(window.SpeechRecognition || (window as any).webkitSpeechRecognition),
      audioContext: !!(window.AudioContext || (window as any).webkitAudioContext)
    }
  };
}
