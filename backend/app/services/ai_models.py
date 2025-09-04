"""
AI模型集成服务
支持ChatGLM、LLaMA、BERT等多个大模型
"""

import os
import asyncio
import time
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum
import numpy as np
from loguru import logger

# AI框架导入
try:
    import torch
    from transformers import (
        AutoTokenizer, 
        AutoModelForSequenceClassification,
        AutoModel,
        pipeline
    )
    from peft import PeftModel, LoraConfig, TaskType
    TORCH_AVAILABLE = True
except ImportError:
    logger.warning("PyTorch或Transformers未安装，将使用模拟模式")
    TORCH_AVAILABLE = False


class ModelType(Enum):
    """模型类型枚举"""
    CHATGLM = "chatglm"
    LLAMA = "llama"  
    BERT = "bert"
    VICUNA = "vicuna"
    RULE_BASED = "rule_based"


@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    type: ModelType
    path: str
    device: str = "cpu"
    max_length: int = 512
    batch_size: int = 8
    use_lora: bool = False
    lora_path: Optional[str] = None


class AIModelManager:
    """AI模型管理器"""
    
    def __init__(self):
        self.models: Dict[str, Any] = {}
        self.tokenizers: Dict[str, Any] = {}
        self.configs: Dict[str, ModelConfig] = {}
        self.device = torch.device("cuda" if torch.cuda.is_available() and TORCH_AVAILABLE else "cpu")
        logger.info(f"AI模型管理器初始化，设备: {self.device}")
        
        # 初始化模型配置
        self._init_model_configs()
        
        # 加载模型
        asyncio.create_task(self._load_models())
    
    def _init_model_configs(self):
        """初始化模型配置"""
        self.configs = {
            "chatglm": ModelConfig(
                name="ChatGLM-6B",
                type=ModelType.CHATGLM,
                path="THUDM/chatglm-6b",
                device=str(self.device),
                max_length=2048,
                use_lora=True,
                lora_path="./models/chatglm_lora"
            ),
            "bert": ModelConfig(
                name="Chinese-BERT-wwm",
                type=ModelType.BERT,
                path="hfl/chinese-bert-wwm-ext",
                device=str(self.device),
                max_length=512
            ),
            "llama": ModelConfig(
                name="LLaMA-7B-Chinese",
                type=ModelType.LLAMA,
                path="ziqingyang/chinese-llama-7b",
                device=str(self.device),
                max_length=1024,
                use_lora=True,
                lora_path="./models/llama_lora"
            )
        }
    
    async def _load_models(self):
        """异步加载所有模型"""
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch不可用，使用模拟模型")
            return
        
        for model_id, config in self.configs.items():
            try:
                logger.info(f"正在加载模型: {config.name}")
                await self._load_single_model(model_id, config)
                logger.info(f"模型 {config.name} 加载成功")
            except Exception as e:
                logger.error(f"模型 {config.name} 加载失败: {e}")
    
    async def _load_single_model(self, model_id: str, config: ModelConfig):
        """加载单个模型"""
        if config.type == ModelType.CHATGLM:
            await self._load_chatglm(model_id, config)
        elif config.type == ModelType.BERT:
            await self._load_bert(model_id, config)
        elif config.type == ModelType.LLAMA:
            await self._load_llama(model_id, config)
    
    async def _load_chatglm(self, model_id: str, config: ModelConfig):
        """加载ChatGLM模型"""
        try:
            from transformers import AutoTokenizer, AutoModel
            
            # 加载tokenizer
            tokenizer = AutoTokenizer.from_pretrained(
                config.path, 
                trust_remote_code=True
            )
            
            # 加载模型
            model = AutoModel.from_pretrained(
                config.path,
                trust_remote_code=True,
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32,
                device_map="auto"
            )
            
            # 加载LoRA权重（如果有）
            if config.use_lora and config.lora_path and os.path.exists(config.lora_path):
                model = PeftModel.from_pretrained(model, config.lora_path)
                logger.info(f"已加载LoRA权重: {config.lora_path}")
            
            model.eval()
            
            self.tokenizers[model_id] = tokenizer
            self.models[model_id] = model
            
        except Exception as e:
            logger.error(f"ChatGLM加载失败: {e}")
            # 使用模拟模型
            self.models[model_id] = MockModel(config)
            self.tokenizers[model_id] = MockTokenizer()
    
    async def _load_bert(self, model_id: str, config: ModelConfig):
        """加载BERT模型"""
        try:
            # 加载用于虚假信息分类的BERT模型
            tokenizer = AutoTokenizer.from_pretrained(config.path)
            model = AutoModelForSequenceClassification.from_pretrained(
                config.path,
                num_labels=3,  # safe, warning, danger
                torch_dtype=torch.float32
            )
            
            # 如果有微调权重，加载它们
            checkpoint_path = f"./models/{model_id}_finetuned.pt"
            if os.path.exists(checkpoint_path):
                checkpoint = torch.load(checkpoint_path, map_location=self.device)
                model.load_state_dict(checkpoint['model_state_dict'])
                logger.info(f"已加载微调权重: {checkpoint_path}")
            
            model.to(self.device)
            model.eval()
            
            self.tokenizers[model_id] = tokenizer
            self.models[model_id] = model
            
        except Exception as e:
            logger.error(f"BERT加载失败: {e}")
            self.models[model_id] = MockModel(config)
            self.tokenizers[model_id] = MockTokenizer()
    
    async def _load_llama(self, model_id: str, config: ModelConfig):
        """加载LLaMA模型"""
        try:
            from transformers import LlamaTokenizer, LlamaForSequenceClassification
            
            tokenizer = LlamaTokenizer.from_pretrained(config.path)
            model = LlamaForSequenceClassification.from_pretrained(
                config.path,
                num_labels=3,
                torch_dtype=torch.float16 if self.device.type == "cuda" else torch.float32,
                device_map="auto"
            )
            
            # 加载LoRA权重
            if config.use_lora and config.lora_path and os.path.exists(config.lora_path):
                model = PeftModel.from_pretrained(model, config.lora_path)
            
            model.eval()
            
            self.tokenizers[model_id] = tokenizer
            self.models[model_id] = model
            
        except Exception as e:
            logger.error(f"LLaMA加载失败: {e}")
            self.models[model_id] = MockModel(config)
            self.tokenizers[model_id] = MockTokenizer()
    
    async def predict(self, model_id: str, text: str, features: Dict = None) -> Dict:
        """
        使用指定模型进行预测
        
        Args:
            model_id: 模型ID
            text: 输入文本
            features: 额外特征
            
        Returns:
            预测结果字典
        """
        if model_id not in self.models:
            raise ValueError(f"模型 {model_id} 未加载")
        
        model = self.models[model_id]
        tokenizer = self.tokenizers[model_id]
        config = self.configs[model_id]
        
        start_time = time.time()
        
        try:
            # 根据模型类型调用不同的预测方法
            if config.type == ModelType.CHATGLM:
                result = await self._predict_chatglm(model, tokenizer, text, config)
            elif config.type == ModelType.BERT:
                result = await self._predict_bert(model, tokenizer, text, config)
            elif config.type == ModelType.LLAMA:
                result = await self._predict_llama(model, tokenizer, text, config)
            else:
                result = await self._predict_mock(text)
            
            # 添加预测时间
            result['inference_time'] = time.time() - start_time
            result['model'] = config.name
            
            return result
            
        except Exception as e:
            logger.error(f"模型 {model_id} 预测失败: {e}")
            return self._get_fallback_result(text)
    
    async def _predict_chatglm(self, model, tokenizer, text: str, config: ModelConfig) -> Dict:
        """ChatGLM预测"""
        try:
            # 构建提示词
            prompt = f"""请分析以下内容是否包含虚假信息或诈骗内容：

内容：{text}

请从以下几个方面分析：
1. 是否包含金融诈骗（如保证高收益、无风险投资等）
2. 是否包含医疗虚假信息（如包治百病、祖传秘方等）
3. 是否使用诱导性语言（如紧急、限时、错过后悔等）
4. 是否要求提供个人信息或转账

分析结果请给出：
- 风险等级：安全/警告/危险
- 置信度：0-1之间的数值
- 主要风险点：列出主要问题
- 建议：给出具体建议
"""
            
            # 生成响应
            response, _ = model.chat(tokenizer, prompt, history=[])
            
            # 解析响应
            result = self._parse_chatglm_response(response)
            
            return result
            
        except Exception as e:
            logger.error(f"ChatGLM预测错误: {e}")
            return self._get_fallback_result(text)
    
    async def _predict_bert(self, model, tokenizer, text: str, config: ModelConfig) -> Dict:
        """BERT预测"""
        try:
            # 文本编码
            inputs = tokenizer(
                text,
                padding=True,
                truncation=True,
                max_length=config.max_length,
                return_tensors="pt"
            ).to(self.device)
            
            # 模型推理
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
            
            # 获取预测结果
            predicted_class = torch.argmax(probabilities, dim=-1).item()
            confidence = probabilities[0][predicted_class].item()
            
            # 映射到风险等级
            risk_levels = ['safe', 'warning', 'danger']
            
            return {
                'prediction': risk_levels[predicted_class],
                'confidence': float(confidence),
                'probabilities': {
                    'safe': float(probabilities[0][0]),
                    'warning': float(probabilities[0][1]),
                    'danger': float(probabilities[0][2])
                },
                'explanation': self._generate_bert_explanation(text, predicted_class),
                'features': self._extract_bert_features(outputs)
            }
            
        except Exception as e:
            logger.error(f"BERT预测错误: {e}")
            return self._get_fallback_result(text)
    
    async def _predict_llama(self, model, tokenizer, text: str, config: ModelConfig) -> Dict:
        """LLaMA预测"""
        try:
            # 构建输入
            inputs = tokenizer(
                text,
                padding=True,
                truncation=True,
                max_length=config.max_length,
                return_tensors="pt"
            ).to(self.device)
            
            # 生成预测
            with torch.no_grad():
                outputs = model(**inputs)
                logits = outputs.logits
                probabilities = torch.softmax(logits, dim=-1)
            
            predicted_class = torch.argmax(probabilities, dim=-1).item()
            confidence = probabilities[0][predicted_class].item()
            
            risk_levels = ['safe', 'warning', 'danger']
            
            return {
                'prediction': risk_levels[predicted_class],
                'confidence': float(confidence),
                'explanation': f"LLaMA模型检测到{risk_levels[predicted_class]}级别风险",
                'features': {
                    'text_risk': float(probabilities[0][2]),
                    'behavior_risk': 0,
                    'visual_risk': 0,
                    'audio_risk': 0
                }
            }
            
        except Exception as e:
            logger.error(f"LLaMA预测错误: {e}")
            return self._get_fallback_result(text)
    
    async def _predict_mock(self, text: str) -> Dict:
        """模拟预测（用于测试）"""
        # 简单的关键词检测
        danger_keywords = ['保证收益', '月入万元', '包治百病']
        warning_keywords = ['投资', '理财', '保健品']
        
        risk_level = 'safe'
        confidence = 0.9
        
        for keyword in danger_keywords:
            if keyword in text:
                risk_level = 'danger'
                confidence = 0.85
                break
        
        if risk_level == 'safe':
            for keyword in warning_keywords:
                if keyword in text:
                    risk_level = 'warning'
                    confidence = 0.75
                    break
        
        return {
            'prediction': risk_level,
            'confidence': confidence,
            'explanation': f"基于关键词检测的{risk_level}级别风险",
            'features': {
                'text_risk': 0.8 if risk_level == 'danger' else 0.5 if risk_level == 'warning' else 0.2,
                'behavior_risk': 0,
                'visual_risk': 0,
                'audio_risk': 0
            }
        }
    
    def _parse_chatglm_response(self, response: str) -> Dict:
        """解析ChatGLM的响应"""
        # 简单的响应解析，实际应用中需要更复杂的解析逻辑
        result = {
            'prediction': 'safe',
            'confidence': 0.5,
            'explanation': response,
            'features': {}
        }
        
        if '危险' in response or '高风险' in response:
            result['prediction'] = 'danger'
            result['confidence'] = 0.85
        elif '警告' in response or '可疑' in response:
            result['prediction'] = 'warning'
            result['confidence'] = 0.70
        else:
            result['prediction'] = 'safe'
            result['confidence'] = 0.90
        
        return result
    
    def _generate_bert_explanation(self, text: str, predicted_class: int) -> str:
        """生成BERT预测的解释"""
        explanations = [
            "BERT模型判断内容安全，未发现明显风险因素",
            "BERT模型检测到可疑内容，建议谨慎对待",
            "BERT模型发现高风险内容，强烈建议避免"
        ]
        return explanations[predicted_class]
    
    def _extract_bert_features(self, outputs) -> Dict:
        """提取BERT的特征重要性"""
        # 这里可以使用注意力权重或其他可解释性方法
        return {
            'text_risk': 0.7,
            'behavior_risk': 0.1,
            'visual_risk': 0.1,
            'audio_risk': 0.1
        }
    
    def _get_fallback_result(self, text: str) -> Dict:
        """降级结果"""
        return {
            'prediction': 'warning',
            'confidence': 0.5,
            'explanation': 'AI模型暂时不可用，使用默认策略',
            'features': {
                'text_risk': 0.5,
                'behavior_risk': 0,
                'visual_risk': 0,
                'audio_risk': 0
            }
        }
    
    async def ensemble_predict(self, text: str, features: Dict = None) -> Dict:
        """
        集成多个模型的预测结果
        
        Args:
            text: 输入文本
            features: 额外特征
            
        Returns:
            集成预测结果
        """
        predictions = []
        weights = {'chatglm': 0.4, 'bert': 0.3, 'llama': 0.3}
        
        # 并行预测
        tasks = []
        for model_id in self.models.keys():
            if model_id in weights:
                tasks.append(self.predict(model_id, text, features))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 处理结果
        for i, result in enumerate(results):
            if not isinstance(result, Exception):
                predictions.append(result)
        
        if not predictions:
            return self._get_fallback_result(text)
        
        # 加权投票
        final_prediction = self._weighted_voting(predictions, weights)
        
        return final_prediction
    
    def _weighted_voting(self, predictions: List[Dict], weights: Dict) -> Dict:
        """加权投票集成"""
        vote_scores = {'safe': 0, 'warning': 0, 'danger': 0}
        total_confidence = 0
        explanations = []
        
        for pred in predictions:
            model_name = pred.get('model', 'unknown')
            weight = weights.get(model_name.lower(), 0.1)
            
            vote_scores[pred['prediction']] += weight * pred['confidence']
            total_confidence += pred['confidence'] * weight
            explanations.append(f"{model_name}: {pred['explanation']}")
        
        # 确定最终预测
        final_prediction = max(vote_scores, key=vote_scores.get)
        
        return {
            'prediction': final_prediction,
            'confidence': total_confidence / len(predictions),
            'explanation': ' | '.join(explanations),
            'vote_scores': vote_scores,
            'model_predictions': predictions
        }
    
    def get_model_status(self) -> Dict:
        """获取所有模型的状态"""
        status = {}
        for model_id, config in self.configs.items():
            status[model_id] = {
                'name': config.name,
                'loaded': model_id in self.models,
                'device': str(self.device),
                'type': config.type.value,
                'max_length': config.max_length
            }
        return status


