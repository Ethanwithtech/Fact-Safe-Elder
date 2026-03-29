import { DetectionResult } from '../types/detection';

export interface OpenClawConfig {
  enabled: boolean;
  /** QClaw 安装 Skill 后分配的 Webhook URL（用户从 QClaw 获取后填入） */
  qclawWebhookUrl: string;
  /** 备用：直接企业微信/QQ webhook（不经过 QClaw） */
  directWebhookUrl: string;
  channel: 'wecom' | 'qq' | 'both';
  threshold: number; // 0-100
  /** 优先使用 QClaw（通过后端 /api/qclaw/push），否则降级直接 webhook */
  useQClaw: boolean;
  /** 企业微信推送开关 */
  useWecom: boolean;
  /** 企业微信群机器人 Webhook URL */
  wecomWebhookUrl: string;
  /** 飞书推送开关 */
  useFeishu: boolean;
  /** 飞书自定义机器人 Webhook URL */
  feishuWebhookUrl: string;
}

/**
 * OpenClaw 智能通知服务
 * 
 * 数据流:
 *   检测到风险 → 后端 POST /api/qclaw/push → 后端 POST 到 QClaw Webhook
 *   → QClaw 调用 Skill handleRiskAlert() → 企业微信/QQ 通知家属
 * 
 * 降级:
 *   QClaw 不可用时 → 直接 POST 到企业微信/QQ webhook
 */
export default class OpenClawService {
  private config: OpenClawConfig;

  constructor(config?: Partial<OpenClawConfig>) {
    const defaults: OpenClawConfig = {
      enabled: true,
      qclawWebhookUrl: '',
      directWebhookUrl: '',
      channel: 'wecom',
      threshold: 70,
      useQClaw: true,
      useWecom: true,
      wecomWebhookUrl: '',
      useFeishu: false,
      feishuWebhookUrl: '',
    };

    const saved = localStorage.getItem('openclawConfig');
    let savedConfig: Partial<OpenClawConfig> = {};
    if (saved) {
      try {
        savedConfig = JSON.parse(saved);
      } catch {
        // 解析失败则忽略
      }
      // 迁移：如果旧配置中不存在 useWecom 字段，强制使用默认值 true
      if (!('useWecom' in savedConfig)) {
        savedConfig.useWecom = defaults.useWecom;
      }
    }

    this.config = {
      ...defaults,
      ...savedConfig,
      ...config,
    };

    // 确保配置持久化（含新字段）
    localStorage.setItem('openclawConfig', JSON.stringify(this.config));

    console.log('[OpenClaw] 初始化配置:', {
      enabled: this.config.enabled,
      useWecom: this.config.useWecom,
      useFeishu: this.config.useFeishu,
      useQClaw: this.config.useQClaw,
      threshold: this.config.threshold,
    });
  }

  getConfig(): OpenClawConfig {
    return { ...this.config };
  }

  /** 从 localStorage 重新加载最新配置（用于跨组件同步） */
  reloadConfig(): void {
    const saved = localStorage.getItem('openclawConfig');
    if (saved) {
      try {
        const savedConfig = JSON.parse(saved) as Partial<OpenClawConfig>;
        this.config = { ...this.config, ...savedConfig };
        console.log('[OpenClaw] 重新加载配置:', {
          enabled: this.config.enabled,
          useWecom: this.config.useWecom,
          threshold: this.config.threshold,
        });
      } catch { /* ignore */ }
    }
  }

  updateConfig(config: Partial<OpenClawConfig>) {
    this.config = { ...this.config, ...config };
    localStorage.setItem('openclawConfig', JSON.stringify(this.config));
  }

  /**
   * 根据检测结果判断是否需要发送告警
   */
  shouldAlert(result: DetectionResult): boolean {
    const enabled = this.config.enabled;
    const hasChannel = this.config.useWecom || this.config.useFeishu || this.config.useQClaw || !!this.config.qclawWebhookUrl || !!this.config.directWebhookUrl;
    const score = Math.round((result.score ?? 0) * 100);
    const meetsThreshold = score >= this.config.threshold;
    const notSafe = result.level !== 'safe';
    const shouldSend = enabled && hasChannel && meetsThreshold && notSafe;

    console.log('[OpenClaw] shouldAlert 判断:', {
      enabled,
      hasChannel,
      channels: { useWecom: this.config.useWecom, useFeishu: this.config.useFeishu, useQClaw: this.config.useQClaw },
      score,
      threshold: this.config.threshold,
      meetsThreshold,
      level: result.level,
      notSafe,
      result: shouldSend,
    });

    return shouldSend;
  }

