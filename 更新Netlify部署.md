# 🚀 更新 Netlify 部署 - 添加图片

## ✅ 已完成的工作

1. ✅ 重命名图片文件：
   - `scene1.jpg` - 场景1：屋邨黄昏
   - `scene2.jpg` - 场景2：社区小厨房
   - `scene3.jpg` - 场景3：街坊试吃
   - `scene4.jpg` - 场景4：孩子创作
   - `scene5.jpg` - 场景5：家庭共享

2. ✅ 修改 HTML 图片路径：
   - 从 `assets/keto/scene*.jpg` 改为 `scene*.jpg`
   - 所有5个场景的图片路径已更新

## 📂 文件位置

所有文件都在：`D:\Projects\Fact-Safe-Elder\keto-quiz-deploy\`

包含：
- `keto-mom-interactive-quiz.html` (已更新)
- `scene1.jpg` 到 `scene5.jpg` (5张图片)
- `index.html`
- `vercel.json`

---

## 🌐 方法一：通过 Netlify 网页更新（最简单）

### 步骤：

1. **访问 Netlify**
   - 打开：https://app.netlify.com
   - 登录您的账号

2. **找到您的网站**
   - 在 Sites 列表中找到：`wondrous-alfajores-37b4c0`
   - 点击进入

3. **部署新版本**
   
   **方法 A - 拖拽更新（推荐）：**
   - 点击顶部的 **"Deploys"** 标签
   - 拖拽整个 `keto-quiz-deploy` 文件夹到页面上
   - 等待部署完成（约30秒）
   
   **方法 B - 手动上传：**
   - 在 Deploys 页面，找到底部的拖拽区域
   - 或点击 **"Deploy manually"**
   - 选择 `D:\Projects\Fact-Safe-Elder\keto-quiz-deploy` 文件夹
   - 上传并等待部署

4. **验证更新**
   - 部署完成后，访问：
     ```
     https://wondrous-alfajores-37b4c0.netlify.app/keto-mom-interactive-quiz.html
     ```
   - 检查每个场景是否显示图片
   - 可能需要强制刷新（Ctrl+Shift+R 或 Cmd+Shift+R）

---

## 🌐 方法二：使用 Netlify CLI（命令行）

### 步骤：

1. **安装 Netlify CLI**（如果还没安装）
   ```powershell
   npm install -g netlify-cli
   ```

2. **登录 Netlify**
   ```powershell
   cd keto-quiz-deploy
   netlify login
   ```
   - 会打开浏览器进行授权

3. **链接现有网站**
   ```powershell
   netlify link
   ```
   - 选择 `wondrous-alfajores-37b4c0` 网站

4. **部署更新**
   ```powershell
   netlify deploy --prod
   ```
   - 等待上传和部署完成

---

## 🔍 验证图片显示

部署完成后，检查以下页面：

### 场景 1 - 屋邨黄昏
```
https://wondrous-alfajores-37b4c0.netlify.app/keto-mom-interactive-quiz.html
```
滚动到场景1，应该看到屋邨街景图片

### 所有场景
- ✅ 场景 1：屋邨黄昏 → 应显示 scene1.jpg
- ✅ 场景 2：社区小厨房 → 应显示 scene2.jpg
- ✅ 场景 3：街坊试吃 → 应显示 scene3.jpg
- ✅ 场景 4：孩子创作 → 应显示 scene4.jpg
- ✅ 场景 5：家庭共享 → 应显示 scene5.jpg

---

## 🐛 如果图片不显示

### 解决方法：

1. **清除浏览器缓存**
   - Chrome/Edge: 按 `Ctrl+Shift+Delete`
   - 或使用无痕模式打开

2. **强制刷新页面**
   - Windows: `Ctrl+Shift+R`
   - Mac: `Cmd+Shift+R`

3. **检查图片文件**
   - 确认 `keto-quiz-deploy` 文件夹中有 5 个 jpg 文件
   - 文件名正确：`scene1.jpg` 到 `scene5.jpg`

4. **查看 Netlify 部署日志**
   - 在 Netlify 控制台，点击最新的 Deploy
   - 检查是否有错误信息
   - 确认所有文件都已上传

---

## 📱 更新二维码（可选）

如果您之前生成的二维码链接还是旧的，可以：

1. **重新生成二维码**
   ```powershell
   python 生成二维码.py
   ```

2. **使用在线工具**
   - 访问：https://cli.im （草料二维码）
   - 输入：`https://wondrous-alfajores-37b4c0.netlify.app/keto-mom-interactive-quiz.html`
   - 生成新的二维码

**注意**：网址没变，所以之前的二维码依然有效！

---

## 🎉 预期效果

更新成功后：
- ✅ 每个场景顶部显示对应的真实照片
- ✅ 图片会有圆角和阴影效果
- ✅ 图片上有场景标签（如"屋邨黄昏现场"）
- ✅ 用户体验更加沉浸和真实

---

## 💡 额外优化建议

### 图片压缩（加快加载速度）

如果图片文件太大，可以压缩：

1. **在线压缩工具**
   - TinyPNG: https://tinypng.com
   - Squoosh: https://squoosh.app

2. **使用脚本压缩**
   ```powershell
   # 安装 Pillow
   pip install pillow
   
   # 运行压缩脚本（如果需要我可以创建）
   ```

### 添加图片占位符

为了更好的加载体验，可以：
- 添加加载动画
- 使用模糊预览（blur placeholder）
- 延迟加载（lazy loading）

---

## 🆘 需要帮助？

如果遇到问题：

1. **Netlify 拖拽最简单**
   - 访问：https://app.netlify.com
   - 拖拽 `keto-quiz-deploy` 文件夹

2. **检查文件完整性**
   ```powershell
   cd keto-quiz-deploy
   dir
   ```
   应该看到 5 个 .jpg 文件

3. **联系我**
   - 提供截图或错误信息
   - 我可以帮您排查问题

---

## 🎯 快速操作（1分钟更新）

**最快方式**：

1. 打开：https://app.netlify.com
2. 找到您的网站
3. 点击 "Deploys"
4. 拖拽 `D:\Projects\Fact-Safe-Elder\keto-quiz-deploy` 文件夹
5. 等待 30 秒
6. 刷新网页，查看效果！

**就是这么简单！** 🎉

