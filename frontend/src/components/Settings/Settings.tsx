import React, { useState } from 'react';
import { Switch, Radio, Button, Input, message } from 'antd';
import { Language, t } from '../../i18n';
import { ThemeMode } from '../../theme';
import OpenClawService, { OpenClawConfig } from '../../services/OpenClawService';
import './Settings.css';

interface SettingsProps {
  fontSize: 'normal' | 'large' | 'extra-large';
  highContrast: boolean;
  lang: Language;
  themeMode: ThemeMode;
  onFontSizeChange: (size: 'normal' | 'large' | 'extra-large') => void;
  onHighContrastChange: (enabled: boolean) => void;
  onLanguageChange: (lang: Language) => void;
  onThemeChange: (mode: ThemeMode) => void;
  onClose: () => void;
}

const Settings: React.FC<SettingsProps> = ({
  fontSize, highContrast, lang, themeMode,
  onFontSizeChange, onHighContrastChange, onLanguageChange, onThemeChange, onClose,
}) => {
  const [sensitivity, setSensitivity] = useState<'low' | 'medium' | 'high'>('medium');
  const [enableSound, setEnableSound] = useState(true);
  const [familyContact, setFamilyContact] = useState('');
  const [enableNotification, setEnableNotification] = useState(true);

  // OpenClaw 配置
  const [openClawService] = useState(() => new OpenClawService());
  const [openClawConfig, setOpenClawConfig] = useState<OpenClawConfig>(openClawService.getConfig());
  const [testingSending, setTestingSending] = useState(false);

  const updateOpenClaw = (partial: Partial<OpenClawConfig>) => {
    const newConfig = { ...openClawConfig, ...partial };
    setOpenClawConfig(newConfig);
    openClawService.updateConfig(partial);
  };

  const handleSave = () => {
    localStorage.setItem('elderSafetySettings', JSON.stringify({
      fontSize, highContrast, sensitivity, enableSound, familyContact, lang, themeMode,
    }));
    message.success(t(lang, 'settingsSaved'));
    onClose();
  };

  const handleReset = () => {
    onFontSizeChange('large');
    onHighContrastChange(false);
    onLanguageChange('zh');
    onThemeChange('dark');
    setSensitivity('medium');
    setEnableSound(true);
    setFamilyContact('');
    setEnableNotification(true);
    updateOpenClaw({ enabled: false, qclawWebhookUrl: '', directWebhookUrl: '', channel: 'wecom', threshold: 70, useQClaw: true });
    message.info(t(lang, 'settingsReset'));
  };

  const testAlert = () => {
    if (enableSound) {
      const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.connect(gain); gain.connect(ctx.destination);
      osc.frequency.setValueAtTime(800, ctx.currentTime);
      gain.gain.setValueAtTime(0.3, ctx.currentTime);
      osc.start(); osc.stop(ctx.currentTime + 0.5);
    }
    message.success(lang === 'zh' ? '测试警报已播放' : 'Test alert played');
  };

  const handleTestOpenClaw = async () => {
    if (!openClawConfig.qclawWebhookUrl && !openClawConfig.directWebhookUrl) {
      message.warning(lang === 'zh' ? '请先填写 QClaw Webhook 或直接 Webhook 地址' : 'Please enter a Webhook URL first');
      return;
    }
    setTestingSending(true);
    try {
      const success = await openClawService.sendTestAlert();
      if (success) {
        message.success(t(lang, 'openclawTestSuccess'));
      } else {
        message.error(lang === 'zh' ? '发送失败，请检查 Webhook 地址' : 'Failed. Check Webhook URL');
      }
    } catch {
      message.error(lang === 'zh' ? '发送失败' : 'Send failed');
    } finally {
      setTestingSending(false);
    }
  };

  return (
    <div className="settings-overlay" onClick={onClose}>
      <div className="settings-panel" onClick={(e) => e.stopPropagation()}>
        <div className="settings-panel-header">
          <div className="settings-title"><span className="settings-icon">⚙️</span><span>{t(lang, 'settingsTitle')}</span></div>
          <button className="settings-panel-close" onClick={onClose}>✕</button>
        </div>
        <div className="settings-content">
        {/* 显示设置 */}
        <div className="settings-section">
          <h3>{t(lang, 'displaySettings')}</h3>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'language')}</span>
              <span className="setting-desc">{t(lang, 'languageDesc')}</span>
            </div>
            <div className="setting-control">
              <Radio.Group value={lang} onChange={(e) => onLanguageChange(e.target.value)} size="large">
                <Radio value="zh">🇨🇳 中文</Radio>
                <Radio value="en">🇺🇸 English</Radio>
              </Radio.Group>
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'themeMode')}</span>
              <span className="setting-desc">{t(lang, 'themeModeDesc')}</span>
            </div>
            <div className="setting-control">
              <Radio.Group value={themeMode} onChange={(e) => onThemeChange(e.target.value)} size="large">
                <Radio value="dark">🌙 {t(lang, 'themeDark')}</Radio>
                <Radio value="light">☀️ {t(lang, 'themeLight')}</Radio>
              </Radio.Group>
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'fontSize')}</span>
              <span className="setting-desc">{t(lang, 'fontSizeDesc')}</span>
            </div>
            <div className="setting-control">
              <Radio.Group value={fontSize} onChange={(e) => onFontSizeChange(e.target.value)} size="large">
                <Radio value="normal">{t(lang, 'fontNormal')}</Radio>
                <Radio value="large">{t(lang, 'fontLarge')}</Radio>
                <Radio value="extra-large">{t(lang, 'fontExtraLarge')}</Radio>
              </Radio.Group>
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'highContrast')}</span>
              <span className="setting-desc">{t(lang, 'highContrastDesc')}</span>
            </div>
            <div className="setting-control">
              <Switch checked={highContrast} onChange={onHighContrastChange} checkedChildren={t(lang, 'on')} unCheckedChildren={t(lang, 'off')} />
            </div>
          </div>
        </div>

        {/* 检测设置 */}
        <div className="settings-section">
          <h3>{t(lang, 'detectionSettings')}</h3>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'sensitivity')}</span>
              <span className="setting-desc">{t(lang, 'sensitivityDesc')}</span>
            </div>
            <div className="setting-control">
              <Radio.Group value={sensitivity} onChange={(e) => setSensitivity(e.target.value)} size="large">
                <Radio value="low"><div><div>{t(lang, 'sensitivityLow')}</div><small>{t(lang, 'sensitivityLowDesc')}</small></div></Radio>
                <Radio value="medium"><div><div>{t(lang, 'sensitivityMedium')}</div><small>{t(lang, 'sensitivityMediumDesc')}</small></div></Radio>
                <Radio value="high"><div><div>{t(lang, 'sensitivityHigh')}</div><small>{t(lang, 'sensitivityHighDesc')}</small></div></Radio>
              </Radio.Group>
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'soundAlert')}</span>
              <span className="setting-desc">{t(lang, 'soundAlertDesc')}</span>
            </div>
            <div className="setting-control">
              <Switch checked={enableSound} onChange={setEnableSound} checkedChildren={t(lang, 'on')} unCheckedChildren={t(lang, 'off')} />
              <Button size="small" onClick={testAlert} style={{ marginLeft: 10 }}>{t(lang, 'testSound')}</Button>
            </div>
          </div>
        </div>

        {/* 家人设置 */}
        <div className="settings-section">
          <h3>{t(lang, 'familySettings')}</h3>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'familyPhone')}</span>
              <span className="setting-desc">{t(lang, 'familyPhoneDesc')}</span>
            </div>
            <div className="setting-control">
              <Input value={familyContact} onChange={(e) => setFamilyContact(e.target.value)} placeholder={t(lang, 'familyPhonePlaceholder')} size="large" maxLength={20} />
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'riskNotify')}</span>
              <span className="setting-desc">{t(lang, 'riskNotifyDesc')}</span>
            </div>
            <div className="setting-control">
              <Switch checked={enableNotification} onChange={setEnableNotification} checkedChildren={t(lang, 'on')} unCheckedChildren={t(lang, 'off')} />
            </div>
          </div>
        </div>

        {/* OpenClaw 配置 */}
        <div className="settings-section openclaw-section">
          <h3>{t(lang, 'openclawSettings')}</h3>
          <p className="section-desc">{t(lang, 'openclawDesc')}</p>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'openclawEnable')}</span>
              <span className="setting-desc">{t(lang, 'openclawEnableDesc')}</span>
            </div>
            <div className="setting-control">
              <Switch checked={openClawConfig.enabled} onChange={(v) => updateOpenClaw({ enabled: v })} checkedChildren={t(lang, 'on')} unCheckedChildren={t(lang, 'off')} />
            </div>
          </div>

          {openClawConfig.enabled && (
            <>
              <div className="setting-item">
                <div className="setting-label">
                  <span>{lang === 'zh' ? 'QClaw Webhook URL' : 'QClaw Webhook URL'}</span>
                  <span className="setting-desc">{lang === 'zh' ? '从 QClaw 安装 Skill 后获取' : 'Get from QClaw after installing Skill'}</span>
                </div>
                <div className="setting-control" style={{ flex: 1 }}>
                  <Input
                    value={openClawConfig.qclawWebhookUrl}
                    onChange={(e) => {
                      updateOpenClaw({ qclawWebhookUrl: e.target.value });
                      // 同步保存到后端
                      if (e.target.value) {
                        openClawService.saveQClawWebhookToBackend(e.target.value);
                      }
                    }}
                    placeholder={lang === 'zh' ? 'QClaw 分配的 Webhook URL' : 'QClaw assigned Webhook URL'}
                    size="large"
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              <div className="setting-item">
                <div className="setting-label">
                  <span>{lang === 'zh' ? '备用直接 Webhook' : 'Direct Webhook (Fallback)'}</span>
                  <span className="setting-desc">{lang === 'zh' ? '企业微信/QQ 机器人 Webhook（不经过 QClaw）' : 'WeCom/QQ bot Webhook (bypass QClaw)'}</span>
                </div>
                <div className="setting-control" style={{ flex: 1 }}>
                  <Input
                    value={openClawConfig.directWebhookUrl}
                    onChange={(e) => updateOpenClaw({ directWebhookUrl: e.target.value })}
                    placeholder={t(lang, 'openclawWebhookPlaceholder')}
                    size="large"
                    style={{ width: '100%' }}
                  />
                </div>
              </div>

              <div className="setting-item">
                <div className="setting-label">
                  <span>{t(lang, 'openclawChannel')}</span>
                </div>
                <div className="setting-control">
                  <Radio.Group value={openClawConfig.channel} onChange={(e) => updateOpenClaw({ channel: e.target.value })} size="large">
                    <Radio value="wecom">{t(lang, 'openclawWecom')}</Radio>
                    <Radio value="qq">{t(lang, 'openclawQQ')}</Radio>
                    <Radio value="both">{t(lang, 'openclawBoth')}</Radio>
                  </Radio.Group>
                </div>
              </div>

              <div className="setting-item">
                <div className="setting-label">
                  <span>{t(lang, 'openclawThreshold')}</span>
                  <span className="setting-desc">{t(lang, 'openclawThresholdDesc')}</span>
                </div>
                <div className="setting-control">
                  <Radio.Group
                    value={openClawConfig.threshold}
                    onChange={(e) => updateOpenClaw({ threshold: e.target.value })}
                    size="large"
                    optionType="button"
                    buttonStyle="solid"
                  >
                    <Radio.Button value={30}>30</Radio.Button>
                    <Radio.Button value={50}>50</Radio.Button>
                    <Radio.Button value={70}>70</Radio.Button>
                    <Radio.Button value={85}>85</Radio.Button>
                  </Radio.Group>
                </div>
              </div>

              <div className="setting-item">
                <Button type="primary" ghost onClick={handleTestOpenClaw} loading={testingSending} block>
                  🔔 {t(lang, 'openclawTest')}
                </Button>
              </div>

              <div className="openclaw-skill-info">
                <div className="skill-info-title">📋 QClaw Skill {lang === 'zh' ? '安装说明' : 'Install Guide'}</div>
                <div className="skill-info-content">
                  {lang === 'zh' ? (
                    <>
                      <p>1. 在 QClaw 中安装 Skill: <code>qclaw skill install github.com/yuchendeng/Fact-Safe-Elder/qclaw-skill</code></p>
                      <p>2. 安装完成后，QClaw 会分配一个 <strong>Webhook URL</strong></p>
                      <p>3. 将该 Webhook URL 粘贴到上方「QClaw Webhook URL」输入框中</p>
                      <p>4. 当 AI 检测到风险时，系统自动推送告警到 QClaw → 通知家属</p>
                    </>
                  ) : (
                    <>
                      <p>1. Install Skill in QClaw: <code>qclaw skill install github.com/yuchendeng/Fact-Safe-Elder/qclaw-skill</code></p>
                      <p>2. After install, QClaw assigns a <strong>Webhook URL</strong></p>
                      <p>3. Paste the URL into the "QClaw Webhook URL" field above</p>
                      <p>4. Alerts auto-push to QClaw → notify family when risk detected</p>
                    </>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* 隐私 */}
        <div className="settings-section privacy-section">
          <h3>{t(lang, 'privacyTitle')}</h3>
          <div className="privacy-info">
            <p>🛡️ {lang === 'zh' ? '我们严格保护您的隐私：' : 'We strictly protect your privacy:'}</p>
            <ul>
              <li>{lang === 'zh' ? '音频数据仅在本地处理，不会上传到服务器' : 'Audio data is processed locally only'}</li>
              <li>{lang === 'zh' ? '检测结果和设置信息仅存储在您的设备上' : 'Results and settings are stored on your device only'}</li>
              <li>{lang === 'zh' ? '您可以随时清除所有数据' : 'You can clear all data anytime'}</li>
            </ul>
            <Button type="link" size="small" onClick={() => {
              localStorage.removeItem('elderSafetySettings');
              localStorage.removeItem('detectionHistory');
              localStorage.removeItem('openclawConfig');
              message.success(t(lang, 'dataCleared'));
            }}>{t(lang, 'clearData')}</Button>
          </div>
        </div>
      </div>
        <div className="settings-panel-footer">
          <button className="settings-footer-btn reset" onClick={handleReset}>{t(lang, 'resetDefault')}</button>
          <button className="settings-footer-btn cancel" onClick={onClose}>{t(lang, 'cancel')}</button>
          <button className="settings-footer-btn save" onClick={handleSave}>{t(lang, 'save')}</button>
        </div>
      </div>
    </div>
  );
};

export default Settings;
