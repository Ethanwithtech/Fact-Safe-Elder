import React, { useState, useEffect, useRef } from 'react';

import './App.css';

import MobileSimulator from './components/MobileSimulator/MobileSimulator';

import Settings from './components/Settings/Settings';

import { DetectionResult } from './types/detection';

import { Language, normalizeLanguage, t } from './i18n';

import { ThemeMode, applyTheme } from './theme';

import {

  isCompetitionDemoEnabled,

  setCompetitionDemoEnabled,

  preloadDemoAssets,

} from './demoMode';

import {

  getSimulatorPlatform,

  setSimulatorPlatform,

  SimulatorPlatform,

} from './utils/simulatorPlatform';



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

  const [lang, setLang] = useState<Language>(normalizeLanguage(savedSettings?.lang));

  const [themeMode, setThemeMode] = useState<ThemeMode>(savedSettings?.themeMode || 'dark');

  const [competitionDemo, setCompetitionDemo] = useState(isCompetitionDemoEnabled());

  const [simPlatform, setSimPlatform] = useState<SimulatorPlatform>(getSimulatorPlatform);

  const [demoPreloadMsg, setDemoPreloadMsg] = useState('');

  const [demoPreloading, setDemoPreloading] = useState(false);

  const initialized = useRef(false);



  useEffect(() => {

    if (!initialized.current) {

      initialized.current = true;

      applyTheme(savedSettings?.themeMode || 'dark');

    }

  }, []);



  useEffect(() => {

    document.body.classList.remove('large-font', 'extra-large-font', 'competition-demo-active');

    if (fontSize === 'large') document.body.classList.add('large-font');

    if (fontSize === 'extra-large') document.body.classList.add('extra-large-font');

    if (highContrast) document.body.classList.add('high-contrast');

    else document.body.classList.remove('high-contrast');

    if (competitionDemo) document.body.classList.add('competition-demo-active');

  }, [fontSize, highContrast, competitionDemo]);



  useEffect(() => {

    if (!competitionDemo) return;

    let cancelled = false;

    setDemoPreloading(true);

    setDemoPreloadMsg(t(lang, 'competitionDemoPreload'));

    preloadDemoAssets().then((r) => {

      if (cancelled) return;

      setDemoPreloadMsg(r.ok ? t(lang, 'competitionDemoReady') : r.message);

      setDemoPreloading(false);

    });

    return () => { cancelled = true; };

  }, [competitionDemo, lang]);



  const handleThemeChange = (mode: ThemeMode) => {

    setThemeMode(mode);

    applyTheme(mode);

  };



  const toggleCompetitionDemo = () => {

    const next = !competitionDemo;

    setCompetitionDemo(next);

    setCompetitionDemoEnabled(next);

    if (next) setShowSettings(false);

  };



  const handleDetectionResult = (result: DetectionResult) => {

    setTotalDetections(prev => prev + 1);

    if (result.level === 'danger' || result.level === 'warning') {

      setRiskyDetections(prev => prev + 1);

    }

    if (result.level === 'danger' && !competitionDemo) {

      try {

        const ctx = new (window.AudioContext || (window as any).webkitAudioContext)();

        const osc = ctx.createOscillator();

        const gain = ctx.createGain();

        osc.connect(gain);

        gain.connect(ctx.destination);

        osc.frequency.setValueAtTime(800, ctx.currentTime);

        gain.gain.setValueAtTime(0.2, ctx.currentTime);

        osc.start();

        osc.stop(ctx.currentTime + 0.4);

      } catch {

        /* ignore */

      }

    }

  };



  return (

    <div className={`app ${themeMode} ${competitionDemo ? 'competition-demo-app' : ''}`}>

      {!competitionDemo && (
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

            <button

              className="theme-toggle-btn"

              onClick={() => handleThemeChange(themeMode === 'dark' ? 'light' : 'dark')}

              title={t(lang, 'themeMode')}

            >

              {themeMode === 'dark' ? '☀️' : '🌙'}

            </button>

            <button

              className="lang-toggle-btn"

              onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}

              title={t(lang, 'language')}

            >

              {lang === 'zh' ? 'EN' : '中'}

            </button>

            <label className={`competition-demo-toggle ${competitionDemo ? 'on' : ''}`} title={t(lang, 'competitionDemoDesc')}>

              <input

                type="checkbox"

                checked={competitionDemo}

                onChange={toggleCompetitionDemo}

              />

              <span className="cdt-track">

                <span className="cdt-thumb" />

              </span>

              <span className="cdt-label">{t(lang, 'competitionDemo')}</span>

            </label>

            <button className="settings-btn" onClick={() => setShowSettings(true)}>

              ⚙️

            </button>

          </div>

        </div>

      </header>
      )}

      {competitionDemo && (
        <div className="competition-floating-bar" role="toolbar">
          {demoPreloadMsg && (
            <span className={`competition-preload-hint ${demoPreloading ? 'loading' : 'ready'}`}>
              {demoPreloading ? '⏳' : '✅'} {demoPreloadMsg}
            </span>
          )}
          <button
            type="button"
            className={`competition-float-btn ${simPlatform === 'ios' ? 'active' : ''}`}
            onClick={() => { setSimPlatform('ios'); setSimulatorPlatform('ios'); }}
          >
            iPhone
          </button>
          <button
            type="button"
            className={`competition-float-btn ${simPlatform === 'android' ? 'active' : ''}`}
            onClick={() => { setSimPlatform('android'); setSimulatorPlatform('android'); }}
          >
            Android
          </button>
          <button
            type="button"
            className="competition-float-btn"
            onClick={() => setLang(lang === 'zh' ? 'en' : 'zh')}
            title={t(lang, 'language')}
          >
            {lang === 'zh' ? 'EN' : '中'}
          </button>
          <button
            type="button"
            className="competition-float-btn exit"
            onClick={toggleCompetitionDemo}
          >
            {lang === 'en' ? 'Exit demo' : '退出演示'}
          </button>
        </div>
      )}



      <main className="app-main">

        <MobileSimulator

          onDetectionResult={handleDetectionResult}

          lang={lang}

          competitionDemo={competitionDemo}

          simulatorPlatform={simPlatform}

        />

      </main>



      {showSettings && !competitionDemo && (

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


