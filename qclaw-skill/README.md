# FactSafe Elder Alert — QClaw Skill

🛡️ **老人短视频安全守护** QClaw 技能插件

当 FactSafe AI 检测系统发现老人观看的短视频包含诈骗、虚假医疗、高风险理财等内容时，通过 QClaw 自动通知家属。

## 架构

```
FactSafe AI 检测系统（后端）
        │
        │  POST 风险告警数据
        ▼
QClaw Webhook Endpoint ← QClaw 安装本 Skill 后注册
        │
        │  调用 handleRiskAlert()
        ▼
本 Skill 格式化消息
        │
        │  agent.send()
        ▼
QClaw Agent → 企业微信 / QQ 通知家属
```

## 安装

### 方式一：QClaw 界面安装
1. 在 QClaw 中搜索 `factsafe-elder-alert`
2. 点击「安装」
3. 安装完成后复制分配的 **Webhook URL**
4. 打开 FactSafe 系统 → 设置 → OpenClaw 配置 → 粘贴 Webhook URL

### 方式二：GitHub 安装
```bash
# QClaw CLI
qclaw skill install https://github.com/factsafe/factsafe-elder-alert-skill
```

## 配置

安装后在 QClaw 的 Skill 设置中可配置：

| 设置项 | 说明 | 默认值 |
|--------|------|--------|
| FactSafe 后端地址 | AI 检测系统地址 | `http://localhost:8000` |
| 告警阈值 | 风险评分超过此值触发 | 50 |
| 告警级别 | danger / warning | 两者都启用 |
| 免打扰时段 | warning 级别免打扰 | 23:00 - 07:00 |

## Webhook 数据格式

FactSafe 后端 POST 到 QClaw webhook 的数据：

```json
{
  "level": "danger",
  "score": 0.92,
  "video_title": "月入10万的投资秘诀",
  "reasons": [
    "金融风险词汇: 保证收益, 无风险投资",
    "含有紧急性诱导词汇"
  ],
  "suggestions": [
    "投资需谨慎，高收益伴随高风险",
    "冷静思考，不被紧急性语言误导"
  ],
  "detection_method": "ai_multimodal",
  "timestamp": "2026-03-22T15:30:00.000Z"
}
```

## 推送效果

### 企业微信（Markdown）
```
## 🚨 短视频风险告警
> FactSafe AI守护系统 检测到可疑内容

视频: 月入10万的投资秘诀
风险等级: 🔴 高风险 - 疑似诈骗
风险评分: 92/100

> 🛡️ 请及时关注老人的上网安全，如遇诈骗请拨打 96110
```

### 高风险紧急通知（score ≥ 80）
额外发送一条纯文本紧急消息，提醒立即联系老人。

## 开发

```bash
cd qclaw-skill
npm install
npm test
```

## License

MIT
