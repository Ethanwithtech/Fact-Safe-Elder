/**
 * FactSafe Elder Alert — QClaw Skill 核心入口
 * 
 * 架构说明:
 *   本 Skill 上传到 GitHub → QClaw 下载安装 → QClaw 为本 Skill 注册 webhook endpoint
 *   → 用户将该 webhook URL 配到 FactSafe 后端
 *   → FactSafe 检测到风险时 POST 告警到 webhook
 *   → 本 Skill 的 handleRiskAlert() 被 QClaw 调用
 *   → 格式化消息 → 通过 QClaw Agent 推送给企业微信/QQ
 * 
 * 数据流:
 *   FactSafe 后端 --POST /webhook--> QClaw --调用--> handleRiskAlert() --推送--> 企业微信/QQ
 */

/**
 * QClaw 收到 webhook 后调用此函数处理风险告警
 * 
 * @param {object} context - QClaw 提供的上下文
 * @param {object} context.payload - webhook POST body（来自 FactSafe 后端）
 * @param {object} context.settings - 用户在 QClaw 中配置的 Skill 设置
 * @param {object} context.agent - QClaw Agent 实例（用于发消息）
 * @param {function} context.reply - 快捷回复函数
 * @returns {object} 处理结果
 */
async function handleRiskAlert(context) {
  const { payload, settings, agent } = context;

  // ===== 1. 校验告警数据 =====
  if (!payload || !payload.level) {
    return { success: false, message: '告警数据缺少 level 字段' };
  }

  // safe 级别不需要告警
  if (payload.level === 'safe') {
    return { success: true, message: '安全内容，无需告警', forwarded: false };
  }

  // ===== 2. 检查阈值和级别 =====
  const threshold = (settings && settings.notify_threshold) || 50;
  const allowedLevels = (settings && settings.notify_levels) || ['danger', 'warning'];
  const scorePct = Math.round((payload.score || 0) * 100);

  if (scorePct < threshold) {
    return { success: true, message: `评分 ${scorePct} 低于阈值 ${threshold}，跳过`, forwarded: false };
  }

  if (!allowedLevels.includes(payload.level)) {
    return { success: true, message: `级别 ${payload.level} 不在告警范围内`, forwarded: false };
  }

  // ===== 3. 免打扰时段检查 =====
  if (settings && settings.quiet_hours && payload.level !== 'danger') {
    const now = new Date();
    const hour = now.getHours();
    const startHour = parseInt((settings.quiet_hours.start || '23:00').split(':')[0], 10);
    const endHour = parseInt((settings.quiet_hours.end || '07:00').split(':')[0], 10);

    const inQuietHours = startHour > endHour
      ? (hour >= startHour || hour < endHour)   // 跨午夜: 23:00-07:00
      : (hour >= startHour && hour < endHour);   // 同天

    if (inQuietHours) {
      return { success: true, message: '免打扰时段，warning 级别跳过', forwarded: false };
    }
  }

  // ===== 4. 格式化消息 =====
  const levelEmoji = { danger: '🔴', warning: '🟡' }[payload.level] || '⚪';
  const levelText = {
    danger: '高风险 - 疑似诈骗',
    warning: '注意 - 内容可疑',
  }[payload.level] || payload.level;

  const reasons = (payload.reasons || []).map(r => `  • ${r}`).join('\n') || '  无';
  const suggestions = (payload.suggestions || []).map(s => `  💡 ${s}`).join('\n') || '  无';

  // 企业微信 markdown 格式
  const wecomMarkdown = [
    '## 🚨 短视频风险告警',
    '> **FactSafe AI守护系统** 检测到可疑内容',
    '',
    `**视频**: ${payload.video_title || '未知视频'}`,
    `**风险等级**: <font color="${payload.level === 'danger' ? 'warning' : 'comment'}">${levelEmoji} ${levelText}</font>`,
    `**风险评分**: ${scorePct}/100`,
    `**检测方式**: ${payload.detection_method || 'AI多模态'}`,
    '',
    `**风险因素**:`,
    reasons,
    '',
    `**安全建议**:`,
    suggestions,
    '',
    `> ⏰ ${payload.timestamp || new Date().toISOString()}`,
    '> 🛡️ 请及时关注老人的上网安全，如遇诈骗请拨打 **96110**',
  ].join('\n');

  // 纯文本格式（QQ / 紧急通知）
  const plainText = [
    '🚨 短视频风险告警',
    '━━━━━━━━━━━━━━',
    `📹 视频: ${payload.video_title || '未知视频'}`,
    `${levelEmoji} 风险等级: ${levelText}`,
    `📊 风险评分: ${scorePct}/100`,
    '',
    '⚡ 风险因素:',
    reasons,
    '',
    '💡 安全建议:',
    suggestions,
    '',
    `⏰ ${payload.timestamp || new Date().toISOString()}`,
    '🛡️ FactSafe AI守护系统 | 如遇诈骗请拨打 96110',
  ].join('\n');

  // ===== 5. 通过 QClaw Agent 推送消息 =====
  const results = [];

  try {
    // 企业微信推送（markdown）
    if (agent && agent.send) {
      const wecomResult = await agent.send({
        channel: 'wecom',
        type: 'markdown',
        content: wecomMarkdown,
        metadata: {
          source: 'factsafe-elder-alert',
          level: payload.level,
          score: payload.score,
        },
      });
      results.push({ channel: 'wecom', success: true, data: wecomResult });
    }
  } catch (err) {
    results.push({ channel: 'wecom', success: false, error: err.message });
  }

  try {
    // QQ 推送（纯文本）
    if (agent && agent.send) {
      const qqResult = await agent.send({
        channel: 'qq',
        type: 'text',
        content: plainText,
        metadata: {
          source: 'factsafe-elder-alert',
          level: payload.level,
          score: payload.score,
        },
      });
      results.push({ channel: 'qq', success: true, data: qqResult });
    }
  } catch (err) {
    results.push({ channel: 'qq', success: false, error: err.message });
  }

  // 高风险紧急额外通知
  if (payload.level === 'danger' && scorePct >= 80) {
    try {
      if (agent && agent.send) {
        await agent.send({
          channel: 'wecom',
          type: 'text',
          content: `🚨【紧急】检测到高风险诈骗内容！\n视频：${payload.video_title || '未知'}\n评分：${scorePct}/100\n请立即联系老人确认安全！\n反诈热线：96110`,
          priority: 'urgent',
        });
        results.push({ channel: 'wecom-urgent', success: true });
      }
    } catch (err) {
      results.push({ channel: 'wecom-urgent', success: false, error: err.message });
    }
  }

  const anySuccess = results.some(r => r.success);

  return {
    success: anySuccess,
    message: anySuccess ? '告警已推送给家属' : '推送失败',
    forwarded: true,
    details: results,
  };
}

