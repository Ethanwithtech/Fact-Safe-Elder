#!/usr/bin/env python3
"""
基于BERT + 注意力机制的虚假信息检测模型

参考文献:
1. AnswerFact: Fact Checking in Product Question Answering (Zhang et al., EMNLP 2020)
   - 使用证据排序机制进行事实核查
   - 多任务学习框架
   
2. Attention-based Rumor Detection with Tree-structured RvNN (Ma et al., TIST 2020)
   - 基于注意力的递归神经网络
   - 利用传播结构信息

本实现:
- 使用Chinese-BERT-wwm作为编码器
- 添加多头注意力机制捕捉关键特征
- 支持三分类: safe, warning, danger
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader
from typing import Dict, List, Optional, Tuple
import json
import numpy as np

# 检查transformers库是否可用
try:
    from transformers import (
        BertModel, 
        BertTokenizer, 
        BertConfig,
        AdamW,
        get_linear_schedule_with_warmup
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("[WARN] transformers库未安装，部分功能不可用")


class MultiHeadSelfAttention(nn.Module):
    """
    多头自注意力机制
    参考Ma et al. (2020)的注意力机制设计
    """
    def __init__(self, hidden_size: int, num_heads: int = 8, dropout: float = 0.1):
        super().__init__()
        self.hidden_size = hidden_size
        self.num_heads = num_heads
        self.head_dim = hidden_size // num_heads
        
        assert hidden_size % num_heads == 0, "hidden_size必须能被num_heads整除"
        
        self.query = nn.Linear(hidden_size, hidden_size)
        self.key = nn.Linear(hidden_size, hidden_size)
        self.value = nn.Linear(hidden_size, hidden_size)
        self.output = nn.Linear(hidden_size, hidden_size)
        
        self.dropout = nn.Dropout(dropout)
        self.scale = self.head_dim ** -0.5
    
    def forward(self, x: torch.Tensor, mask: Optional[torch.Tensor] = None):
        batch_size, seq_len, _ = x.size()
        
        # 线性变换
        Q = self.query(x)
        K = self.key(x)
        V = self.value(x)
        
        # 重塑为多头形式
        Q = Q.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        K = K.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        V = V.view(batch_size, seq_len, self.num_heads, self.head_dim).transpose(1, 2)
        
        # 计算注意力分数
        scores = torch.matmul(Q, K.transpose(-2, -1)) * self.scale
        
        if mask is not None:
            mask = mask.unsqueeze(1).unsqueeze(2)
            scores = scores.masked_fill(mask == 0, float('-inf'))
        
        attn_weights = F.softmax(scores, dim=-1)
        attn_weights = self.dropout(attn_weights)
        
        # 加权求和
        context = torch.matmul(attn_weights, V)
        context = context.transpose(1, 2).contiguous().view(batch_size, seq_len, self.hidden_size)
        
        output = self.output(context)
        
        return output, attn_weights


class EvidenceRankingModule(nn.Module):
    """
    证据排序模块
    参考AnswerFact (Zhang et al., 2020)的证据排序组件
    用于识别文本中的关键证据
    """
    def __init__(self, hidden_size: int):
        super().__init__()
        self.evidence_scorer = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(hidden_size // 2, 1)
        )
    
    def forward(self, hidden_states: torch.Tensor, attention_mask: torch.Tensor):
        # 计算每个token的证据分数
        evidence_scores = self.evidence_scorer(hidden_states).squeeze(-1)
        
        # 使用attention_mask屏蔽padding
        evidence_scores = evidence_scores.masked_fill(attention_mask == 0, float('-inf'))
        evidence_weights = F.softmax(evidence_scores, dim=-1)
        
        # 加权聚合
        weighted_hidden = torch.bmm(evidence_weights.unsqueeze(1), hidden_states).squeeze(1)
        
        return weighted_hidden, evidence_weights


class BERTAttentionDetector(nn.Module):
    """
    基于BERT和注意力机制的虚假信息检测模型
    
    架构:
    1. BERT编码器 - 提取语义特征
    2. 多头自注意力 - 捕捉关键信息
    3. 证据排序模块 - 识别关键证据
    4. 分类头 - 三分类输出
    """
    
    def __init__(
        self, 
        pretrained_model: str = "hfl/chinese-bert-wwm-ext",
        num_classes: int = 3,
        hidden_dropout: float = 0.1,
        attention_heads: int = 8,
        use_evidence_ranking: bool = True
    ):
        super().__init__()
        
        self.num_classes = num_classes
        self.use_evidence_ranking = use_evidence_ranking
        
        # BERT编码器
        if TRANSFORMERS_AVAILABLE:
            self.bert = BertModel.from_pretrained(pretrained_model)
            self.hidden_size = self.bert.config.hidden_size
        else:
            # 模拟BERT输出
            self.hidden_size = 768
            self.bert = None
        
        # 多头自注意力层
        self.self_attention = MultiHeadSelfAttention(
            self.hidden_size, 
            num_heads=attention_heads,
            dropout=hidden_dropout
        )
        
        # 证据排序模块
        if use_evidence_ranking:
            self.evidence_module = EvidenceRankingModule(self.hidden_size)
        
        # LayerNorm
        self.layer_norm = nn.LayerNorm(self.hidden_size)
        
        # 分类头
        classifier_input_size = self.hidden_size * 2 if use_evidence_ranking else self.hidden_size
        self.classifier = nn.Sequential(
            nn.Linear(classifier_input_size, self.hidden_size),
            nn.ReLU(),
            nn.Dropout(hidden_dropout),
            nn.Linear(self.hidden_size, self.hidden_size // 2),
            nn.ReLU(),
            nn.Dropout(hidden_dropout),
            nn.Linear(self.hidden_size // 2, num_classes)
        )
        
        # 初始化权重
        self._init_weights()
    
    def _init_weights(self):
        """初始化非预训练层的权重"""
        for module in [self.self_attention, self.classifier]:
            for name, param in module.named_parameters():
                if 'weight' in name and param.dim() > 1:
                    nn.init.xavier_uniform_(param)
                elif 'bias' in name:
                    nn.init.zeros_(param)
    
    def forward(
        self, 
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        token_type_ids: Optional[torch.Tensor] = None,
        return_attention: bool = False
    ):
        # BERT编码
        if self.bert is not None:
            bert_outputs = self.bert(
                input_ids=input_ids,
                attention_mask=attention_mask,
                token_type_ids=token_type_ids
            )
            hidden_states = bert_outputs.last_hidden_state  # [batch, seq_len, hidden]
            pooled_output = bert_outputs.pooler_output  # [batch, hidden]
        else:
            # 模拟输出用于测试
            batch_size, seq_len = input_ids.size()
            hidden_states = torch.randn(batch_size, seq_len, self.hidden_size)
            pooled_output = torch.randn(batch_size, self.hidden_size)
        
        # 多头自注意力
        attn_output, attn_weights = self.self_attention(hidden_states, attention_mask)
        attn_output = self.layer_norm(hidden_states + attn_output)
        
        # 获取CLS位置的表示
        cls_output = attn_output[:, 0, :]
        
        # 证据排序
        if self.use_evidence_ranking:
            evidence_output, evidence_weights = self.evidence_module(attn_output, attention_mask)
            # 拼接CLS和证据加权表示
            combined = torch.cat([cls_output, evidence_output], dim=-1)
        else:
            combined = cls_output
            evidence_weights = None
        
        # 分类
        logits = self.classifier(combined)
        
        if return_attention:
            return logits, attn_weights, evidence_weights
        return logits


class FraudDetectionDataset(Dataset):
    """虚假信息检测数据集"""
    
    def __init__(
        self, 
        data_path: str,
        tokenizer,
        max_length: int = 256,
        label_map: Dict[str, int] = None
    ):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.label_map = label_map or {"safe": 0, "warning": 1, "danger": 2}
        
        # 加载数据
        with open(data_path, 'r', encoding='utf-8') as f:
            self.data = json.load(f)
        
        print(f"[OK] 加载数据集: {len(self.data)} 样本")
    
    def __len__(self):
        return len(self.data)
    
    def __getitem__(self, idx):
        item = self.data[idx]
        text = item['text']
        label = self.label_map.get(item['label'], 1)  # 默认为warning
        
        # Tokenize
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=self.max_length,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(0),
            'attention_mask': encoding['attention_mask'].squeeze(0),
            'token_type_ids': encoding.get('token_type_ids', torch.zeros(self.max_length, dtype=torch.long)),
            'label': torch.tensor(label, dtype=torch.long)
        }


class FraudDetectorTrainer:
    """模型训练器"""
    
    def __init__(
        self,
        model: BERTAttentionDetector,
        train_dataloader: DataLoader,
        val_dataloader: DataLoader,
        device: str = 'cuda',
        learning_rate: float = 2e-5,
        weight_decay: float = 0.01,
        num_epochs: int = 5,
        warmup_steps: int = 100
    ):
        self.model = model.to(device)
        self.train_dataloader = train_dataloader
        self.val_dataloader = val_dataloader
        self.device = device
        self.num_epochs = num_epochs
        
        # 优化器
        self.optimizer = AdamW(
            model.parameters(),
            lr=learning_rate,
            weight_decay=weight_decay
        )
        
        # 学习率调度器
        total_steps = len(train_dataloader) * num_epochs
        self.scheduler = get_linear_schedule_with_warmup(
            self.optimizer,
            num_warmup_steps=warmup_steps,
            num_training_steps=total_steps
        )
        
        # 损失函数
        self.criterion = nn.CrossEntropyLoss()
        
        # 训练历史
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'val_accuracy': [],
            'val_f1': []
        }
    
    def train_epoch(self, epoch: int):
        """训练一个epoch"""
        self.model.train()
        total_loss = 0
        
        for batch_idx, batch in enumerate(self.train_dataloader):
            input_ids = batch['input_ids'].to(self.device)
            attention_mask = batch['attention_mask'].to(self.device)
            labels = batch['label'].to(self.device)
            
            self.optimizer.zero_grad()
            
            logits = self.model(input_ids, attention_mask)
            loss = self.criterion(logits, labels)
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            
            self.optimizer.step()
            self.scheduler.step()
            
            total_loss += loss.item()
            
            if batch_idx % 10 == 0:
                print(f"Epoch {epoch+1}, Batch {batch_idx}/{len(self.train_dataloader)}, Loss: {loss.item():.4f}")
        
        avg_loss = total_loss / len(self.train_dataloader)
        self.history['train_loss'].append(avg_loss)
        return avg_loss
    
    def evaluate(self):
        """评估模型"""
        self.model.eval()
        total_loss = 0
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for batch in self.val_dataloader:
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['label'].to(self.device)
                
                logits = self.model(input_ids, attention_mask)
                loss = self.criterion(logits, labels)
                
                total_loss += loss.item()
                
                preds = torch.argmax(logits, dim=-1)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        avg_loss = total_loss / len(self.val_dataloader)
        accuracy = np.mean(np.array(all_preds) == np.array(all_labels))
        
        # 计算F1
        from sklearn.metrics import f1_score
        f1 = f1_score(all_labels, all_preds, average='weighted')
        
        self.history['val_loss'].append(avg_loss)
        self.history['val_accuracy'].append(accuracy)
        self.history['val_f1'].append(f1)
        
        return {
            'loss': avg_loss,
            'accuracy': accuracy,
            'f1': f1,
            'predictions': all_preds,
            'labels': all_labels
        }
    
    def train(self):
        """完整训练流程"""
        best_f1 = 0
        best_model_state = None
        
        for epoch in range(self.num_epochs):
            print(f"\n{'='*50}")
            print(f"Epoch {epoch+1}/{self.num_epochs}")
            print('='*50)
            
            # 训练
            train_loss = self.train_epoch(epoch)
            print(f"\n训练损失: {train_loss:.4f}")
            
            # 评估
            eval_results = self.evaluate()
            print(f"验证损失: {eval_results['loss']:.4f}")
            print(f"验证准确率: {eval_results['accuracy']:.4f}")
            print(f"验证F1: {eval_results['f1']:.4f}")
            
            # 保存最佳模型
            if eval_results['f1'] > best_f1:
                best_f1 = eval_results['f1']
                best_model_state = self.model.state_dict().copy()
                print(f"[NEW BEST] F1: {best_f1:.4f}")
        
        # 恢复最佳模型
        if best_model_state:
            self.model.load_state_dict(best_model_state)
        
        return self.history
    
    def save_model(self, path: str):
        """保存模型"""
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'history': self.history
        }, path)
        print(f"[OK] 模型已保存到 {path}")


# 模型推理接口
class FraudDetectorInference:
    """推理接口"""
    
    def __init__(self, model_path: str, device: str = 'cpu'):
        self.device = device
        self.label_map = {0: 'safe', 1: 'warning', 2: 'danger'}
        
        if TRANSFORMERS_AVAILABLE:
            self.tokenizer = BertTokenizer.from_pretrained("hfl/chinese-bert-wwm-ext")
            self.model = BERTAttentionDetector()
            
            checkpoint = torch.load(model_path, map_location=device)
            self.model.load_state_dict(checkpoint['model_state_dict'])
            self.model.to(device)
            self.model.eval()
        else:
            self.tokenizer = None
            self.model = None
    
    def predict(self, text: str) -> Dict:
        """单文本预测"""
        if self.model is None:
            return self._fallback_predict(text)
        
        encoding = self.tokenizer(
            text,
            add_special_tokens=True,
            max_length=256,
            padding='max_length',
            truncation=True,
            return_tensors='pt'
        )
        
        input_ids = encoding['input_ids'].to(self.device)
        attention_mask = encoding['attention_mask'].to(self.device)
        
        with torch.no_grad():
            logits, attn_weights, evidence_weights = self.model(
                input_ids, attention_mask, return_attention=True
            )
            probs = F.softmax(logits, dim=-1)
        
        pred_class = torch.argmax(probs, dim=-1).item()
        confidence = probs[0][pred_class].item()
        
        return {
            'label': self.label_map[pred_class],
            'confidence': confidence,
            'probabilities': {
                'safe': probs[0][0].item(),
                'warning': probs[0][1].item(),
                'danger': probs[0][2].item()
            }
        }
    
    def _fallback_predict(self, text: str) -> Dict:
        """降级预测（基于规则）"""
        danger_keywords = ['保证收益', '包治百病', '祖传秘方', '无风险']
        warning_keywords = ['限时', '促销', '投资', '理财']
        
        for kw in danger_keywords:
            if kw in text:
                return {'label': 'danger', 'confidence': 0.85}
        
        for kw in warning_keywords:
            if kw in text:
                return {'label': 'warning', 'confidence': 0.7}
        
        return {'label': 'safe', 'confidence': 0.9}


if __name__ == "__main__":
    # 测试模型
    print("测试BERT+Attention检测模型...")
    
    if TRANSFORMERS_AVAILABLE:
        model = BERTAttentionDetector()
        print(f"模型参数量: {sum(p.numel() for p in model.parameters()):,}")
        
        # 测试前向传播
        batch_size = 2
        seq_len = 128
        input_ids = torch.randint(0, 21128, (batch_size, seq_len))
        attention_mask = torch.ones(batch_size, seq_len)
        
        logits = model(input_ids, attention_mask)
        print(f"输出形状: {logits.shape}")  # [batch_size, num_classes]
    else:
        print("transformers库未安装，跳过模型测试")









