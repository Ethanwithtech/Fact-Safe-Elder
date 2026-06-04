import React, { ReactNode } from 'react';
import { Language } from '../../i18n';
import './DouyinPhoneUI.css';

interface DouyinPhoneUIProps {
  lang: Language;
  timeLabel: string;
  islandSlot: ReactNode;
  children: ReactNode;
  bottomBar?: ReactNode;
}

/** 参考真机抖音：状态栏 + 顶栏叠在视频上，底栏独立 */
const DouyinPhoneUI: React.FC<DouyinPhoneUIProps> = ({
  lang,
  timeLabel,
  islandSlot,
  children,
  bottomBar,
}) => {
  const zh = lang !== 'en';
  const tabs = zh
    ? ['选', '经验', '直播', '北京', '关注', '商城', '推荐']
    : ['Pick', 'Tips', 'Live', 'City', 'Follow', 'Shop', 'For you'];

  return (
    <div className="douyin-phone-root">
      <div className="douyin-viewport">
        {children}
        <div className="douyin-overlay-top">
          <div className="douyin-status-row">
            <span className="dy-time">{timeLabel}</span>
            <div className="dy-island-slot">{islandSlot}</div>
            <div className="dy-status-icons" aria-hidden>
              <span className="dy-signal" />
              <span className="dy-wifi" />
              <span className="dy-battery"><span className="dy-battery-fill" />78%</span>
            </div>
          </div>
          <nav className="douyin-nav-row" aria-label="Douyin tabs">
            <button type="button" className="dy-menu-btn" aria-label="menu">
              ☰<em className="dy-menu-badge">1</em>
            </button>
            <div className="dy-tabs-scroll">
              {tabs.map((label) => (
                <span
                  key={label}
                  className={`dy-tab ${label === (zh ? '推荐' : 'For you') ? 'active' : ''}`}
                >
                  {label}
                </span>
              ))}
            </div>
            <button type="button" className="dy-search-btn" aria-label="search">🔍</button>
          </nav>
        </div>
      </div>
      {bottomBar}
    </div>
  );
};

export default DouyinPhoneUI;
