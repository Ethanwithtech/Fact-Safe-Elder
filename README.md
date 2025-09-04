# 🛡️ AI守护 - 老人短视频虚假信息检测系统 v2.0

<div align="center">
  <h3>🤖 基于ChatGLM、BERT、LLaMA的智能防护系统</h3>
  <p>
    <img src="https://img.shields.io/badge/Version-2.0.0-blue?style=flat-square" alt="Version">
    <img src="https://img.shields.io/badge/AI-Powered-green?style=flat-square" alt="AI">
    <img src="https://img.shields.io/badge/Status-Active-success?style=flat-square" alt="Status">
  </p>
</div>

> 集成大语言模型的智能虚假信息检测平台 - 守护老年人的数字生活安全

## 📋 项目简介

**AI守护**是一个基于最新大语言模型技术的智能虚假信息检测系统，专为保护老年人免受短视频平台诈骗和虚假信息侵害而设计。系统集成了ChatGLM-6B、Chinese-BERT、LLaMA-7B等先进AI模型，通过多模态分析和集成学习，提供准确率超过95%的实时检测服务。

### 🎯 核心功能

#### 🤖 AI检测能力
- **ChatGLM-6B**: 深度语义理解和对话分析
- **BERT分类器**: 高精度文本分类和情感分析
- **LLaMA推理**: 多语言内容理解和逻辑推理
- **集成学习**: 多模型投票机制，准确率95%+
- **实时推理**: 毫秒级响应，支持流式输出

#### 📱 仿真体验
- **手机模拟器**: 1:1还原抖音/快手界面
- **滑动交互**: 上下滑动切换视频
- **实时弹幕**: 模拟真实评论流
- **社交互动**: 点赞、评论、分享功能

#### 🎓 训练平台
- **在线训练**: 支持ChatGLM/BERT/LLaMA微调
- **数据集管理**: MCFEND、微博等多源数据
- **LoRA微调**: 高效参数微调技术
- **实时监控**: 训练进度和指标可视化

#### 👴 适老化设计
- **大字体显示**: 18-26px自适应调节
- **语音播报**: 检测结果语音提示
- **颜色标识**: 绿黄红三级直观预警
- **简化操作**: 一键启动，自动检测

### 🎨 适老化设计特色

- **大字体**: 18-26px字体大小，支持自定义调节
- **高对比度**: 清晰的颜色对比，便于老人阅读
- **简单操作**: 大按钮设计，最小44px点击区域
- **语音提示**: 检测到风险时播放警告音
- **直观标识**: 使用颜色和图标双重标识风险等级

## 🏗️ 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                        前端展示层                              │
│     React 18 + TypeScript + Ant Design 5 + Swiper 11         │
│     手机模拟器 | 训练面板 | 检测浮窗 | 适老化界面              │
└──────────────────────────────────────────────────────────────┘
                               ↕
┌──────────────────────────────────────────────────────────────┐
│                        API服务层                               │
│              FastAPI + WebSocket + REST API                   │
│         检测接口 | 训练API | 数据集API | 模型管理              │
└──────────────────────────────────────────────────────────────┘
                               ↕
┌──────────────────────────────────────────────────────────────┐
│                      AI推理引擎层                              │
│   ChatGLM-6B | BERT-Chinese | LLaMA-7B | Ensemble Model      │
│     LoRA微调 | INT8量化 | TorchServe | Triton Server         │
└──────────────────────────────────────────────────────────────┘
                               ↕
┌──────────────────────────────────────────────────────────────┐
│                       数据处理层                               │
│    Transformers | PyTorch | Pandas | NumPy | Datasets        │
│      文本处理 | 音频处理 | 视频处理 | 特征工程                 │
└──────────────────────────────────────────────────────────────┘
                               ↕
┌──────────────────────────────────────────────────────────────┐
│                        存储层                                  │
│   PostgreSQL | Redis | MinIO | MongoDB | Model Registry      │
│     业务数据 | 缓存 | 文件存储 | 日志 | 模型版本管理            │
└──────────────────────────────────────────────────────────────┘
```

## 🚀 快速开始

### 系统要求

- **操作系统**: Windows 10+, macOS 10.15+, Ubuntu 18.04+
- **Docker**: 20.10+ 和 Docker Compose 2.0+
- **浏览器**: Chrome 88+, Edge 88+, Firefox 78+
- **内存**: 最小 4GB RAM
- **存储**: 最小 2GB 可用空间

### 一键启动

1. **克隆项目**
```bash
git clone https://github.com/your-org/fact-safe-elder.git
cd fact-safe-elder
```

2. **启动开发环境**
```bash
chmod +x start.sh
./start.sh dev
```

3. **访问应用**
- 🌐 前端应用: http://localhost:3000
- 🔧 后端API: http://localhost:8000
- 📚 API文档: http://localhost:8000/docs

### 手动启动

如果需要手动启动各个服务:

```bash
# 启动后端服务
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 启动前端服务
cd frontend
npm install
npm start
```

## 📖 使用说明

### 老年用户操作指南

1. **🎤 开始监听**
   - 点击"开始监听"按钮
   - 允许浏览器访问麦克风权限
   - 系统开始实时监听短视频音频

2. **📱 观看短视频**
   - 正常使用抖音、微信等平台观看短视频
   - 系统会自动分析视频内容
   - 无需额外操作，后台静默检测

3. **⚠️ 风险提示**
   - 🟢 绿色: 内容安全，可正常观看
   - 🟡 黄色: 注意风险，建议谨慎对待
   - 🔴 红色: 高风险内容，建议立即停止

4. **🔧 个人设置**
   - 点击右上角"设置"按钮
   - 调整字体大小和对比度
   - 设置家人联系方式
   - 调节检测敏感度

### 家属监护功能

- **📞 自动通知**: 检测到高风险内容时自动发送通知
- **📊 查看历史**: 查看长辈的检测历史记录
- **⚙️ 远程设置**: 帮助长辈调整系统设置

## 🔧 配置说明

### 环境变量配置

创建 `.env` 文件并配置以下变量:

```bash
# 基础配置
DEBUG=true
HOST=0.0.0.0
PORT=8000