class MockModel:
    """模拟模型（用于测试和降级）"""
    def __init__(self, config: ModelConfig):
        self.config = config
    
    def __call__(self, *args, **kwargs):
        # 返回模拟结果
        return type('MockOutput', (), {'logits': torch.randn(1, 3)})()
    
    def chat(self, tokenizer, prompt, history):
        return f"模拟响应：检测到可疑内容", []


class MockTokenizer:
    """模拟Tokenizer"""
    def __call__(self, text, **kwargs):
        return type('MockInputs', (), {
            'input_ids': torch.randint(0, 1000, (1, 10)),
            'attention_mask': torch.ones(1, 10),
            'to': lambda x: self
        })()


# 全局模型管理器实例
model_manager = AIModelManager()


# API接口函数
async def detect_with_chatglm(text: str, features: Dict = None) -> Dict:
    """使用ChatGLM检测"""
    return await model_manager.predict('chatglm', text, features)


async def detect_with_bert(text: str, features: Dict = None) -> Dict:
    """使用BERT检测"""
    return await model_manager.predict('bert', text, features)


async def detect_with_llama(text: str, features: Dict = None) -> Dict:
    """使用LLaMA检测"""
    return await model_manager.predict('llama', text, features)


async def detect_with_ensemble(text: str, features: Dict = None) -> Dict:
    """使用集成方法检测"""
    return await model_manager.ensemble_predict(text, features)


def get_models_status() -> Dict:
    """获取模型状态"""
    return model_manager.get_model_status()
