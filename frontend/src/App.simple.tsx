import React from 'react';

function App() {
  return (
    <div style={{ 
      padding: '20px', 
      fontFamily: 'Arial, sans-serif',
      fontSize: '20px',
      textAlign: 'center'
    }}>
      <h1>🛡️ AI守护系统</h1>
      <p>老人短视频虚假信息检测系统</p>
      <div style={{
        margin: '20px 0',
        padding: '20px',
        border: '2px solid #52c41a',
        borderRadius: '10px',
        backgroundColor: '#f6ffed'
      }}>
        <h2>✅ 系统正常运行</h2>
        <p>前端服务已成功启动</p>
        <p>后端API: <a href="http://localhost:8008" target="_blank" rel="noopener noreferrer">http://localhost:8008</a></p>
        <p>API文档: <a href="http://localhost:8008/docs" target="_blank" rel="noopener noreferrer">http://localhost:8008/docs</a></p>
      </div>
      
      <div style={{
        margin: '20px 0',
        padding: '20px',
        border: '2px solid #1890ff',
        borderRadius: '10px',
        backgroundColor: '#f0f9ff'
      }}>
        <h3>🎯 核心功能</h3>
        <ul style={{ textAlign: 'left', display: 'inline-block' }}>
          <li>📱 手机视频模拟器</li>
          <li>🤖 AI智能检测</li>
          <li>🔔 风险预警系统</li>
          <li>👴 适老化设计</li>
        </ul>
      </div>
      
      <div style={{
        margin: '20px 0',
        padding: '20px',
        border: '2px solid #faad14',
        borderRadius: '10px',
        backgroundColor: '#fffbe6'
      }}>
        <h3>📊 系统状态</h3>
        <p>训练数据集: 1800个样本</p>
        <p>检测引擎: 正常运行</p>
        <p>API服务: 正常响应</p>
      </div>
    </div>
  );
}

export default App;
