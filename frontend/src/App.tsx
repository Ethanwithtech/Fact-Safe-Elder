import React, { useState, useEffect, useRef } from 'react';
import './App.css';
import MobileSimulator from './components/MobileSimulator/MobileSimulator';
import Settings from './components/Settings/Settings';
import { DetectionResult } from './types/detection';
import { Language, t } from './i18n';
import { ThemeMode, applyTheme } from './theme';

// 从 localStorage 读取初始值
function loadSavedSettings() {
  try {
    const saved = localStorage.getItem('elderSafetySettings');
    if (saved) return JSON.parse(saved);
  } catch {}
  return null;
}

const savedSettings = loadSavedSettings();

function App() {
  const [showSettings, setShowSettings] = useState(false);
  const [fontSize, setFontSize] = useState<'normal' | 'large' | 'extra-large'>(savedSettings?.fontSize || 'large');
  const [highContrast, setHighContrast] = useState(savedSettings?.highContrast || false);
  const [totalDetections, setTotalDetections] = useState(0);
  const [riskyDetections, setRiskyDetections] = useState(0);
  const [lang, setLang] = useState<Language>(savedSettings?.lang || 'en');
  const [themeMode, setThemeMode] = useState<ThemeMode>(savedSettings?.themeMode || 'dark');
  const initialized = useRef(false);

  // 初始化主题（只执行一次）
  useEffect(() => {
    if (!initialized.current) {
      initialized.current = true;
      applyTheme(savedSettings?.themeMode || 'dark');
    }
  });

  // 应用字体设置
  useEffect(() => {
    document.body.classList.remove('large-font', 'extra-large-font');
    if (fontSize === 'large') document.body.classList.add('large-font');
    if (fontSize === 'extra-large') document.body.classList.add('extra-large-font');
    if (highContrast) { document.body.classList.add('high-contrast'); }
    else { document.body.classList.remove('high-contrast'); }
  }, [fontSize, highContrast]);

  const handleThemeChange = (mode: ThemeMode) => {
    setThemeMode(mode);
    applyTheme(mode);
  };

  const handleDetectionResult = (result: DetectionResult) => {
    setTotalDetections(prev => prev + 1);
    if (result.level === 'danger' || result.level === 'warning') {
      setRiskyDetections(prev => prev + 1);
    }
    if (result.level === 'danger') {
      try {
        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.connect(gain); gain.connect(ctx.destination);
        osc.frequency.setValueAtTime(800, ctx.currentTime);
        gain.gain.setValueAtTime(0.2, ctx.currentTime);
        osc.start(); osc.stop(ctx.currentTime + 0.4);
      } catch (e) {}
    }
  };

  return (
    <div className={`app ${themeMode}`}>
      <header className="app-header">
        <div className="header-inner">
          <div className="header-left">
            <span className="logo">🛡️</span>
            <div>
              <h1>{t(lang, 'appName')}</h1>
              <p>{t(lang, 'appDesc')}</p>
            </div>
          </div>
          <div className="header-right">
            <div className="header-stat">
              <span className="stat-value">{totalDetections}</span>
              <span className="stat-name">{t(lang, 'detected')}</span>
            </div>
            <div className="header-stat risky">
              <span className="stat-value">{riskyDetections}</span>
              <span className="stat-name">{t(lang, 'riskBlocked')}</span>
            </div>
            <div className="header-status">
              <span className="status-dot"></span>
              {t(lang, 'aiOnline')}
            </div>
            <button className="theme-toggle-btn" onClick={() => handleThemeChange(themeMode === 'dark' ? 'light' : 'dark')} title={t(lang, 'themeMode')}>
              {themeMode === 'dark' ? '☀️' : '🌙'}
            </button>
            <button className="lang-toggle-btn" onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')} title={t(lang, 'language')}>
              {lang === 'zh' ? 'EN' : '中'}
            </button>
            <button className="settings-btn" onClick={() => setShowSettings(true)}>
              ⚙️
            </button>
          </div>
        </div>
      </header>

      <main className="app-main">
        <MobileSimulator onDetectionResult={handleDetectionResult} lang={lang} />
      </main>

      {showSettings && (
        <Settings
          fontSize={fontSize}
          highContrast={highContrast}
          lang={lang}
          themeMode={themeMode}
          onFontSizeChange={setFontSize}
          onHighContrastChange={setHighContrast}
          onLanguageChange={setLang}
          onThemeChange={handleThemeChange}
          onClose={() => setShowSettings(false)}
        />
      )}
    </div>
  );
}

export default App;
