import React, { useEffect, useState } from 'react';

import { DetectionResult } from '../../types/detection';

import { Language } from '../../i18n';

import PandaMascot, { PandaState } from '../PandaMascot/PandaMascot';

import { RiskTier } from '../../utils/elderAlert';

import './AiGuardianIsland.css';



export type IslandMode = 'idle' | 'scanning' | 'result';



interface AiGuardianIslandProps {

  mode: IslandMode;

  result: DetectionResult | null;

  riskTier: RiskTier;

  isDetecting: boolean;

  scanProgress?: number;

  lang: Language;

  onOpenMainAlert?: () => void;

}



function toPandaState(mode: IslandMode, tier: RiskTier, level?: DetectionResult['level']): PandaState {

  if (mode === 'scanning') return 'scanning';

  if (tier === 'high' || level === 'danger') return 'danger';

  if (tier === 'medium' || level === 'warning') return 'warn';

  if (level === 'safe') return 'safe';

  return 'idle';

}



/** iOS 灵动岛：三级渐进提醒（≤6 字）+ 熊猫 IP */

const AiGuardianIsland: React.FC<AiGuardianIslandProps> = ({

  mode,

  result,

  riskTier,

  isDetecting,

  scanProgress = 0,

  lang,

  onOpenMainAlert,

}) => {

  const [lowExpanded, setLowExpanded] = useState(false);

  const level = result?.level ?? 'safe';

  const zh = lang !== 'en';

  const pandaState = toPandaState(mode, riskTier, level);



  useEffect(() => {

    if (mode !== 'result' || riskTier !== 'low') setLowExpanded(false);

  }, [mode, riskTier, result?.detection_id]);



  const shortLabel = (() => {

    if (mode === 'scanning') return zh ? '检测中' : 'Scan';

    if (level === 'safe') return zh ? '放心' : 'OK';

    if (riskTier === 'high') return zh ? '骗子!' : 'Scam!';

    if (riskTier === 'medium') return zh ? '可能骗子' : 'Risky';

    return zh ? '小心' : 'Care';

  })();



  const expanded = mode === 'scanning' || riskTier === 'medium' || riskTier === 'high' || lowExpanded;



  const handleClick = () => {
    if (mode === 'scanning') return;
    onOpenMainAlert?.();
  };



  return (

    <div

      className={`ai-guardian-island ${mode} tier-${riskTier} ${level} ${expanded ? 'expanded' : ''} ${riskTier === 'high' && mode === 'result' ? 'high-blink' : ''} ${mode === 'result' ? 'clickable' : ''}`}

      onClick={handleClick}

      role="button"

      tabIndex={mode === 'result' ? 0 : undefined}

      aria-live="polite"

    >

      <PandaMascot state={pandaState} size="mini" />

      <div className="agi-text">

        <span className="agi-brand">FactSafe</span>

        <span className="agi-status">{shortLabel}</span>

      </div>

      {mode === 'scanning' && (

        <span className="agi-progress">{scanProgress}%</span>

      )}

      {riskTier === 'high' && mode === 'result' && (

        <span className="agi-warn-icon" aria-hidden>⚠️</span>

      )}

      {isDetecting && <span className="agi-pulse-dot" />}

      {lowExpanded && riskTier === 'low' && (

        <span className="agi-low-tip">{zh ? '视频有风险' : 'Risky video'}</span>

      )}

    </div>

  );

};



export default AiGuardianIsland;

