# 🛡️ AI虚假信息检测系统

基于BERT+Attention的中文诈骗/谣言检测系统，专为保护老年人免受短视频诈骗信息侵害而设计。

## 📖 参考文献

本项目的AI模型实现参考了以下学术论文：

1. **AnswerFact: Fact Checking in Product Question Answering**
   - 作者: Wenxuan Zhang, Yang Deng, Jing Ma, and Wai Lam
   - 会议: EMNLP 2020
   - 贡献: 证据排序模块，用于识别文本中的关键证据

2. **An Attention-based Rumor Detection Model with Tree-structured Recursive Neural Networks**
   - 作者: Jing Ma, Wei Gao, Shafiq Joty, and Kam-Fai Wong
   - 期刊: ACM TIST 2020
   - 贡献: 多头注意力机制，用于捕捉关键信息

## 🚀 快速开始

### 方式一: 直接运行（使用规则引擎）

```bash
# 安装依赖
pip install fastapi uvicorn scikit-learn numpy

# 启动系统
python start_system.py
```

访问 http://localhost:3000 使用系统。

### 方式二: 使用训练好的深度学习模型

1. **在Google Colab中训练模型**:
   - 打开 https://colab.research.google.com/
   - 创建新笔记本
   - 复制 `Colab_Training.py` 中的代码
   - 选择 GPU 运行时 (Runtime -> Change runtime type -> GPU)
   - 运行所有代码
   - 下载 `fraud_detector_final.pth` 文件

2. **部署训练好的模型**:
   ```bash
   # 将模型文件放到 models 目录
   mkdir -p models
   mv fraud_detector_final.pth models/
   
   # 安装PyTorch和transformers
   pip install torch transformers
   
   # 启动系统
   python start_system.py
   ```

### 方式三：从 GitHub Releases 下载大模型（推荐，另一台电脑也可用）

大文件（如 `best_text_model.pt`，约数百 MB）**不能**用普通 `git clone` 带上，请按下面做：

1. 在仓库 **Releases** 页面下载附件（由维护者上传）。
2. 将 `best_text_model.pt` 放到项目根目录，或复制为 `models/fraud_detector_final.pth`（需与 `enhanced_backend.py` 中加载逻辑一致）。
3. 可选：在 PowerShell 中运行（**先修改**脚本里的 Tag / 仓库名，且 **Release 已发布**）：

   ```powershell
   .\scripts\download_models_from_release.ps1 -Tag "v1.0.0-models"
   ```

**完整步骤（含网页上传 Release、直链下载）**：见  
[`docs/GITHUB_RELEASE_模型分发完整指南.md`](docs/GITHUB_RELEASE_模型分发完整指南.md)

## 📁 项目结构

```
📁 项目根目录
├── 📄 start_system.py              # 系统启动脚本
├── 📄 enhanced_backend.py          # 后端API服务
├── 📄 index.html                   # 前端检测界面
│
├── 📄 Colab_Training.py            # Google Colab训练脚本
├── 📄 download_real_training_data.py  # 训练数据生成器
│
├── 📁 models/
│   ├── 📄 bert_attention_detector.py  # BERT+Attention模型定义
│   └── 📄 fraud_detector_final.pth    # 训练好的模型 (需要训练后放置)
│
├── 📁 data/
│   └── 📁 real_datasets/           # 训练数据
│
├── 📁 backend/                     # 后端代码
└── 📁 frontend/                    # React前端代码
```

## 🔧 API接口

### 文本检测
```bash
POST http://localhost:8008/detect
Content-Type: application/json

{
    "text": "保证收益20%，无风险投资，错过后悔！"
}
```

响应:
```json
{
    "success": true,
    "level": "danger",
    "score": 0.95,
    "confidence": 0.95,
    "message": "BERT+Attention模型检测完成",
    "reasons": ["AI模型识别为高风险内容", "包含金融诈骗相关特征"],
    "suggestions": ["🚨 建议立即停止观看，谨防诈骗！", "..."]
}
```

### 健康检查
```bash
GET http://localhost:8008/health
```

### 模型状态
```bash
GET http://localhost:8008/models/status
```

## 📊 模型性能

使用Google Colab训练后的预期性能：

| 指标 | 数值 |
|------|------|
| 准确率 | ~85% |
| F1分数 | ~83% |
| 推理延迟 | <100ms |

## 🎯 检测类别

### 危险内容 (Danger)
- 金融诈骗：投资骗局、股票推荐、虚假理财
- 医疗虚假信息：假药广告、虚假疗效宣传
- 冒充身份诈骗：假冒银行、公安

### 可疑内容 (Warning)
- 过度营销：限时促销、夸大宣传
- 诱导消费：充值返利、会员优惠

### 安全内容 (Safe)
- 正常新闻、天气预报
- 健康科普、生活常识

## 🔬 技术架构

```
┌─────────────────────────────────────────────────────────┐
│                    用户界面 (前端)                        │
│    手机模拟器 + 浮窗提示 + 数据可视化                      │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP/JSON
┌──────────────────────▼──────────────────────────────────┐
│                    检测服务 (后端)                        │
├─────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐  │
│  │ BERT编码器   │→│ 多头自注意力   │→│ 证据排序模块  │  │
│  │ (语义特征)   │  │ (关键信息)    │  │ (重要证据)   │  │
│  └──────────────┘  └───────────────┘  └──────┬───────┘  │
│                                              │          │
│  ┌──────────────────────────────────────────▼────────┐  │
│  │                   分类器 (3分类)                   │  │
│  │              safe / warning / danger              │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 📝 训练数据

数据来源：
- 公安部反诈中心案例
- 国家卫健委辟谣平台
- LIAR数据集（英文）

数据类别：
- 金融诈骗（20+案例）
- 医疗虚假信息（15+案例）
- 可疑营销内容（10+案例）
- 正常内容（15+案例）

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目仅供学术研究和教育目的使用。

## 📞 联系方式

如有问题或建议，请提交 Issue。

---

**重要提示**: 本系统仅作为辅助工具，不能完全替代人工判断。遇到可疑内容，请务必咨询专业人士或拨打反诈热线 96110。