  /**
   * 发送风险告警
   * 优先: 通过后端 → QClaw Webhook（后端已配置 URL 和 token）
   * 降级: 直接企业微信/QQ Webhook
   */
  async sendAlert(result: DetectionResult, videoTitle?: string): Promise<boolean> {
    if (!this.shouldAlert(result)) return false;

    console.log('[OpenClaw] 开始发送告警, 视频:', videoTitle);

    // 优先走企业微信
    if (this.config.useWecom) {
      const success = await this._sendViaWecom(result, videoTitle);
      if (success) return true;
      console.log('[OpenClaw] 企业微信推送失败，降级到飞书');
    }

    // 走飞书
    if (this.config.useFeishu) {
      const success = await this._sendViaFeishu(result, videoTitle);
      if (success) return true;
      console.log('[OpenClaw] 飞书推送失败，降级到 QClaw');
    }

    // 走 QClaw
    if (this.config.useQClaw) {
      const success = await this._sendViaQClaw(result, videoTitle);
      if (success) return true;
      console.log('[OpenClaw] QClaw 推送失败，降级到直接 webhook');
    }

    // 降级: 直接 webhook
    if (this.config.directWebhookUrl) {
      return this._sendDirectWebhook(result, videoTitle);
    }

    return false;
  }

  /**
   * 通过后端 /api/wecom/push 推送到企业微信
   */
  private async _sendViaWecom(result: DetectionResult, videoTitle?: string): Promise<boolean> {
    const payload = {
      level: result.level,
      score: result.score ?? 0,
      video_title: videoTitle || '未知视频',
      reasons: result.reasons || [],
      suggestions: result.suggestions || [],
      detection_method: (result as any).detection_method || 'ai_multimodal',
      timestamp: new Date().toISOString(),
    };

    try {
      const backendUrl = `${window.location.protocol}//${window.location.hostname}:8000/api/wecom/push`;
      const response = await fetch(backendUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      console.log('[OpenClaw] WeCom push response:', data);
      return data.success && data.pushed;
    } catch (error) {
      console.error('[OpenClaw] WeCom push error:', error);
      return false;
    }
  }

  /**
   * 通过后端 /api/feishu/push 推送到飞书
   */
  private async _sendViaFeishu(result: DetectionResult, videoTitle?: string): Promise<boolean> {
    const payload = {
      level: result.level,
      score: result.score ?? 0,
      video_title: videoTitle || '未知视频',
      reasons: result.reasons || [],
      suggestions: result.suggestions || [],
      detection_method: (result as any).detection_method || 'ai_multimodal',
      timestamp: new Date().toISOString(),
    };

    try {
      const backendUrl = `${window.location.protocol}//${window.location.hostname}:8000/api/feishu/push`;
      const response = await fetch(backendUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      console.log('[OpenClaw] Feishu push response:', data);
      return data.success && data.pushed;
    } catch (error) {
      console.error('[OpenClaw] Feishu push error:', error);
      return false;
    }
  }

  /**
   * 通过后端 /api/qclaw/push 推送到 QClaw
   */
  private async _sendViaQClaw(result: DetectionResult, videoTitle?: string): Promise<boolean> {
    const payload = {
      level: result.level,
      score: result.score ?? 0,
      video_title: videoTitle || '未知视频',
      reasons: result.reasons || [],
      suggestions: result.suggestions || [],
      detection_method: (result as any).detection_method || 'ai_multimodal',
      timestamp: new Date().toISOString(),
    };

    try {
      const backendUrl = `${window.location.protocol}//${window.location.hostname}:8000/api/qclaw/push`;
      const response = await fetch(backendUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await response.json();
      console.log('[OpenClaw] QClaw push response:', data);
      return data.success && data.pushed;
    } catch (error) {
      console.error('[OpenClaw] QClaw push error:', error);
      return false;
    }
  }

  /**
   * 直接推送到企业微信/QQ Webhook（不经过 QClaw）
   */
  private async _sendDirectWebhook(result: DetectionResult, videoTitle?: string): Promise<boolean> {
    if (!this.config.directWebhookUrl) return false;

    const score = Math.round((result.score ?? 0) * 100);
    const reasons = (result.reasons || []).join('\n  • ');
    const suggestions = (result.suggestions || []).join('\n  • ');

    const wecomPayload = {
      msgtype: 'markdown',
      markdown: {
        content: [
          `## 🚨 短视频风险告警`,
          `> **AI守护系统** 检测到可疑内容`,
          '',
          `**视频**: ${videoTitle || '未知视频'}`,
          `**风险等级**: <font color="${result.level === 'danger' ? 'warning' : 'comment'}">${result.level === 'danger' ? '🔴 高风险' : '🟡 注意'}</font>`,
          `**风险评分**: ${score}/100`,
          '',
          reasons ? `**风险因素**:\n  • ${reasons}` : '',
          suggestions ? `**建议**:\n  • ${suggestions}` : '',
          '',
          `> 请及时关注老人的上网安全，如遇诈骗请拨打 96110`,
        ].filter(Boolean).join('\n'),
      },
    };

    const qqPayload = {
      content: [
        `🚨 短视频风险告警`,
        `━━━━━━━━━━━━━━`,
        `📹 视频: ${videoTitle || '未知视频'}`,
        `⚠️ 风险等级: ${result.level === 'danger' ? '🔴 高风险' : '🟡 注意'}`,
        `📊 风险评分: ${score}/100`,
        reasons ? `\n⚡ 风险因素:\n  • ${reasons}` : '',
        suggestions ? `\n💡 建议:\n  • ${suggestions}` : '',
        `\n🛡️ AI守护系统提醒您关注老人上网安全`,
      ].filter(Boolean).join('\n'),
    };

    try {
      const targets: string[] = [];
      if (this.config.channel === 'wecom' || this.config.channel === 'both') targets.push('wecom');
      if (this.config.channel === 'qq' || this.config.channel === 'both') targets.push('qq');

      const results = await Promise.allSettled(
        targets.map(async (target) => {
          const payload = target === 'wecom' ? wecomPayload : qqPayload;
          const response = await fetch(this.config.directWebhookUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
          });
          if (!response.ok) throw new Error(`${target} webhook failed: ${response.status}`);
          return response.json();
        })
      );

      const success = results.some((r) => r.status === 'fulfilled');
      console.log('[OpenClaw] Direct webhook sent:', success);
      return success;
    } catch (error) {
      console.error('[OpenClaw] Direct webhook failed:', error);
      return false;
    }
  }

  /**
   * 发送测试通知
   */
  async sendTestAlert(): Promise<boolean> {
    const testResult: DetectionResult = {
      level: 'danger',
      score: 0.85,
      confidence: 0.9,
      message: '这是一条测试告警',
      reasons: ['这是测试风险因素1', '这是测试风险因素2'],
      suggestions: ['这是测试建议1', '这是测试建议2'],
      timestamp: new Date(),
    };

    const origThreshold = this.config.threshold;
    const origEnabled = this.config.enabled;
    this.config.threshold = 0;
    this.config.enabled = true;
    const success = await this.sendAlert(testResult, '🧪 测试视频 - AI守护系统');
    this.config.threshold = origThreshold;
    this.config.enabled = origEnabled;
    return success;
  }

  /**
   * 检查 QClaw 状态
   */
  async checkQClawStatus(): Promise<{ configured: boolean; reachable: boolean; message: string }> {
    try {
      const url = `${window.location.protocol}//${window.location.hostname}:8000/api/qclaw/status`;
      const response = await fetch(url);
      const data = await response.json();
      return {
        configured: data.data?.webhook_configured ?? false,
        reachable: data.data?.reachable ?? false,
        message: data.data?.reachable ? 'QClaw 连接正常' : '未连接到 QClaw',
      };
    } catch (error) {
      return { configured: false, reachable: false, message: String(error) };
    }
  }

  /**
   * 将 QClaw Webhook URL 保存到后端
   */
  async saveQClawWebhookToBackend(webhookUrl: string): Promise<boolean> {
    try {
      const url = `${window.location.protocol}//${window.location.hostname}:8000/api/qclaw/config`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhook_url: webhookUrl, enabled: true }),
      });
      const data = await response.json();
      return data.success;
    } catch {
      return false;
    }
  }

  /**
   * 将飞书 Webhook URL 保存到后端
   */
  async saveFeishuWebhookToBackend(webhookUrl: string): Promise<boolean> {
    try {
      const url = `${window.location.protocol}//${window.location.hostname}:8000/api/feishu/config`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhook_url: webhookUrl, enabled: true }),
      });
      const data = await response.json();
      return data.success;
    } catch {
      return false;
    }
  }

  /**
   * 检查飞书连接状态
   */
  async checkFeishuStatus(): Promise<{ configured: boolean; reachable: boolean; message: string }> {
    try {
      const url = `${window.location.protocol}//${window.location.hostname}:8000/api/feishu/status`;
      const response = await fetch(url);
      const data = await response.json();
      return {
        configured: data.data?.webhook_configured ?? false,
        reachable: data.data?.reachable ?? false,
        message: data.data?.reachable ? '飞书连接正常' : '未连接到飞书',
      };
    } catch (error) {
      return { configured: false, reachable: false, message: String(error) };
    }
  }

  /**
   * 发送飞书测试通知
   */
  async sendFeishuTestAlert(): Promise<boolean> {
    try {
      const url = `${window.location.protocol}//${window.location.hostname}:8000/api/feishu/test`;
      const response = await fetch(url, { method: 'POST' });
      const data = await response.json();
      return data.success;
    } catch {
      return false;
    }
  }

  /**
   * 将企业微信 Webhook URL 保存到后端
   */
  async saveWecomWebhookToBackend(webhookUrl: string): Promise<boolean> {
    try {
      const url = `${window.location.protocol}//${window.location.hostname}:8000/api/wecom/config`;
      const response = await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ webhook_url: webhookUrl, enabled: true }),
      });
      const data = await response.json();
      return data.success;
    } catch {
      return false;
    }
  }

  /**
   * 发送企业微信测试通知
   */
  async sendWecomTestAlert(): Promise<boolean> {
    try {
      const url = `${window.location.protocol}//${window.location.hostname}:8000/api/wecom/test`;
      const response = await fetch(url, { method: 'POST' });
      const data = await response.json();
      return data.success;
    } catch {
      return false;
    }
  }
}
