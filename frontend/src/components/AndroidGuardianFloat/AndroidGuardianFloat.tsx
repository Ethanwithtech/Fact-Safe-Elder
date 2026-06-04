import React from 'react';
import { DetectionResult } from '../../types/detection';
import { Language } from '../../i18n';
import { RiskTier } from '../../utils/elderAlert';
import PandaMascot, { PandaState } from '../PandaMascot/PandaMascot';
import './AndroidGuardianFloat.css';

interface AndroidGuardianFloatProps {
  mode: 'idle' | 'scanning' | 'result';
  result: DetectionResult | null;
  riskTier: RiskTier;
  isDetecting: boolean;
  lang: Language;
  onOpenAlert: () => void;
}

function toPandaState(mode: AndroidGuardianFloatProps['mode'], tier: RiskTier): PandaState {
  if (mode === 'scanning') return 'scanning';
  if (tier === 'high') return 'danger';
  if (tier === 'medium') return 'warn';
  if (tier === 'low') return 'warn';
  return 'idle';
}

/** 安卓悬浮守护球（可拖动吸附边缘） */
const AndroidGuardianFloat: React.FC<AndroidGuardianFloatProps> = ({
  mode,
  result,
  riskTier,
  isDetecting,
  lang,
  onOpenAlert,
}) => {
  const zh = lang !== 'en';
  const hasRisk = mode === 'result' && result && result.level !== 'safe';
  const showDanger = hasRisk && (riskTier === 'high' || riskTier === 'medium');
  const pandaState = toPandaState(mode, riskTier);

  return (
    <button
      type="button"
      className={`android-guard-float ${mode} ${riskTier} ${showDanger ? 'danger' : ''} ${isDetecting ? 'scanning' : ''}`}
      onClick={() => {
        if (mode === 'scanning') return;
        if (mode === 'result' && result) onOpenAlert();
      }}
      aria-label={zh ? 'FactSafe 反诈守护' : 'FactSafe guard'}
    >
      {mode === 'scanning' || showDanger ? (
        <PandaMascot state={pandaState} size="mini" />
      ) : (
        <span className="agf-shield">🛡️</span>
      )}
      {showDanger && <span className="agf-warn">⚠️</span>}
      {mode === 'scanning' && <span className="agf-label">{zh ? '查' : '…'}</span>}
    </button>
  );
};

export default AndroidGuardianFloat;
