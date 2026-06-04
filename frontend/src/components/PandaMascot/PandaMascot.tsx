import React from 'react';
import './PandaMascot.css';

export type PandaState = 'idle' | 'scanning' | 'safe' | 'warn' | 'danger';

interface PandaMascotProps {
  state: PandaState;
  size?: 'mini' | 'md' | 'lg';
  className?: string;
}

/** FactSafe 熊猫守护 IP — 随检测状态切换动作 */
const PandaMascot: React.FC<PandaMascotProps> = ({ state, size = 'md', className = '' }) => (
  <div
    className={`panda-mascot panda-size-${size} panda-state-${state} ${className}`}
    role="img"
    aria-label="FactSafe Panda"
  >
    <div className="panda-body-wrap">
      <div className="panda-ear panda-ear-l" />
      <div className="panda-ear panda-ear-r" />
      <div className="panda-face">
        <div className="panda-eye panda-eye-l">
          <span className="panda-pupil" />
        </div>
        <div className="panda-eye panda-eye-r">
          <span className="panda-pupil" />
        </div>
        <div className="panda-blush panda-blush-l" />
        <div className="panda-blush panda-blush-r" />
        <div className="panda-nose" />
        <div className="panda-mouth" />
      </div>
      {state === 'scanning' && <div className="panda-scan-ring" aria-hidden />}
      {state === 'danger' && <span className="panda-badge">!</span>}
      {state === 'safe' && <span className="panda-badge ok">✓</span>}
    </div>
    {size === 'lg' && (
      <div className="panda-status-caption">
        {state === 'idle' && '守护中'}
        {state === 'scanning' && '检测中…'}
        {state === 'safe' && '放心看'}
        {state === 'warn' && '留意一下'}
        {state === 'danger' && '别轻信！'}
      </div>
    )}
  </div>
);

export default PandaMascot;
