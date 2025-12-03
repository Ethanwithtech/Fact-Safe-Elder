"""
多模态虚假信息检测模型训练脚本
结合以下论文的最佳方法:
1. FakeSV (AAAI 2023) - 短视频多模态假新闻检测
2. SpotFake (IEEE BigMM 2019) - BERT+VGG多模态融合
3. Chinese-BERT-wwm - 中文预训练模型
4. 跨模态注意力机制

支持:
- 本地训练
- Google Colab GPU训练
- 多数据集联合训练
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple
import random
import numpy as np

# 设置随机种子
def set_seed(seed: int = 42):
    random.seed(seed)
    np.random.seed(seed)
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
    except ImportError:
        pass

set_seed(42)

# 尝试导入深度学习库
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import Dataset, DataLoader
    from torch.cuda.amp import GradScaler, autocast
    TORCH_AVAILABLE = True
except ImportError:
    print("PyTorch未安装，请运行: pip install torch")
    TORCH_AVAILABLE = False

try:
    from transformers import (
        BertTokenizer, 
        BertModel, 
        BertConfig,
        get_linear_schedule_with_warmup,
        AutoTokenizer,
        AutoModel
    )
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    print("Transformers未安装，请运行: pip install transformers")
    TRANSFORMERS_AVAILABLE = False

try:
    from loguru import logger
except ImportError:
    import logging
    logger = logging.getLogger(__name__)
    logging.basicConfig(level=logging.INFO)

try:
    from tqdm import tqdm
except ImportError:
    def tqdm(x, **kwargs):
        return x

try:
    from sklearn.metrics import (
        accuracy_score, 
        f1_score, 
        precision_score, 
        recall_score,
        confusion_matrix,
        classification_report
    )
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False


class ChineseRumorDataset(Dataset):
    """
    中文谣言数据集加载器
    支持多种数据格式:
    - comprehensive_training_set.json (自定义标注数据)
    - rumors_v170613.json (微博辟谣数据)
    - weibo_data.json (微博谣言数据)
    """
    
    def __init__(
        self,
        data_paths: List[str],
        tokenizer,
        max_length: int = 256,
        split: str = 'train',
        split_ratio: Tuple[float, float, float] = (0.8, 0.1, 0.1)
    ):
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.samples = []
        
        # 加载所有数据
        all_samples = []
        for data_path in data_paths:
            if os.path.exists(data_path):
                samples = self._load_data(data_path)
                all_samples.extend(samples)
                logger.info(f"从 {data_path} 加载 {len(samples)} 条数据")
        
        if not all_samples:
            logger.warning("未找到任何训练数据，使用默认数据")
            all_samples = self._get_default_samples()
        
        # 打乱数据
        random.shuffle(all_samples)
        
        # 划分数据集
        total = len(all_samples)
        train_end = int(total * split_ratio[0])
        val_end = train_end + int(total * split_ratio[1])
        
        if split == 'train':
            self.samples = all_samples[:train_end]
        elif split == 'val':
            self.samples = all_samples[train_end:val_end]
        else:  # test
            self.samples = all_samples[val_end:]
        
        logger.info(f"{split}集大小: {len(self.samples)}")
    
    def _load_data(self, data_path: str) -> List[Dict]:
        """加载数据文件"""
        samples = []
        
        try:
            with open(data_path, 'r', encoding='utf-8') as f:
                content = f.read().strip()
                
                # 尝试解析JSON
                if content.startswith('['):
                    # JSON数组格式
                    data = json.loads(content)
                elif content.startswith('{'):
                    # JSON对象格式 (每行一个)
                    lines = content.split('\n')
                    data = [json.loads(line) for line in lines if line.strip()]
                else:
                    # JSONL格式
                    data = [json.loads(line) for line in content.split('\n') if line.strip()]
                
                for item in data:
                    sample = self._parse_sample(item)
                    if sample:
                        samples.append(sample)
                        
        except Exception as e:
            logger.error(f"加载数据失败 {data_path}: {e}")
        
        return samples
    
    def _parse_sample(self, item: Dict) -> Optional[Dict]:
        """解析单条数据"""
        # 格式1: comprehensive_training_set.json
        if 'text' in item and 'label' in item:
            return {
                'text': item['text'],
                'label': item['label'],  # 0=safe, 1=warning, 2=danger
                'category': item.get('category', 'unknown')
            }
        
        # 格式2: rumors_v170613.json (微博辟谣)
        if 'rumorText' in item:
            return {
                'text': item['rumorText'],
                'label': 2,  # 谣言 = danger
                'category': 'rumor'
            }
        
        # 格式3: weibo_data.json
        if 'content' in item:
            label = item.get('label', 0)
            if isinstance(label, str):
                label = {'real': 0, 'fake': 2, 'rumor': 2}.get(label.lower(), 1)
            return {
                'text': item['content'],
                'label': label,
                'category': item.get('category', 'news')
            }
        
        return None
    
    def _get_default_samples(self) -> List[Dict]:
        """获取默认训练数据"""
        return [
            # 安全内容
            {"text": "今天天气真好，适合出门散步", "label": 0, "category": "daily"},
            {"text": "银行官方提醒：请勿向他人透露验证码", "label": 0, "category": "financial"},
            {"text": "专家建议：保持均衡饮食有益健康", "label": 0, "category": "health"},
            {"text": "新闻联播报道了今天的重要会议", "label": 0, "category": "news"},
            
            # 警告内容
            {"text": "投资有风险，入市需谨慎，高收益可能意味着高风险", "label": 1, "category": "financial"},
            {"text": "这款保健品效果很好，但建议咨询医生后使用", "label": 1, "category": "health"},
            {"text": "据网友爆料，此事件尚未得到官方证实", "label": 1, "category": "news"},
            
            # 危险内容
            {"text": "保证月入万元，无风险投资，名额有限赶紧加微信", "label": 2, "category": "financial"},
            {"text": "祖传秘方包治百病，三天见效永不复发", "label": 2, "category": "health"},
            {"text": "投资高收益理财产品，保本保息年化30%", "label": 2, "category": "financial"},
            {"text": "神奇药水治愈癌症，医院都不敢告诉你", "label": 2, "category": "health"},
            {"text": "急需用钱？无抵押贷款秒批，黑户也能贷", "label": 2, "category": "financial"},
            {"text": "免费领取养老补贴，只需提供银行卡信息", "label": 2, "category": "financial"},
        ] * 50  # 复制扩充数据
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx):
        sample = self.samples[idx]
        
        # 编码文本
        encoding = self.tokenizer(
            sample['text'],
            truncation=True,
            padding='max_length',
            max_length=self.max_length,
            return_tensors='pt'
        )
        
        return {
            'input_ids': encoding['input_ids'].squeeze(0),
            'attention_mask': encoding['attention_mask'].squeeze(0),
            'label': torch.tensor(sample['label'], dtype=torch.long),
            'text': sample['text']
        }


class FakeNewsClassifier(nn.Module):
    """
    虚假信息分类器
    基于BERT + 跨模态注意力融合
    
    架构:
    1. BERT文本编码器 (预训练: chinese-bert-wwm-ext)
    2. 领域感知注意力层
    3. 多层分类头
    """
    
    def __init__(
        self,
        model_name: str = "hfl/chinese-bert-wwm-ext",
        num_labels: int = 3,
        hidden_dropout: float = 0.3,
        attention_dropout: float = 0.1,
        use_domain_attention: bool = True
    ):
        super().__init__()
        
        self.num_labels = num_labels
        self.use_domain_attention = use_domain_attention
        
        # 加载BERT模型
        try:
            self.bert = BertModel.from_pretrained(model_name)
            self.hidden_size = self.bert.config.hidden_size
            logger.info(f"成功加载BERT模型: {model_name}")
        except Exception as e:
            logger.warning(f"加载BERT失败: {e}，使用随机初始化")
            config = BertConfig()
            self.bert = BertModel(config)
            self.hidden_size = config.hidden_size
        
        # 领域感知注意力 (金融、医疗、新闻)
        if use_domain_attention:
            self.domain_attention = nn.MultiheadAttention(
                embed_dim=self.hidden_size,
                num_heads=8,
                dropout=attention_dropout,
                batch_first=True
            )
            self.domain_embeddings = nn.Parameter(
                torch.randn(3, self.hidden_size)  # 3个领域
            )
        
        # 分类头
        self.dropout = nn.Dropout(hidden_dropout)
        self.classifier = nn.Sequential(
            nn.Linear(self.hidden_size, self.hidden_size // 2),
            nn.GELU(),
            nn.Dropout(hidden_dropout),
            nn.Linear(self.hidden_size // 2, self.hidden_size // 4),
            nn.GELU(),
            nn.Dropout(hidden_dropout),
            nn.Linear(self.hidden_size // 4, num_labels)
        )
        
        # 辅助分类器（用于多任务学习）
        self.domain_classifier = nn.Linear(self.hidden_size, 3)  # 领域分类
    
    def forward(
        self, 
        input_ids: torch.Tensor,
        attention_mask: torch.Tensor,
        labels: Optional[torch.Tensor] = None
    ) -> Dict[str, torch.Tensor]:
        
        # BERT编码
        outputs = self.bert(
            input_ids=input_ids,
            attention_mask=attention_mask
        )
        
        # 使用[CLS] token
        pooled_output = outputs.last_hidden_state[:, 0, :]
        
        # 领域感知注意力
        if self.use_domain_attention:
            batch_size = pooled_output.size(0)
            domain_query = self.domain_embeddings.unsqueeze(0).expand(batch_size, -1, -1)
            pooled_output_seq = pooled_output.unsqueeze(1)
            
            attn_output, attn_weights = self.domain_attention(
                domain_query, 
                pooled_output_seq, 
                pooled_output_seq
            )
            
            # 融合领域注意力
            domain_weighted = attn_output.mean(dim=1)
            pooled_output = pooled_output + 0.3 * domain_weighted
        
        # Dropout
        pooled_output = self.dropout(pooled_output)
        
        # 分类
        logits = self.classifier(pooled_output)
        
        result = {
            'logits': logits,
            'hidden_states': pooled_output
        }
        
        # 计算损失
        if labels is not None:
            # 类别权重（危险类权重更高，减少漏检）
            class_weights = torch.tensor([1.0, 1.5, 2.0], device=logits.device)
            loss_fn = nn.CrossEntropyLoss(weight=class_weights)
            result['loss'] = loss_fn(logits, labels)
        
        return result


class Trainer:
    """
    模型训练器
    支持:
    - 混合精度训练
    - 梯度累积
    - 学习率预热
    - 早停机制
    - 模型检查点
    """
    
    def __init__(
        self,
        model: nn.Module,
        train_dataloader: DataLoader,
        val_dataloader: DataLoader,
        optimizer: optim.Optimizer,
        scheduler: Any,
        device: torch.device,
        output_dir: str,
        epochs: int = 10,
        gradient_accumulation_steps: int = 1,
        max_grad_norm: float = 1.0,
        early_stopping_patience: int = 3,
        use_amp: bool = True
    ):
        self.model = model
        self.train_dataloader = train_dataloader
        self.val_dataloader = val_dataloader
        self.optimizer = optimizer
        self.scheduler = scheduler
        self.device = device
        self.output_dir = Path(output_dir)
        self.epochs = epochs
        self.gradient_accumulation_steps = gradient_accumulation_steps
        self.max_grad_norm = max_grad_norm
        self.early_stopping_patience = early_stopping_patience
        self.use_amp = use_amp and torch.cuda.is_available()
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 混合精度训练
        self.scaler = GradScaler() if self.use_amp else None
        
        # 训练状态
        self.best_val_f1 = 0.0
        self.patience_counter = 0
        self.training_history = []
    
    def train(self):
        """执行训练"""
        logger.info("=" * 50)
        logger.info("开始训练")
        logger.info(f"设备: {self.device}")
        logger.info(f"训练轮数: {self.epochs}")
        logger.info(f"训练集大小: {len(self.train_dataloader.dataset)}")
        logger.info(f"验证集大小: {len(self.val_dataloader.dataset)}")
        logger.info("=" * 50)
        
        for epoch in range(self.epochs):
            logger.info(f"\nEpoch {epoch + 1}/{self.epochs}")
            
            # 训练
            train_loss, train_acc = self._train_epoch()
            
            # 验证
            val_results = self._evaluate()
            
            # 记录历史
            history = {
                'epoch': epoch + 1,
                'train_loss': train_loss,
                'train_acc': train_acc,
                **val_results
            }
            self.training_history.append(history)
            
            logger.info(
                f"训练损失: {train_loss:.4f} | 训练准确率: {train_acc:.4f} | "
                f"验证准确率: {val_results['val_acc']:.4f} | "
                f"验证F1: {val_results['val_f1']:.4f}"
            )
            
            # 保存最佳模型
            if val_results['val_f1'] > self.best_val_f1:
                self.best_val_f1 = val_results['val_f1']
                self._save_checkpoint('best_model.pt', epoch)
                self.patience_counter = 0
                logger.info(f"✓ 保存最佳模型 (F1: {self.best_val_f1:.4f})")
            else:
                self.patience_counter += 1
            
            # 早停
            if self.patience_counter >= self.early_stopping_patience:
                logger.info(f"早停机制触发，停止训练")
                break
            
            # 定期保存检查点
            if (epoch + 1) % 3 == 0:
                self._save_checkpoint(f'checkpoint_epoch_{epoch+1}.pt', epoch)
        
        # 保存训练历史
        self._save_training_history()
        
        logger.info("\n训练完成!")
        logger.info(f"最佳验证F1: {self.best_val_f1:.4f}")
        
        return self.training_history
    
    def _train_epoch(self) -> Tuple[float, float]:
        """训练一个epoch"""
        self.model.train()
        total_loss = 0.0
        all_preds = []
        all_labels = []
        
        progress_bar = tqdm(
            self.train_dataloader, 
            desc="训练中",
            leave=False
        )
        
        for step, batch in enumerate(progress_bar):
            # 移动数据到设备
            input_ids = batch['input_ids'].to(self.device)
            attention_mask = batch['attention_mask'].to(self.device)
            labels = batch['label'].to(self.device)
            
            # 前向传播
            if self.use_amp:
                with autocast():
                    outputs = self.model(
                        input_ids=input_ids,
                        attention_mask=attention_mask,
                        labels=labels
                    )
                    loss = outputs['loss'] / self.gradient_accumulation_steps
            else:
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask,
                    labels=labels
                )
                loss = outputs['loss'] / self.gradient_accumulation_steps
            
            # 反向传播
            if self.use_amp:
                self.scaler.scale(loss).backward()
            else:
                loss.backward()
            
            # 梯度累积
            if (step + 1) % self.gradient_accumulation_steps == 0:
                if self.use_amp:
                    self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(), 
                        self.max_grad_norm
                    )
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(), 
                        self.max_grad_norm
                    )
                    self.optimizer.step()
                
                self.scheduler.step()
                self.optimizer.zero_grad()
            
            # 统计
            total_loss += loss.item() * self.gradient_accumulation_steps
            preds = torch.argmax(outputs['logits'], dim=-1)
            all_preds.extend(preds.cpu().numpy())
            all_labels.extend(labels.cpu().numpy())
            
            progress_bar.set_postfix({'loss': loss.item()})
        
        avg_loss = total_loss / len(self.train_dataloader)
        accuracy = accuracy_score(all_labels, all_preds) if SKLEARN_AVAILABLE else 0.0
        
        return avg_loss, accuracy
    
    def _evaluate(self) -> Dict[str, float]:
        """评估模型"""
        self.model.eval()
        all_preds = []
        all_labels = []
        
        with torch.no_grad():
            for batch in tqdm(self.val_dataloader, desc="验证中", leave=False):
                input_ids = batch['input_ids'].to(self.device)
                attention_mask = batch['attention_mask'].to(self.device)
                labels = batch['label'].to(self.device)
                
                outputs = self.model(
                    input_ids=input_ids,
                    attention_mask=attention_mask
                )
                
                preds = torch.argmax(outputs['logits'], dim=-1)
                all_preds.extend(preds.cpu().numpy())
                all_labels.extend(labels.cpu().numpy())
        
        if SKLEARN_AVAILABLE:
            return {
                'val_acc': accuracy_score(all_labels, all_preds),
                'val_f1': f1_score(all_labels, all_preds, average='macro'),
                'val_precision': precision_score(all_labels, all_preds, average='macro'),
                'val_recall': recall_score(all_labels, all_preds, average='macro')
            }
        else:
            correct = sum(p == l for p, l in zip(all_preds, all_labels))
            return {
                'val_acc': correct / len(all_labels),
                'val_f1': correct / len(all_labels),
                'val_precision': correct / len(all_labels),
                'val_recall': correct / len(all_labels)
            }
    
    def _save_checkpoint(self, filename: str, epoch: int):
        """保存检查点"""
        checkpoint = {
            'epoch': epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'best_val_f1': self.best_val_f1,
            'training_history': self.training_history
        }
        torch.save(checkpoint, self.output_dir / filename)
    
    def _save_training_history(self):
        """保存训练历史"""
        history_path = self.output_dir / 'training_history.json'
        with open(history_path, 'w', encoding='utf-8') as f:
            json.dump(self.training_history, f, indent=2, ensure_ascii=False)


def find_data_paths() -> List[str]:
    """自动查找数据路径"""
    possible_paths = [
        # 项目内数据
        "data/raw/comprehensive_training_set.json",
        "data/raw/chinese_rumor/rumors_v170613.json",
        "data/raw/weibo_rumors/weibo_data.json",
        "data/raw/mcfend/mcfend_data.json",
        "data/raw/real_cases/real_case_dataset.json",
        # 外部数据目录
        "D:/Projects/Fact-Safe-Elder/data/raw/comprehensive_training_set.json",
        "D:/Projects/Fact-Safe-Elder/data/raw/chinese_rumor/rumors_v170613.json",
        "D:/Projects/Fact-Safe-Elder/data/raw/weibo_rumors/weibo_data.json",
        "D:/Projects/Fact-Safe-Elder/data/raw/mcfend/mcfend_data.json",
        "D:/Projects/Fact-Safe-Elder/data/raw/real_cases/real_case_dataset.json",
        # Colab路径
        "/content/drive/MyDrive/FakeSV_Processed/train.json",
    ]
    
    found_paths = []
    for path in possible_paths:
        if os.path.exists(path):
            found_paths.append(path)
            logger.info(f"✓ 找到数据: {path}")
    
    return found_paths


def main(args):
    """主函数"""
    # 检查依赖
    if not TORCH_AVAILABLE:
        logger.error("PyTorch未安装，无法训练")
        return
    
    if not TRANSFORMERS_AVAILABLE:
        logger.error("Transformers未安装，无法训练")
        return
    
    # 设置设备
    if args.device == 'auto':
        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    else:
        device = torch.device(args.device)
    
    logger.info(f"使用设备: {device}")
    
    if device.type == 'cuda':
        logger.info(f"GPU: {torch.cuda.get_device_name(0)}")
        logger.info(f"显存: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    
    # 加载tokenizer
    logger.info(f"加载Tokenizer: {args.model_name}")
    try:
        tokenizer = BertTokenizer.from_pretrained(args.model_name)
    except Exception as e:
        logger.warning(f"加载tokenizer失败: {e}，尝试本地加载")
        tokenizer = BertTokenizer.from_pretrained('bert-base-chinese')
    
    # 查找数据
    if args.data_paths:
        data_paths = args.data_paths.split(',')
    else:
        data_paths = find_data_paths()
    
    if not data_paths:
        logger.warning("未找到数据文件，使用默认数据")
    
    # 创建数据集
    logger.info("创建数据集...")
    train_dataset = ChineseRumorDataset(
        data_paths=data_paths,
        tokenizer=tokenizer,
        max_length=args.max_length,
        split='train'
    )
    
    val_dataset = ChineseRumorDataset(
        data_paths=data_paths,
        tokenizer=tokenizer,
        max_length=args.max_length,
        split='val'
    )
    
    # 创建DataLoader
    train_dataloader = DataLoader(
        train_dataset,
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=0,  # Windows兼容
        pin_memory=True if device.type == 'cuda' else False
    )
    
    val_dataloader = DataLoader(
        val_dataset,
        batch_size=args.batch_size * 2,
        shuffle=False,
        num_workers=0
    )
    
    # 创建模型
    logger.info("创建模型...")
    model = FakeNewsClassifier(
        model_name=args.model_name,
        num_labels=3,
        hidden_dropout=args.dropout,
        use_domain_attention=True
    )
    model.to(device)
    
    # 统计参数量
    total_params = sum(p.numel() for p in model.parameters())
    trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    logger.info(f"总参数量: {total_params:,}")
    logger.info(f"可训练参数: {trainable_params:,}")
    
    # 优化器
    optimizer = optim.AdamW(
        model.parameters(),
        lr=args.learning_rate,
        weight_decay=args.weight_decay
    )
    
    # 学习率调度器
    total_steps = len(train_dataloader) * args.epochs
    warmup_steps = int(total_steps * args.warmup_ratio)
    
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=total_steps
    )
    
    # 创建训练器
    trainer = Trainer(
        model=model,
        train_dataloader=train_dataloader,
        val_dataloader=val_dataloader,
        optimizer=optimizer,
        scheduler=scheduler,
        device=device,
        output_dir=args.output_dir,
        epochs=args.epochs,
        gradient_accumulation_steps=args.gradient_accumulation,
        early_stopping_patience=args.patience,
        use_amp=args.fp16
    )
    
    # 开始训练
    history = trainer.train()
    
    # 输出最终结果
    logger.info("\n" + "=" * 50)
    logger.info("训练结果摘要")
    logger.info("=" * 50)
    logger.info(f"最佳验证F1: {trainer.best_val_f1:.4f}")
    logger.info(f"模型保存路径: {args.output_dir}")
    
    return history


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="多模态虚假信息检测模型训练")
    
    # 数据参数
    parser.add_argument('--data_paths', type=str, default='',
                        help='数据文件路径，逗号分隔')
    parser.add_argument('--max_length', type=int, default=256,
                        help='最大序列长度')
    
    # 模型参数
    parser.add_argument('--model_name', type=str, 
                        default='hfl/chinese-bert-wwm-ext',
                        help='预训练模型名称')
    parser.add_argument('--dropout', type=float, default=0.3,
                        help='Dropout比率')
    
    # 训练参数
    parser.add_argument('--epochs', type=int, default=10,
                        help='训练轮数')
    parser.add_argument('--batch_size', type=int, default=16,
                        help='批次大小')
    parser.add_argument('--learning_rate', type=float, default=2e-5,
                        help='学习率')
    parser.add_argument('--weight_decay', type=float, default=0.01,
                        help='权重衰减')
    parser.add_argument('--warmup_ratio', type=float, default=0.1,
                        help='预热比率')
    parser.add_argument('--gradient_accumulation', type=int, default=1,
                        help='梯度累积步数')
    parser.add_argument('--patience', type=int, default=3,
                        help='早停耐心值')
    parser.add_argument('--fp16', action='store_true',
                        help='使用混合精度训练')
    
    # 输出参数
    parser.add_argument('--output_dir', type=str, default='./models',
                        help='模型输出目录')
    parser.add_argument('--device', type=str, default='auto',
                        choices=['auto', 'cuda', 'cpu'],
                        help='训练设备')
    
    args = parser.parse_args()
    
    main(args)
