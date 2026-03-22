# GitHub Releases 上传模型 + 另一台电脑下载（完整指南）

> **说明**：我无法替你在浏览器里登录 GitHub 或点「上传」。下面是你**自己操作一遍**就能完成发布的步骤；按做完后，**任意电脑**只要有权访问该仓库，都可以从 Release 页面**下载**大模型文件。

---

## 一、另一台电脑能从 GitHub 下载吗？

**可以。**

- 发布在 **Releases** 里的附件（如 `best_text_model.pt`）会生成**固定下载链接**。  
- 另一台电脑用 **浏览器** 打开 Release 页面点击下载，或用 **`curl` / `wget` / PowerShell** 下载均可。  
- **公开仓库**：任何人可下载。  
- **私有仓库**：需要登录有权限的账号，或使用带 token 的 API 链接。

---

## 二、建议上传哪些文件（AI / 模型相关）

### 必传（大权重，不能进普通 Git）

| 本机路径（示例） | Release 里建议的文件名 | 说明 |
|------------------|------------------------|------|
| `D:\Projects\Fact-Safe-Elder\best_text_model.pt` | `best_text_model.pt` | 约 400MB，PyTorch 文本大模型 |
| （可选）`D:\Projects\Fact-Safe-Elder\models\trained\simple_ai_model.joblib` | `simple_ai_model.joblib` | sklearn 管线，约 1MB，无 GPU 也可用 |
| （可选）`D:\Projects\Fact-Safe-Elder\models\trained\high_accuracy_model.joblib` | `high_accuracy_model.joblib` | 若你需要对比实验 |

**不要**把几百 MB 的文件 `git add` 进普通提交；只放在 **Release 附件**里。

### 已在仓库里的（无需再放 Release）

以下应已通过 `git push` 在 GitHub **代码**里：

- `models/bert_attention_detector.py`、`models/README.md`、`models/trained/model_metrics.json`
- `enhanced_backend.py`、`train_real_model.py`、`Colab_Training.py`、`download_real_training_data.py`
- `docs/` 下各说明文档

若还有未推送的分支，在本地执行 `git push` 即可。

---

## 三、用网页创建 Release 并上传（推荐）

1. 打开仓库：  
   **https://github.com/Ethanwithtech/Fact-Safe-Elder**  
   （若你的用户名/仓库名不同，请改成自己的。）

2. 右侧点击 **「Releases」** → **「Draft a new release」**。

3. **Choose a tag**：新建标签，例如 `v1.0.0-models` → **Create new tag**。

4. **Release title**：例如：`Model weights v1.0`（任意描述性标题）。

5. **Describe**：可写：「含 best_text_model.pt，详见仓库 docs」。

6. 在 **Attach binaries** 区域，把  
   `D:\Projects\Fact-Safe-Elder\best_text_model.pt`  
   **拖拽上传**（单文件 GitHub Release 上限约 **2GB**，你约 400MB 没问题）。

7. 可选：再上传 `simple_ai_model.joblib` 等小文件。

8. 勾选 **Set as the latest release**（若需要），点击 **Publish release**。

完成后，Release 页面会显示附件列表，每个文件都有**下载按钮** —— 这就是另一台电脑要用的入口。

---

## 四、另一台电脑如何下载并放到项目里

### 方法 A：浏览器

1. 打开同一 Release 页面。  
2. 点击 `best_text_model.pt` 下载到本机。  
3. 放到你的项目根目录，例如：  
   `你的项目\best_text_model.pt`  
   或复制为后端默认路径（见下一节）。

### 方法 B：直链（发布后才能用）

格式为：

```text
https://github.com/<用户名>/<仓库>/releases/download/<标签>/<文件名>
```

示例（请把标签和文件名改成你实际发布的）：

```text
https://github.com/Ethanwithtech/Fact-Safe-Elder/releases/download/v1.0.0-models/best_text_model.pt
```

PowerShell 下载示例：

```powershell
$url = "https://github.com/Ethanwithtech/Fact-Safe-Elder/releases/download/v1.0.0-models/best_text_model.pt"
Invoke-WebRequest -Uri $url -OutFile "best_text_model.pt"
```

### 放到哪里才能被后端加载？

当前 `enhanced_backend.py` 会按顺序查找：

1. `models/fraud_detector_final.pth`  
2. `models/trained/simple_ai_model.joblib`  
3. 都没有则用规则引擎  

因此下载 `best_text_model.pt` 后，任选其一：

- **推荐**：复制为  
  `项目根目录\models\fraud_detector_final.pth`  
  （若 checkpoint 与代码里 `BERTFraudDetector` 结构一致）；或  
- **改代码**：在 `enhanced_backend.py` 里把加载路径改为 `best_text_model.pt`（需与训练时模型类一致）。

> 若你的 `.pt` 里键名不是 `model_state_dict`，可能还要微调 `torch.load` 后取权重的语句 —— 以你训练脚本为准。

---

## 五、用 GitHub CLI（可选，适合命令行用户）

已安装 [GitHub CLI](https://cli.github.com/) 且已 `gh auth login` 时：

```powershell
cd D:\Projects\Fact-Safe-Elder
gh release create v1.0.0-models best_text_model.pt `
  --repo Ethanwithtech/Fact-Safe-Elder `
  --title "Model weights v1.0" `
  --notes "Text model + optional sklearn weights"
```

（路径、标签、仓库名按你的实际情况修改。）

---

## 六、和「完整 AI 相关」上传的对应关系

| 内容 | 放哪里 |
|------|--------|
| 代码、文档、小 JSON | **Git 仓库**（`git push`） |
| `best_text_model.pt`、`.joblib` 大文件 | **Releases 附件**（本指南） |
| 训练数据若很大 | 网盘或另开数据集仓库，README 里写链接 |

这样 **Git 仓库保持可克隆**，大文件 **按需从 Release 下载**，另一台电脑流程清晰。

---

## 七、常见问题

**Q：为什么我 `git push` 还是传不上去 `.pt`？**  
A：大文件应走 **Release**，不要强行加入 Git 历史；或用 **Git LFS**（需单独配置）。

**Q：私有仓库别人能下吗？**  
A：只有被邀请的协作者登录后可下；或生成带 `token` 的链接（注意安全）。

**Q：你能帮我验证 Release 是否成功吗？**  
A：我无法登录你的 GitHub。请你打开 Release 页面，确认附件存在；或用上面的直链在浏览器试下载。

---

维护：若 Release 标签或文件名变更，请同步更新仓库根目录 `README.md` 中的下载说明。
