import React, { useEffect, useState } from 'react';
import { Language, t } from '../../i18n';
import { triggerElderHaptic } from '../../utils/elderAlert';
import './RiskAlertModal.css';

interface RiskAlertModalProps {
  visible: boolean;
  level: 'warning' | 'danger';
  lang: Language;
  onStopWatching: () => void;
  onViewDetails: () => void;
  onDismiss?: () => void;
}

/** 第一层：老人友好主警告（1 秒能看懂） */
const RiskAlertModal: React.FC<RiskAlertModalProps> = ({
  visible,
  lang,
  onStopWatching,
  onViewDetails,
  onDismiss,
}) => {
  const [canStop, setCanStop] = useState(false);
  const zh = lang !== 'en';

  useEffect(() => {
    if (!visible) {
      setCanStop(false);
      return;
    }
    triggerElderHaptic();
    setCanStop(false);
    const tmr = window.setTimeout(() => setCanStop(true), 3000);
    return () => window.clearTimeout(tmr);
  }, [visible]);

  if (!visible) return null;

  return (
    <div className="risk-alert-backdrop elder-layer1" role="dialog" aria-modal="true">
      <div className="risk-alert-card elder-layer1-card">
        <div className="risk-alert-icon elder-warn-icon" aria-hidden>⚠️</div>
        <p className="risk-alert-kicker">{t(lang, 'elderAlertKicker')}</p>
        <p className="risk-alert-headline">{t(lang, 'elderAlertHeadline')}</p>
        <div className="risk-alert-actions elder-actions-row">
          <button
            type="button"
            className="risk-alert-btn elder-btn-stop"
            disabled={!canStop}
            onClick={onStopWatching}
          >
            🛑 {t(lang, 'elderBtnStop')}
          </button>
          <button type="button" className="risk-alert-btn elder-btn-why" onClick={onViewDetails}>
            ❓ {t(lang, 'elderBtnWhy')}
          </button>
        </div>
        {onDismiss && (
          <button type="button" className="risk-alert-dismiss" onClick={onDismiss}>
            {zh ? '先继续看' : 'Keep watching'}
          </button>
        )}
        {!canStop && (
          <p className="risk-alert-hint">{t(lang, 'elderStopHint')}</p>
        )}
      </div>
    </div>
  );
};

export default RiskAlertModal;
