# 🛡️ 老人短视频虚假信息检测系统

基于多模态AI的短视频虚假信息检测系统，专为保护老年人群体设计。

## 📋 项目简介

随着短视频平台的快速发展，虚假信息传播问题日益严重，老年人群体因数字素养相对较低成为主要受害者。本系统运用先进的多模态AI技术，实时检测并预警金融诈骗、医疗错误信息和假新闻。

### 🎯 核心功能

- 🔍 **多模态检测**: 文本 + 视觉 + 音频三模态融合分析
- ⚠️ **智能预警**: 三级风险评估（安全/警告/危险）
- 📱 **家人通知**: 检测到高风险内容时自动通知家人
- 📊 **可解释性**: 清晰说明风险原因和建议

### 🧪 技术亮点

- **FakeSV架构**: 基于AAAI 2023最新短视频假新闻检测方法
- **BERT中文预训练**: 使用chinese-bert-wwm-ext进行语义理解
- **跨模态注意力**: 实现文本-视觉-音频信息融合
- **规则引擎增强**: AI + 规则双重保障

## 🚀 快速开始

### 环境要求

- Python 3.9+
- Node.js 18+ (前端开发)
- CUDA 11.8+ (GPU训练，可选)

### 安装步骤

```bash
# 1. 克隆项目
git clone https://github.com/yourusername/Fact-Safe-Elder.git
cd Fact-Safe-Elder

# 2. 安装后端依赖
cd backend
pip install -r requirements.txt

# 3. 启动后端服务
python -m app.main
# 或使用简化版
uvicorn app.main_simple:app --reload --port 8000

# 4. 安装前端依赖 (可选)
cd ../frontend
npm install
npm start
```

### Docker部署

```bash
docker-compose up -d
```

## 📊 数据集

系统支持以下数据集进行训练:

| 数据集 | 描述 | 样本量 |
|--------|------|--------|
| comprehensive_training_set | 自定义标注数据 | 12,000+ |
| chinese_rumor (CED) | 微博辟谣数据 | 31,000+ |
| weibo_rumors | 微博谣言数据 | 5,000+ |
| mcfend | 多源中文假新闻 | 10,000+ |

## 🏋️ 模型训练

### 本地训练

```bash
# 使用默认参数训练
python train_multimodal_model.py

# 自定义参数
python train_multimodal_model.py \
    --epochs 10 \
    --batch_size 16 \
    --learning_rate 2e-5 \
    --output_dir ./models \
    --fp16
```

### Google Colab训练

详见 [COLAB_训练指南.md](./COLAB_训练指南.md)

```python
# Colab快速开始
!pip install torch transformers loguru tqdm scikit-learn
!python train_multimodal_model.py --device cuda --fp16
```

## 📁 项目结构

```
tyt/
├── backend/                 # 后端服务
│   ├── app/
│   │   ├── main.py         # FastAPI主入口
│   │   ├── services/       # 业务逻辑
│   │   │   ├── multimodal_detector.py  # 多模态检测器
│   │   │   ├── family_notification.py  # 家人通知
│   │   │   └── dataset_loader.py       # 数据加载
│   │   └── api/            # API路由
│   └── requirements.txt
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/     # React组件
│   │   └── services/       # 前端服务
│   └── package.json
├── data/                   # 数据目录
│   └── raw/               # 原始数据
├── models/                # 模型文件
├── train_multimodal_model.py  # 训练脚本
├── PRD_老人短视频虚假信息检测系统.md
├── 技术设计文档.md
└── README.md
```

## 🔌 API接口

### 检测接口

```bash
POST /detect
Content-Type: application/json

{
    "text": "投资高收益理财产品，保本保息年化30%",
    "source": "test"
}
```

响应示例:
```json
{
    "success": true,
    "message": "检测完成",
    "data": {
        "level": "danger",
        "score": 0.92,
        "confidence": 0.88,
        "message": "⚠️ 高风险：检测到疑似诈骗信息",
        "reasons": ["金融风险词汇: 高收益, 保本保息, 年化"],
        "suggestions": ["投资需谨慎，高收益往往伴随高风险"]
    }
}
```

### 健康检查

```bash
GET /health
```

## 📚 参考论文

1. **FakeSV** - "A Multimodal Benchmark with Rich Social Context for Fake News Detection on Short Video Platforms" (AAAI 2023)
2. **SpotFake** - "A Multimodal Framework for Fake News Detection" (IEEE BigMM 2019)
3. **Chinese-BERT-wwm** - "Pre-Training with Whole Word Masking for Chinese BERT"

## 🤝 贡献指南

欢迎提交Issue和Pull Request!

## 📄 许可证

MIT License

## 📞 联系方式

如有问题，请提交Issue或联系项目维护者。
