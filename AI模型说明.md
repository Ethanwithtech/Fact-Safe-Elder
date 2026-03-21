# 🤖 AI模型说明文档

## 📊 当前视频检测AI使用的模型和参数

### 1. 多模态检测器架构

**类名：** `MultimodalDetector`  
**位置：** `backend/app/services/multimodal_detector.py`

### 2. 模型组件

#### 2.1 文本编码器 (TextEncoder)
- **模型：** BERT中文预训练模型
- **默认模型：** `hfl/chinese-bert-wwm-ext` 或本地 `./models/chinese-bert`
- **隐藏维度：** 768
- **功能：** 提取文本语义特征

#### 2.2 视觉编码器 (VisualEncoder)
- **模型：** ResNet-50 或 EfficientNet-B0
- **默认：** ResNet-50 (预训练)
- **隐藏维度：** 768
- **功能：** 提取视频帧视觉特征
- **预处理：** Resize(256) -> CenterCrop(224) -> Normalize

#### 2.3 音频编码器 (AudioEncoder)
- **模型：** OpenAI Whisper
- **默认模型：** `base` 版本
- **功能：** 音频转写为文本，然后使用文本编码器提取特征
- **语言：** 中文 (zh)

#### 2.4 跨模态注意力 (CrossModalAttention)
- **隐藏维度：** 768
- **注意力头数：** 8
- **Dropout：** 0.1
- **功能：** 融合文本-视觉-音频三种模态的信息

### 3. 融合策略

**默认策略：** `attention`（注意力融合）

可选策略：
- `attention`: 使用跨模态注意力机制融合
- `early`: 早期融合（直接拼接特征）
- `late`: 后期融合（分别分类后融合）

### 4. 检测参数

#### 4.1 初始化参数
```python
MultimodalDetector(
    model_path: Optional[str] = None,  # 训练好的模型路径（可选）
    device: str = "auto",                # 设备：auto/cuda/cpu
    fusion_strategy: str = "attention"   # 融合策略
)
```

#### 4.2 检测参数
- **最大序列长度：** 512 (文本)
- **最大帧数：** 3 (视频关键帧)
- **OCR最大字符：** 800
- **转写最大字符：** 500

### 5. 风险等级分类

**输出类别：** 3类
- `safe` (0): 安全
- `warning` (1): 警告
- `danger` (2): 危险

### 6. 降级机制

如果AI模型不可用，系统自动使用**规则引擎**：
- 基于关键词匹配
- 金融诈骗关键词检测
- 医疗虚假信息关键词检测
- 紧急性诱导词汇检测

### 7. 视频检测流程

```
上传视频
  ↓
提取关键帧 (OpenCV)
  ↓
OCR识别画面文字 (EasyOCR/Pytesseract)
  ↓
语音转写 (Whisper)
  ↓
合并文本内容
  ↓
多模态检测
  ├─ 文本特征提取 (BERT)
  ├─ 视觉特征提取 (ResNet)
  ├─ 音频特征提取 (Whisper + BERT)
  └─ 跨模态融合 (Attention)
  ↓
风险等级判断
  ↓
返回检测结果
```

### 8. 检测输出

```python
{
    "level": "safe/warning/danger",
    "score": 0.0-1.0,           # 风险分数
    "confidence": 0.0-1.0,      # 置信度
    "text_risk": 0.0-1.0,       # 文本风险度
    "visual_risk": 0.0-1.0,     # 视觉风险度
    "audio_risk": 0.0-1.0,      # 音频风险度
    "reasons": [...],            # 风险原因列表
    "suggestions": [...],        # 建议列表
    "detection_method": "...",   # 检测方法
    "inference_time": 0.0        # 推理时间（秒）
}
```

### 9. 性能指标

- **推理时间：** < 3秒（CPU），< 1秒（GPU）
- **准确率：** > 85%（使用训练好的模型）
- **召回率：** > 90%（优先不漏检）

### 10. 依赖库

**必需：**
- `torch` - PyTorch深度学习框架
- `transformers` - HuggingFace模型库
- `pillow` - 图像处理

**可选（视频功能）：**
- `opencv-python` - 视频帧提取
- `easyocr` / `pytesseract` - OCR文字识别
- `openai-whisper` - 语音转写

---

**最后更新：** 2025-12-28

