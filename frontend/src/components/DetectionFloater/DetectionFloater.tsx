import React, { useState, useEffect } from 'react';
import { DetectionResult } from '../../types/detection';
import { Language, t } from '../../i18n';
import './DetectionFloater.css';

interface DetectionFloaterProps {
  result: DetectionResult;
  onClose: () => void;
  embedded?: boolean;
  lang?: Language;
}

const DetectionFloater: React.FC<DetectionFloaterProps> = ({ result, onClose, embedded = false, lang = 'zh' }) => {
  const [expanded, setExpanded] = useState(false);
  const [visible, setVisible] = useState(true);

  const reasons = result?.reasons || [];
  const suggestions = result?.suggestions || [];
  const score = result?.score ?? 0;
  const level = result?.level || 'safe';
  const scoreNum = Math.round(score * 100);

  const riskInfo = (() => {
    switch (level) {
      case 'danger':
        return { color: '#ff4d4f', icon: '🚨', label: lang === 'zh' ? '高风险' : 'HIGH RISK' };
      case 'warning':
        return { color: '#faad14', icon: '⚠️', label: lang === 'zh' ? '注意' : 'CAUTION' };
      case 'safe': default:
        return { color: '#52c41a', icon: '✅', label: lang === 'zh' ? '安全' : 'SAFE' };
    }
  })();

  useEffect(() => {
    if (level === 'safe') {
      const timer = setTimeout(() => {
        setVisible(false);
        setTimeout(onClose, 300);
      }, 2500);
      return () => clearTimeout(timer);
    }
  }, [level, onClose]);

  if (!visible && level === 'safe') return null;

  // ===== 灵动岛模式（手机内嵌）=====
  if (embedded) {
    return (
      <>
        {/* 迷你药丸 — 灵动岛风格 */}
        <div
          className={`island-pill ${level} ${visible ? 'show' : 'hide'} ${expanded ? 'expanded' : ''}`}
          onClick={() => level !== 'safe' && setExpanded(!expanded)}
        >
          <span className="island-icon">{riskInfo.icon}</span>
          <span className="island-label">{riskInfo.label}</span>
          <span className="island-score" style={{ color: riskInfo.color }}>{scoreNum}</span>
          <button className="island-dismiss" onClick={(e) => { e.stopPropagation(); onClose(); }}>✕</button>
        </div>

        {/* 展开详情面板 */}
        {expanded && level !== 'safe' && (
          <div className="island-detail-backdrop" onClick={() => setExpanded(false)}>
            <div className="island-detail-sheet" onClick={(e) => e.stopPropagation()}>
              <div className="island-detail-head" style={{ borderBottomColor: riskInfo.color }}>
                <span>{riskInfo.icon} {riskInfo.label}</span>
                <span className="island-detail-score" style={{ color: riskInfo.color }}>{scoreNum}</span>
              </div>
              {reasons.length > 0 && (
                <div className="island-detail-sec">
                  <div className="island-detail-label">⚡ {lang === 'zh' ? '风险因素' : 'Risk Factors'}</div>
                  {reasons.map((r, i) => (
                    <div key={i} className="island-detail-reason" style={{ borderLeftColor: riskInfo.color }}>• {r}</div>
                  ))}
                </div>
              )}
              {suggestions.length > 0 && (
                <div className="island-detail-sec">
                  <div className="island-detail-label">💡 {lang === 'zh' ? '安全建议' : 'Suggestions'}</div>
                  {suggestions.map((s, i) => (
                    <div key={i} className="island-detail-suggestion">💡 {s}</div>
                  ))}
                </div>
              )}
              <button className="island-detail-close-btn" onClick={() => setExpanded(false)}>
                {t(lang!, 'iKnow')}
              </button>
            </div>
          </div>
        )}
      </>
    );
  }

  // ===== 桌面灵动岛浮窗 =====
  return (
    <>
      <div
        className={`desktop-island ${level} ${expanded ? 'expanded' : ''}`}
        onClick={() => level !== 'safe' && setExpanded(!expanded)}
      >
        <span className="island-icon">{riskInfo.icon}</span>
        <span className="island-label">{riskInfo.label}</span>
        <span className="island-score" style={{ color: riskInfo.color }}>{scoreNum}</span>
        <button className="island-dismiss" onClick={(e) => { e.stopPropagation(); onClose(); }}>✕</button>
      </div>

      {/* 桌面详情覆盖层 */}
      {expanded && (
        <div className="desktop-detail-overlay" onClick={() => setExpanded(false)}>
          <div className="desktop-detail-panel" onClick={(e) => e.stopPropagation()}>
            <div className="desktop-detail-header" style={{ borderBottomColor: riskInfo.color }}>
              <span className="desktop-detail-title">{riskInfo.icon} {riskInfo.label} — {scoreNum}/100</span>
              <button className="desktop-detail-close" onClick={() => setExpanded(false)}>✕</button>
            </div>
            <div className="desktop-detail-body">
              {reasons.length > 0 && (
                <div className="detail-section">
                  <h4>{t(lang!, 'riskFactors')}</h4>
                  {reasons.map((r, i) => <div key={i} className="reason-tag" style={{ borderLeftColor: riskInfo.color }}>{r}</div>)}
                </div>
              )}
              {suggestions.length > 0 && (
                <div className="detail-section">
                  <h4>{t(lang!, 'safetySuggestions')}</h4>
                  {suggestions.map((s, i) => <div key={i} className="suggestion-tag">{s}</div>)}
                </div>
              )}
            </div>
            <div className="desktop-detail-footer">
              <button className="desktop-detail-ok-btn" onClick={() => setExpanded(false)}>{t(lang!, 'close')}</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default DetectionFloater;
