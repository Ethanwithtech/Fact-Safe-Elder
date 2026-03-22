# 模型目录说明（GitHub 上传策略）

本目录**会上传**：模型定义代码、训练指标 JSON、说明文档。  
**不会上传**：`.joblib` / `.pth` 等权重文件（体积大，易超 GitHub 限制）。

## 目录结构

| 路径 | 说明 | 是否提交 Git |
|------|------|--------------|
| `bert_attention_detector.py` | BERT + Attention + 证据排序（论文思路实现） | ✅ |
| `trained/model_metrics.json` | 最近一次训练的指标（准确率、F1 等） | ✅ |
| `trained/simple_ai_model.joblib` | sklearn 训练产物（RandomForest 等） | ❌ 忽略，本地或 Release 分发 |
| `fraud_detector_final.pth` | Colab 训练的 PyTorch 权重（若存在） | ❌ 忽略 |
| `finetuned/**/training_result.json` | 历史模拟/训练结果摘要 | ✅（体积小） |

## 本地如何生成权重

在项目根目录执行：

```bash
python download_real_training_data.py
python train_real_model.py
```

生成：`models/trained/simple_ai_model.joblib`（被 `.gitignore` 排除）。

## GPU 训练（推荐）

使用根目录 `Colab_Training.py` 在 **Google Colab** 中运行，下载 `fraud_detector_final.pth` 放到 `models/`，并重启 `enhanced_backend.py`。

## 大文件分发方式（任选）

1. **GitHub Releases**：上传 `.joblib` 或 `.pth` 作为 Release 附件。  
2. **网盘 / 对象存储**：放链接在本文档或 `README.md`。  
3. **仅团队使用**：不公开权重，只公开代码与指标。

---

与 AI 检测相关的其它代码（不在 `models/` 内）见仓库根目录 `README.md` 与 `enhanced_backend.py`。
