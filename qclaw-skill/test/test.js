/**
 * FactSafe Elder Alert Skill — 简单测试
 */

const { handleRiskAlert } = require('../src/index');

// 模拟 QClaw Agent
const mockAgent = {
  send: async (msg) => {
    console.log(`[Mock Agent] 推送到 ${msg.channel}:`, msg.type);
    console.log(msg.content.substring(0, 200) + '...');
    return { ok: true };
  },
};

async function runTests() {
  console.log('===== Test 1: 高风险投资诈骗 =====\n');
  const result1 = await handleRiskAlert({
    payload: {
      level: 'danger',
      score: 0.92,
      video_title: '月入10万的投资秘诀！错过后悔一辈子',
      reasons: ['金融风险词汇: 保证收益, 无风险投资, 限时优惠', '含有紧急性诱导词汇'],
      suggestions: ['投资需谨慎，高收益伴随高风险', '不要轻信陌生人的投资建议'],
      detection_method: 'ai_multimodal',
      timestamp: new Date().toISOString(),
    },
    settings: { notify_threshold: 50, notify_levels: ['danger', 'warning'] },
    agent: mockAgent,
  });
  console.log('\n结果:', JSON.stringify(result1, null, 2));

  console.log('\n===== Test 2: 安全内容（应跳过）=====\n');
  const result2 = await handleRiskAlert({
    payload: { level: 'safe', score: 0.1, video_title: '太极养生' },
    settings: {},
    agent: mockAgent,
  });
  console.log('结果:', JSON.stringify(result2, null, 2));

  console.log('\n===== Test 3: 低于阈值（应跳过）=====\n');
  const result3 = await handleRiskAlert({
    payload: { level: 'warning', score: 0.3, video_title: '免费领奖品' },
    settings: { notify_threshold: 50 },
    agent: mockAgent,
  });
  console.log('结果:', JSON.stringify(result3, null, 2));

  console.log('\n===== 所有测试完成 =====');
}

runTests().catch(console.error);
