import React from 'react';
import { DetectionResult } from '../../types/detection';
import { Language, t } from '../../i18n';
import { buildElderDetailPoints, VideoContext } from '../../utils/elderAlert';
import './RiskAlertDetailModal.css';

interface RiskAlertDetailModalProps {
  visible: boolean;
  result: DetectionResult;
  lang: Language;
  videoContext?: VideoContext;
  onTellFamily: () => void;
  onGotIt: () => void;
  onBack?: () => void;
}

/** 第二层：大白话原因 + 告诉子女 / 我知道了 */
const RiskAlertDetailModal: React.FC<RiskAlertDetailModalProps> = ({
  visible,
  result,
  lang,
  onTellFamily,
  onGotIt,
  onBack,
  videoContext,
}) => {
  if (!visible) return null;

  const points = buildElderDetailPoints(result, lang, videoContext);
  const zh = lang !== 'en';

  return (
    <div className="elder-detail-backdrop" role="dialog" aria-modal="true">
      <div className="elder-detail-card">
        <button type="button" className="elder-detail-back" onClick={onBack ?? onGotIt} aria-label={zh ? '返回' : 'Back'}>
          ← {zh ? '返回' : 'Back'}
        </button>
        <h2 className="elder-detail-title">
          {result.level === 'safe'
            ? (zh ? '✅ 为什么可以放心看？' : '✅ Why this looks safe')
            : (zh ? '⚠️ 为什么说它是骗子？' : '⚠️ Why is this suspicious?')}
        </h2>
        <p className="elder-detail-source">
          {zh ? '以下根据本条视频 AI 实时分析生成' : 'From real-time AI analysis of this clip'}
        </p>
        <ul className="elder-detail-list">
          {points.map((p, i) => (
            <li key={i} className="elder-detail-item">
              <span className="elder-detail-icon">{p.icon}</span>
              <div>
                <div className="elder-detail-line-title">{p.title}</div>
                <div className="elder-detail-line-sub">{p.subtitle}</div>
              </div>
            </li>
          ))}
        </ul>
        <div className="elder-detail-actions">
          <button type="button" className="elder-detail-btn primary" onClick={onTellFamily}>
            {t(lang, 'elderTellFamily')}
          </button>
          <button type="button" className="elder-detail-btn secondary" onClick={onGotIt}>
            {t(lang, 'elderCareGotIt')}
          </button>
        </div>
      </div>
    </div>
  );
};

export default RiskAlertDetailModal;
