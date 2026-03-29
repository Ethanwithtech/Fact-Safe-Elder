import React, { useState } from 'react';
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

/* ---------- 轻量级 toast 代替 antd message ---------- */
let toastTimer: ReturnType<typeof setTimeout> | null = null;
function showToast(text: string, type: 'success' | 'info' | 'warning' | 'error' = 'info') {
  const existing = document.getElementById('settings-toast');
  if (existing) existing.remove();
  if (toastTimer) clearTimeout(toastTimer);

  const el = document.createElement('div');
  el.id = 'settings-toast';
  el.className = `settings-toast settings-toast-${type}`;
  el.textContent = text;
  document.body.appendChild(el);
  requestAnimationFrame(() => el.classList.add('show'));
  toastTimer = setTimeout(() => {
    el.classList.remove('show');
    setTimeout(() => el.remove(), 300);
  }, 2500);
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
    showToast(t(lang, 'settingsSaved'), 'success');
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
    updateOpenClaw({ enabled: true, qclawWebhookUrl: '', directWebhookUrl: '', channel: 'wecom', threshold: 70, useQClaw: true, useWecom: true, wecomWebhookUrl: '', useFeishu: false, feishuWebhookUrl: '' });
    showToast(t(lang, 'settingsReset'), 'info');
  };

  const testAlert = () => {
    if (enableSound) {
      try {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.frequency.setValueAtTime(800, ctx.currentTime);
        gain.gain.setValueAtTime(0.3, ctx.currentTime);
        osc.start(); osc.stop(ctx.currentTime + 0.5);
      } catch {}
    }
    showToast(lang === 'zh' ? '测试警报已播放' : 'Test alert played', 'success');
  };

  const handleTestOpenClaw = async () => {
    // useQClaw 模式下 URL 在后端，不要求前端填
    if (!openClawConfig.useQClaw && !openClawConfig.qclawWebhookUrl && !openClawConfig.directWebhookUrl) {
      showToast(lang === 'zh' ? '请先填写 Webhook 地址' : 'Please enter a Webhook URL first', 'warning');
      return;
    }
    setTestingSending(true);
    try {
      const success = await openClawService.sendTestAlert();
      if (success) {
        showToast(t(lang, 'openclawTestSuccess'), 'success');
      } else {
        showToast(lang === 'zh' ? '发送失败，请检查配置' : 'Failed. Check config', 'error');
      }
    } catch {
      showToast(lang === 'zh' ? '发送失败' : 'Send failed', 'error');
    } finally {
      setTestingSending(false);
    }
  };

  const [feishuTesting, setFeishuTesting] = useState(false);
  const handleTestFeishu = async () => {
    if (!openClawConfig.feishuWebhookUrl) {
      showToast(lang === 'zh' ? '请先填写飞书 Webhook URL' : 'Please enter Feishu Webhook URL first', 'warning');
      return;
    }
    setFeishuTesting(true);
    try {
      const success = await openClawService.sendFeishuTestAlert();
      if (success) {
        showToast(lang === 'zh' ? '飞书测试消息发送成功！' : 'Feishu test message sent!', 'success');
      } else {
        showToast(lang === 'zh' ? '飞书发送失败，请检查 Webhook URL' : 'Feishu failed. Check URL', 'error');
      }
    } catch {
      showToast(lang === 'zh' ? '飞书发送失败' : 'Feishu send failed', 'error');
    } finally {
      setFeishuTesting(false);
    }
  };

  const [wecomTesting, setWecomTesting] = useState(false);
  const handleTestWecom = async () => {
    setWecomTesting(true);
    try {
      const success = await openClawService.sendWecomTestAlert();
      if (success) {
        showToast(lang === 'zh' ? '企业微信测试消息发送成功！' : 'WeCom test message sent!', 'success');
      } else {
        showToast(lang === 'zh' ? '企业微信发送失败，请检查 Webhook URL' : 'WeCom failed. Check URL', 'error');
      }
    } catch {
      showToast(lang === 'zh' ? '企业微信发送失败' : 'WeCom send failed', 'error');
    } finally {
      setWecomTesting(false);
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
              <div className="native-radio-group">
                <label className={`native-radio ${lang === 'zh' ? 'checked' : ''}`}>
                  <input type="radio" name="lang" checked={lang === 'zh'} onChange={() => onLanguageChange('zh')} />
                  <span className="radio-dot" /><span>🇨🇳 中文</span>
                </label>
                <label className={`native-radio ${lang === 'en' ? 'checked' : ''}`}>
                  <input type="radio" name="lang" checked={lang === 'en'} onChange={() => onLanguageChange('en')} />
                  <span className="radio-dot" /><span>🇺🇸 English</span>
                </label>
              </div>
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'themeMode')}</span>
              <span className="setting-desc">{t(lang, 'themeModeDesc')}</span>
            </div>
            <div className="setting-control">
              <div className="native-radio-group">
                <label className={`native-radio ${themeMode === 'dark' ? 'checked' : ''}`}>
                  <input type="radio" name="theme" checked={themeMode === 'dark'} onChange={() => onThemeChange('dark')} />
                  <span className="radio-dot" /><span>🌙 {t(lang, 'themeDark')}</span>
                </label>
                <label className={`native-radio ${themeMode === 'light' ? 'checked' : ''}`}>
                  <input type="radio" name="theme" checked={themeMode === 'light'} onChange={() => onThemeChange('light')} />
                  <span className="radio-dot" /><span>☀️ {t(lang, 'themeLight')}</span>
                </label>
              </div>
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'fontSize')}</span>
              <span className="setting-desc">{t(lang, 'fontSizeDesc')}</span>
            </div>
            <div className="setting-control">
              <div className="native-radio-group">
                {(['normal', 'large', 'extra-large'] as const).map((s) => (
                  <label key={s} className={`native-radio ${fontSize === s ? 'checked' : ''}`}>
                    <input type="radio" name="fontSize" checked={fontSize === s} onChange={() => onFontSizeChange(s)} />
                    <span className="radio-dot" /><span>{t(lang, s === 'normal' ? 'fontNormal' : s === 'large' ? 'fontLarge' : 'fontExtraLarge')}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'highContrast')}</span>
              <span className="setting-desc">{t(lang, 'highContrastDesc')}</span>
            </div>
            <div className="setting-control">
              <button className={`native-switch ${highContrast ? 'on' : ''}`} onClick={() => onHighContrastChange(!highContrast)} role="switch" aria-checked={highContrast}>
                <span className="switch-knob" />
                <span className="switch-label">{highContrast ? t(lang, 'on') : t(lang, 'off')}</span>
              </button>
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
              <div className="native-radio-group">
                {(['low', 'medium', 'high'] as const).map((s) => (
                  <label key={s} className={`native-radio ${sensitivity === s ? 'checked' : ''}`}>
                    <input type="radio" name="sensitivity" checked={sensitivity === s} onChange={() => setSensitivity(s)} />
                    <span className="radio-dot" />
                    <span>
                      <span>{t(lang, s === 'low' ? 'sensitivityLow' : s === 'medium' ? 'sensitivityMedium' : 'sensitivityHigh')}</span>
                      <small>{t(lang, s === 'low' ? 'sensitivityLowDesc' : s === 'medium' ? 'sensitivityMediumDesc' : 'sensitivityHighDesc')}</small>
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'soundAlert')}</span>
              <span className="setting-desc">{t(lang, 'soundAlertDesc')}</span>
            </div>
            <div className="setting-control">
              <button className={`native-switch ${enableSound ? 'on' : ''}`} onClick={() => setEnableSound(!enableSound)} role="switch" aria-checked={enableSound}>
                <span className="switch-knob" />
                <span className="switch-label">{enableSound ? t(lang, 'on') : t(lang, 'off')}</span>
              </button>
              <button className="native-btn small" onClick={testAlert}>{t(lang, 'testSound')}</button>
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
              <input
                className="native-input"
                type="text"
                value={familyContact}
                onChange={(e) => setFamilyContact(e.target.value)}
                placeholder={t(lang, 'familyPhonePlaceholder')}
                maxLength={20}
              />
            </div>
          </div>

          <div className="setting-item">
            <div className="setting-label">
              <span>{t(lang, 'riskNotify')}</span>
              <span className="setting-desc">{t(lang, 'riskNotifyDesc')}</span>
            </div>
            <div className="setting-control">
              <button className={`native-switch ${enableNotification ? 'on' : ''}`} onClick={() => setEnableNotification(!enableNotification)} role="switch" aria-checked={enableNotification}>
                <span className="switch-knob" />
                <span className="switch-label">{enableNotification ? t(lang, 'on') : t(lang, 'off')}</span>
              </button>
            </div>
          </div>
        </div>

        {/* 企业微信推送配置（主推送通道） */}
        <div className="settings-section wecom-section">
          <h3>💬 {lang === 'zh' ? '企业微信推送' : 'WeCom Push Notification'}</h3>
          <p className="section-desc">{lang === 'zh' ? '将风险告警推送到企业微信群聊，及时通知家人' : 'Push risk alerts to WeCom group to notify family'}</p>

          <div className="setting-item">
            <div className="setting-label">
              <span>{lang === 'zh' ? '启用企业微信推送' : 'Enable WeCom Push'}</span>
              <span className="setting-desc">{lang === 'zh' ? '检测到风险内容时自动推送到企业微信群' : 'Auto-push to WeCom group when risk detected'}</span>
            </div>
            <div className="setting-control">
              <button className={`native-switch ${openClawConfig.useWecom ? 'on' : ''}`} onClick={() => updateOpenClaw({ useWecom: !openClawConfig.useWecom, enabled: true })} role="switch" aria-checked={openClawConfig.useWecom}>
                <span className="switch-knob" />
                <span className="switch-label">{openClawConfig.useWecom ? t(lang, 'on') : t(lang, 'off')}</span>
              </button>
            </div>
          </div>

          {openClawConfig.useWecom && (
            <>
              <div className="setting-item">
                <div className="setting-label">
                  <span>{lang === 'zh' ? '企业微信 Webhook URL' : 'WeCom Webhook URL'}</span>
                  <span className="setting-desc">{lang === 'zh' ? '企业微信群 → 群机器人 → 添加 → 复制 Webhook 地址' : 'WeCom group → Bot → Add → Copy Webhook URL'}</span>
                </div>
                <div className="setting-control" style={{ flex: 1 }}>
                  <input
                    className="native-input full"
                    type="text"
                    value={openClawConfig.wecomWebhookUrl}
                    onChange={(e) => {
                      updateOpenClaw({ wecomWebhookUrl: e.target.value });
                      if (e.target.value) {
                        openClawService.saveWecomWebhookToBackend(e.target.value);
                      }
                    }}
                    placeholder="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx"
                  />
                </div>
              </div>

              <div className="setting-item">
                <div className="setting-label">
                  <span>{lang === 'zh' ? '推送阈值' : 'Alert Threshold'}</span>
                  <span className="setting-desc">{lang === 'zh' ? '风险分数超过此值时推送通知' : 'Push when risk score exceeds this value'}</span>
                </div>
                <div className="setting-control">
                  <div className="native-btn-group">
                    {[30, 50, 70, 85].map((v) => (
                      <button key={v} className={`native-btn-seg ${openClawConfig.threshold === v ? 'active' : ''}`} onClick={() => updateOpenClaw({ threshold: v })}>{v}</button>
                    ))}
                  </div>
                </div>
              </div>

              <div className="setting-item">
                <button className="native-btn primary block" onClick={handleTestWecom} disabled={wecomTesting}>
                  {wecomTesting ? '⏳' : '💬'} {lang === 'zh' ? '发送企业微信测试消息' : 'Send WeCom Test'}
                </button>
              </div>

              <div className="openclaw-skill-info wecom-info">
                <div className="skill-info-title">📋 {lang === 'zh' ? '企业微信机器人配置步骤' : 'WeCom Bot Setup'}</div>
                <div className="skill-info-content">
                  {lang === 'zh' ? (
                    <>
                      <p>1. 打开 <strong>企业微信</strong>，进入需要接收告警的 <strong>群聊</strong></p>
                      <p>2. 点击右上角 <strong>···</strong> → <strong>群机器人</strong> → <strong>添加群机器人</strong></p>
                      <p>3. 设置机器人名称（如 "AI守护系统"），点击添加</p>
                      <p>4. 复制 <strong>Webhook 地址</strong>，粘贴到上方输入框</p>
                      <p>5. 点击「发送企业微信测试消息」验证连接</p>
                    </>
                  ) : (
                    <>
                      <p>1. Open <strong>WeCom</strong>, enter the <strong>group chat</strong> for alerts</p>
                      <p>2. Tap <strong>···</strong> → <strong>Group Bot</strong> → <strong>Add Bot</strong></p>
                      <p>3. Name it (e.g. "AI Guardian"), tap Add</p>
                      <p>4. Copy the <strong>Webhook URL</strong>, paste above</p>
                      <p>5. Click "Send WeCom Test" to verify</p>
                    </>
                  )}
                </div>
              </div>
            </>
          )}
        </div>

        {/* 飞书推送配置（备选通道） */}
        <div className="settings-section feishu-section">
          <h3>📮 {lang === 'zh' ? '飞书推送（备选）' : 'Feishu Push (Backup)'}</h3>
          <p className="section-desc">{lang === 'zh' ? '企业微信不可用时，降级推送到飞书' : 'Fallback to Feishu when WeCom is unavailable'}</p>

          <div className="setting-item">
            <div className="setting-label">
              <span>{lang === 'zh' ? '启用飞书推送' : 'Enable Feishu Push'}</span>
              <span className="setting-desc">{lang === 'zh' ? '作为备选推送通道' : 'Use as backup push channel'}</span>
            </div>
            <div className="setting-control">
              <button className={`native-switch ${openClawConfig.useFeishu ? 'on' : ''}`} onClick={() => updateOpenClaw({ useFeishu: !openClawConfig.useFeishu, enabled: true })} role="switch" aria-checked={openClawConfig.useFeishu}>
                <span className="switch-knob" />
                <span className="switch-label">{openClawConfig.useFeishu ? t(lang, 'on') : t(lang, 'off')}</span>
              </button>
            </div>
          </div>

          {openClawConfig.useFeishu && (
            <>
              <div className="setting-item">
                <div className="setting-label">
                  <span>{lang === 'zh' ? '飞书 Webhook URL' : 'Feishu Webhook URL'}</span>
                </div>
                <div className="setting-control" style={{ flex: 1 }}>
                  <input
                    className="native-input full"
                    type="text"
                    value={openClawConfig.feishuWebhookUrl}
                    onChange={(e) => {
                      updateOpenClaw({ feishuWebhookUrl: e.target.value });
                      if (e.target.value) {
                        openClawService.saveFeishuWebhookToBackend(e.target.value);
                      }
                    }}
                    placeholder="https://open.feishu.cn/open-apis/bot/v2/hook/xxx"
                  />
                </div>
              </div>

              <div className="setting-item">
                <button className="native-btn primary block" onClick={handleTestFeishu} disabled={feishuTesting}>
                  {feishuTesting ? '⏳' : '📮'} {lang === 'zh' ? '发送飞书测试消息' : 'Send Feishu Test'}
                </button>
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
            <button className="native-btn link" onClick={() => {
              localStorage.removeItem('elderSafetySettings');
              localStorage.removeItem('detectionHistory');
              localStorage.removeItem('openclawConfig');
              showToast(t(lang, 'dataCleared'), 'success');
            }}>{t(lang, 'clearData')}</button>
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
