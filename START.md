# 🚀 Fact-Safe-Elder 启动指南

## 快速启动

### 方法1：自动启动（推荐）

#### Windows PowerShell:
```powershell
# 启动后端
Start-Process powershell -ArgumentList "cd backend; python -m app.main"

# 启动前端
Start-Process powershell -ArgumentList "cd frontend; npm start"
```

### 方法2：手动启动

#### 终端1 - 后端服务
```bash
cd backend
python -m app.main
```
访问：http://localhost:8000

#### 终端2 - 前端服务
```bash
cd frontend
npm start
```
访问：http://localhost:3000

## 📊 服务状态

### ✅ 后端服务
- 地址：http://localhost:8000
- API文档：http://localhost:8000/docs
- 状态：运行中

### ✅ 前端服务
- 地址：http://localhost:3000
- 状态：运行中

## 🎨 界面说明

### 黑白蓝主题
- **黑色背景** - 更护眼
- **白色文字** - 更清晰
- **蓝色高亮** - 更明显
- **霓虹发光** - 更炫酷

### 布局
```
┌──────────────────────────────────┐
│         页面顶部标题              │
├──────────────┬───────────────────┤
│              │                   │
│  手机模拟器   │   视频上传检测     │
│    (左侧)    │   模型训练面板     │
│              │     (右侧)        │
│              │                   │
└──────────────┴───────────────────┘
```

## 🛠️ 功能说明

### 1. 手机模拟器（左侧）
- 模拟真实短视频场景
- 交互式演示
- 实时风险提示

### 2. 视频检测（右侧上方）
- 上传视频文件
- AI自动检测
- 显示风险等级和建议

### 3. 模型训练（右侧下方）
- 查看训练进度
- 模型性能指标
- 数据集统计

## 📝 常见问题

### Q: 前端页面看不清？
A: 已修复！现在是黑白蓝主题，文字都是白色

### Q: 后端报错？
A: 已修复！pydantic和TensorFlow错误都已解决

### Q: 模型训练失败？
A: 使用 `train_real_models_fixed.py` 代替旧版本

## 🎯 下一步

1. 打开浏览器访问：http://localhost:3000
2. 查看左侧手机模拟器
3. 在右侧上传视频进行检测
4. 在右侧查看模型训练状态

---
**享受你的防诈骗系统吧！** 🎉






