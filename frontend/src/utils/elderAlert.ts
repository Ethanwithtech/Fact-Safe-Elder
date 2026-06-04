import { DetectionResult } from '../types/detection';
import { Language } from '../i18n';

export type RiskTier = 'low' | 'medium' | 'high';

export interface ElderDetailPoint {
  icon: string;
  title: string;
  subtitle: string;
}

export interface VideoContext {
  title: string;
  description: string;
  content: string;
  ocrText?: string;
}

/** 按分数 + 等级得到三级风险（与灵动岛/悬浮球一致） */
export function getRiskTier(result: DetectionResult): RiskTier {
  let score = result.score ?? 0;
  if (result.level === 'danger') score = Math.max(score, 0.76);
  else if (result.level === 'warning') score = Math.max(score, 0.52);
  if (score >= 0.75) return 'high';
  if (score >= 0.5) return 'medium';
  return 'low';
}

export function triggerElderHaptic(): void {
  try {
    if (typeof navigator !== 'undefined' && navigator.vibrate) {
      navigator.vibrate(120);
    }
  } catch {
    /* ignore */
  }
}

function clip(s: string, n: number): string {
  const t = s.trim();
  return t.length > n ? `${t.slice(0, n)}…` : t;
}

function plainReason(text: string): string {
  return text
    .replace(/^(GPT|AI|MacBERT|TF-IDF|BERT)[：:]\s*/i, '')
    .replace(/跨模态|语义差异|手法标签|证据链/gi, '')
    .trim();
}

function pickRiskyPhrase(ctx: VideoContext): string | null {
  const blob = `${ctx.content} ${ctx.title} ${ctx.description}`;
  const patterns = [
    /加微信[^，。]{0,12}/,
    /保证收益[^，。]{0,12}/,
    /包治百病[^，。]{0,8}/,
    /央视推荐[^，。]{0,12}/,
    /限时[^，。]{0,10}/,
    /转账|汇款/,
  ];
  for (const p of patterns) {
    const m = blob.match(p);
    if (m) return m[0];
  }
  return null;
}

/** 结合 API 结果 + 本条视频标题/口播/OCR 生成解释 */
export function buildElderDetailPoints(
  result: DetectionResult,
  lang: Language,
  ctx?: VideoContext,
): ElderDetailPoint[] {
  const zh = lang !== 'en';
  const points: ElderDetailPoint[] = [];
  const ocr = (ctx?.ocrText || `${ctx?.title || ''} ${ctx?.description || ''}`).trim();
  const asr = (ctx?.content || '').trim();

  const cross = result.asr_ocr_conflict;
  if (cross?.conflict && (ocr || asr)) {
    points.push({
      icon: '📺',
      title: zh ? '画面和说话对不上' : 'Screen vs voice mismatch',
      subtitle: zh
        ? `画面：「${clip(ocr, 18)}」≠ 口里：「${clip(asr, 18)}」`
        : `On-screen: "${clip(ocr, 22)}" vs speech: "${clip(asr, 22)}"`,
    });
  }

  const manip = result.manipulation_detail?.[0];
  if (manip?.name) {
    points.push({
      icon: '🔴',
      title: manip.name,
      subtitle: manip.desc || clip(asr || ocr, 32),
    });
  }

  const apiReasons = (result.reasons || [])
    .map((r) => plainReason(String(r)))
    .filter((r) => r.length > 4 && !/BERT|TF-IDF|模型判定/.test(r));

  const contentReason = apiReasons.find((r) => r.includes('画面') || r.includes('语音') || r.includes('口播'));
  if (contentReason) {
    points.push({
      icon: '🎬',
      title: zh ? '就这条视频说的' : 'About this clip',
      subtitle: clip(contentReason, 40),
    });
  } else if (apiReasons[0]) {
    points.push({
      icon: '🔴',
      title: zh ? 'AI 发现的问题' : 'AI found',
      subtitle: clip(apiReasons[0], 40),
    });
  } else {
    const phrase = ctx ? pickRiskyPhrase(ctx) : null;
    if (phrase) {
      points.push({
        icon: '🔴',
        title: zh ? '视频里提到' : 'Mentioned in video',
        subtitle: `「${phrase}」`,
      });
    } else if (asr) {
      points.push({
        icon: '🎬',
        title: zh ? '口播内容' : 'Spoken content',
        subtitle: `「${clip(asr, 28)}」`,
      });
    }
  }

  const falseClaims = result.gpt_fact_check?.false_claims || [];
  if (falseClaims.length > 0 && points.length < 3) {
    const c = falseClaims[0] as { original?: string; correction?: string };
    if (c.original) {
      points.push({
        icon: '❌',
        title: zh ? '这句话不对' : 'This claim is wrong',
        subtitle: `「${clip(String(c.original), 22)}」`,
      });
    }
  }

  const related = result.related_cases?.[0];
  if (related?.victims || related?.avg_loss) {
    points.push({
      icon: '📊',
      title: related.victims
        ? (zh ? `类似案例约${related.victims}人受害` : `~${related.victims} similar victims`)
        : (zh ? '有类似骗局' : 'Similar scams exist'),
      subtitle: related.avg_loss
        ? (zh ? `人均损失约${(related.avg_loss / 10000).toFixed(1)}万元` : `Avg loss ~${(related.avg_loss / 1000).toFixed(0)}k`)
        : clip(related.title || '', 28),
    });
  } else if (points.length < 3) {
    points.push({
      icon: '💡',
      title: zh ? '建议' : 'Tip',
      subtitle: zh ? '拿不准就先问子女或打 96110' : 'Ask family or call anti-fraud hotline',
    });
  }

  return points.slice(0, 3);
}
