#!/usr/bin/env python3
"""
增强版AI检测后端服务
支持BERT+Attention模型和规则引擎混合检测

参考文献:
1. Zhang et al. "AnswerFact: Fact Checking in Product Question Answering" (EMNLP 2020)
2. Ma et al. "Attention-based Rumor Detection with Tree-structured RvNN" (TIST 2020)
"""

import os
import sys
import json
import time
import uuid
import asyncio
import re
from datetime import datetime
from typing import Dict, List, Any, Optional
from pathlib import Path

# Web框架
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# AI相关
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from transformers import BertModel, BertTokenizer
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[WARN] PyTorch未安装，将使用规则引擎")

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    import joblib
    import numpy as np
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    print("[WARN] scikit-learn未安装")

# 项目路径
PROJECT_ROOT = Path(__file__).parent

# ============================================================
# 模型定义 (与训练代码一致)
# ============================================================

if TORCH_AVAILABLE:
    class MultiHeadSelfAttention(nn.Module):
        def __init__(self, hidden_size, num_heads=8, dropout=0.1):
            super().__init__()
            self.hidden_size = hidden_size
            self.num_heads = num_heads
            self.head_dim = hidden_size // num_heads
            
            self.query = nn.Linear(hidden_size, hidden_size)
            self.key = nn.Linear(hidden_size, hidden_size)
            self.value = nn.Linear(hidden_size, hidden_size)
            self.output = nn.Linear(hidden_size, hidden_size)
            
            self.dropout = nn.Dropout(dropout)
            self.scale = self.head_dim ** -0.5
        
        def forward(self, x, mask=None):
            batch_size, seq_len, _ = x.size()
            
            Q = self.query(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
            K = self.key(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
            V = self.value(x).view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
            
            scores = torch.matmul(Q, K.transpose(-2, -1)) * self.scale
            
            if mask is not None:
                mask = mask.unsqueeze(1).unsqueeze(2)
                scores = scores.masked_fill(mask == 0, float('-inf'))
            
            attn_weights = F.softmax(scores, dim=-1)
            attn_weights = self.dropout(attn_weights)
            
            context = torch.matmul(attn_weights, V)
            context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, self.hidden_size)
            
            return self.output(context), attn_weights

    class EvidenceRankingModule(nn.Module):
        def __init__(self, hidden_size):
            super().__init__()
            self.scorer = nn.Sequential(
                nn.Linear(hidden_size, hidden_size // 2),
                nn.ReLU(),
                nn.Dropout(0.1),
                nn.Linear(hidden_size // 2, 1)
            )
        
        def forward(self, hidden_states, attention_mask):
            scores = self.scorer(hidden_states).squeeze(-1)
            scores = scores.masked_fill(attention_mask == 0, float('-inf'))
            weights = F.softmax(scores, dim=-1)
            weighted = torch.bmm(weights.unsqueeze(1), hidden_states).squeeze(1)
            return weighted, weights

    class BERTFraudDetector(nn.Module):
        def __init__(self, num_classes=3, dropout=0.1):
            super().__init__()
            
            self.bert = BertModel.from_pretrained('hfl/chinese-bert-wwm-ext')
            self.hidden_size = self.bert.config.hidden_size
            
            self.self_attention = MultiHeadSelfAttention(self.hidden_size, num_heads=8)
            self.evidence_module = EvidenceRankingModule(self.hidden_size)
            self.layer_norm = nn.LayerNorm(self.hidden_size)
            
            self.classifier = nn.Sequential(
                nn.Linear(self.hidden_size * 2, self.hidden_size),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(self.hidden_size, self.hidden_size // 2),
                nn.ReLU(),
                nn.Dropout(dropout),
                nn.Linear(self.hidden_size // 2, num_classes)
            )
        
        def forward(self, input_ids, attention_mask):
            bert_output = self.bert(input_ids=input_ids, attention_mask=attention_mask)
            hidden_states = bert_output.last_hidden_state
            
            attn_output, _ = self.self_attention(hidden_states, attention_mask)
            attn_output = self.layer_norm(hidden_states + attn_output)
            
            cls_output = attn_output[:, 0, :]
            evidence_output, _ = self.evidence_module(attn_output, attention_mask)
            
            combined = torch.cat([cls_output, evidence_output], dim=-1)
            logits = self.classifier(combined)
            
            return logits

# ============================================================
# 增强版检测引擎
# ============================================================

class EnhancedDetectionEngine:
    """增强版检测引擎 - 支持深度学习和规则引擎"""
    
    def __init__(self):
        self.device = 'cpu'
        self.bert_model = None
        self.bert_tokenizer = None
        self.sklearn_model = None
        self.sklearn_vectorizer = None
        self.label_map = {0: 'safe', 1: 'warning', 2: 'danger'}
        
        # 模型指标
        self.model_metrics = {
            'accuracy': 0.0,
            'f1': 0.0,
            'model_type': 'rule_based'
        }
        
        # 加载模型
        self._load_models()
        
        # 规则引擎关键词
        self._init_rule_engine()
    
    def _load_models(self):
        """加载AI模型"""
        # 尝试加载BERT模型
        bert_model_path = PROJECT_ROOT / "models" / "fraud_detector_final.pth"
        if TORCH_AVAILABLE and bert_model_path.exists():
            try:
                print("[INFO] 正在加载BERT+Attention模型...")
                self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
                
                self.bert_tokenizer = BertTokenizer.from_pretrained('hfl/chinese-bert-wwm-ext')
                self.bert_model = BERTFraudDetector(num_classes=3)
                
                checkpoint = torch.load(bert_model_path, map_location=self.device)
                self.bert_model.load_state_dict(checkpoint['model_state_dict'])
                self.bert_model.to(self.device)
                self.bert_model.eval()
                
                self.model_metrics = checkpoint.get('training_info', {})
                self.model_metrics['model_type'] = 'bert_attention'
                
                print(f"[OK] BERT模型加载成功! 设备: {self.device}")
                print(f"    准确率: {self.model_metrics.get('test_accuracy', 0):.2%}")
                print(f"    F1分数: {self.model_metrics.get('test_f1', 0):.2%}")
                return
            except Exception as e:
                print(f"[WARN] BERT模型加载失败: {e}")
        
        # 尝试加载sklearn模型
        sklearn_model_path = PROJECT_ROOT / "models" / "trained" / "simple_ai_model.joblib"
        if SKLEARN_AVAILABLE and sklearn_model_path.exists():
            try:
                print("[INFO] 正在加载sklearn模型...")
                model_data = joblib.load(sklearn_model_path)
                self.sklearn_model = model_data.get('model')
                self.sklearn_vectorizer = model_data.get('vectorizer')
                self.model_metrics = model_data.get('metrics', {})
                self.model_metrics['model_type'] = 'sklearn'
                print(f"[OK] sklearn模型加载成功!")
                return
            except Exception as e:
                print(f"[WARN] sklearn模型加载失败: {e}")
        
        print("[INFO] 将使用规则引擎进行检测")
        self.model_metrics['model_type'] = 'rule_based'
    
    def _init_rule_engine(self):
        """初始化规则引擎"""
        # 高危关键词 (金融诈骗)
        self.danger_keywords_financial = [
            '保证收益', '稳赚不赔', '无风险投资', '内幕消息', '月入万元',
            '日赚千元', '一夜暴富', '翻倍收益', '股票推荐', '期货配资',
            '内部信息', '跟单', '带单', '喊单', '私募内部', '暴涨',
            '百分百赚', '包赚', '必涨', '躺赚', '刷单兼职',
        ]
        
        # 高危关键词 (医疗虚假信息)
        self.danger_keywords_medical = [
            '包治百病', '祖传秘方', '神奇疗效', '一次根治', '永不复发',
            '药到病除', '特效药', '偏方', '癌症克星', '治愈率100%',
            '不复发', '三天见效', '一周见效', '纯天然无副作用',
        ]
        
        # 警告关键词
        self.warning_keywords = [
            '投资', '理财', '保健品', '限时', '促销', '优惠',
            '抢购', '特价', '代购', '加盟', '微信', '联系方式',
            '扫码入群', '私聊', '低价', '免费领取', '充值返利',
        ]
        
        # 冒充身份模式
        self.impersonation_patterns = [
            r'我是.{0,10}(银行|公安|法院|检察院|客服)',
            r'(账户|账号).{0,10}(异常|风险|冻结)',
            r'涉嫌.{0,10}(诈骗|洗钱|犯罪)',
            r'转入.{0,10}(安全账户|验证账户)',
        ]
    
    async def detect(self, text: str) -> Dict:
        """检测文本"""
        try:
            # 优先使用深度学习模型
            if self.bert_model is not None:
                return await self._detect_with_bert(text)
            elif self.sklearn_model is not None:
                return await self._detect_with_sklearn(text)
            else:
                return await self._detect_with_rules(text)
        except Exception as e:
            print(f"[ERROR] 检测失败: {e}")
            return self._get_fallback_result(text)
    
    async def _detect_with_bert(self, text: str) -> Dict:
        """使用BERT模型检测"""
        encoding = self.bert_tokenizer(
            text,
            add_special_tokens=True,
            max_length=128,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        
        with torch.no_grad():
            logits = self.bert_model(input_ids, attention_mask)
            probs = F.softmax(logits, dim=-1)
        
        pred_class = torch.argmax(probs, dim=-1).item()
        confidence = probs[0][pred_class].item()
        
        level = self.label_map[pred_class]
        
        return {
            'success': True,
            'level': level,
            'score': confidence,
            'confidence': confidence,
            'message': f'BERT+Attention模型检测完成',
            'reasons': self._generate_reasons(text, level),
            'suggestions': self._generate_suggestions(level),
            'model': 'BERT-Attention-Chinese',
            'probabilities': {
                'safe': probs[0][0].item(),
                'warning': probs[0][1].item(),
                'danger': probs[0][2].item()
            },
            'detection_id': f"bert_{int(time.time())}_{hash(text) % 10000}",
            'timestamp': time.time()
        }
    
    async def _detect_with_sklearn(self, text: str) -> Dict:
        """使用sklearn模型检测"""
        text_vec = self.sklearn_vectorizer.transform([text])
        pred = self.sklearn_model.predict(text_vec)[0]
        prob = self.sklearn_model.predict_proba(text_vec)[0]
        
        level = self.label_map.get(pred, 'warning')
        confidence = float(prob[pred])
        
        return {
            'success': True,
            'level': level,
            'score': confidence,
            'confidence': confidence,
            'message': f'机器学习模型检测完成',
            'reasons': self._generate_reasons(text, level),
            'suggestions': self._generate_suggestions(level),
            'model': 'LogisticRegression-TF-IDF',
            'probabilities': {
                'safe': float(prob[0]),
                'warning': float(prob[1]),
                'danger': float(prob[2])
            },
            'detection_id': f"sklearn_{int(time.time())}_{hash(text) % 10000}",
            'timestamp': time.time()
        }
    
    async def _detect_with_rules(self, text: str) -> Dict:
        """使用规则引擎检测"""
        risk_score = 0.0
        found_keywords = []
        
        # 检查金融诈骗关键词
        for kw in self.danger_keywords_financial:
            if kw in text:
                risk_score += 0.3
                found_keywords.append(('金融诈骗', kw))
        
        # 检查医疗虚假信息关键词
        for kw in self.danger_keywords_medical:
            if kw in text:
                risk_score += 0.3
                found_keywords.append(('医疗虚假', kw))
        
        # 检查警告关键词
        for kw in self.warning_keywords:
            if kw in text:
                risk_score += 0.1
                found_keywords.append(('可疑', kw))
        
        # 检查冒充身份模式
        for pattern in self.impersonation_patterns:
            if re.search(pattern, text):
                risk_score += 0.4
                found_keywords.append(('冒充身份', pattern))
        
        # 检查联系方式
        if re.search(r'微信|qq|电话|\d{11}', text, re.I):
            if risk_score > 0.2:
                risk_score += 0.1
        
        # 确定风险等级
        risk_score = min(1.0, risk_score)
        if risk_score >= 0.5:
            level = 'danger'
        elif risk_score >= 0.2:
            level = 'warning'
        else:
            level = 'safe'
        
        reasons = []
        for category, kw in found_keywords[:5]:
            reasons.append(f"检测到{category}相关内容: '{kw}'")
        if not reasons:
            reasons = ["未发现明显风险因素"]
        
        return {
            'success': True,
            'level': level,
            'score': risk_score,
            'confidence': 0.75 if found_keywords else 0.9,
            'message': f'规则引擎检测完成',
            'reasons': reasons,
            'suggestions': self._generate_suggestions(level),
            'model': 'Rule-Engine-Enhanced',
            'keywords_found': [kw for _, kw in found_keywords],
            'detection_id': f"rule_{int(time.time())}_{hash(text) % 10000}",
            'timestamp': time.time()
        }
    
    def _generate_reasons(self, text: str, level: str) -> List[str]:
        """生成检测原因"""
        if level == 'danger':
            reasons = ["AI模型识别为高风险内容"]
            if any(kw in text for kw in self.danger_keywords_financial):
                reasons.append("包含金融诈骗相关特征")
            if any(kw in text for kw in self.danger_keywords_medical):
                reasons.append("包含医疗虚假信息特征")
            return reasons
        elif level == 'warning':
            return ["AI模型识别为可疑内容", "建议谨慎对待"]
        else:
            return ["AI模型未检测到明显风险"]
    
    def _generate_suggestions(self, level: str) -> List[str]:
        """生成安全建议"""
        if level == 'danger':
            return [
                "🚨 建议立即停止观看，谨防诈骗！",
                "❌ 不要相信高收益低风险的投资项目",
                "❌ 不要向陌生人转账或透露个人信息",
                "📞 如有疑问请咨询家人或拨打反诈热线96110"
            ]
        elif level == 'warning':
            return [
                "⚠️ 请谨慎对待此内容",
                "🔍 购买前请核实商家资质",
                "💡 投资理财请咨询正规金融机构",
                "📋 注意保护个人隐私信息"
            ]
        else:
            return [
                "✅ 内容相对安全",
                "💡 继续保持防骗意识",
                "📞 遇到可疑内容可随时求助"
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
            'suggestions': ['请谨慎对待此内容'],
            'model': 'Fallback',
            'detection_id': f"fallback_{int(time.time())}",
            'timestamp': time.time()
        }
    
    def get_model_status(self) -> Dict:
        """获取模型状态"""
        return {
            'model_type': self.model_metrics.get('model_type', 'unknown'),
            'accuracy': self.model_metrics.get('test_accuracy', 0),
            'f1_score': self.model_metrics.get('test_f1', 0),
            'device': self.device,
            'bert_available': self.bert_model is not None,
            'sklearn_available': self.sklearn_model is not None
        }


# ============================================================
# FastAPI应用
# ============================================================

app = FastAPI(
    title="AI虚假信息检测系统",
    description="基于BERT+Attention的中文诈骗/谣言检测API",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局检测引擎
detection_engine = EnhancedDetectionEngine()

# 统计信息
stats = {
    "total_detections": 0,
    "danger_count": 0,
    "warning_count": 0,
    "safe_count": 0
}


@app.get("/")
async def root():
    model_status = detection_engine.get_model_status()
    return {
        "message": "AI虚假信息检测系统",
        "version": "2.0.0",
        "status": "运行中",
        "model": model_status
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "model_status": detection_engine.get_model_status()
    }


@app.post("/detect")
async def detect_text(request: dict):
    """文本检测API"""
    text = request.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="文本内容不能为空")
    
    result = await detection_engine.detect(text)
    
    # 更新统计
    stats["total_detections"] += 1
    if result['level'] == 'danger':
        stats["danger_count"] += 1
    elif result['level'] == 'warning':
        stats["warning_count"] += 1
    else:
        stats["safe_count"] += 1
    
    return result


@app.get("/stats")
async def get_stats():
    """获取统计信息"""
    return {
        "stats": stats,
        "model_status": detection_engine.get_model_status()
    }


@app.get("/models/status")
async def get_models_status():
    """获取模型状态"""
    return detection_engine.get_model_status()


if __name__ == "__main__":
    print("""
╔════════════════════════════════════════════════════════════╗
║     AI虚假信息检测系统 v2.0                                ║
║     基于BERT+Attention的中文诈骗/谣言检测                   ║
╚════════════════════════════════════════════════════════════╝
    """)
    
    uvicorn.run(app, host="0.0.0.0", port=8008, log_level="info")









