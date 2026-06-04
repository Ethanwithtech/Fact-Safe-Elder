"""
多模态虚假信息检测器
基于FakeSV和SpotFake论文架构
支持文本、视觉、音频三模态融合检测
"""

import os
import re
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np
from loguru import logger

# scikit-learn 模型加载
try:
    import joblib
    JOBLIB_AVAILABLE = True
except ImportError:
    logger.warning("joblib未安装，简单AI模型不可用")
    JOBLIB_AVAILABLE = False

# 深度学习框架
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from transformers import (
        BertTokenizer, 
        BertModel,
        AutoTokenizer,
        AutoModel
    )
    TORCH_AVAILABLE = True
except ImportError:
    logger.warning("PyTorch/Transformers未安装，使用模拟模式")
    TORCH_AVAILABLE = False

# 视觉处理
try:
    from torchvision import models, transforms
    from PIL import Image
    VISION_AVAILABLE = True
except ImportError:
    logger.warning("torchvision未安装，视觉模态不可用")
    VISION_AVAILABLE = False

# 音频处理
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    logger.warning("Whisper未安装，音频转写功能不可用")
    WHISPER_AVAILABLE = False

# 老年人认知操控特征分类法（突破点2/4 共用）
try:
    from app.core.manipulation_taxonomy import (
        weak_label, FEATURE_KEYS, multihot_to_features, describe_features,
    )
    TAXONOMY_AVAILABLE = True
except ImportError:
    try:
        from core.manipulation_taxonomy import (
            weak_label, FEATURE_KEYS, multihot_to_features, describe_features,
        )
        TAXONOMY_AVAILABLE = True
    except ImportError:
        TAXONOMY_AVAILABLE = False
        FEATURE_KEYS = []

        def weak_label(text):
            return []

        def multihot_to_features(vec, threshold=0.5):
            return []

        def describe_features(keys, lang="zh"):
            return []


