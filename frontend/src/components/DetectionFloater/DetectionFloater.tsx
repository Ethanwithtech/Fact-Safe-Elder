import React, { useState, useEffect } from 'react';
import { Button, Modal } from 'antd';
import { DetectionResult } from '../../types/detection';
import './DetectionFloater.css';

interface DetectionFloaterProps {
  result: DetectionResult;
  onClose: () => void;
}

const DetectionFloater: React.FC<DetectionFloaterProps> = ({ result, onClose }) => {
  const [showDetail, setShowDetail] = useState(false);
  const [position, setPosition] = useState({ x: 20, y: 20 });

  // 根据风险等级获取样式和信息
  const getRiskInfo = () => {
    switch (result.level) {
      case 'danger':
        return {
          color: '#ff4d4f',
          bgColor: '#fff2f0',
          borderColor: '#ffccc7',
          icon: '🚨',
          title: '高风险警告',
          description: '检测到可能的诈骗或虚假信息',
          action: '建议立即停止观看'
        };
      case 'warning':
        return {
          color: '#faad14',
          bgColor: '#fffbe6',
          borderColor: '#ffe58f',
          icon: '⚠️',
          title: '注意风险',
          description: '内容存在可疑信息',
          action: '建议谨慎对待'
        };
      case 'safe':
        return {
          color: '#52c41a',
          bgColor: '#f6ffed',
          borderColor: '#b7eb8f',
          icon: '✅',
          title: '内容安全',
          description: '未发现明显风险',
          action: '可以正常观看'
        };
      default:
        return {
          color: '#666',
          bgColor: '#fafafa',
          borderColor: '#d9d9d9',
          icon: '❓',
          title: '检测中',
          description: '正在分析内容',
          action: '请稍候'
        };
    }
  };

  const riskInfo = getRiskInfo();

  // 自动隐藏安全提示
  useEffect(() => {
    if (result.level === 'safe') {
      const timer = setTimeout(() => {
        onClose();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [result.level, onClose]);

  // 拖拽功能
  const handleMouseDown = (e: React.MouseEvent) => {
    const startX = e.clientX - position.x;
    const startY = e.clientY - position.y;

    const handleMouseMove = (e: MouseEvent) => {
      setPosition({
        x: e.clientX - startX,
        y: e.clientY - startY
      });
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  };

  return (
    <>
      {/* 主浮窗 */}
      <div 
        className={`detection-floater ${result.level}`}
        style={{
          left: position.x,
          top: position.y,
          backgroundColor: riskInfo.bgColor,
          borderColor: riskInfo.borderColor,
          color: riskInfo.color
        }}
        onMouseDown={handleMouseDown}
      >
        {/* 拖拽手柄 */}
        <div className="drag-handle">
          <span className="drag-dots">⋮⋮</span>
        </div>

        {/* 主要内容 */}
        <div className="floater-content">
          <div className="risk-icon">{riskInfo.icon}</div>
          <div className="risk-info">
            <div className="risk-title">{riskInfo.title}</div>
            <div className="risk-score">
              风险评分: {Math.round(result.score * 100)}/100
            </div>
          </div>
        </div>

        {/* 操作按钮 */}
        <div className="floater-actions">
          <Button 
            type="text" 
            size="small"
            onClick={() => setShowDetail(true)}
            className="detail-btn"
          >
            详情
          </Button>
          <Button 
            type="text" 
            size="small"
            onClick={onClose}
            className="close-btn"
          >
            ✕
          </Button>
        </div>

        {/* 简要提示 */}
        <div className="quick-tip">
          {riskInfo.description}
        </div>
      </div>

      {/* 详细信息弹窗 */}
      <Modal
        title={
          <div className="modal-title">
            <span className="modal-icon">{riskInfo.icon}</span>
            <span>{riskInfo.title}</span>
          </div>
        }
        open={showDetail}
        onCancel={() => setShowDetail(false)}
        footer={[
          <Button key="close" onClick={() => setShowDetail(false)}>
            关闭
          </Button>
        ]}
        className="detection-detail-modal"
        width={600}
      >
        <div className="detection-details">
          {/* 风险概况 */}
          <div className="detail-section">
            <h4>🔍 检测结果</h4>
            <div className="result-summary">
              <div className="summary-item">
                <span className="label">风险等级：</span>
                <span className={`value ${result.level}`}>
                  {riskInfo.title}
                </span>
              </div>
              <div className="summary-item">
                <span className="label">风险评分：</span>
                <span className="value">{Math.round(result.score * 100)}/100</span>
              </div>
              <div className="summary-item">
                <span className="label">检测时间：</span>
                <span className="value">
                  {result.timestamp.toLocaleString('zh-CN')}
                </span>
              </div>
            </div>
          </div>

          {/* 风险原因 */}
          {result.reasons.length > 0 && (
            <div className="detail-section">
              <h4>⚡ 识别到的风险因素</h4>
              <ul className="risk-reasons">
                {result.reasons.map((reason, index) => (
                  <li key={index}>{reason}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 建议措施 */}
          {result.suggestions.length > 0 && (
            <div className="detail-section">
              <h4>💡 安全建议</h4>
              <ul className="suggestions">
                {result.suggestions.map((suggestion, index) => (
                  <li key={index}>{suggestion}</li>
                ))}
              </ul>
            </div>
          )}

          {/* 通用安全提示 */}
          <div className="detail-section safety-tips">
            <h4>🛡️ 防骗提醒</h4>
            <div className="tips-grid">
              <div className="tip-item">
                <div className="tip-icon">💰</div>
                <div className="tip-text">
                  <strong>投资理财</strong><br/>
                  保证高收益的都是骗局，正规投资都有风险
                </div>
              </div>
              <div className="tip-item">
                <div className="tip-icon">💊</div>
                <div className="tip-text">
                  <strong>医疗健康</strong><br/>
                  包治百病的产品不存在，有病请找正规医院
                </div>
              </div>
              <div className="tip-item">
                <div className="tip-icon">📞</div>
                <div className="tip-text">
                  <strong>紧急情况</strong><br/>
                  遇到可疑情况，立即咨询家人或拨打110
                </div>
              </div>
            </div>
          </div>

          {/* 举报功能 */}
          <div className="detail-section">
            <h4>🚨 举报可疑内容</h4>
            <div className="report-actions">
              <Button 
                type="primary" 
                danger={result.level === 'danger'}
                onClick={() => {
                  // 这里可以实现举报功能
                  Modal.info({
                    title: '举报成功',
                    content: '感谢您的举报，我们会及时处理可疑内容。',
                  });
                }}
              >
                举报此内容
              </Button>
              <Button 
                type="default"
                onClick={() => {
                  // 这里可以实现通知家人功能
                  Modal.confirm({
                    title: '通知家人',
                    content: '是否要将此检测结果发送给您的家人？',
                    onOk: () => {
                      // 实现通知家人的逻辑
                      console.log('通知家人:', result);
                    }
                  });
                }}
              >
                通知家人
              </Button>
            </div>
          </div>
        </div>
      </Modal>
    </>
  );
};

export default DetectionFloater;
