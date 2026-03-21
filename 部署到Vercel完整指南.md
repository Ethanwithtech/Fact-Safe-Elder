# 🚀 部署到 Vercel - 完整指南

## 方法一：通过 Vercel 网页部署（推荐，最简单）⭐⭐⭐⭐⭐

### 步骤 1：准备文件

创建一个单独的文件夹，只包含需要的文件：

1. 在桌面或任意位置创建文件夹：`keto-quiz`
2. 复制以下文件到该文件夹：
   - `keto-mom-interactive-quiz.html`
   - `vercel.json`（已创建）

### 步骤 2：注册/登录 Vercel

1. 访问：https://vercel.com
2. 点击右上角 **"Sign Up"** 或 **"Login"**
3. 选择用以下方式登录：
   - GitHub（推荐）
   - GitLab
   - Bitbucket
   - 或邮箱注册

### 步骤 3：创建新项目

1. 登录后，点击 **"Add New..."** → **"Project"**
2. 选择 **"Import Third-Party Git Repository"** 或直接拖拽文件

### 步骤 4：部署

**方法 A - 拖拽部署（最简单）：**

1. 在 Vercel 控制台，找到项目导入界面
2. 直接将 `keto-quiz` 文件夹拖到浏览器窗口
3. Vercel 会自动上传和部署

**方法 B - 通过 Git（更专业）：**

1. 先将代码推送到 GitHub
2. 在 Vercel 中连接 GitHub 仓库
3. 选择仓库并部署

### 步骤 5：获取网址

部署完成后，Vercel 会自动生成一个网址，格式类似：
- `https://your-project-name.vercel.app`
- 或自定义域名

---

## 方法二：使用 Vercel CLI 部署（命令行）

### 前提：
- ✅ Vercel CLI 已安装（已完成）

### 步骤：

1. **登录 Vercel**
   ```powershell
   vercel login
   ```
   会打开浏览器让您登录

2. **首次部署**
   ```powershell
   vercel
   ```
   按提示操作：
   - Set up and deploy? → 选择 **Y**
   - Which scope? → 选择您的账号
   - Link to existing project? → 选择 **N**
   - Project name? → 输入项目名（如 `keto-quiz`）
   - In which directory? → 直接回车（当前目录）
   - Override settings? → 选择 **N**

3. **部署到生产环境**
   ```powershell
   vercel --prod
   ```

---

## 方法三：使用 GitHub Pages（备选）

如果您更熟悉 GitHub：

### 步骤：

1. **创建 GitHub 仓库**
   - 访问 https://github.com/new
   - 创建新仓库（如 `keto-quiz`）

2. **推送代码**
   ```powershell
   git init
   git add keto-mom-interactive-quiz.html
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/你的用户名/keto-quiz.git
   git push -u origin main
   ```

3. **启用 GitHub Pages**
   - 进入仓库设置（Settings）
   - 找到 "Pages" 选项
   - Source 选择 "main" 分支
   - 保存

4. **访问网站**
   - 网址：`https://你的用户名.github.io/keto-quiz/keto-mom-interactive-quiz.html`

---

## 方法四：使用 Netlify（备选）

### 步骤：

1. 访问：https://www.netlify.com
2. 注册/登录
3. 点击 **"Add new site"** → **"Deploy manually"**
4. 拖拽包含 HTML 文件的文件夹
5. 自动部署，获得网址

---

## 🎯 推荐方案对比

| 平台 | 难度 | 速度 | 自定义域名 | 推荐度 |
|------|------|------|------------|--------|
| **Vercel** | ⭐⭐ | ⚡⚡⚡ | ✅ 免费 | ⭐⭐⭐⭐⭐ |
| **Netlify** | ⭐ | ⚡⚡⚡ | ✅ 免费 | ⭐⭐⭐⭐⭐ |
| **GitHub Pages** | ⭐⭐⭐ | ⚡⚡ | ✅ 免费 | ⭐⭐⭐⭐ |

---

## 📝 需要帮助？

如果您想要：
1. **我帮您完成 Vercel CLI 部署** - 回复 "vercel cli"
2. **我教您 GitHub Pages 部署** - 回复 "github"
3. **我教您 Netlify 拖拽部署** - 回复 "netlify"

---

## ✅ 部署后的优势

- 🌐 **全球访问**：任何人都可以通过链接访问
- 📱 **移动友好**：手机、平板完美适配
- ⚡ **超快速度**：全球 CDN 加速
- 🔒 **HTTPS 安全**：自动配置 SSL 证书
- 💰 **完全免费**：无需信用卡

---

## 🎉 预期结果

部署成功后，您会得到类似这样的链接：
- `https://keto-quiz.vercel.app`
- `https://keto-quiz.netlify.app`
- `https://yourusername.github.io/keto-quiz/`

**分享这个链接，任何人都可以访问您的问卷！**

