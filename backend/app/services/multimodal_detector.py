<<<<<<< Current (Your changes)
=======
"""
多模态虚假信息检测器
基于FakeSV和SpotFake论文架构
支持文本、视觉、音频三模态融合检测
"""

import os
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import numpy as np
from loguru import logger

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
    
    # 领域特定关键词
    FINANCIAL_KEYWORDS = [
        "保证收益", "无风险", "月入万元", "稳赚不赔", "高收益",
        "内幕消息", "限时优惠", "投资理财", "虚拟货币", "传销",
        "无抵押贷款", "秒批", "黑户贷款", "刷单", "套现"
    ]
    
    MEDICAL_KEYWORDS = [
        "包治百病", "神奇疗效", "祖传秘方", "一次根治", "永不复发",
        "药到病除", "100%治愈", "三天见效", "医院不告诉你", "特效药",
        "保健品", "偏方", "土方", "民间验方"
    ]
    
    URGENCY_KEYWORDS = [
        "赶紧", "立即", "马上", "紧急", "限时", "截止今晚",
        "最后一天", "错过后悔", "机不可失", "名额有限"
    ]
    
    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "auto",
        fusion_strategy: str = "attention"
    ):
        """
        初始化检测器
        
        Args:
            model_path: 预训练模型路径
            device: 运行设备
            fusion_strategy: 融合策略
        """
        # 设置设备
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        logger.info(f"检测器运行设备: {self.device}")
        
        # 初始化模型
        self.model = MultimodalFusionModel(
            hidden_dim=768,
            num_classes=3,
            fusion_strategy=fusion_strategy
        )
        
        # 加载预训练权重
        if model_path and os.path.exists(model_path):
            self._load_model(model_path)
        
        self.model.to(self.device)
        self.model.eval()
        
        # 风险等级映射
        self.risk_levels = [RiskLevel.SAFE, RiskLevel.WARNING, RiskLevel.DANGER]
        
        logger.info("多模态检测器初始化完成")
    
    def _load_model(self, model_path: str):
        """加载模型权重"""
        try:
            checkpoint = torch.load(model_path, map_location=self.device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            logger.info(f"模型权重加载成功: {model_path}")
        except Exception as e:
            logger.error(f"加载模型失败: {e}")
    
    async def detect(
        self,
        input_data: Union[MultimodalInput, str, Dict]
    ) -> DetectionOutput:
        """
        执行多模态检测
        
        Args:
            input_data: 多模态输入数据
            
        Returns:
            检测结果
        """
        start_time = time.time()
        
        # 解析输入
        if isinstance(input_data, str):
            input_data = MultimodalInput(text=input_data)
        elif isinstance(input_data, dict):
            input_data = MultimodalInput(**input_data)
        
        try:
            # 准备输入数据
            texts = [input_data.text] if input_data.text else None
            images = [input_data.image] if input_data.image else None
            audios = [input_data.audio] if input_data.audio else None
            
            # 模型推理
            with torch.no_grad():
                outputs = self.model(
                    texts=texts,
                    images=images,
                    audios=audios,
                    return_attention=True
                )
            
            # 获取预测结果
            predicted_class = outputs['predicted_class'][0].item()
            probabilities = outputs['probabilities'][0]
            
            risk_level = self.risk_levels[predicted_class]
            confidence = probabilities[predicted_class].item()
            risk_score = probabilities[2].item()  # danger类概率
            
            # 获取各模态风险
            text_risk = outputs['text_risk'][0].item() if texts else 0.0
            visual_risk = outputs['visual_risk'][0].item() if images else 0.0
            audio_risk = outputs['audio_risk'][0].item() if audios else 0.0
            
            # 规则增强检测
            rule_result = self._rule_based_detection(input_data.text or "")
            
            # 综合风险评估
            if rule_result['risk_score'] > 0.7:
                risk_score = max(risk_score, rule_result['risk_score'])
                if risk_score > 0.7:
                    risk_level = RiskLevel.DANGER
                elif risk_score > 0.4:
                    risk_level = RiskLevel.WARNING
            
            # 生成解释
            reasons = rule_result['reasons']
            suggestions = rule_result['suggestions']
            explanation = self._generate_explanation(
                risk_level, text_risk, visual_risk, audio_risk, reasons
            )
            
            # 处理注意力权重
            attention_weights = None
            if outputs['attention_weights']:
                attention_weights = {
                    k: v[0].cpu().numpy().tolist() 
                    for k, v in outputs['attention_weights'].items()
                }
            
            inference_time = time.time() - start_time
            
            return DetectionOutput(
                risk_level=risk_level,
                confidence=confidence,
                risk_score=risk_score,
                text_risk=text_risk,
                visual_risk=visual_risk,
                audio_risk=audio_risk,
                reasons=reasons,
                suggestions=suggestions,
                attention_weights=attention_weights,
                explanation=explanation,
                inference_time=inference_time
            )
            
        except Exception as e:
            logger.error(f"检测失败: {e}", exc_info=True)
            return self._fallback_detection(input_data)
    
    def _rule_based_detection(self, text: str) -> Dict:
        """
        基于规则的检测（增强AI检测）
        
        Args:
            text: 输入文本
            
        Returns:
            规则检测结果
        """
        risk_score = 0.0
        reasons = []
        suggestions = []
        
        # 金融诈骗检测
        financial_matches = [kw for kw in self.FINANCIAL_KEYWORDS if kw in text]
        if financial_matches:
            risk_score += min(len(financial_matches) * 0.15, 0.5)
            reasons.append(f"检测到{len(financial_matches)}个金融风险关键词: {', '.join(financial_matches[:3])}")
            suggestions.append("投资需谨慎，高收益往往伴随高风险")
            suggestions.append("不要轻易相信保证收益的投资项目")
        
        # 医疗虚假信息检测
        medical_matches = [kw for kw in self.MEDICAL_KEYWORDS if kw in text]
        if medical_matches:
            risk_score += min(len(medical_matches) * 0.15, 0.5)
            reasons.append(f"检测到{len(medical_matches)}个医疗风险关键词: {', '.join(medical_matches[:3])}")
            suggestions.append("有病请找正规医院，不要轻信偏方")
            suggestions.append("保健品不能替代药物治疗")
        
        # 紧急性检测
        urgency_matches = [kw for kw in self.URGENCY_KEYWORDS if kw in text]
        if urgency_matches:
            risk_score += min(len(urgency_matches) * 0.1, 0.3)
            reasons.append(f"检测到{len(urgency_matches)}个紧急性诱导词汇")
            suggestions.append("冷静思考，不要被紧急性语言误导")
        
        # 联系方式检测
        contact_patterns = ["微信", "qq", "电话", "手机", "转账", "汇款"]
        contact_matches = [p for p in contact_patterns if p in text.lower()]
        if contact_matches and risk_score > 0.2:
            risk_score += 0.1
            reasons.append("含有联系方式且存在其他风险因素")
            suggestions.append("不要轻易添加陌生人联系方式或转账")
        
        risk_score = min(risk_score, 1.0)
        
        return {
            'risk_score': risk_score,
            'reasons': reasons,
            'suggestions': suggestions
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
            inference_time=0.0
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


def get_detector() -> MultimodalDetector:
    """获取检测器实例（单例模式）"""
    global _detector
    if _detector is None:
        _detector = MultimodalDetector()
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





>>>>>>> Incoming (Background Agent changes)

