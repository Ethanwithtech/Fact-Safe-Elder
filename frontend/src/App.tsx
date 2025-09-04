import React, { useState, useEffect } from 'react';
import { ConfigProvider, Tabs, Badge } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import './App.css';
import MobileSimulator from './components/MobileSimulator/MobileSimulator';
import VideoSimulator from './components/VideoSimulator/VideoSimulator';
import DetectionFloater from './components/DetectionFloater/DetectionFloater';
import Settings from './components/Settings/Settings';
import TrainingDashboard from './components/TrainingDashboard/TrainingDashboard';
import { DetectionResult } from './types/detection';

function App() {
  const [detectionResult, setDetectionResult] = useState<DetectionResult | null>(null);
  const [isListening, setIsListening] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [fontSize, setFontSize] = useState<'normal' | 'large' | 'extra-large'>('large');
  const [highContrast, setHighContrast] = useState(true);

  // 应用适老化设置
  useEffect(() => {
    const body = document.body;
    
    // 字体大小设置
    body.classList.remove('large-font', 'extra-large-font');
    if (fontSize === 'large') {
      body.classList.add('large-font');
    } else if (fontSize === 'extra-large') {
      body.classList.add('extra-large-font');
    }
    
    // 高对比度设置
    if (highContrast) {
      body.classList.add('high-contrast');
    } else {
      body.classList.remove('high-contrast');
    }
  }, [fontSize, highContrast]);

  const handleDetectionResult = (result: DetectionResult) => {
    setDetectionResult(result);
    
    // 如果检测到高风险，播放警告音
    if (result.level === 'danger') {
      // 创建警告音频
      const audioContext = new (window.AudioContext || (window as any).webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();
      
      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);
      
      oscillator.frequency.setValueAtTime(800, audioContext.currentTime);
      gainNode.gain.setValueAtTime(0.3, audioContext.currentTime);
      
      oscillator.start();
      oscillator.stop(audioContext.currentTime + 0.5);
    }
  };

  const tabItems = [
    {
      key: 'mobile',
      label: (
        <span>
          📱 手机模拟
          <Badge 
            count="AI" 
            style={{ 
              backgroundColor: '#52c41a',
              marginLeft: 8,
              fontSize: 10
            }}
          />
        </span>
      ),
      children: (
        <MobileSimulator 
          onDetectionResult={handleDetectionResult}
        />
      )
    },
    {
      key: 'desktop',
      label: '🖥️ 桌面检测',
      children: (
        <div className="desktop-container">
          <VideoSimulator 
            isListening={isListening}
            onListeningChange={setIsListening}
            onDetectionResult={handleDetectionResult}
          />
          <div className="info-panel">
            <div className="status-card">
              <h3>🔍 检测状态</h3>
              <div className={`status-indicator ${isListening ? 'listening' : 'stopped'}`}>
                {isListening ? '🟢 正在监听' : '🔴 已停止'}
              </div>
              <p>
                {isListening 
                  ? 'AI模型正在实时分析视频内容' 
                  : '点击"开始监听"激活AI检测'
                }
              </p>
            </div>
          </div>
        </div>
      )
    },
    {
      key: 'training',
      label: (
        <span>
          🎓 模型训练
          <Badge 
            count="New" 
            style={{ 
              backgroundColor: '#ff4d4f',
              marginLeft: 8,
              fontSize: 10
            }}
          />
        </span>
      ),
      children: <TrainingDashboard />
    }
  ];

  return (
    <ConfigProvider locale={zhCN}>
      <div className={`app ${highContrast ? 'high-contrast' : ''}`}>
        <header className="app-header">
          <div className="header-content">
            <h1>
              🛡️ AI守护 - 老人短视频虚假信息检测系统
              <span className="version-badge">v2.0 AI版</span>
            </h1>
            <div className="header-actions">
              <span className="ai-status">
                🤖 AI状态: <span className="status-online">在线</span>
              </span>
              <button 
                className="settings-btn"
                onClick={() => setShowSettings(true)}
                title="设置"
              >
                ⚙️ 设置
              </button>
            </div>
          </div>
        </header>

        <main className="app-main-v2">
          <Tabs
            defaultActiveKey="mobile"
            size="large"
            className="main-tabs"
            items={tabItems}
          />
          
          {/* 全局检测浮窗 */}
          {detectionResult && (
            <DetectionFloater 
              result={detectionResult}
              onClose={() => setDetectionResult(null)}
            />
          )}
        </main>

        {/* 设置面板 */}
        {showSettings && (
          <Settings 
            fontSize={fontSize}
            highContrast={highContrast}
            onFontSizeChange={setFontSize}
            onHighContrastChange={setHighContrast}
            onClose={() => setShowSettings(false)}
          />
        )}
      </div>
    </ConfigProvider>
  );
}

export default App;
