# 🚀 AI守护系统 - 完整部署与使用指南

## 📋 目录
1. [系统概述](#系统概述)
2. [环境要求](#环境要求)
3. [快速部署](#快速部署)
4. [AI模型配置](#ai模型配置)
5. [使用说明](#使用说明)
6. [高级功能](#高级功能)
7. [常见问题](#常见问题)

---

## 🎯 系统概述

**AI守护** 是一个专为老年人设计的短视频虚假信息实时检测系统，集成了最新的大语言模型技术。

### 核心功能

#### 🤖 AI检测能力
- **ChatGLM-6B**: 中文语言理解和对话生成
- **BERT-Chinese**: 文本分类和特征提取
- **LLaMA-7B**: 多语言理解和推理
- **多模态融合**: 文本、音频、视频综合分析

#### 📱 用户界面
- **手机视频模拟器**: 1:1还原抖音界面
- **智能检测浮窗**: 实时风险提示
- **适老化设计**: 大字体、高对比度、语音提示

#### 🎓 模型训练平台
- **数据集管理**: MCFEND、微博等多源数据
- **在线训练**: LoRA微调、分布式训练
- **性能监控**: 实时训练进度、指标可视化

---

## 💻 环境要求

### 最低配置
```yaml
CPU: 8核心以上
内存: 16GB RAM
显卡: NVIDIA GTX 1060 (6GB) 或更高
存储: 100GB可用空间
系统: Windows 10/11, Ubuntu 20.04+, macOS 11+
```

### 推荐配置
```yaml
CPU: 16核心
内存: 32GB RAM
显卡: NVIDIA RTX 3080 (10GB) 或 A100
存储: 500GB SSD
网络: 100Mbps稳定连接
```

### 软件依赖
```yaml
Docker: 20.10+
Docker Compose: 2.0+
Node.js: 18+
Python: 3.9+
CUDA: 11.8+ (如使用GPU)
Git: 2.0+
```

---

## ⚡ 快速部署

### 1️⃣ 获取代码
```bash
# 克隆仓库
git clone https://github.com/your-org/fact-safe-elder.git
cd fact-safe-elder

# 切换到AI版本分支
git checkout ai-integration
```

### 2️⃣ 配置环境变量
```bash
# 复制环境配置模板
cp .env.example .env

# 编辑配置文件
nano .env
```

配置示例：
```env
# API配置
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_PORT=3000

# AI模型配置
USE_GPU=true
MODEL_CACHE_DIR=./models
DEVICE=cuda  # 或 cpu

# 数据库配置
DATABASE_URL=postgresql://user:pass@localhost/elderguard
REDIS_URL=redis://localhost:6379

# 安全配置
SECRET_KEY=your-secret-key-here
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### 3️⃣ 一键部署

#### Docker方式（推荐）
```bash
# 构建并启动所有服务
docker-compose up --build -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

#### 本地开发方式
```bash
# 安装前端依赖
cd frontend
npm install

# 安装后端依赖
cd ../backend
pip install -r requirements.txt

# 下载AI模型
python scripts/download_models.py

# 启动服务
# 终端1 - 启动后端
python -m uvicorn app.main:app --reload

# 终端2 - 启动前端
cd frontend && npm start
```

### 4️⃣ 验证部署
```bash
# 检查服务健康状态
curl http://localhost:8000/api/health

# 访问前端界面
open http://localhost:3000

# 测试AI接口
curl -X POST http://localhost:8000/api/ai/status
```

---

## 🧠 AI模型配置

### 下载预训练模型

#### 自动下载
```bash
python scripts/download_models.py --all
```

#### 手动下载
```bash
# ChatGLM-6B
git lfs clone https://huggingface.co/THUDM/chatglm-6b

# Chinese-BERT
git lfs clone https://huggingface.co/hfl/chinese-bert-wwm-ext

# LLaMA-7B-Chinese
git lfs clone https://huggingface.co/ziqingyang/chinese-llama-7b
```

### 模型微调

#### 准备数据集
```bash
# 下载MCFEND数据集
python scripts/download_dataset.py --name mcfend

# 预处理数据
python scripts/preprocess_data.py \
  --dataset mcfend \
  --output ./data/processed/
```

#### 启动训练
```bash
# 使用LoRA微调ChatGLM
python train.py \
  --model_type chatglm \
  --dataset mcfend_v1 \
  --epochs 10 \
  --batch_size 8 \
  --learning_rate 5e-5 \
  --use_lora \
  --lora_rank 8
```

#### 监控训练
访问 http://localhost:3000 -> 模型训练 -> 查看实时进度

---

## 📱 使用说明

### 基础操作

#### 1. 手机视频模拟
1. 打开系统首页
2. 点击"📱 手机模拟"标签
3. 上下滑动切换视频
4. 观察右侧AI检测结果

#### 2. 风险等级说明
- 🟢 **绿色（安全）**: 内容可信，可以正常观看
- 🟡 **黄色（警告）**: 存在风险，需谨慎对待
- 🔴 **红色（危险）**: 高风险内容，建议立即停止

#### 3. 家人通知设置
1. 点击"⚙️ 设置"
2. 输入家人联系方式
3. 设置通知阈值
4. 保存配置

### 高级功能

#### 模型训练
1. 进入"🎓 模型训练"页面
2. 点击"开始新训练"
3. 选择模型和数据集
4. 配置训练参数
5. 点击"开始训练"
6. 实时监控训练进度

#### 数据集管理
1. 进入"💾 数据集"标签
2. 上传自定义数据集
3. 执行数据预处理
4. 应用数据增强

#### 模型部署
1. 训练完成后点击"部署"
2. 选择部署环境
3. 配置推理参数
4. 一键部署到生产

---

## 🔧 高级配置

### GPU加速设置

#### NVIDIA GPU
```bash
# 安装CUDA
wget https://developer.download.nvidia.com/compute/cuda/11.8.0/local_installers/cuda_11.8.0_520.61.05_linux.run
sudo sh cuda_11.8.0_520.61.05_linux.run

# 配置环境变量
export CUDA_HOME=/usr/local/cuda-11.8
export PATH=$CUDA_HOME/bin:$PATH
export LD_LIBRARY_PATH=$CUDA_HOME/lib64:$LD_LIBRARY_PATH

# 验证安装
nvidia-smi
nvcc --version
```

#### AMD GPU（ROCm）
```bash
# 安装ROCm
wget https://repo.radeon.com/amdgpu-install/latest/ubuntu/focal/amdgpu-install.deb
sudo apt install ./amdgpu-install.deb
sudo amdgpu-install --usecase=rocm

# 安装PyTorch for ROCm
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/rocm5.6
```

### 性能优化

#### 模型量化
```python
# INT8量化加速推理
python scripts/quantize_model.py \
  --model chatglm \
  --quantization int8 \
  --output ./models/chatglm_int8
```

#### 批处理优化
```yaml
# config/inference.yaml
batch_size: 16
max_sequence_length: 512
num_workers: 4
use_mixed_precision: true
```

#### 缓存配置
```python
# 配置Redis缓存
CACHE_CONFIG = {
    'host': 'localhost',
    'port': 6379,
    'db': 0,
    'ttl': 3600,  # 1小时
    'max_connections': 50
}
```

---

## ❓ 常见问题

### Q1: 模型加载失败
```bash
# 错误: CUDA out of memory
解决方案:
1. 减小batch_size
2. 使用模型量化
3. 启用gradient checkpointing
4. 使用CPU推理模式
```

### Q2: 训练速度慢
```bash
解决方案:
1. 启用混合精度训练
2. 使用分布式训练
3. 调整学习率调度器
4. 优化数据加载pipeline
```

### Q3: 检测准确率低
```bash
解决方案:
1. 增加训练数据
2. 调整模型超参数
3. 使用数据增强
4. 集成多个模型
```

### Q4: Docker容器无法启动
```bash
# 检查Docker状态
sudo systemctl status docker

# 清理旧容器
docker system prune -a

# 重新构建
docker-compose build --no-cache
docker-compose up -d
```

### Q5: 前端页面加载慢
```bash
解决方案:
1. 启用生产模式构建
npm run build

2. 配置Nginx缓存
3. 使用CDN加速
4. 开启gzip压缩
```

---

## 📞 技术支持

### 获取帮助
- 📧 邮箱: support@elderguard.ai
- 💬 微信群: 扫码加入技术交流群
- 📖 文档: https://docs.elderguard.ai
- 🐛 提交问题: https://github.com/your-org/fact-safe-elder/issues

### 社区资源
- [模型下载镜像站](https://mirror.elderguard.ai)
- [数据集共享平台](https://data.elderguard.ai)
- [在线Demo演示](https://demo.elderguard.ai)
- [视频教程](https://video.elderguard.ai)

### 贡献指南
欢迎贡献代码、文档、数据集！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)

---

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

---

## 🙏 致谢

感谢以下开源项目和研究机构：
- THUDM (ChatGLM)
- Hugging Face (Transformers)
- Meta AI (LLaMA)
- 香港浸会大学 (MCFEND数据集)
- 所有贡献者和测试用户

---

**让AI守护每一位长辈的网络安全！** 🛡️👴👵