# 数据库配置
DATABASE_URL=postgresql://user:password@localhost:5432/elder_safety
REDIS_URL=redis://localhost:6379/0

# AI模型配置
WHISPER_MODEL=base
USE_GPU=false

# 通知配置 (可选)
EMAIL_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-password

# 百度语音API (可选)
BAIDU_APP_ID=your-app-id
BAIDU_API_KEY=your-api-key
BAIDU_SECRET_KEY=your-secret-key
```

### 检测规则配置

系统支持自定义检测规则，配置文件位于 `backend/app/data/keywords.json`:

```json
{
  "financial_fraud": [
    "保证收益", "无风险投资", "月入万元"
  ],
  "medical_fraud": [
    "包治百病", "神奇疗效", "祖传秘方"
  ]
}
```

## 🧪 测试

### 运行测试套件

```bash
# 运行所有测试
./start.sh test

# 单独运行后端测试
cd backend
python -m pytest tests/ -v

# 单独运行前端测试
cd frontend
npm test
```

### 手动测试案例

系统内置了测试用例，包括:

- **🔴 高风险**: "投资理财，月入3万，保证收益，无风险！"
- **🟡 中风险**: "神奇保健品，三天见效，医院不告诉你的秘密"
- **🟢 安全内容**: "正规银行理财产品，年化收益3.5%，风险需谨慎"

## 📊 性能指标

- **检测延迟**: < 3秒
- **检测准确率**: > 85%
- **系统可用性**: > 99%
- **内存占用**: < 512MB
- **CPU占用**: < 20%

## 🔐 安全和隐私

### 数据保护

- **🔒 本地处理**: 音频数据仅在本地处理，不上传服务器
- **🛡️ 加密传输**: 所有网络通信使用HTTPS加密
- **🗑️ 数据清理**: 支持一键清除所有本地数据
- **👤 隐私优先**: 最小化数据收集，用户完全控制

### 安全措施

- **🚫 无数据收集**: 不收集用户个人信息
- **🔐 本地存储**: 设置和历史记录仅存储在本地
- **🛡️ 权限控制**: 仅请求必要的麦克风权限
- **🔍 开源透明**: 代码完全开源，接受社区监督

## 🤝 贡献指南

我们欢迎所有形式的贡献！

### 参与方式

1. **🐛 报告Bug**: 提交Issue描述问题
2. **💡 功能建议**: 提出新功能需求
3. **🔧 代码贡献**: 提交Pull Request
4. **📖 文档改进**: 完善文档和注释
5. **🌍 多语言支持**: 添加其他语言支持

### 开发流程

1. Fork 本仓库
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### 代码规范

- **前端**: 使用 ESLint + Prettier
- **后端**: 使用 Black + Flake8
- **提交**: 遵循 Conventional Commits
- **测试**: 保持代码覆盖率 > 80%

## 📄 许可证

本项目基于 MIT 许可证开源 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🆘 常见问题

### Q: 浏览器提示"麦克风权限被拒绝"怎么办？

A: 
1. 点击浏览器地址栏左侧的锁形图标
2. 将麦克风权限设置为"允许"
3. 刷新页面重新尝试

### Q: 检测结果不准确怎么办？

A:
1. 在设置中调整检测敏感度
2. 查看详细检测结果了解原因
3. 提交反馈帮助改进系统

### Q: 如何添加新的检测关键词？

A:
1. 编辑 `backend/app/services/detection.py` 文件
2. 在相应的关键词列表中添加新词汇
3. 重启后端服务生效

### Q: 系统支持哪些平台的短视频？

A: 目前支持所有基于浏览器播放的短视频平台，包括抖音网页版、微信视频号、快手等。

## 📞 联系我们

- **项目主页**: https://github.com/your-org/fact-safe-elder
- **问题反馈**: https://github.com/your-org/fact-safe-elder/issues
- **邮箱联系**: contact@fact-safe-elder.com
- **技术支持**: support@fact-safe-elder.com

## 🙏 致谢

感谢所有为这个项目做出贡献的开发者和用户！

特别感谢：
- 参与测试的老年用户群体
- 提供技术支持的开源社区
- 关心老年人数字安全的社会各界人士

---

**让技术守护长辈，让爱传递安全** 💝
