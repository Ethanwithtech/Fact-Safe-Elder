/**
 * 竞赛演示模式：一键切换布局、敏感度、资源预加载
 */

import { DEFAULT_FEISHU_WEBHOOK } from './services/OpenClawService';

export const COMPETITION_DEMO_KEY = 'factsafe_competition_demo';

export const DEMO_VIDEO_ASSETS = [
  { index: 0, labelZh: '保健品诈骗', labelEn: 'Health scam', url: '/demo-videos/health_supplement_wechat.mp4', risk: 'danger' as const },
  { index: 1, labelZh: '金融诈骗', labelEn: 'Finance scam', url: '/demo-videos/finance_scam_elder.mp4', risk: 'danger' as const },
  { index: 2, labelZh: '安全科普', labelEn: 'Safe content', url: '/demo-videos/normal_nutrition.mp4', risk: 'safe' as const },
];

const SENSITIVITY_BACKUP_KEY = 'factsafe_sensitivity_before_demo';

export function isCompetitionDemoEnabled(): boolean {
  try {
    return localStorage.getItem(COMPETITION_DEMO_KEY) === 'true';
  } catch {
    return false;
  }
}

export function setCompetitionDemoEnabled(on: boolean): void {
  localStorage.setItem(COMPETITION_DEMO_KEY, on ? 'true' : 'false');
  if (on) {
    lockSensitivityPrecision();
  } else {
    restoreSensitivityIfBackedUp();
  }
}

/** 锁定为「宁漏勿误」→ 后端 precision */
export function lockSensitivityPrecision(): void {
  try {
    const raw = localStorage.getItem('elderSafetySettings');
    const prev = raw ? JSON.parse(raw) : {};
    if (!localStorage.getItem(SENSITIVITY_BACKUP_KEY)) {
      localStorage.setItem(SENSITIVITY_BACKUP_KEY, prev.sensitivity || 'medium');
    }
    localStorage.setItem(
      'elderSafetySettings',
      JSON.stringify({ ...prev, sensitivity: 'low' }),
    );
  } catch {
    /* ignore */
  }
}

function restoreSensitivityIfBackedUp(): void {
  try {
    const backed = localStorage.getItem(SENSITIVITY_BACKUP_KEY);
    if (!backed) return;
    const raw = localStorage.getItem('elderSafetySettings');
    const prev = raw ? JSON.parse(raw) : {};
    localStorage.setItem(
      'elderSafetySettings',
      JSON.stringify({ ...prev, sensitivity: backed }),
    );
    localStorage.removeItem(SENSITIVITY_BACKUP_KEY);
  } catch {
    /* ignore */
  }
}

function apiBase(): string {
  const configured = process.env.REACT_APP_API_URL || 'http://localhost:8000';
  const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
  const isRemote = host !== 'localhost' && host !== '127.0.0.1';
  if (isRemote && configured.includes('localhost')) {
    return `${window.location.protocol}//${host}:8000`;
  }
  return configured;
}

/** 预加载：健康检查 + 模型探活 + 演示视频 + 飞书配置同步 */
export async function preloadDemoAssets(): Promise<{ ok: boolean; message: string }> {
  const base = apiBase();
  const steps: string[] = [];

  try {
    const health = await fetch(`${base}/health`, { method: 'GET' });
    const h = await health.json();
    const modelsOk = h?.models?.all_models_ready ?? h?.ai_available;
    steps.push(modelsOk ? '模型已就绪' : '模型部分未加载');
  } catch {
    steps.push('后端未连接');
    return { ok: false, message: steps.join(' · ') };
  }

  try {
    await fetch(`${base}/api/detect`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: '保健品加微信保证收益祖传秘方',
        sensitivity: 'precision',
      }),
    });
    steps.push('推理预热完成');
  } catch {
    steps.push('推理预热跳过');
  }

  DEMO_VIDEO_ASSETS.forEach(({ url }) => {
    const v = document.createElement('video');
    v.preload = 'auto';
    v.muted = true;
    v.src = url;
    v.load();
  });
  steps.push('演示视频已预加载');

  try {
    await fetch(`${base}/api/feishu/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ webhook_url: DEFAULT_FEISHU_WEBHOOK, enabled: true }),
    });
    steps.push('飞书通道已同步');
  } catch {
    steps.push('飞书同步跳过');
  }

  return { ok: true, message: steps.join(' · ') };
}