/**
 * Skill 初始化钩子 — QClaw 安装后调用一次
 * 用于注册 webhook、验证配置等
 */
async function onInstall(context) {
  const { settings, registerWebhook } = context;

  // 向 QClaw 注册 webhook，QClaw 返回一个 URL
  // 用户需要把这个 URL 配到 FactSafe 后端的 OpenClaw 设置里
  const webhookInfo = await registerWebhook({
    event: 'risk_alert',
    handler: 'handleRiskAlert',
    description: '接收 FactSafe AI 检测系统的风险告警',
  });

  return {
    success: true,
    message: '安装成功！请将以下 Webhook URL 配置到 FactSafe 系统设置中：',
    webhook_url: webhookInfo.url,
    instructions: [
      `1. 复制 Webhook URL: ${webhookInfo.url}`,
      '2. 打开 FactSafe 系统 → 设置 → OpenClaw 配置',
      '3. 粘贴 Webhook URL 并启用',
      '4. 点击「测试推送」验证连通性',
    ],
  };
}

/**
 * Skill 卸载钩子
 */
async function onUninstall(context) {
  // 清理注册的 webhook
  if (context && context.unregisterWebhook) {
    await context.unregisterWebhook('risk_alert');
  }
  return { success: true, message: 'Skill 已卸载' };
}

// ===== 导出 =====
module.exports = {
  handleRiskAlert,
  onInstall,
  onUninstall,
};
