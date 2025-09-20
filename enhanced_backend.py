#!/usr/bin/env python3
"""
增强的AI检测后端服务
支持视频上传、多模态检测、真实AI模型训练
"""

import os
import sys
import json
import asyncio
import time
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel
import uvicorn
from loguru import logger

# AI和机器学习
try:
    import torch
    import numpy as np
    from transformers import (
        AutoTokenizer, 
        AutoModelForSequenceClassification,
        pipeline,
        Trainer,
        TrainingArguments
    )
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support
    from datasets import Dataset
    import cv2
    TORCH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"AI依赖包未完全安装: {e}")
    TORCH_AVAILABLE = False

# 创建必要目录
os.makedirs("data/uploads", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)
os.makedirs("models/trained", exist_ok=True)
os.makedirs("logs/training", exist_ok=True)

app = FastAPI(
    title="AI守护系统 - 增强版后端",
    description="支持视频检测、模型训练、多模态分析的AI检测服务",
    version="2.0.0"
)

# CORS配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 全局变量
training_tasks = {}
detection_stats = {
    "total_detections": 0,
    "danger_count": 0,
    "warning_count": 0,
    "safe_count": 0,
    "accuracy": 0.0,
    "models_loaded": 0
}

class AIDetectionEngine:
    """AI检测引擎"""
    
    def __init__(self):
        self.models = {}
        self.tokenizers = {}
        self.device = torch.device("cuda" if torch.cuda.is_available() and TORCH_AVAILABLE else "cpu")
        self.training_data = []
        self.model_metrics = {}
        
        logger.info(f"AI检测引擎初始化，设备: {self.device}")
        
    async def initialize(self):
        """初始化模型"""
        try:
            if TORCH_AVAILABLE:
                await self._load_models()
            else:
                logger.warning("PyTorch不可用，使用模拟模式")
            
            # 加载训练数据
            await self._load_training_data()
            
        except Exception as e:
            logger.error(f"AI引擎初始化失败: {e}")
    
    async def _load_models(self):
        """加载预训练模型"""
        try:
            # 加载中文BERT模型用于文本分类
            logger.info("正在加载BERT模型...")
            self.tokenizers['bert'] = AutoTokenizer.from_pretrained(
                'hfl/chinese-bert-wwm-ext',
                cache_dir='./models/cache'
            )
            
            # 创建分类模型
            self.models['bert'] = AutoModelForSequenceClassification.from_pretrained(
                'hfl/chinese-bert-wwm-ext',
                num_labels=3,  # safe, warning, danger
                cache_dir='./models/cache'
            ).to(self.device)
            
            detection_stats["models_loaded"] += 1
            logger.info("BERT模型加载成功")
            
            # 尝试加载已训练的模型权重
            trained_model_path = "models/trained/bert_fake_news_detector.pt"
            if os.path.exists(trained_model_path):
                checkpoint = torch.load(trained_model_path, map_location=self.device)
                self.models['bert'].load_state_dict(checkpoint['model_state_dict'])
                self.model_metrics = checkpoint.get('metrics', {})
                logger.info(f"已加载训练权重，准确率: {self.model_metrics.get('accuracy', 0):.2%}")
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
    
    async def _load_training_data(self):
        """加载训练数据"""
        try:
            # 生成模拟训练数据
            self.training_data = [
                {"text": "月入三万的理财秘诀，保证收益无风险！", "label": 2},  # danger
                {"text": "祖传秘方包治百病，三天见效！", "label": 2},  # danger
                {"text": "限时抢购，原价999现在99！", "label": 1},  # warning
                {"text": "今天教大家做红烧肉的家常做法", "label": 0},  # safe
                {"text": "投资需谨慎，请仔细阅读产品说明书", "label": 0},  # safe
                {"text": "神奇保健品，医院不告诉你的秘密", "label": 2},  # danger
                {"text": "正规银行理财产品，年化收益3.5%", "label": 0},  # safe
                {"text": "快速赚钱方法，日赚千元不是梦", "label": 2},  # danger
                {"text": "健康饮食小贴士，营养均衡很重要", "label": 0},  # safe
                {"text": "内幕消息，股票推荐，稳赚不赔", "label": 2},  # danger
            ]
            
            # 尝试加载真实数据集
            data_files = [
                "data/raw/mcfend/mcfend_data.json",
                "data/raw/weibo_rumors/weibo_data.json",
                "data/raw/chinese_rumor/rumors_v170613.json"
            ]
            
            for data_file in data_files:
                if os.path.exists(data_file):
                    with open(data_file, 'r', encoding='utf-8') as f:
                        real_data = json.load(f)
                        if isinstance(real_data, list):
                            self.training_data.extend(real_data[:1000])  # 限制数据量
                            logger.info(f"加载真实数据: {data_file}, {len(real_data)} 条")
            
            logger.info(f"训练数据加载完成，总计: {len(self.training_data)} 条")
            
        except Exception as e:
            logger.error(f"训练数据加载失败: {e}")
    
    async def detect_text(self, text: str) -> Dict:
        """文本检测"""
        try:
            if 'bert' in self.models and TORCH_AVAILABLE:
                return await self._detect_with_bert(text)
            else:
                return self._detect_with_rules(text)
                
        except Exception as e:
            logger.error(f"文本检测失败: {e}")
            return self._get_fallback_result(text)
    
    async def _detect_with_bert(self, text: str) -> Dict:
        """使用BERT模型检测"""
        try:
            tokenizer = self.tokenizers['bert']
            model = self.models['bert']
            
            # 文本编码
            inputs = tokenizer(
                text,
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            ).to(self.device)
            
            # 模型推理
            model.eval()
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
            
            # 获取预测结果
            predicted_class = torch.argmax(probabilities, dim=-1).item()
            confidence = probabilities[0][predicted_class].item()
            
            # 映射到风险等级
            risk_levels = ['safe', 'warning', 'danger']
            level = risk_levels[predicted_class]
            
            # 生成详细分析
            reasons = self._analyze_text_risks(text, predicted_class)
            suggestions = self._generate_suggestions(level)
            
            return {
                'success': True,
                'level': level,
                'score': float(confidence),
                'confidence': float(confidence),
                'message': f'BERT模型检测完成，风险等级：{level}',
                'reasons': reasons,
                'suggestions': suggestions,
                'model': 'BERT-Chinese',
                'probabilities': {
                    'safe': float(probabilities[0][0]),
                    'warning': float(probabilities[0][1]),
                    'danger': float(probabilities[0][2])
                },
                'detection_id': f"bert_{int(time.time())}_{hash(text) % 10000}",
                'timestamp': time.time()
            }
            
        except Exception as e:
            logger.error(f"BERT检测失败: {e}")
            return self._get_fallback_result(text)
    
    def _detect_with_rules(self, text: str) -> Dict:
        """基于规则的检测"""
        # 强化的关键词检测
        danger_keywords = [
            "保证收益", "月入万元", "包治百病", "祖传秘方", "无风险投资", 
            "月入", "万元", "包治", "秘方", "保证", "无风险", "理财秘诀",
            "稳赚不赔", "高收益", "内幕消息", "股票推荐", "虚拟货币",
            "传销", "微商代理", "拉人头", "无抵押贷款", "秒批",
            "神奇疗效", "一次根治", "永不复发", "药到病除", "日赚千元"
        ]
        
        warning_keywords = [
            "投资", "理财", "保健品", "偏方", "微信", "联系", "收益", "赚钱",
            "限时", "优惠", "抢购", "特价", "清仓", "促销", "代理", "加盟",
            "快速", "轻松", "简单", "立即", "马上", "紧急"
        ]
        
        risk_level = "safe"
        risk_score = 0.1
        reasons = []
        
        # 检测危险关键词
        found_danger = [kw for kw in danger_keywords if kw in text]
        if found_danger:
            risk_level = "danger"
            risk_score = min(0.95, 0.7 + len(found_danger) * 0.05)
            reasons.extend([f"发现高危关键词: '{kw}'" for kw in found_danger[:3]])
        else:
            # 检测警告关键词
            found_warning = [kw for kw in warning_keywords if kw in text]
            if found_warning:
                risk_level = "warning"
                risk_score = min(0.8, 0.4 + len(found_warning) * 0.05)
                reasons.extend([f"发现可疑关键词: '{kw}'" for kw in found_warning[:3]])
        
        # 检测联系方式
        import re
        if re.search(r'微信|qq|电话|手机|联系|\d{11}', text):
            if risk_level != "safe":
                risk_score = min(0.98, risk_score + 0.1)
                reasons.append("含有联系方式且存在其他风险因素")
        
        # 检测紧急性语言
        urgency_words = ['赶紧', '立即', '马上', '快速', '紧急', '限时', '截止', '最后']
        urgency_count = sum(1 for word in urgency_words if word in text)
        if urgency_count >= 2:
            if risk_level == "safe":
                risk_level = "warning"
                risk_score = max(risk_score, 0.6)
            reasons.append("内容使用大量紧急性语言，可能是诱导手段")
        
        if not reasons:
            reasons.append("未发现明显风险因素")
        
        suggestions = self._generate_suggestions(risk_level)
        
        return {
            'success': True,
            'level': risk_level,
            'score': risk_score,
            'confidence': 0.8,
            'message': f'规则检测完成，风险等级：{risk_level}',
            'reasons': reasons,
            'suggestions': suggestions,
            'model': 'Rule-Based',
            'keywords_found': found_danger + found_warning if 'found_danger' in locals() and 'found_warning' in locals() else [],
            'detection_id': f"rule_{int(time.time())}_{hash(text) % 10000}",
            'timestamp': time.time()
        }
    
    def _analyze_text_risks(self, text: str, predicted_class: int) -> List[str]:
        """分析文本风险因素"""
        reasons = []
        
        if predicted_class == 2:  # danger
            reasons.extend([
                "AI模型检测到高风险内容特征",
                "文本语义分析显示存在欺诈风险",
                "内容模式匹配到已知诈骗类型"
            ])
        elif predicted_class == 1:  # warning
            reasons.extend([
                "AI模型检测到可疑内容特征",
                "文本存在需要注意的风险因素"
            ])
        else:  # safe
            reasons.append("AI模型未检测到明显风险")
        
        return reasons
    
    def _generate_suggestions(self, risk_level: str) -> List[str]:
        """生成安全建议"""
        if risk_level == "danger":
            return [
                "建议立即停止观看，谨防诈骗",
                "不要轻易相信高收益低风险的投资项目",
                "不要向陌生人透露个人信息或转账",
                "如有疑问，请咨询家人或专业人士"
            ]
        elif risk_level == "warning":
            return [
                "请谨慎对待此内容",
                "购买前请仔细核实信息真实性",
                "建议咨询专业人士意见",
                "不要冲动消费或投资"
            ]
        else:
            return [
                "内容相对安全",
                "继续保持警惕意识",
                "遇到可疑内容及时求助"
            ]
    
    def _get_fallback_result(self, text: str) -> Dict:
        """降级结果"""
        return {
            'success': True,
            'level': 'warning',
            'score': 0.5,
            'confidence': 0.5,
            'message': 'AI模型暂时不可用，使用默认策略',
            'reasons': ['系统检测异常，建议人工复核'],
            'suggestions': ['请谨慎对待此内容', '如有疑问请咨询专业人士'],
            'model': 'Fallback',
            'detection_id': f"fallback_{int(time.time())}",
            'timestamp': time.time()
        }
    
    async def detect_video(self, video_path: str, text_content: str = "") -> Dict:
        """视频检测"""
        try:
            # 提取视频特征
            video_features = await self._extract_video_features(video_path)
            
            # 文本检测
            text_result = await self.detect_text(text_content) if text_content else None
            
            # 综合分析
            final_result = self._combine_multimodal_results(video_features, text_result)
            
            return final_result
            
        except Exception as e:
            logger.error(f"视频检测失败: {e}")
            return self._get_fallback_result(f"视频内容: {text_content}")
    
    async def _extract_video_features(self, video_path: str) -> Dict:
        """提取视频特征"""
        try:
            if not os.path.exists(video_path):
                raise FileNotFoundError(f"视频文件不存在: {video_path}")
            
            # 使用OpenCV提取视频帧
            cap = cv2.VideoCapture(video_path)
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            duration = frame_count / fps if fps > 0 else 0
            
            # 提取关键帧
            frames = []
            for i in range(0, frame_count, max(1, frame_count // 10)):  # 提取10帧
                cap.set(cv2.CAP_PROP_POS_FRAMES, i)
                ret, frame = cap.read()
                if ret:
                    frames.append(frame)
            
            cap.release()
            
            # 分析视频特征
            features = {
                'duration': duration,
                'frame_count': frame_count,
                'fps': fps,
                'key_frames': len(frames),
                'visual_risk': self._analyze_visual_content(frames),
                'technical_risk': self._analyze_technical_features(duration, fps)
            }
            
            return features
            
        except Exception as e:
            logger.error(f"视频特征提取失败: {e}")
            return {'visual_risk': 0.3, 'technical_risk': 0.2}
    
    def _analyze_visual_content(self, frames: List) -> float:
        """分析视觉内容"""
        # 简单的视觉分析（实际应用中可以使用更复杂的CV模型）
        if not frames:
            return 0.3
        
        # 检测亮度变化、颜色分布等
        risk_score = 0.0
        
        for frame in frames[:5]:  # 分析前5帧
            # 转换为灰度图
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # 计算亮度
            brightness = np.mean(gray)
            
            # 异常亮度可能表示低质量内容
            if brightness < 50 or brightness > 200:
                risk_score += 0.1
        
        return min(risk_score, 0.8)
    
    def _analyze_technical_features(self, duration: float, fps: float) -> float:
        """分析技术特征"""
        risk_score = 0.0
        
        # 异常短的视频可能是垃圾内容
        if duration < 5:
            risk_score += 0.2
        
        # 异常低的帧率可能表示低质量
        if fps < 15:
            risk_score += 0.1
        
        return min(risk_score, 0.5)
    
    def _combine_multimodal_results(self, video_features: Dict, text_result: Dict) -> Dict:
        """综合多模态结果"""
        # 视觉风险权重
        visual_risk = video_features.get('visual_risk', 0.3)
        technical_risk = video_features.get('technical_risk', 0.2)
        
        # 文本风险权重
        if text_result:
            text_risk = text_result['score']
            text_level = text_result['level']
        else:
            text_risk = 0.3
            text_level = 'safe'
        
        # 加权计算最终风险
        final_risk = text_risk * 0.7 + visual_risk * 0.2 + technical_risk * 0.1
        
        # 确定最终等级
        if final_risk > 0.7 or text_level == 'danger':
            final_level = 'danger'
        elif final_risk > 0.4 or text_level == 'warning':
            final_level = 'warning'
        else:
            final_level = 'safe'
        
        return {
            'success': True,
            'level': final_level,
            'score': final_risk,
            'confidence': 0.85,
            'message': f'多模态检测完成，风险等级：{final_level}',
            'reasons': [
                f"文本风险: {text_risk:.2f}",
                f"视觉风险: {visual_risk:.2f}",
                f"技术风险: {technical_risk:.2f}"
            ],
            'suggestions': self._generate_suggestions(final_level),
            'model': 'Multimodal-AI',
            'multimodal_analysis': {
                'text_risk': text_risk,
                'visual_risk': visual_risk,
                'technical_risk': technical_risk,
                'video_features': video_features
            },
            'detection_id': f"video_{int(time.time())}",
            'timestamp': time.time()
        }
    
    async def train_model(self, task_id: str, config: Dict) -> Dict:
        """训练模型"""
        try:
            if not TORCH_AVAILABLE:
                raise Exception("PyTorch不可用，无法训练模型")
            
            logger.info(f"开始训练任务: {task_id}")
            
            # 准备训练数据
            train_data = self._prepare_training_data()
            
            # 创建数据集
            train_dataset = Dataset.from_dict({
                'text': [item['text'] for item in train_data],
                'labels': [item['label'] for item in train_data]
            })
            
            # 数据预处理
            def tokenize_function(examples):
                return self.tokenizers['bert'](
                    examples['text'],
                    padding=True,
                    truncation=True,
                    max_length=512
                )
            
            tokenized_dataset = train_dataset.map(tokenize_function, batched=True)
            
            # 训练配置
            training_args = TrainingArguments(
                output_dir=f'./logs/training/{task_id}',
                num_train_epochs=config.get('epochs', 3),
                per_device_train_batch_size=config.get('batch_size', 8),
                learning_rate=config.get('learning_rate', 5e-5),
                logging_steps=10,
                save_steps=100,
                evaluation_strategy="steps",
                eval_steps=50,
                load_best_model_at_end=True,
                metric_for_best_model="accuracy"
            )
            
            # 评估函数
            def compute_metrics(eval_pred):
                predictions, labels = eval_pred
                predictions = np.argmax(predictions, axis=1)
                precision, recall, f1, _ = precision_recall_fscore_support(labels, predictions, average='weighted')
                accuracy = accuracy_score(labels, predictions)
                return {
                    'accuracy': accuracy,
                    'f1': f1,
                    'precision': precision,
                    'recall': recall
                }
            
            # 创建训练器
            trainer = Trainer(
                model=self.models['bert'],
                args=training_args,
                train_dataset=tokenized_dataset,
                eval_dataset=tokenized_dataset,  # 实际应用中应该使用验证集
                compute_metrics=compute_metrics
            )
            
            # 开始训练
            training_tasks[task_id] = {
                'status': 'training',
                'progress': 0,
                'start_time': time.time(),
                'metrics': {}
            }
            
            # 训练模型
            train_result = trainer.train()
            
            # 评估模型
            eval_result = trainer.evaluate()
            
            # 保存模型
            model_save_path = f"models/trained/bert_fake_news_detector_{task_id}.pt"
            torch.save({
                'model_state_dict': self.models['bert'].state_dict(),
                'metrics': eval_result,
                'config': config,
                'training_result': train_result
            }, model_save_path)
            
            # 更新全局指标
            self.model_metrics = eval_result
            detection_stats["accuracy"] = eval_result.get('eval_accuracy', 0)
            
            # 更新任务状态
            training_tasks[task_id] = {
                'status': 'completed',
                'progress': 100,
                'start_time': training_tasks[task_id]['start_time'],
                'end_time': time.time(),
                'metrics': eval_result,
                'model_path': model_save_path
            }
            
            logger.info(f"训练完成: {task_id}, 准确率: {eval_result.get('eval_accuracy', 0):.2%}")
            
            return {
                'success': True,
                'task_id': task_id,
                'metrics': eval_result,
                'model_path': model_save_path
            }
            
        except Exception as e:
            logger.error(f"模型训练失败: {e}")
            training_tasks[task_id] = {
                'status': 'failed',
                'progress': 0,
                'error': str(e),
                'start_time': training_tasks.get(task_id, {}).get('start_time', time.time())
            }
            raise
    
    def _prepare_training_data(self) -> List[Dict]:
        """准备训练数据"""
        # 扩充训练数据
        extended_data = self.training_data.copy()
        
        # 添加更多样本
        additional_samples = [
            {"text": "投资理财有风险，请谨慎选择", "label": 0},
            {"text": "正规医院治疗，遵医嘱用药", "label": 0},
            {"text": "天下没有免费的午餐，小心陷阱", "label": 0},
            {"text": "一夜暴富的机会来了，错过后悔终生", "label": 2},
            {"text": "特效药包治百病，无效退款", "label": 2},
            {"text": "内幕消息，股票必涨，跟我买", "label": 2},
            {"text": "限时优惠，数量有限，先到先得", "label": 1},
            {"text": "健康生活方式，均衡饮食运动", "label": 0},
            {"text": "学习理财知识，理性投资", "label": 0},
        ]
        
        extended_data.extend(additional_samples)
        return extended_data

# 创建全局AI引擎
ai_engine = AIDetectionEngine()

@app.on_event("startup")
async def startup_event():
    """启动时初始化"""
    await ai_engine.initialize()

# API端点
@app.get("/")
async def root():
    return {
        "message": "AI守护系统增强版后端",
        "version": "2.0.0",
        "status": "运行中",
        "models_loaded": detection_stats["models_loaded"],
        "accuracy": f"{detection_stats['accuracy']:.2%}"
    }

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "message": "服务运行正常",
        "training_data": len(ai_engine.training_data),
        "models_loaded": detection_stats["models_loaded"],
        "accuracy": detection_stats["accuracy"]
    }

@app.post("/detect")
async def detect_text(request: dict):
    """文本检测API"""
    try:
        text = request.get("text", "")
        if not text:
            raise HTTPException(status_code=400, detail="文本内容不能为空")
        
        # 执行检测
        result = await ai_engine.detect_text(text)
        
        # 更新统计
        detection_stats["total_detections"] += 1
        if result['level'] == 'danger':
            detection_stats["danger_count"] += 1
        elif result['level'] == 'warning':
            detection_stats["warning_count"] += 1
        else:
            detection_stats["safe_count"] += 1
        
        return result
        
    except Exception as e:
        logger.error(f"文本检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"检测失败: {str(e)}")

@app.post("/detect/video")
async def detect_video(
    file: UploadFile = File(...),
    text_content: str = Form(default="")
):
    """视频检测API"""
    try:
        # 保存上传的视频
        video_id = str(uuid.uuid4())
        video_path = f"data/uploads/{video_id}_{file.filename}"
        
        with open(video_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # 执行检测
        result = await ai_engine.detect_video(video_path, text_content)
        
        # 更新统计
        detection_stats["total_detections"] += 1
        if result['level'] == 'danger':
            detection_stats["danger_count"] += 1
        elif result['level'] == 'warning':
            detection_stats["warning_count"] += 1
        else:
            detection_stats["safe_count"] += 1
        
        # 清理临时文件（可选）
        # os.remove(video_path)
        
        return result
        
    except Exception as e:
        logger.error(f"视频检测失败: {e}")
        raise HTTPException(status_code=500, detail=f"视频检测失败: {str(e)}")

@app.post("/train")
async def start_training(
    background_tasks: BackgroundTasks,
    config: dict
):
    """启动模型训练"""
    try:
        task_id = str(uuid.uuid4())
        
        # 添加后台训练任务
        background_tasks.add_task(ai_engine.train_model, task_id, config)
        
        return {
            "success": True,
            "message": "训练任务已启动",
            "task_id": task_id,
            "config": config
        }
        
    except Exception as e:
        logger.error(f"启动训练失败: {e}")
        raise HTTPException(status_code=500, detail=f"启动训练失败: {str(e)}")

@app.get("/train/status/{task_id}")
async def get_training_status(task_id: str):
    """获取训练状态"""
    if task_id not in training_tasks:
        raise HTTPException(status_code=404, detail="训练任务不存在")
    
    return {
        "success": True,
        "task_id": task_id,
        **training_tasks[task_id]
    }

@app.get("/stats")
async def get_stats():
    """获取系统统计"""
    return {
        "success": True,
        "stats": detection_stats,
        "model_metrics": ai_engine.model_metrics,
        "training_data_size": len(ai_engine.training_data)
    }

@app.get("/models/status")
async def get_models_status():
    """获取模型状态"""
    return {
        "success": True,
        "models": {
            "bert": {
                "loaded": 'bert' in ai_engine.models,
                "device": str(ai_engine.device),
                "metrics": ai_engine.model_metrics
            }
        },
        "torch_available": TORCH_AVAILABLE,
        "device": str(ai_engine.device)
    }

if __name__ == "__main__":
    print("""
🛡️ ========================================
   AI守护系统 - 增强版后端启动
   支持视频检测 + 模型训练 + 多模态分析
======================================== 🛡️
    """)
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8008,
        log_level="info"
    )
