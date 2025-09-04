import React, { useState } from 'react';
import { Modal, Switch, Radio, Slider, Button, Input, message } from 'antd';
import { UserSettings } from '../../types/detection';
import './Settings.css';

interface SettingsProps {
  fontSize: 'normal' | 'large' | 'extra-large';
  highContrast: boolean;
  onFontSizeChange: (size: 'normal' | 'large' | 'extra-large') => void;
  onHighContrastChange: (enabled: boolean) => void;
  onClose: () => void;
}

const Settings: React.FC<SettingsProps> = ({
  fontSize,
  highContrast,
  onFontSizeChange,
  onHighContrastChange,
  onClose
}) => {
  const [sensitivity, setSensitivity] = useState<'low' | 'medium' | 'high'>('medium');
  const [enableSound, setEnableSound] = useState(true);
  const [familyContact, setFamilyContact] = useState('');
  const [enableNotification, setEnableNotification] = useState(true);

  const handleSave = () => {
    // 保存设置到本地存储
    const settings: UserSettings = {
      fontSize,
      highContrast,
      sensitivity,
      enableSound,
      familyContact
    };
    
    localStorage.setItem('elderSafetySettings', JSON.stringify(settings));
    message.success('设置已保存');
    onClose();
  };

  const handleReset = () => {
    onFontSizeChange('large');
    onHighContrastChange(true);
    setSensitivity('medium');
    setEnableSound(true);
    setFamilyContact('');
    setEnableNotification(true);
    message.info('设置已重置为推荐配置');
  };

  const testAlert = () => {
    if (enableSound) {
      // 播放测试音效
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
    message.success('测试警报已播放');
  };

  return (
    <Modal
      title={
        <div className="settings-title">
          <span className="settings-icon">⚙️</span>
          <span>个人设置</span>
        </div>
      }
      open={true}
      onCancel={onClose}
      width={700}
      className="settings-modal"
      footer={[
        <Button key="reset" onClick={handleReset}>
          恢复默认
        </Button>,
        <Button key="cancel" onClick={onClose}>
          取消
        </Button>,
        <Button key="save" type="primary" onClick={handleSave}>
          保存设置
        </Button>
      ]}
    >
      <div className="settings-content">
        {/* 显示设置 */}
        <div className="settings-section">
          <h3>📱 显示设置</h3>
          
          <div className="setting-item">
            <div className="setting-label">
              <span>字体大小</span>
              <span className="setting-desc">选择适合的字体大小</span>
            </div>
            <div className="setting-control">
              <Radio.Group 
                value={fontSize} 
                onChange={(e) => onFontSizeChange(e.target.value)}
                size="large"
              >
                <Radio value="normal">标准</Radio>
                <Radio value="large">大字体 (推荐)</Radio>
                <Radio value="extra-large">超大字体</Radio>
              </Radio.Group>
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-label">
              <span>高对比度</span>
              <span className="setting-desc">提高文字和背景的对比度</span>
            </div>
            <div className="setting-control">
              <Switch 
                checked={highContrast}
                onChange={onHighContrastChange}
                size="default"
                checkedChildren="开启"
                unCheckedChildren="关闭"
              />
            </div>
          </div>
        </div>

        {/* 检测设置 */}
        <div className="settings-section">
          <h3>🔍 检测设置</h3>
          
          <div className="setting-item">
            <div className="setting-label">
              <span>检测敏感度</span>
              <span className="setting-desc">调整虚假信息检测的敏感程度</span>
            </div>
            <div className="setting-control">
              <Radio.Group 
                value={sensitivity} 
                onChange={(e) => setSensitivity(e.target.value)}
                size="large"
              >
                <Radio value="low">
                  <div>
                    <div>宽松</div>
                    <small>只检测明显的诈骗信息</small>
                  </div>
                </Radio>
                <Radio value="medium">
                  <div>
                    <div>适中 (推荐)</div>
                    <small>平衡检测准确性和误报率</small>
                  </div>
                </Radio>
                <Radio value="high">
                  <div>
                    <div>严格</div>
                    <small>检测所有可疑内容</small>
                  </div>
                </Radio>
              </Radio.Group>
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-label">
              <span>声音提醒</span>
              <span className="setting-desc">检测到风险时播放提示音</span>
            </div>
            <div className="setting-control">
              <Switch 
                checked={enableSound}
                onChange={setEnableSound}
                size="default"
                checkedChildren="开启"
                unCheckedChildren="关闭"
              />
              <Button 
                size="small" 
                onClick={testAlert}
                style={{ marginLeft: 10 }}
              >
                测试音效
              </Button>
            </div>
          </div>
        </div>

        {/* 家人联系 */}
        <div className="settings-section">
          <h3>👨‍👩‍👧‍👦 家人设置</h3>
          
          <div className="setting-item">
            <div className="setting-label">
              <span>家人电话</span>
              <span className="setting-desc">紧急情况下联系的家人电话</span>
            </div>
            <div className="setting-control">
              <Input
                value={familyContact}
                onChange={(e) => setFamilyContact(e.target.value)}
                placeholder="请输入家人电话号码"
                size="large"
                maxLength={20}
              />
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-label">
              <span>风险通知</span>
              <span className="setting-desc">检测到高风险内容时通知家人</span>
            </div>
            <div className="setting-control">
              <Switch 
                checked={enableNotification}
                onChange={setEnableNotification}
                size="default"
                checkedChildren="开启"
                unCheckedChildren="关闭"
              />
            </div>
          </div>
        </div>

        {/* 使用帮助 */}
        <div className="settings-section">
          <h3>❓ 使用帮助</h3>
          
          <div className="help-content">
            <div className="help-item">
              <strong>🎤 如何使用音频监听？</strong>
              <p>点击"开始监听"按钮，系统会通过麦克风监听视频音频内容并进行实时分析。</p>
            </div>
            
            <div className="help-item">
              <strong>🚨 风险提示说明</strong>
              <ul>
                <li><span className="risk-color safe">绿色</span> - 内容安全，可以正常观看</li>
                <li><span className="risk-color warning">黄色</span> - 存在可疑内容，建议谨慎对待</li>
                <li><span className="risk-color danger">红色</span> - 高风险内容，建议立即停止观看</li>
              </ul>
            </div>
            
            <div className="help-item">
              <strong>📞 遇到问题怎么办？</strong>
              <p>如遇紧急情况或可疑内容，请立即联系家人或拨打110报警。</p>
            </div>
          </div>
        </div>

        {/* 隐私说明 */}
        <div className="settings-section privacy-section">
          <h3>🔒 隐私保护</h3>
          <div className="privacy-info">
            <p>🛡️ 我们严格保护您的隐私：</p>
            <ul>
              <li>音频数据仅在本地处理，不会上传到服务器</li>
              <li>检测结果和设置信息仅存储在您的设备上</li>
              <li>您可以随时清除所有数据</li>
            </ul>
            <Button 
              type="link" 
              size="small"
              onClick={() => {
                localStorage.removeItem('elderSafetySettings');
                localStorage.removeItem('detectionHistory');
                message.success('本地数据已清除');
              }}
            >
              清除所有本地数据
            </Button>
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default Settings;
