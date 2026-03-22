# 将「模型 + AI 功能」相关文件推送到 GitHub

## 1. 已配置：不上传的大文件

根目录 `.gitignore` 已设置**不提交**：

- `models/**/*.joblib`、`*.pth`、`*.pt`、`*.bin`、`*.safetensors` 等权重
- 避免仓库体积过大、超过 GitHub 单文件约 100MB 建议上限

**会上传**的模型相关内容：

- `models/bert_attention_detector.py`（模型代码）
- `models/README.md`（说明）
- `models/trained/model_metrics.json`（指标，体积小）
- `models/finetuned/**/training_result.json`（若有）

## 2. 建议一并提交的 AI 相关文件（按需增减）

在项目根目录 `vfg` 下执行 `git add` 时，可包含：

| 类型 | 路径 |
|------|------|
| 后端推理/训练入口 | `enhanced_backend.py`、`train_real_model.py`、`train_models.py` |
| Colab / 数据 | `Colab_Training.py`、`download_real_training_data.py` |
| 原后端 AI 服务 | `backend/app/services/ai_models.py`、`detection.py`、`training.py`、`dataset_manager.py` |
| API | `backend/app/api/detection.py`、`ai_training.py` |
| 依赖 | `backend/requirements.txt`（或你实际使用的 requirements） |

**一般不要提交**：`data/raw/` 下超大 JSON/TSV（若需可改用 Git LFS 或只保留 `dataset_info` 说明）。

## 3. 命令示例（在仓库根目录）

```bash
cd C:\Users\dyc06\.cursor\worktrees\Fact-Safe-Elder\vfg

git status
git add .gitignore
git add models/
git add enhanced_backend.py train_real_model.py Colab_Training.py download_real_training_data.py train_models.py
git add backend/app/services/ai_models.py backend/app/services/detection.py backend/app/services/training.py backend/app/services/dataset_manager.py
git add backend/app/api/detection.py backend/app/api/ai_training.py
git add README.md docs/GITHUB_模型与AI上传说明.md

git commit -m "chore: 上传模型代码与AI模块，排除大权重文件"
git remote add origin https://github.com/<你的用户名>/<仓库名>.git
git branch -M main
git push -u origin main
```

若已存在 `origin`，只需 `git push`。

## 4. 权重文件给协作者的方式

1. 本地运行 `python train_real_model.py` 生成 `simple_ai_model.joblib`  
2. 或使用 **GitHub Releases** 上传 `.joblib` / `.pth`，在 `models/README.md` 写明下载链接  

---

**说明**：若某路径在你本机不存在，从 `git add` 列表里删掉对应一行即可。