# === 训练好的文本分类模型（与 train_multimodal_model.py 中的 TextClassifier 对齐） ===
if TORCH_AVAILABLE:
    class TextClassifier(nn.Module):
        """
        BERT 文本分类器 - 与训练脚本 train_multimodal_model.py 中结构一致
        encoder: MacBERT (hfl/chinese-macbert-base), hidden=768
        head: Linear(768,384) -> GELU -> Dropout -> Linear(384,2)
        """
        def __init__(self, model_name: str = "hfl/chinese-macbert-base", num_labels: int = 2, dropout: float = 0.3):
            super().__init__()
            self.encoder = AutoModel.from_pretrained(model_name)
            hidden = self.encoder.config.hidden_size  # 768
            self.dropout = nn.Dropout(dropout)
            self.head = nn.Sequential(
                nn.Linear(hidden, hidden // 2),
                nn.GELU(),
                nn.Dropout(dropout),
                nn.Linear(hidden // 2, num_labels),
            )

        def forward(self, input_ids, attention_mask=None, token_type_ids=None):
            out = self.encoder(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
            cls_emb = self.dropout(out.last_hidden_state[:, 0])  # [CLS] token
            return self.head(cls_emb)


    class ElderCognitiveClassifier(nn.Module):
        """
        老年人认知特征多任务模型 (突破点2)

        与大厂"通用反诈模型"的关键区别：在判断风险等级的同时，显式输出
        诈骗分子使用的"认知操控手法"多标签（情感操控/权威伪造/利益诱导/
        紧迫感/AI合成），为证据链可解释提供"手法标注"。

        - encoder: MacBERT (hfl/chinese-macbert-base)
        - risk_head:  Linear -> 3 (safe / warning / danger)  —— 多分类
        - manip_head: Linear -> num_features                 —— 多标签 (sigmoid)
        """
        def __init__(self, model_name: str = "hfl/chinese-macbert-base",
                     num_risk: int = 3, num_features: int = 5, dropout: float = 0.3):
            super().__init__()
            self.encoder = AutoModel.from_pretrained(model_name)
            hidden = self.encoder.config.hidden_size
            self.dropout = nn.Dropout(dropout)
            self.shared = nn.Sequential(
                nn.Linear(hidden, hidden // 2),
                nn.GELU(),
                nn.Dropout(dropout),
            )
            self.risk_head = nn.Linear(hidden // 2, num_risk)
            self.manip_head = nn.Linear(hidden // 2, num_features)

        def forward(self, input_ids, attention_mask=None, token_type_ids=None):
            out = self.encoder(input_ids=input_ids, attention_mask=attention_mask, token_type_ids=token_type_ids)
            cls_emb = self.dropout(out.last_hidden_state[:, 0])
            shared = self.shared(cls_emb)
            return self.risk_head(shared), self.manip_head(shared)


class RiskLevel(Enum):
    """风险等级"""
    SAFE = "safe"
    WARNING = "warning"
    DANGER = "danger"


@dataclass
class MultimodalInput:
    """多模态输入数据"""
    text: Optional[str] = None
    image: Optional[Any] = None  # PIL.Image or np.ndarray
    audio: Optional[np.ndarray] = None
    video_frames: Optional[List[Any]] = None
    metadata: Optional[Dict] = None


@dataclass
class DetectionOutput:
    """检测输出结果"""
    risk_level: RiskLevel
    confidence: float
    risk_score: float
    text_risk: float
    visual_risk: float
    audio_risk: float
    reasons: List[str]
    suggestions: List[str]
    attention_weights: Optional[Dict] = None
    explanation: Optional[str] = None
    inference_time: float = 0.0
    detection_method: str = "rule_engine"
    bert_score: Optional[float] = None
    tfidf_score: Optional[float] = None
    # 突破点2: 老年人认知操控手法（多标签）
    manipulation_features: Optional[List[str]] = None  # 命中的特征 key 列表
    manipulation_detail: Optional[List[Dict]] = None   # [{key,name,desc}] 供证据链展示
    manipulation_source: Optional[str] = None          # "cognitive_model" | "weak_rule"
    cognitive_risk: Optional[float] = None             # 认知模型给出的风险分


class CrossModalAttention(nn.Module):
    """
    跨模态注意力机制
    参考论文: FakeSV - Multimodal Benchmark for Fake News Detection
    """
    def __init__(self, hidden_dim: int = 768, num_heads: int = 8, dropout: float = 0.1):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_heads = num_heads
        self.head_dim = hidden_dim // num_heads
        
        # 查询、键、值投影层
        self.query_proj = nn.Linear(hidden_dim, hidden_dim)
        self.key_proj = nn.Linear(hidden_dim, hidden_dim)
        self.value_proj = nn.Linear(hidden_dim, hidden_dim)
        
        # 输出投影
        self.output_proj = nn.Linear(hidden_dim, hidden_dim)
        
        # Dropout和LayerNorm
        self.dropout = nn.Dropout(dropout)
        self.layer_norm = nn.LayerNorm(hidden_dim)
        
        # 门控机制
        self.gate = nn.Sequential(
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.Sigmoid()
        )
    
    def forward(
        self, 
        query: torch.Tensor, 
        key: torch.Tensor, 
        value: torch.Tensor,
        mask: Optional[torch.Tensor] = None
    ) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            query: [batch, seq_len, hidden_dim] - 查询模态特征
            key: [batch, seq_len, hidden_dim] - 键模态特征
            value: [batch, seq_len, hidden_dim] - 值模态特征
            mask: 可选的注意力掩码
        Returns:
            output: 融合后的特征
            attention_weights: 注意力权重（用于可解释性）
        """
        batch_size = query.size(0)
        
        # 投影
        Q = self.query_proj(query)
        K = self.key_proj(key)
        V = self.value_proj(value)
        
        # 重塑为多头格式
        Q = Q.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        K = K.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        V = V.view(batch_size, -1, self.num_heads, self.head_dim).transpose(1, 2)
        
        # 计算注意力分数
        attention_scores = torch.matmul(Q, K.transpose(-2, -1)) / np.sqrt(self.head_dim)
        
        if mask is not None:
            attention_scores = attention_scores.masked_fill(mask == 0, -1e9)
        
        attention_weights = F.softmax(attention_scores, dim=-1)
        attention_weights = self.dropout(attention_weights)
        
        # 加权求和
        context = torch.matmul(attention_weights, V)
        context = context.transpose(1, 2).contiguous().view(batch_size, -1, self.hidden_dim)
        
        # 输出投影
        output = self.output_proj(context)
        
        # 门控融合
        gate_input = torch.cat([query, output], dim=-1)
        gate_weight = self.gate(gate_input)
        output = gate_weight * output + (1 - gate_weight) * query
        
        # 残差连接和LayerNorm
        output = self.layer_norm(output + query)
        
        return output, attention_weights.mean(dim=1)  # 平均多头注意力


class TextEncoder(nn.Module):
    """
    文本编码器
    使用BERT-base-chinese进行中文文本特征提取
    """
    def __init__(
        self, 
        model_name: str = "hfl/chinese-bert-wwm-ext",
        hidden_dim: int = 768,
        freeze_bert: bool = False
    ):
        super().__init__()
        self.model_name = model_name
        self.hidden_dim = hidden_dim
        
        if TORCH_AVAILABLE:
            try:
                self.tokenizer = BertTokenizer.from_pretrained(model_name)
                self.bert = BertModel.from_pretrained(model_name)
                
                if freeze_bert:
                    for param in self.bert.parameters():
                        param.requires_grad = False
                        
                logger.info(f"文本编码器加载成功: {model_name}")
            except Exception as e:
                logger.error(f"加载BERT失败: {e}")
                self.tokenizer = None
                self.bert = None
        else:
            self.tokenizer = None
            self.bert = None
        
        # 特征投影层
        self.projection = nn.Linear(768, hidden_dim) if TORCH_AVAILABLE else None
    
    def forward(self, texts: List[str], max_length: int = 512) -> torch.Tensor:
        """
        编码文本
        Args:
            texts: 文本列表
            max_length: 最大序列长度
        Returns:
            text_features: [batch, hidden_dim]
        """
        if self.bert is None:
            # 返回模拟特征
            return torch.randn(len(texts), self.hidden_dim)
        
        # 编码文本
        inputs = self.tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=max_length,
            return_tensors="pt"
        )
        
        device = next(self.bert.parameters()).device
        inputs = {k: v.to(device) for k, v in inputs.items()}
        
        with torch.no_grad() if not self.training else torch.enable_grad():
            outputs = self.bert(**inputs)
            
        # 使用[CLS]token的输出
        cls_output = outputs.last_hidden_state[:, 0, :]
        
        # 投影到统一维度
        text_features = self.projection(cls_output)
        
        return text_features


class VisualEncoder(nn.Module):
    """
    视觉编码器
    使用ResNet50/EfficientNet提取图像特征
    """
    def __init__(
        self,
        backbone: str = "resnet50",
        hidden_dim: int = 768,
        pretrained: bool = True,
        freeze_backbone: bool = True
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.backbone_name = backbone
        
        if VISION_AVAILABLE and TORCH_AVAILABLE:
            if backbone == "resnet50":
                self.backbone = models.resnet50(pretrained=pretrained)
                backbone_dim = 2048
                # 移除最后的分类层
                self.backbone = nn.Sequential(*list(self.backbone.children())[:-1])
            elif backbone == "efficientnet_b0":
                self.backbone = models.efficientnet_b0(pretrained=pretrained)
                backbone_dim = 1280
                self.backbone = nn.Sequential(*list(self.backbone.children())[:-1])
            else:
                raise ValueError(f"不支持的backbone: {backbone}")
            
            if freeze_backbone:
                for param in self.backbone.parameters():
                    param.requires_grad = False
            
            # 特征投影
            self.projection = nn.Sequential(
                nn.Linear(backbone_dim, hidden_dim),
                nn.ReLU(),
                nn.Dropout(0.1)
            )
            
            # 图像预处理
            self.preprocess = transforms.Compose([
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(
                    mean=[0.485, 0.456, 0.406],
                    std=[0.229, 0.224, 0.225]
                )
            ])
            
            logger.info(f"视觉编码器加载成功: {backbone}")
        else:
            self.backbone = None
            self.projection = None
            self.preprocess = None
    
    def forward(self, images: List[Any]) -> torch.Tensor:
        """
        编码图像
        Args:
            images: PIL Image列表或已处理的tensor
        Returns:
            visual_features: [batch, hidden_dim]
        """
        if self.backbone is None:
            return torch.randn(len(images), self.hidden_dim)
        
        # 预处理图像
        if isinstance(images[0], Image.Image):
            processed = torch.stack([self.preprocess(img) for img in images])
        else:
            processed = images
        
        device = next(self.backbone.parameters()).device
        processed = processed.to(device)
        
        # 提取特征
        with torch.no_grad() if not self.training else torch.enable_grad():
            features = self.backbone(processed)
            features = features.view(features.size(0), -1)
        
        # 投影
        visual_features = self.projection(features)
        
        return visual_features


class AudioEncoder(nn.Module):
    """
    音频编码器
    使用Whisper进行语音转写，然后用BERT编码
    """
    def __init__(
        self,
        whisper_model: str = "base",
        text_encoder: Optional[TextEncoder] = None,
        hidden_dim: int = 768
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        
        # 加载Whisper模型
        if WHISPER_AVAILABLE:
            try:
                self.whisper = whisper.load_model(whisper_model)
                logger.info(f"Whisper模型加载成功: {whisper_model}")
            except Exception as e:
                logger.error(f"加载Whisper失败: {e}")
                self.whisper = None
        else:
            self.whisper = None
        
        # 文本编码器（用于编码转写结果）
        self.text_encoder = text_encoder
    
    def transcribe(self, audio: np.ndarray) -> str:
        """
        将音频转写为文本
        """
        if self.whisper is None:
            return ""
        
        try:
            result = self.whisper.transcribe(audio, language="zh")
            return result["text"]
        except Exception as e:
            logger.error(f"音频转写失败: {e}")
            return ""
    
    def forward(self, audios: List[np.ndarray]) -> Tuple[torch.Tensor, List[str]]:
        """
        编码音频
        Args:
            audios: 音频数组列表
        Returns:
            audio_features: [batch, hidden_dim]
            transcripts: 转写文本列表
        """
        # 转写音频
        transcripts = [self.transcribe(audio) for audio in audios]
        
        # 使用文本编码器编码转写结果
        if self.text_encoder is not None and any(transcripts):
            # 过滤空转写
            valid_transcripts = [t if t else " " for t in transcripts]
            audio_features = self.text_encoder(valid_transcripts)
        else:
            audio_features = torch.randn(len(audios), self.hidden_dim)
        
        return audio_features, transcripts


class MultimodalFusionModel(nn.Module):
    """
    多模态融合模型
    架构参考: FakeSV和SpotFake论文
    
    支持三种融合策略:
    1. Early Fusion (早期融合): 直接拼接特征
    2. Late Fusion (晚期融合): 独立分类后投票
    3. Attention Fusion (注意力融合): 使用跨模态注意力
    """
    def __init__(
        self,
        hidden_dim: int = 768,
        num_classes: int = 3,  # safe, warning, danger
        fusion_strategy: str = "attention",
        dropout: float = 0.1
    ):
        super().__init__()
        self.hidden_dim = hidden_dim
        self.num_classes = num_classes
        self.fusion_strategy = fusion_strategy
        
        # 模态编码器
        self.text_encoder = TextEncoder(hidden_dim=hidden_dim)
        self.visual_encoder = VisualEncoder(hidden_dim=hidden_dim)
        self.audio_encoder = AudioEncoder(
            text_encoder=self.text_encoder, 
            hidden_dim=hidden_dim
        )
        
        # 跨模态注意力层
        if fusion_strategy == "attention":
            self.text_visual_attention = CrossModalAttention(hidden_dim)
            self.text_audio_attention = CrossModalAttention(hidden_dim)
            self.visual_audio_attention = CrossModalAttention(hidden_dim)
        
        # 融合层
        if fusion_strategy == "early":
            fusion_input_dim = hidden_dim * 3
        elif fusion_strategy == "attention":
            fusion_input_dim = hidden_dim * 3
        else:
            fusion_input_dim = hidden_dim
        
        self.fusion_layer = nn.Sequential(
            nn.Linear(fusion_input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        
        # 分类头
        self.classifier = nn.Linear(hidden_dim // 2, num_classes)
        
        # 各模态独立分类器（用于Late Fusion和可解释性）
        self.text_classifier = nn.Linear(hidden_dim, num_classes)
        self.visual_classifier = nn.Linear(hidden_dim, num_classes)
        self.audio_classifier = nn.Linear(hidden_dim, num_classes)
        
        logger.info(f"多模态融合模型初始化完成，融合策略: {fusion_strategy}")
    
    def forward(
        self,
        texts: Optional[List[str]] = None,
        images: Optional[List[Any]] = None,
        audios: Optional[List[np.ndarray]] = None,
        return_attention: bool = True
    ) -> Dict[str, Any]:
        """
        多模态前向传播
        
        Args:
            texts: 文本列表
            images: 图像列表
            audios: 音频列表
            return_attention: 是否返回注意力权重
            
        Returns:
            包含预测结果和中间特征的字典
        """
        batch_size = len(texts) if texts else (len(images) if images else len(audios))
        device = next(self.parameters()).device
        
        attention_weights = {}
        
        # 编码各模态
        # 文本特征
        if texts:
            text_features = self.text_encoder(texts).to(device)
        else:
            text_features = torch.zeros(batch_size, self.hidden_dim, device=device)
        
        # 视觉特征
        if images:
            visual_features = self.visual_encoder(images).to(device)
        else:
            visual_features = torch.zeros(batch_size, self.hidden_dim, device=device)
        
        # 音频特征
        transcripts = []
        if audios:
            audio_features, transcripts = self.audio_encoder(audios)
            audio_features = audio_features.to(device)
        else:
            audio_features = torch.zeros(batch_size, self.hidden_dim, device=device)
        
        # 模态融合
        if self.fusion_strategy == "attention":
            # 跨模态注意力融合
            # 添加序列维度
            text_feat = text_features.unsqueeze(1)
            visual_feat = visual_features.unsqueeze(1)
            audio_feat = audio_features.unsqueeze(1)
            
            # 文本-视觉注意力
            tv_fused, tv_attn = self.text_visual_attention(text_feat, visual_feat, visual_feat)
            attention_weights['text_visual'] = tv_attn
            
            # 文本-音频注意力
            ta_fused, ta_attn = self.text_audio_attention(text_feat, audio_feat, audio_feat)
            attention_weights['text_audio'] = ta_attn
            
            # 视觉-音频注意力
            va_fused, va_attn = self.visual_audio_attention(visual_feat, audio_feat, audio_feat)
            attention_weights['visual_audio'] = va_attn
            
            # 合并融合特征
            fused_features = torch.cat([
                tv_fused.squeeze(1), 
                ta_fused.squeeze(1), 
                va_fused.squeeze(1)
            ], dim=-1)
            
        elif self.fusion_strategy == "early":
            # 早期融合：直接拼接
            fused_features = torch.cat([
                text_features, 
                visual_features, 
                audio_features
            ], dim=-1)
            
        else:  # late fusion
            # 晚期融合：独立预测后投票
            fused_features = text_features  # 使用文本作为主特征
        
        # 融合层
        fused_output = self.fusion_layer(fused_features)
        
        # 主分类器
        logits = self.classifier(fused_output)
        probabilities = F.softmax(logits, dim=-1)
        
        # 各模态独立预测（用于可解释性）
        text_logits = self.text_classifier(text_features)
        visual_logits = self.visual_classifier(visual_features)
        audio_logits = self.audio_classifier(audio_features)
        
        text_probs = F.softmax(text_logits, dim=-1)
        visual_probs = F.softmax(visual_logits, dim=-1)
        audio_probs = F.softmax(audio_logits, dim=-1)
        
        return {
            'logits': logits,
            'probabilities': probabilities,
            'predicted_class': torch.argmax(probabilities, dim=-1),
            'text_risk': text_probs[:, 2],  # danger类概率
            'visual_risk': visual_probs[:, 2],
            'audio_risk': audio_probs[:, 2],
            'text_features': text_features,
            'visual_features': visual_features,
            'audio_features': audio_features,
            'attention_weights': attention_weights if return_attention else None,
            'transcripts': transcripts
        }


class MultimodalDetector:
    """
    多模态虚假信息检测器
    提供高层API用于实际检测
    """
    
    # 领域特定关键词（中英文双语）
    FINANCIAL_KEYWORDS = [
        # 中文
        "保证收益", "无风险", "月入万元", "稳赚不赔", "高收益",
        "内幕消息", "限时优惠", "投资理财", "虚拟货币", "传销",
        "无抵押贷款", "秒批", "黑户贷款", "刷单", "套现",
        "赌博", "挖矿", "博彩", "彩票预测", "赌场", "下注",
        "财务自由", "日赚千元", "月入十万", "躺赚", "被动收入",
        "保本保息", "年化收益", "翻倍", "百倍收益",
        # 粤语 / 香港常见金融诈骗话术
        "保證回報", "冇風險", "無風險", "高息", "穩賺", "包賺",
        "轉數快", "FPS", "入數", "匯款", "加我WhatsApp", "加我微信",
        "股票貼士", "內幕消息", "退休投資", "長者投資",
        # English
        "guaranteed return", "no risk", "free money", "get rich",
        "mining", "gambling", "casino", "bet", "cheat",
        "investment secret", "passive income", "financial freedom",
        "cryptocurrency", "bitcoin", "forex", "mlm", "pyramid",
    ]
    
    # 单独出现「保健品」等词可能是科普，仅匹配明确虚假宣传短语
    MEDICAL_KEYWORDS = [
        # 中文
        "包治百病", "神奇疗效", "祖传秘方", "一次根治", "永不复发",
        "药到病除", "100%治愈", "三天见效", "医院不告诉你", "特效药",
        "偏方", "土方", "民间验方", "癌症克星", "延年益寿",
        # 粤语 / 繁体健康误导话术
        "包醫百病", "祖傳秘方", "神奇療效", "三日見效", "醫院唔會話你知",
        "保健產品", "長壽秘方", "降血糖", "通血管", "冇副作用",
        # English
        "miracle cure", "cure all", "secret remedy", "guaranteed cure",
        "doctors hate", "big pharma", "anti-aging", "detox",
    ]
    
    # 平台内正常带货（单独出现不应判诈骗）
    LEGIT_COMMERCE_MARKERS = [
        "官方旗舰店", "小黄车", "购物车", "点击链接", "直播间",
        "抖音商城", "包邮", "7天无理由", "现货", "正品", "官旗",
        "小黄车下单", "商品链接", "店铺主页",
    ]

    HIGH_RISK_SCAM_MARKERS = [
        "加微信", "加微", "私信买", "私下", "转账", "汇款", "银行卡",
        "包治百病", "保证收益", "无风险", "月入万元", "稳赚", "祖传秘方",
        "央视推荐", "包治", "根治", "治愈", "订购热线", "验证码",
        "身份证", "传销", "挖矿躺赚",
    ]

    URGENCY_KEYWORDS = [
        # 中文
        "赶紧", "立即", "马上", "紧急", "限时", "截止今晚",
        "最后一天", "错过后悔", "机不可失", "名额有限",
        # 粤语紧迫性话术
        "即刻", "而家", "快啲", "限時", "今晚截止", "最後機會",
        "唔好錯過", "名額有限", "只限今日",
        # English
        "urgent", "hurry", "act now", "limited time", "don't miss",
        "last chance", "expires today", "click now",
    ]
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        simple_model_path: Optional[str] = None,
        cognitive_model_path: Optional[str] = None,
        device: str = "auto",
        fusion_strategy: str = "attention"
    ):
        """
        初始化检测器
        
        Args:
            model_path: BERT文本分类模型路径 (best_text_model.pt)
            simple_model_path: 简单AI模型路径 (simple_ai_model.joblib)
            cognitive_model_path: 老年人认知特征多任务模型 (elder_cognitive_model.pt)
            device: 运行设备
            fusion_strategy: 融合策略
        """
        # 设置设备
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu") if TORCH_AVAILABLE else "cpu"
        else:
            self.device = torch.device(device) if TORCH_AVAILABLE else device
        
        logger.info(f"检测器运行设备: {self.device}")
        
        # === 真实AI模型：BERT TextClassifier (F1=0.93) ===
        self.text_classifier = None
        self.text_tokenizer = None
        self._text_model_loaded = False
        
        if TORCH_AVAILABLE and model_path and os.path.exists(model_path):
            self._load_text_classifier(model_path)
        
        # === 简单AI模型：TF-IDF + VotingClassifier (Acc=99.7%) ===
        self.simple_model = None
        self.simple_vectorizer = None
        self._simple_model_loaded = False
        
        if JOBLIB_AVAILABLE and simple_model_path and os.path.exists(simple_model_path):
            self._load_simple_model(simple_model_path)

        # === 老年人认知特征多任务模型 (突破点2) ===
        self.cognitive_model = None
        self.cognitive_tokenizer = None
        self._cognitive_model_loaded = False
        self._cognitive_feature_keys = list(FEATURE_KEYS)

        if TORCH_AVAILABLE and cognitive_model_path and os.path.exists(cognitive_model_path):
            self._load_cognitive_model(cognitive_model_path)

        # === 原始多模态融合模型（保留向后兼容，但无训练权重） ===
        self.model = None
        if TORCH_AVAILABLE:
            try:
                self.model = MultimodalFusionModel(
                    hidden_dim=768,
                    num_classes=3,
                    fusion_strategy=fusion_strategy
                )
                self.model.to(self.device)
                self.model.eval()
            except Exception as e:
                logger.warning(f"多模态融合模型初始化失败（非必须）: {e}")
        
        # 风险等级映射
        self.risk_levels = [RiskLevel.SAFE, RiskLevel.WARNING, RiskLevel.DANGER]
        
        # 日志总结
        ai_status = []
        if self._text_model_loaded:
            ai_status.append("BERT文本分类器✅")
        if self._simple_model_loaded:
            ai_status.append("TF-IDF集成模型✅")
        if self._cognitive_model_loaded:
            ai_status.append("认知特征多任务模型✅")
        if not ai_status:
            ai_status.append("仅规则引擎（无AI模型）")
        logger.info(f"多模态检测器初始化完成 | AI模型: {', '.join(ai_status)}")
    
    def _load_text_classifier(self, model_path: str):
        """加载BERT文本分类器权重"""
        try:
            logger.info(f"正在加载BERT文本分类模型: {model_path}")
            checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)

            # 自动检测 checkpoint 中实际的 num_labels
            state_dict = checkpoint.get('model_state_dict', checkpoint)
            # head.3 是最后一个 Linear 层，其 weight shape = [num_labels, hidden//2]
            head_key = None
            for k in state_dict:
                if 'head' in k and 'weight' in k:
                    head_key = k  # 取最后一个 head 权重
            actual_num_labels = state_dict[head_key].shape[0] if head_key else 3
            logger.info(f"BERT checkpoint num_labels={actual_num_labels}")

            self.text_classifier = TextClassifier(
                model_name="hfl/chinese-macbert-base",
                num_labels=actual_num_labels,
                dropout=0.3
            )
            self.text_classifier.load_state_dict(state_dict)
            self.text_classifier.to(self.device)
            self.text_classifier.eval()
            self._bert_num_labels = actual_num_labels
            
            # 加载对应的 tokenizer
            self.text_tokenizer = AutoTokenizer.from_pretrained("hfl/chinese-macbert-base")
            
            best_f1 = checkpoint.get('best_f1', 'N/A')
            logger.info(f"✅ BERT文本分类模型加载成功 | num_labels={actual_num_labels} | Best F1: {best_f1:.4f}" if isinstance(best_f1, float) else f"✅ BERT模型加载成功 | num_labels={actual_num_labels}")
            self._text_model_loaded = True
        except Exception as e:
            logger.error(f"❌ 加载BERT文本分类模型失败: {e}")
            self.text_classifier = None
            self.text_tokenizer = None
    
    def _load_simple_model(self, model_path: str):
        """加载简单AI模型 (TF-IDF + VotingClassifier)"""
        try:
            logger.info(f"正在加载简单AI模型: {model_path}")
            data = joblib.load(model_path)
            self.simple_model = data['model']
            self.simple_vectorizer = data['vectorizer']
            self._simple_needs_jieba = data.get('needs_jieba_tokenize', data.get('tokenizer') == 'jieba')
            metrics = data.get('metrics', {})
            version = data.get('version', 'unknown')
            acc = metrics.get('accuracy')
            f1 = metrics.get('f1_score')
            acc_s = f"{acc:.4f}" if isinstance(acc, (int, float)) else "N/A"
            f1_s = f"{f1:.4f}" if isinstance(f1, (int, float)) else "N/A"
            logger.info(f"✅ 简单AI模型加载成功 v{version} | Accuracy: {acc_s}, F1: {f1_s}, jieba={self._simple_needs_jieba}")
            self._simple_model_loaded = True
        except Exception as e:
            logger.error(f"❌ 加载简单AI模型失败: {e}")
            self.simple_model = None
            self.simple_vectorizer = None
    
    def _load_cognitive_model(self, model_path: str):
        """加载老年人认知特征多任务模型 (elder_cognitive_model.pt)"""
        try:
            logger.info(f"正在加载老年人认知特征模型: {model_path}")
            checkpoint = torch.load(model_path, map_location=self.device, weights_only=False)
            state_dict = checkpoint.get('model_state_dict', checkpoint)
            feature_keys = checkpoint.get('feature_keys', list(FEATURE_KEYS))
            num_risk = int(checkpoint.get('num_risk', 3))
            num_features = int(checkpoint.get('num_features', len(feature_keys) or 5))
            model_name = checkpoint.get('model_name', 'hfl/chinese-macbert-base')

            self.cognitive_model = ElderCognitiveClassifier(
                model_name=model_name,
                num_risk=num_risk,
                num_features=num_features,
                dropout=0.3,
            )
            self.cognitive_model.load_state_dict(state_dict)
            self.cognitive_model.to(self.device)
            self.cognitive_model.eval()
            self.cognitive_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._cognitive_feature_keys = feature_keys
            self._cognitive_threshold = float(checkpoint.get('manip_threshold', 0.5))
            self._cognitive_model_loaded = True
            metrics = checkpoint.get('metrics', {})
            logger.info(
                f"✅ 认知特征模型加载成功 | 风险类={num_risk} 手法标签={num_features} "
                f"| 指标={metrics}"
            )
        except Exception as e:
            logger.error(f"❌ 加载认知特征模型失败: {e}")
            self.cognitive_model = None
            self.cognitive_tokenizer = None
            self._cognitive_model_loaded = False

    def _infer_cognitive(self, text: str) -> Optional[Dict[str, Any]]:
        """运行认知特征多任务模型，返回 {risk_score, features, scores} 或 None。"""
        if not (self._cognitive_model_loaded and text and self.cognitive_model and self.cognitive_tokenizer):
            return None
        try:
            inputs = self.cognitive_tokenizer(
                text, return_tensors="pt", max_length=512, truncation=True, padding=True
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.no_grad():
                risk_logits, manip_logits = self.cognitive_model(**inputs)
                risk_probs = F.softmax(risk_logits, dim=-1)[0]
                manip_probs = torch.sigmoid(manip_logits)[0]
            # 风险分: warning*0.5 + danger
            risk_score = float(risk_probs[1].item() * 0.5 + risk_probs[2].item()) if len(risk_probs) >= 3 else float(risk_probs[-1].item())
            thr = getattr(self, '_cognitive_threshold', 0.5)
            manip_vec = manip_probs.tolist()
            keys = self._cognitive_feature_keys
            features = [keys[i] for i, p in enumerate(manip_vec) if i < len(keys) and p >= thr]
            scores = {keys[i]: round(float(p), 4) for i, p in enumerate(manip_vec) if i < len(keys)}
            return {"risk_score": min(risk_score, 1.0), "features": features, "scores": scores}
        except Exception as e:
            logger.warning(f"认知特征模型推理异常: {e}")
            return None

    def _get_encoder_and_tokenizer(self):
        """返回可用的 BERT encoder + tokenizer（优先认知模型，其次文本分类器）。"""
        if self._cognitive_model_loaded and self.cognitive_model is not None:
            return self.cognitive_model.encoder, self.cognitive_tokenizer
        if self._text_model_loaded and self.text_classifier is not None:
            return self.text_classifier.encoder, self.text_tokenizer
        return None, None

    def _encode_tokens(self, text: str):
        """提取 BERT token 级隐状态 [1, seq, hidden]，供跨模态注意力使用。无模型时返回 None。"""
        if not TORCH_AVAILABLE or not text or not text.strip():
            return None
        encoder, tokenizer = self._get_encoder_and_tokenizer()
        if encoder is None or tokenizer is None:
            return None
        try:
            inputs = tokenizer(text, return_tensors="pt", max_length=128, truncation=True, padding=True)
            inputs = {k: v.to(self.device) for k, v in inputs.items()}
            with torch.no_grad():
                out = encoder(**inputs)
            return out.last_hidden_state  # [1, seq, hidden]
        except Exception as e:
            logger.warning(f"token 编码失败: {e}")
            return None

    @staticmethod
    def _char_jaccard(a: str, b: str) -> float:
        sa, sb = set(a or ""), set(b or "")
        if not (sa | sb):
            return 0.0
        return len(sa & sb) / len(sa | sb)

    async def cross_modal_reason(
        self, ocr_text: str, asr_text: str, title: str = ""
    ) -> Dict[str, Any]:
        """
        跨模态意图联合推理 (突破点1)

        平台的审核本质是"单模态独立分析 + 结果简单融合"，对"字幕合规/语音诈骗"
        这类跨模态错位伪装识别滞后。这里做真正的联合推理：

        1. 分别评估 画面文字(OCR=视觉通道) 与 语音(ASR=音频通道) 的风险
           -> visual_risk / audio_risk 不再恒为 0
        2. 用 BERT [CLS] 句向量计算两通道语义散度 divergence (1 - cosine)
        3. 用 CrossModalAttention 对两通道 token 表征做联合对齐，得到耦合度(可解释)
        4. 识别"一通道合规、另一通道诈骗"的错位伪装并给出联合风险与解释
        """
        ocr_text = (ocr_text or "").strip()
        asr_text = (asr_text or "").strip()
        result: Dict[str, Any] = {
            "visual_risk": 0.0,
            "audio_risk": 0.0,
            "joint_risk": 0.0,
            "divergence": 0.0,
            "coupling": None,
            "mismatch": False,
            "method": "rule",
            "conflict": None,
        }
        if not ocr_text and not asr_text:
            return result

        # 1) 各通道独立风险（复用全部已加载模型）
        visual_risk = 0.0
        audio_risk = 0.0
        if ocr_text:
            v = await self.detect({"text": ocr_text})
            visual_risk = float(v.risk_score)
        if asr_text:
            a = await self.detect({"text": asr_text})
            audio_risk = float(a.risk_score)
        result["visual_risk"] = round(visual_risk, 4)
        result["audio_risk"] = round(audio_risk, 4)

        # 2) 语义散度（优先 BERT 句向量，无模型时退化为字符 Jaccard）
        divergence = None
        emb_o = self._encode_tokens(ocr_text) if ocr_text else None
        emb_a = self._encode_tokens(asr_text) if asr_text else None
        if emb_o is not None and emb_a is not None:
            try:
                cls_o = emb_o[:, 0]
                cls_a = emb_a[:, 0]
                cos = F.cosine_similarity(cls_o, cls_a, dim=-1).item()
                divergence = max(0.0, min(1.0, 1.0 - cos))
                result["method"] = "model"
                # 3) 用闲置的 CrossModalAttention 做联合对齐，计算跨模态耦合度
                if self.model is not None and hasattr(self.model, "text_visual_attention"):
                    try:
                        with torch.no_grad():
                            _, attn = self.model.text_visual_attention(emb_o, emb_a, emb_a)
                        # attn: [batch, ocr_seq, asr_seq] -> 每个OCR token对ASR的最大注意力均值
                        coupling = float(attn.max(dim=-1).values.mean().item())
                        result["coupling"] = round(coupling, 4)
                    except Exception as e:
                        logger.debug(f"CrossModalAttention 计算跳过: {e}")
            except Exception as e:
                logger.warning(f"语义散度计算失败: {e}")
        if divergence is None and ocr_text and asr_text:
            divergence = max(0.0, min(1.0, 1.0 - self._char_jaccard(ocr_text.lower(), asr_text.lower())))
        result["divergence"] = round(divergence or 0.0, 4)

        # 4) 联合推理决策
        hi, lo = max(visual_risk, audio_risk), min(visual_risk, audio_risk)
        mismatch = False
        conflict = None
        # 错位伪装：一通道明显诈骗，另一通道明显合规，且语义高度发散
        if hi >= 0.5 and lo <= 0.3 and (divergence or 0) >= 0.4:
            mismatch = True
            risky_channel = "画面字幕" if visual_risk >= audio_risk else "语音"
            safe_channel = "语音" if visual_risk >= audio_risk else "画面字幕"
            conflict = {
                "conflict": True,
                "reason": f"{safe_channel}内容看似正规，但{risky_channel}中包含诈骗/诱导信息，"
                          f"疑似用合规{safe_channel}伪装掩盖真实诈骗意图（跨模态错位）",
                "reason_en": "One modality looks legitimate while the other carries scam intent — cross-modal disguise",
                "severity": "high",
                "method": result["method"],
            }
        elif hi >= 0.5 and (divergence or 0) >= 0.6:
            mismatch = True
            conflict = {
                "conflict": True,
                "reason": "画面文字与语音表达的意图存在明显矛盾，存在信息误导嫌疑",
                "reason_en": "On-screen text and speech convey conflicting intent — possible misdirection",
                "severity": "medium",
                "method": result["method"],
            }

        # 联合风险：错位时取高通道并按散度上调
        joint = hi
        if mismatch:
            joint = min(1.0, max(hi, 0.6) + 0.2 * (divergence or 0))
        result["joint_risk"] = round(joint, 4)
        result["mismatch"] = mismatch
        result["conflict"] = conflict
        return result

    def _load_model(self, model_path: str):
        """加载模型权重（向后兼容）"""
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            logger.info(f"模型权重加载成功: {model_path}")
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
    
    async def detect(
        self,
        input_data: Union[MultimodalInput, str, Dict],
        sensitivity: str = "balanced",
    ) -> DetectionOutput:
        """
        执行多模态检测（优先使用真实 AI 模型）
        
        sensitivity 误报控制策略:
          - precision / low  : 宁漏勿误，提高 danger 阈值(0.75)，优先精确率
          - balanced / normal: 默认平衡 (danger 0.65)
          - recall / high    : 高召回，降低阈值(danger 0.50)，宁可多报
        
        检测优先级:
        1. BERT TextClassifier (best_text_model.pt) — F1=0.93
        2. TF-IDF + VotingClassifier (simple_ai_model.joblib) — Acc=94.7% (v3 + jieba分词)
        3. 规则引擎关键词检测
        结果通过加权融合策略合并
        """
        start_time = time.time()
        sens = (sensitivity or "balanced").lower()
        if sens in ("low", "precision", "strict"):
            danger_th, warning_th, valve_mult = 0.75, 0.52, 0.92
        elif sens in ("high", "recall", "sensitive"):
            danger_th, warning_th, valve_mult = 0.50, 0.30, 1.0
        else:
            danger_th, warning_th, valve_mult = 0.65, 0.35, 1.0
        
        # 解析输入
        if isinstance(input_data, str):
            input_data = MultimodalInput(text=input_data)
        elif isinstance(input_data, dict):
            input_data = MultimodalInput(**input_data)
        
        text = input_data.text or ""
        detection_method = "rule_engine"
        
        try:
            # === 1. BERT 文本分类器推理 ===
            bert_risk_score = None
            bert_is_risky = None
            
            if self._text_model_loaded and text and self.text_classifier and self.text_tokenizer:
                try:
                    # 提取中文部分给 BERT（中文模型被英文干扰后性能暴跌）
                    import re as _re
                    chinese_text = _re.sub(r'[a-zA-Z0-9\s.,!?;:\'"()\[\]{}\-_/\\@#$%^&*+=<>~`]+', ' ', text).strip()
                    bert_input_text = chinese_text if len(chinese_text) > 5 else text
                    
                    inputs = self.text_tokenizer(
                        bert_input_text,
                        return_tensors="pt",
                        max_length=512,
                        truncation=True,
                        padding=True
                    )
                    inputs = {k: v.to(self.device) for k, v in inputs.items()}
                    
                    with torch.no_grad():
                        logits = self.text_classifier(**inputs)
                        probs = F.softmax(logits, dim=-1)
                        
                        num_labels = getattr(self, '_bert_num_labels', probs.shape[-1])
                        if num_labels == 2:
                            # 二分类: 0=safe, 1=risky
                            safe_prob = probs[0][0].item()
                            risky_prob = probs[0][1].item()
                            bert_risk_score = risky_prob
                            logger.info(f"BERT推理(2类): safe={safe_prob:.4f}, risky={risky_prob:.4f}")
                        else:
                            # 三分类: safe=0, warning=1, danger=2
                            safe_prob = probs[0][0].item()
                            warning_prob = probs[0][1].item()
                            danger_prob = probs[0][2].item()
                            bert_risk_score = warning_prob * 0.5 + danger_prob
                            logger.info(f"BERT推理(3类): safe={safe_prob:.4f}, warn={warning_prob:.4f}, danger={danger_prob:.4f}")
                        
                        bert_risk_score = min(bert_risk_score, 1.0)
                        bert_is_risky = bert_risk_score > 0.4
                    
                    detection_method = "ai_bert"
                    if num_labels == 2:
                        logger.info(f"BERT推理: safe={safe_prob:.4f}, risky={risky_prob:.4f}, risk_score={bert_risk_score:.4f}, risky={bert_is_risky}")
                    else:
                        logger.info(f"BERT推理: safe={safe_prob:.4f}, warn={warning_prob:.4f}, danger={danger_prob:.4f}, risk_score={bert_risk_score:.4f}, risky={bert_is_risky}")
                except Exception as e:
                    logger.warning(f"BERT推理异常: {e}")
            
            # === 2. 简单 AI 模型推理 ===
            simple_risk_score = None
            simple_is_risky = None
            
            if self._simple_model_loaded and text and self.simple_model and self.simple_vectorizer:
                try:
                    # v3 模型需要 jieba 预分词
                    tfidf_text = text
                    if getattr(self, '_simple_needs_jieba', False):
                        try:
                            import jieba
                            import re as _re
                            _t = _re.sub(r'http\S+', '', tfidf_text)
                            _t = _re.sub(r'@\S+', '', _t)
                            _t = _re.sub(r'#\S+#', '', _t)
                            words = jieba.lcut(_t)
                            tfidf_text = ' '.join(w.strip() for w in words if len(w.strip()) >= 2)
                        except ImportError:
                            logger.warning("jieba 未安装，TF-IDF 分词降级")
                    features = self.simple_vectorizer.transform([tfidf_text])
                    pred = self.simple_model.predict(features)[0]
                    if hasattr(self.simple_model, 'predict_proba'):
                        proba = self.simple_model.predict_proba(features)[0]
                        simple_risk_score = float(proba[1]) if len(proba) > 1 else float(pred)
                    else:
                        simple_risk_score = float(pred)
                    simple_is_risky = pred == 1
                    
                    if detection_method == "rule_engine":
                        detection_method = "ai_tfidf"
                    else:
                        detection_method = "ai_multimodal"
                    logger.info(f"TF-IDF推理: risk_score={simple_risk_score:.4f}, risky={simple_is_risky}")
                except Exception as e:
                    logger.warning(f"TF-IDF推理异常: {e}")
            
            # === 3. 规则引擎检测 ===
            rule_result = self._rule_based_detection(text)

            # === 3.5 老年人认知特征多任务模型 (突破点2) ===
            cognitive_out = self._infer_cognitive(text)
            cognitive_risk_score = cognitive_out["risk_score"] if cognitive_out else None
            if cognitive_out is not None:
                manipulation_features = cognitive_out["features"]
                manipulation_source = "cognitive_model"
                manipulation_scores = cognitive_out["scores"]
                if detection_method == "rule_engine":
                    detection_method = "ai_cognitive"
                elif detection_method.startswith("ai"):
                    detection_method = "ai_multimodal"
                logger.info(f"认知模型: risk={cognitive_risk_score:.4f}, 手法={manipulation_features}")
            else:
                # 模型不可用时用弱监督规则兜底，保证该能力始终可演示
                manipulation_features = weak_label(text)
                manipulation_source = "weak_rule" if manipulation_features else None
                manipulation_scores = {}

            # === 4. 融合策略：多模型投票 + 规则增强 ===
            # BERT: 语义理解最强; TF-IDF v3: 94.7% 准确率 (jieba + 3.7万真实样本); Rules: 关键词匹配
            risk_score = 0.0
            risk_contributions = []
            
            # 融合权重: 归一化比例 0.3:0.1:0.2 → 0.500:0.167:0.333 (sum=1.0)
            # 来源: Section 4.3 grid search 最优权重
            if bert_risk_score is not None:
                risk_contributions.append(("BERT", bert_risk_score, 0.500))  # 50.0%（语义理解）
            if simple_risk_score is not None:
                risk_contributions.append(("TF-IDF", simple_risk_score, 0.167))  # 16.7%（词频统计）
            if cognitive_risk_score is not None:
                risk_contributions.append(("Cognitive", cognitive_risk_score, 0.300))  # 老年人认知特征专用模型
            if rule_result['risk_score'] > 0:
                risk_contributions.append(("Rules", rule_result['risk_score'], 0.333))  # 33.3%（关键词规则）
            
            if risk_contributions:
                total_weight = sum(w for _, _, w in risk_contributions)
                risk_score = sum(s * w for _, s, w in risk_contributions) / total_weight
            
            # 安全阀：如果任一 AI 模型高置信度判断为风险，直接提升分数
            # precision 模式下降低安全阀激进度，减少误报
            if bert_risk_score is not None and bert_risk_score > 0.8:
                risk_score = max(risk_score, bert_risk_score * (0.9 * valve_mult))
            # TF-IDF 安全阀（v3 模型准确率 94.7%，可以更信任）
            if simple_risk_score is not None and simple_risk_score > 0.8:
                if bert_risk_score is not None and bert_risk_score > 0.3:
                    risk_score = max(risk_score, simple_risk_score * (0.8 * valve_mult))
                elif bert_risk_score is None:
                    # BERT 未加载时 TF-IDF 仍作为兜底
                    risk_score = max(risk_score, simple_risk_score * (0.75 * valve_mult))
            # 规则引擎兜底：关键词明确命中时强制提升（precision 模式需更高规则分才触发）
            rule_valve_th = 0.5 if sens in ("low", "precision", "strict") else 0.3
            if rule_result['risk_score'] > rule_valve_th:
                risk_score = max(risk_score, rule_result['risk_score'] * valve_mult)
            # 认知特征模型安全阀：高置信度风险时提升
            if cognitive_risk_score is not None and cognitive_risk_score > 0.8:
                risk_score = max(risk_score, cognitive_risk_score * (0.85 * valve_mult))
            # 命中多个操控手法 = 强信号，轻度提升
            if len(manipulation_features) >= 2:
                risk_score = max(risk_score, 0.55 * valve_mult)
            
            risk_score = min(risk_score, 1.0)

            # 正常直播带货/官旗推广：无高危词时限制融合分，避免误报
            rule_legit = rule_result.get("commerce_legit")
            scam_m = rule_result.get("scam_markers") or []
            if rule_legit and len(scam_m) == 0:
                risk_score = min(risk_score, max(0.12, warning_th - 0.06))
            elif rule_legit and len(scam_m) <= 1:
                risk_score = min(risk_score, danger_th - 0.08)

            # 确定风险等级（阈值随 sensitivity 变化）
            if risk_score > danger_th:
                risk_level = RiskLevel.DANGER
            elif risk_score > warning_th:
                risk_level = RiskLevel.WARNING
            else:
                risk_level = RiskLevel.SAFE
            
            confidence = max(
                bert_risk_score if bert_risk_score is not None else 0,
                simple_risk_score if simple_risk_score is not None else 0,
                rule_result['risk_score'],
                0.5
            )
            
            # 生成检测理由和建议
            reasons = rule_result['reasons']
            suggestions = rule_result['suggestions']
            
            if bert_is_risky and bert_risk_score is not None:
                reasons.insert(0, f"BERT AI模型判定为风险内容（置信度 {bert_risk_score:.0%}）")
            if simple_is_risky and simple_risk_score is not None:
                reasons.insert(0 if not bert_is_risky else 1, f"TF-IDF AI模型判定为风险内容（置信度 {simple_risk_score:.0%}）")

            # 老年人认知操控手法（突破点2）—— 写入可解释理由
            manipulation_detail = describe_features(manipulation_features, lang="zh")
            if manipulation_detail:
                names = "、".join(d["name"] for d in manipulation_detail)
                tag = "AI模型" if manipulation_source == "cognitive_model" else "规则"
                reasons.insert(0, f"识别到针对老人的诈骗操控手法（{tag}）：{names}")
            
            if not reasons:
                if risk_level == RiskLevel.SAFE:
                    reasons = ["AI模型和规则引擎均未发现风险"]
                else:
                    reasons = ["综合分析发现潜在风险"]
            
            if not suggestions and risk_level != RiskLevel.SAFE:
                suggestions = ["建议谨慎对待该内容", "如遇可疑情况请拨打96110反诈热线"]
            
            # 生成解释
            explanation = self._generate_explanation(
                risk_level, risk_score, 0.0, 0.0, reasons
            )
            
            inference_time = time.time() - start_time
            
            return DetectionOutput(
                risk_level=risk_level,
                confidence=confidence,
                risk_score=risk_score,
                text_risk=bert_risk_score if bert_risk_score is not None else rule_result['risk_score'],
                visual_risk=0.0,
                audio_risk=0.0,
                reasons=reasons,
                suggestions=suggestions,
                attention_weights=None,
                explanation=explanation,
                inference_time=inference_time,
                detection_method=detection_method,
                bert_score=bert_risk_score,
                tfidf_score=simple_risk_score,
                manipulation_features=manipulation_features,
                manipulation_detail=manipulation_detail,
                manipulation_source=manipulation_source,
                cognitive_risk=cognitive_risk_score,
            )
            
        except Exception as e:
            logger.error(f"检测失败: {e}", exc_info=True)
            return self._fallback_detection(input_data)
    
    def _effective_scam_markers(self, text: str) -> List[str]:
        """排除辟谣/提醒语境中的高危词（如「不要转账」）。"""
        text_lower = text.lower()
        hits = [m for m in self.HIGH_RISK_SCAM_MARKERS if m in text_lower]
        filtered: List[str] = []
        for marker in hits:
            if marker == "转账" and re.search(
                r"(不要|勿|别|切勿|请勿).{0,12}转账|不要.{0,8}私信.{0,8}转账", text
            ):
                continue
            if marker in ("加微信", "加微") and re.search(
                r"(不要|勿|别).{0,10}(加微信|加微|私信)", text
            ):
                continue
            filtered.append(marker)
        return filtered

    def _rule_based_detection(self, text: str) -> Dict:
        """
        基于规则的检测（增强AI detection）
        
        Args:
            text: 输入文本
            
        Returns:
            规则检测结果
        """
        risk_score = 0.0
        reasons = []
        suggestions = []
        
        text_lower = text.lower()  # 大小写不敏感匹配
        legit_hits_early = [m for m in self.LEGIT_COMMERCE_MARKERS if m in text_lower]

        # 科普/辟谣语境：单独提到保健品不等于诈骗
        edu_safe = [
            "不能代替", "不能替代", "不要轻信", "建议咨询", "正规医院",
            "遵医嘱", "反对虚假宣传", "警惕夸大", "理性看待", "科学科普",
        ]
        if any(p in text for p in edu_safe):
            return {
                'risk_score': min(0.12, 0.0),
                'reasons': [],
                'suggestions': ["如有疑问可咨询家人或社区医生"],
            }

        # 保健品/营养品仅在与推销话术共现时计分
        weak_medical = ["保健品", "营养品", "保健产品"]
        scam_combo = [
            "加微信", "加微", "私信", "转账", "汇款", "包治", "根治",
            "特效", "央视推荐", "订购热线", "保证治愈", "祖传", "包治百病",
        ]
        for wm in weak_medical:
            if wm in text_lower and any(c in text_lower for c in scam_combo):
                risk_score += 0.35
                reasons.append(f"推销话术：提到「{wm}」并诱导私下联系或夸大疗效")
                suggestions.append("正规科普不会要求加微信买产品")
                break
        
        # 金融诈骗检测（直播带货常见「限时优惠」等促销词单独出现时不加重）
        financial_matches = [kw for kw in self.FINANCIAL_KEYWORDS if kw.lower() in text_lower]
        if len(legit_hits_early) >= 2:
            soft_promo = {"限时优惠", "包邮", "现货", "正品", "官方旗舰店"}
            financial_matches = [m for m in financial_matches if m not in soft_promo]
        if financial_matches:
            risk_score += min(len(financial_matches) * 0.15, 0.5)
            reasons.append(f"检测到{len(financial_matches)}个金融风险关键词: {', '.join(financial_matches[:3])}")
            suggestions.append("投资需谨慎，高收益往往伴随高风险")
            suggestions.append("不要轻易相信保证收益的投资项目")
        
        # 医疗虚假信息检测
        medical_matches = [kw for kw in self.MEDICAL_KEYWORDS if kw.lower() in text_lower]
        if medical_matches:
            risk_score += min(len(medical_matches) * 0.15, 0.5)
            reasons.append(f"检测到{len(medical_matches)}个医疗风险关键词: {', '.join(medical_matches[:3])}")
            suggestions.append("有病请找正规医院，不要轻信偏方")
            suggestions.append("保健品不能替代药物治疗")
        
        # 紧急性检测
        urgency_matches = [kw for kw in self.URGENCY_KEYWORDS if kw.lower() in text_lower]
        if urgency_matches:
            risk_score += min(len(urgency_matches) * 0.1, 0.3)
            reasons.append(f"检测到{len(urgency_matches)}个紧急性诱导词汇")
            suggestions.append("冷静思考，不要被紧急性语言误导")
        
        # 联系方式检测
        contact_patterns = ["微信", "qq", "电话", "手机", "转账", "汇款"]
        contact_matches = [p for p in contact_patterns if p in text_lower]
        if contact_matches and risk_score > 0.2:
            risk_score += 0.1
            reasons.append("含有联系方式且存在其他风险因素")
            suggestions.append("不要轻易添加陌生人联系方式或转账")
        
        risk_score = min(risk_score, 1.0)

        legit_hits = legit_hits_early or [m for m in self.LEGIT_COMMERCE_MARKERS if m in text_lower]
        scam_hits = self._effective_scam_markers(text)
        # 正常推销：平台内购买 + 无高危话术 → 压低规则分，交给 BERT 语义
        if len(legit_hits) >= 2 and not scam_hits:
            risk_score = min(risk_score, 0.22)
            reasons = [
                r for r in reasons
                if "医疗风险" not in r and "诈骗常用" not in r and "金融风险" not in r
            ]
            if not reasons:
                reasons.append("内容为平台内商品介绍，未发现典型诈骗话术")
        elif len(legit_hits) >= 2 and len(scam_hits) <= 1:
            risk_score = min(risk_score, 0.38)
        
        return {
            'risk_score': risk_score,
            'reasons': reasons,
            'suggestions': suggestions,
            'commerce_legit': len(legit_hits) > 0,
            'scam_markers': scam_hits[:5],
        }
    
    def _generate_explanation(
        self,
        risk_level: RiskLevel,
        text_risk: float,
        visual_risk: float,
        audio_risk: float,
        reasons: List[str]
    ) -> str:
        """生成可解释性说明"""
        
        explanations = []
        
        # 主要风险来源
        risks = [
            ("文本内容", text_risk),
            ("视觉内容", visual_risk),
            ("音频内容", audio_risk)
        ]
        
        main_risk_source = max(risks, key=lambda x: x[1])
        
        if risk_level == RiskLevel.DANGER:
            explanations.append(f"⚠️ 高风险警告：检测到可能的诈骗或虚假信息")
            explanations.append(f"主要风险来源：{main_risk_source[0]}（风险度：{main_risk_source[1]:.1%}）")
        elif risk_level == RiskLevel.WARNING:
            explanations.append(f"⚡ 注意：内容存在可疑信息")
            explanations.append(f"主要关注：{main_risk_source[0]}")
        else:
            explanations.append("✅ 内容相对安全，未发现明显风险")
        
        if reasons:
            explanations.append("具体原因：" + "；".join(reasons[:3]))
        
        return "\n".join(explanations)
    
    def _fallback_detection(self, input_data: MultimodalInput) -> DetectionOutput:
        """降级检测（当模型失败时）"""
        text = input_data.text or ""
        rule_result = self._rule_based_detection(text)
        
        risk_score = rule_result['risk_score']
        if risk_score > 0.7:
            risk_level = RiskLevel.DANGER
        elif risk_score > 0.4:
            risk_level = RiskLevel.WARNING
        else:
            risk_level = RiskLevel.SAFE
        
        feats = weak_label(text)
        return DetectionOutput(
            risk_level=risk_level,
            confidence=0.6,
            risk_score=risk_score,
            text_risk=risk_score,
            visual_risk=0.0,
            audio_risk=0.0,
            reasons=rule_result['reasons'] or ["使用规则引擎检测"],
            suggestions=rule_result['suggestions'] or ["建议谨慎对待内容"],
            explanation="注：AI模型暂时不可用，使用规则引擎检测",
            inference_time=0.0,
            manipulation_features=feats,
            manipulation_detail=describe_features(feats, lang="zh"),
            manipulation_source="weak_rule" if feats else None,
        )
    
    async def detect_batch(
        self,
        inputs: List[MultimodalInput]
    ) -> List[DetectionOutput]:
        """批量检测"""
        results = []
        for input_data in inputs:
            result = await self.detect(input_data)
            results.append(result)
        return results


# 全局检测器实例
_detector: Optional[MultimodalDetector] = None


def get_detector(
    model_path: Optional[str] = None,
    simple_model_path: Optional[str] = None,
    cognitive_model_path: Optional[str] = None,
) -> MultimodalDetector:
    """获取检测器实例（单例模式）"""
    global _detector
    if _detector is None:
        _detector = MultimodalDetector(
            model_path=model_path,
            simple_model_path=simple_model_path,
            cognitive_model_path=cognitive_model_path,
        )
    return _detector


async def detect_content(
    text: Optional[str] = None,
    image: Optional[Any] = None,
    audio: Optional[np.ndarray] = None
) -> DetectionOutput:
    """
    便捷检测函数
    
    Args:
        text: 文本内容
        image: 图像
        audio: 音频
        
    Returns:
        检测结果
    """
    detector = get_detector()
    input_data = MultimodalInput(text=text, image=image, audio=audio)
    return await detector.detect(input_data)


# 导出
__all__ = [
    'MultimodalDetector',
    'MultimodalFusionModel',
    'MultimodalInput',
    'DetectionOutput',
    'RiskLevel',
    'get_detector',
    'detect_content'
]

