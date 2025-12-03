# 🎓 Google Colab 训练指南

## 老人短视频虚假信息检测模型训练

本指南帮助你在Google Colab上训练多模态虚假信息检测模型。

## 快速开始

### 1. 打开Google Colab

访问 https://colab.research.google.com/ 并创建新笔记本。

### 2. 检查GPU

```python
import torch
print(f"PyTorch版本: {torch.__version__}")
print(f"CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"显存: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
```

### 3. 安装依赖

```python
!pip install transformers datasets scikit-learn loguru tqdm -q
!pip install openai-whisper -q  # 可选：音频处理
```

### 4. 挂载Google Drive

```python
from google.colab import drive
drive.mount('/content/drive')
```

### 5. 克隆项目

```python
!git clone https://github.com/your-repo/Fact-Safe-Elder.git
%cd Fact-Safe-Elder/tyt
```

### 6. 运行训练

```python
!python train_multimodal_model.py --mode colab --epochs 10 --batch_size 8
```

## 训练参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--mode` | local | 运行模式 (local/colab) |
| `--epochs` | 10 | 训练轮数 |
| `--batch_size` | 16 | 批次大小 (Colab建议8) |
| `--learning_rate` | 2e-5 | 学习率 |
| `--max_length` | 256 | 最大序列长度 |
| `--text_only` | False | 仅使用文本模态 |

## Colab优化建议

### 内存优化
```python
# 使用较小的batch_size
!python train_multimodal_model.py --batch_size 8

# 减少序列长度
!python train_multimodal_model.py --max_length 256

# 仅文本模态（节省内存）
!python train_multimodal_model.py --text_only
```

### 训练时间估算

| 数据规模 | Colab Free (T4) | Colab Pro (V100) |
|----------|-----------------|------------------|
| 1000样本 | ~10分钟 | ~5分钟 |
| 5000样本 | ~40分钟 | ~20分钟 |
| 10000样本 | ~80分钟 | ~40分钟 |

## 使用FakeSV数据集

### 1. 下载数据集

FakeSV数据集需要申请访问权限：
1. 签署数据使用协议
2. 发送邮件至 pengqi.qp@gmail.com
3. 等待审核获取下载链接

### 2. 上传到Google Drive

```
/content/drive/MyDrive/
└── FYP_Data/
    └── FakeSV/
        ├── train/
        ├── val/
        ├── test/
        └── features/
```

### 3. 训练

```python
!python train_multimodal_model.py \
    --mode colab \
    --data_dir /content/drive/MyDrive/FYP_Data/FakeSV \
    --epochs 10
```

## 保存和导出模型

### 自动保存位置
```
/content/drive/MyDrive/FYP_Models/
├── checkpoint_best.pt      # 最佳模型
├── checkpoint_latest.pt    # 最新检查点
└── training_history.json   # 训练历史
```

### 手动导出
```python
import torch

# 保存模型
torch.save(model.state_dict(), '/content/drive/MyDrive/FYP_Models/final_model.pt')
```

## 常见问题

### Q1: CUDA内存不足
```python
# 减小batch_size
!python train_multimodal_model.py --batch_size 4

# 清理GPU缓存
import torch
torch.cuda.empty_cache()
```

### Q2: 训练中断
Colab会话可能会断开。建议：
- 使用Google Drive保存检查点
- 实现断点续训功能
- 使用Colab Pro获取更长的运行时间

### Q3: 数据加载慢
```python
# 使用预计算特征
!python train_multimodal_model.py --use_precomputed_features
```

## 训练监控

### TensorBoard
```python
%load_ext tensorboard
%tensorboard --logdir /content/drive/MyDrive/FYP_Models/logs
```

### 实时查看日志
```python
!tail -f /content/drive/MyDrive/FYP_Models/training.log
```

## 模型评估

训练完成后运行评估：
```python
from sklearn.metrics import classification_report

# 评估结果示例
print(classification_report(y_true, y_pred, 
    target_names=['安全', '可疑', '高风险']))
```

## 参考资源

- **FakeSV论文**: AAAI 2023
- **BERT中文模型**: hfl/chinese-bert-wwm-ext
- **Hugging Face**: https://huggingface.co/
- **项目文档**: 技术设计文档.md

---

**作者**: FYP项目组  
**更新日期**: 2025-12-03

