#!/usr/bin/env python3
"""
真实AI模型训练脚本
使用真实数据集训练BERT、ChatGLM等模型
"""

import os
import json
import pandas as pd
import numpy as np
from datetime import datetime
from typing import Dict, List, Tuple
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    import torch
    from torch.utils.data import DataLoader, Dataset
    from transformers import (
        AutoTokenizer, 
        AutoModelForSequenceClassification,
        TrainingArguments,
        Trainer,
        DataCollatorWithPadding
    )
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, precision_recall_fscore_support, classification_report
    from datasets import Dataset as HFDataset
    TORCH_AVAILABLE = True
    logger.info("AI训练依赖包加载成功")
except ImportError as e:
    logger.error(f"AI训练依赖包未安装: {e}")
    TORCH_AVAILABLE = False

class FakeNewsDataset:
    """虚假信息数据集类"""
    
    def __init__(self):
        self.data = []
        self.labels = []
        self.label_map = {'safe': 0, 'warning': 1, 'danger': 2}
        self.reverse_label_map = {0: 'safe', 1: 'warning', 2: 'danger'}
    
    def load_data(self) -> Tuple[List[str], List[int]]:
        """加载训练数据"""
        logger.info("开始加载训练数据...")
        
        # 1. 加载内置示例数据
        self._load_builtin_data()
        
        # 2. 尝试加载真实数据集
        self._load_real_datasets()
        
        # 3. 数据增强
        self._augment_data()
        
        logger.info(f"数据加载完成，总计: {len(self.data)} 条样本")
        logger.info(f"标签分布: {self._get_label_distribution()}")
        
        return self.data, self.labels
    
    def _load_builtin_data(self):
        """加载内置数据"""
        builtin_data = [
            # 金融诈骗类 (danger = 2)
            ("月入三万的理财秘诀，保证收益无风险！跟着老师操作，稳赚不赔！", 2),
            ("投资理财新机会，一夜暴富不是梦！内幕消息，必涨股票！", 2),
            ("无抵押贷款，秒批秒放，利息超低，不看征信！", 2),
            ("虚拟货币投资，日赚千元，错过后悔终生！", 2),
            ("保证收益20%，无风险投资，银行内部产品！", 2),
            ("跟着专家炒股，包赚不赔，月收益翻倍！", 2),
            ("P2P理财平台，年化收益30%，国家背景！", 2),
            ("外汇投资，小投入大回报，专业指导！", 2),
            ("期货交易内幕，跟单必赚，资金安全！", 2),
            ("数字货币挖矿，躺着赚钱，一本万利！", 2),
            
            # 医疗虚假信息类 (danger = 2)
            ("祖传秘方包治百病，三天见效，医院不告诉你的秘密！", 2),
            ("神奇保健品，一次根治，永不复发，药到病除！", 2),
            ("癌症特效药，无副作用，治愈率100%！", 2),
            ("减肥神器，一周瘦20斤，不反弹不节食！", 2),
            ("壮阳神药，一粒见效，重振雄风！", 2),
            ("糖尿病根治方法，告别胰岛素，彻底治愈！", 2),
            ("高血压特效药，一个疗程根治，不用终身服药！", 2),
            ("白发变黑发，天然植物配方，一个月见效！", 2),
            ("近视眼治疗仪，不手术不吃药，恢复视力！", 2),
            ("痔疮根治膏，三天见效，彻底根治不复发！", 2),
            
            # 可疑内容类 (warning = 1)
            ("限时抢购，原价999现在99，数量有限！", 1),
            ("投资理财有风险，请谨慎选择，建议咨询专业人士", 1),
            ("保健品辅助调理，配合医生治疗效果更佳", 1),
            ("网购促销活动，品质保证，七天无理由退货", 1),
            ("学习投资知识，理性投资，分散风险", 1),
            ("健康生活方式，均衡饮食，适量运动", 1),
            ("美容护肤产品，因人而异，建议先试用", 1),
            ("减肥产品辅助，需配合运动和饮食控制", 1),
            ("理财规划建议，根据个人情况制定方案", 1),
            ("保险产品介绍，详细了解条款再购买", 1),
            
            # 安全内容类 (safe = 0)
            ("今天教大家做红烧肉的家常做法，简单易学", 0),
            ("天气预报：明天多云转晴，气温15-25度", 0),
            ("新闻资讯：本市将新建三所学校", 0),
            ("健康提醒：多喝水，注意休息，预防感冒", 0),
            ("交通出行：地铁2号线今日正常运营", 0),
            ("学习分享：如何提高工作效率的几个方法", 0),
            ("生活小贴士：如何正确保存蔬菜水果", 0),
            ("运动健身：适合初学者的瑜伽动作", 0),
            ("文化娱乐：本周末博物馆有特展活动", 0),
            ("科普知识：为什么会有四季变化", 0),
            ("正规银行理财产品，年化收益3.5%，风险需谨慎", 0),
            ("医院正规治疗，遵医嘱用药，定期复查", 0),
            ("健康饮食，营养均衡，适量运动很重要", 0),
            ("学习理财知识，了解风险，理性投资", 0),
            ("购买保险前，仔细阅读条款，了解保障范围", 0),
        ]
        
        for text, label in builtin_data:
            self.data.append(text)
            self.labels.append(label)
        
        logger.info(f"加载内置数据: {len(builtin_data)} 条")
    
    def _load_real_datasets(self):
        """加载真实数据集"""
        dataset_files = [
            ("data/raw/mcfend/mcfend_data.json", self._parse_mcfend),
            ("data/raw/weibo_rumors/weibo_data.json", self._parse_weibo),
            ("data/raw/chinese_rumor/rumors_v170613.json", self._parse_chinese_rumor),
            ("data/raw/liar/train.tsv", self._parse_liar)
        ]
        
        for file_path, parser in dataset_files:
            if os.path.exists(file_path):
                try:
                    count = parser(file_path)
                    logger.info(f"加载真实数据集: {file_path}, {count} 条")
                except Exception as e:
                    logger.warning(f"加载数据集失败 {file_path}: {e}")
    
    def _parse_mcfend(self, file_path: str) -> int:
        """解析MCFEND数据集"""
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            for item in data[:500]:  # 限制数量
                if isinstance(item, dict) and 'text' in item and 'label' in item:
                    text = item['text']
                    label = item['label']
                    
                    # 映射标签
                    if label in ['fake', 'rumor', 'false']:
                        mapped_label = 2  # danger
                    elif label in ['real', 'true']:
                        mapped_label = 0  # safe
                    else:
                        mapped_label = 1  # warning
                    
                    self.data.append(text)
                    self.labels.append(mapped_label)
                    count += 1
        
        return count
    
    def _parse_weibo(self, file_path: str) -> int:
        """解析微博数据集"""
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            for item in data[:300]:  # 限制数量
                if isinstance(item, dict) and 'text' in item:
                    text = item['text']
                    # 简单的标签判断
                    if any(word in text for word in ['虚假', '谣言', '假的', '不实']):
                        label = 2  # danger
                    else:
                        label = 0  # safe
                    
                    self.data.append(text)
                    self.labels.append(label)
                    count += 1
        
        return count
    
    def _parse_chinese_rumor(self, file_path: str) -> int:
        """解析中文谣言数据集"""
        count = 0
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            for item in data[:200]:  # 限制数量
                if isinstance(item, dict) and 'text' in item and 'label' in item:
                    text = item['text']
                    label = 2 if item['label'] == 'rumor' else 0
                    
                    self.data.append(text)
                    self.labels.append(label)
                    count += 1
        
        return count
    
    def _parse_liar(self, file_path: str) -> int:
        """解析LIAR数据集"""
        count = 0
        try:
            df = pd.read_csv(file_path, sep='\t', header=None)
            
            for _, row in df.head(100).iterrows():  # 限制数量
                if len(row) > 2:
                    text = str(row[2])  # 文本内容
                    # 简单映射
                    label = 1  # warning (英文数据集，标记为警告)
                    
                    self.data.append(text)
                    self.labels.append(label)
                    count += 1
        except Exception as e:
            logger.warning(f"解析LIAR数据集失败: {e}")
        
        return count
    
    def _augment_data(self):
        """数据增强"""
        # 简单的数据增强：为少数类别增加样本
        label_counts = {0: 0, 1: 0, 2: 0}
        for label in self.labels:
            label_counts[label] += 1
        
        max_count = max(label_counts.values())
        
        # 为每个类别补充数据
        original_data = list(zip(self.data, self.labels))
        
        for target_label in [0, 1, 2]:
            current_count = label_counts[target_label]
            if current_count < max_count // 2:  # 如果样本数少于最大值的一半
                # 复制一些样本
                samples_to_add = min(max_count // 2 - current_count, current_count)
                label_samples = [(text, label) for text, label in original_data if label == target_label]
                
                for i in range(samples_to_add):
                    text, label = label_samples[i % len(label_samples)]
                    self.data.append(text)
                    self.labels.append(label)
        
        logger.info(f"数据增强完成，新增样本: {len(self.data) - len(original_data)}")
    
    def _get_label_distribution(self) -> Dict[str, int]:
        """获取标签分布"""
        distribution = {}
        for label in self.labels:
            label_name = self.reverse_label_map[label]
            distribution[label_name] = distribution.get(label_name, 0) + 1
        return distribution

class AIModelTrainer:
    """AI模型训练器"""
    
    def __init__(self, model_name: str = "hfl/chinese-bert-wwm-ext"):
        self.model_name = model_name
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.tokenizer = None
        self.model = None
        self.training_results = {}
        
        logger.info(f"初始化AI模型训练器，设备: {self.device}")
    
    def prepare_model(self):
        """准备模型和分词器"""
        logger.info(f"加载模型: {self.model_name}")
        
        try:
            # 加载分词器
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_name,
                cache_dir='./models/cache'
            )
            
            # 加载模型
            self.model = AutoModelForSequenceClassification.from_pretrained(
                self.model_name,
                num_labels=3,  # safe, warning, danger
                cache_dir='./models/cache'
            ).to(self.device)
            
            logger.info("模型加载成功")
            
        except Exception as e:
            logger.error(f"模型加载失败: {e}")
            raise
    
    def prepare_data(self, texts: List[str], labels: List[int], test_size: float = 0.2):
        """准备训练数据"""
        logger.info("准备训练数据...")
        
        # 分割数据
        train_texts, test_texts, train_labels, test_labels = train_test_split(
            texts, labels, test_size=test_size, random_state=42, stratify=labels
        )
        
        # 创建数据集
        def tokenize_function(examples):
            return self.tokenizer(
                examples['text'],
                padding=True,
                truncation=True,
                max_length=512,
                return_tensors="pt"
            )
        
        train_dataset = HFDataset.from_dict({
            'text': train_texts,
            'labels': train_labels
        })
        
        test_dataset = HFDataset.from_dict({
            'text': test_texts,
            'labels': test_labels
        })
        
        train_dataset = train_dataset.map(tokenize_function, batched=True)
        test_dataset = test_dataset.map(tokenize_function, batched=True)
        
        logger.info(f"训练集大小: {len(train_dataset)}, 测试集大小: {len(test_dataset)}")
        
        return train_dataset, test_dataset
    
    def train(self, train_dataset, test_dataset, 
              epochs: int = 3, 
              batch_size: int = 8,
              learning_rate: float = 5e-5):
        """训练模型"""
        logger.info("开始模型训练...")
        
        # 训练参数
        training_args = TrainingArguments(
            output_dir=f'./logs/training/{datetime.now().strftime("%Y%m%d_%H%M%S")}',
            num_train_epochs=epochs,
            per_device_train_batch_size=batch_size,
            per_device_eval_batch_size=batch_size,
            learning_rate=learning_rate,
            weight_decay=0.01,
            logging_dir='./logs/training',
            logging_steps=10,
            evaluation_strategy="epoch",
            save_strategy="epoch",
            load_best_model_at_end=True,
            metric_for_best_model="accuracy",
            greater_is_better=True,
            report_to=None,  # 不使用wandb等
            save_total_limit=2
        )
        
        # 评估函数
        def compute_metrics(eval_pred):
            predictions, labels = eval_pred
            predictions = np.argmax(predictions, axis=1)
            
            accuracy = accuracy_score(labels, predictions)
            precision, recall, f1, _ = precision_recall_fscore_support(
                labels, predictions, average='weighted'
            )
            
            return {
                'accuracy': accuracy,
                'f1': f1,
                'precision': precision,
                'recall': recall
            }
        
        # 创建训练器
        trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=test_dataset,
            compute_metrics=compute_metrics,
            data_collator=DataCollatorWithPadding(tokenizer=self.tokenizer)
        )
        
        # 开始训练
        train_result = trainer.train()
        
        # 评估模型
        eval_result = trainer.evaluate()
        
        # 保存结果
        self.training_results = {
            'train_loss': train_result.training_loss,
            'eval_accuracy': eval_result['eval_accuracy'],
            'eval_f1': eval_result['eval_f1'],
            'eval_precision': eval_result['eval_precision'],
            'eval_recall': eval_result['eval_recall'],
            'training_time': train_result.metrics['train_runtime'],
            'model_name': self.model_name,
            'epochs': epochs,
            'batch_size': batch_size,
            'learning_rate': learning_rate
        }
        
        logger.info(f"训练完成！准确率: {eval_result['eval_accuracy']:.4f}")
        
        return self.training_results
    
    def save_model(self, save_path: str):
        """保存训练好的模型"""
        logger.info(f"保存模型到: {save_path}")
        
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        
        # 保存模型权重和训练结果
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'tokenizer': self.tokenizer,
            'training_results': self.training_results,
            'model_name': self.model_name
        }, save_path)
        
        # 保存训练报告
        report_path = save_path.replace('.pt', '_report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            json.dump(self.training_results, f, ensure_ascii=False, indent=2)
        
        logger.info("模型保存完成")
    
    def test_model(self, test_texts: List[str], test_labels: List[int]):
        """测试模型性能"""
        logger.info("测试模型性能...")
        
        self.model.eval()
        predictions = []
        
        with torch.no_grad():
            for text in test_texts:
                inputs = self.tokenizer(
                    text,
                    padding=True,
                    truncation=True,
                    max_length=512,
                    return_tensors="pt"
                ).to(self.device)
                
                outputs = self.model(**inputs)
                pred = torch.argmax(outputs.logits, dim=-1).item()
                predictions.append(pred)
        
        # 计算详细指标
        accuracy = accuracy_score(test_labels, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            test_labels, predictions, average='weighted'
        )
        
        # 生成分类报告
        target_names = ['safe', 'warning', 'danger']
        report = classification_report(
            test_labels, predictions, 
            target_names=target_names,
            output_dict=True
        )
        
        logger.info(f"测试结果 - 准确率: {accuracy:.4f}, F1: {f1:.4f}")
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1': f1,
            'classification_report': report
        }

def main():
    """主训练流程"""
    if not TORCH_AVAILABLE:
        logger.error("PyTorch不可用，无法进行模型训练")
        return
    
    logger.info("开始AI模型训练流程")
    
    try:
        # 1. 加载数据
        dataset = FakeNewsDataset()
        texts, labels = dataset.load_data()
        
        if len(texts) < 50:
            logger.warning("训练数据不足，建议添加更多数据")
        
        # 2. 初始化训练器
        trainer = AIModelTrainer()
        trainer.prepare_model()
        
        # 3. 准备数据
        train_dataset, test_dataset = trainer.prepare_data(texts, labels)
        
        # 4. 训练模型
        results = trainer.train(
            train_dataset=train_dataset,
            test_dataset=test_dataset,
            epochs=5,
            batch_size=8,
            learning_rate=5e-5
        )
        
        # 5. 保存模型
        save_path = f"models/trained/bert_fake_news_detector_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pt"
        trainer.save_model(save_path)
        
        # 6. 测试模型
        test_texts = texts[-20:]  # 使用最后20个样本测试
        test_labels = labels[-20:]
        test_results = trainer.test_model(test_texts, test_labels)
        
        # 7. 打印结果
        print(f"""
🎉 AI模型训练完成！
==========================================

📊 训练结果:
   准确率: {results['eval_accuracy']:.2%}
   F1分数: {results['eval_f1']:.4f}
   精确率: {results['eval_precision']:.4f}
   召回率: {results['eval_recall']:.4f}
   训练时间: {results['training_time']:.1f}秒

📈 测试结果:
   测试准确率: {test_results['accuracy']:.2%}
   测试F1分数: {test_results['f1']:.4f}

💾 模型保存路径: {save_path}

🎯 数据统计:
   总样本数: {len(texts)}
   训练集: {len(train_dataset)}
   测试集: {len(test_dataset)}
   标签分布: {dataset._get_label_distribution()}

==========================================
        """)
        
        # 创建最新模型的软链接
        latest_path = "models/trained/bert_fake_news_detector.pt"
        if os.path.exists(save_path):
            if os.path.exists(latest_path):
                os.remove(latest_path)
            
            # 在Windows上使用copy而不是symlink
            import shutil
            shutil.copy2(save_path, latest_path)
            logger.info(f"创建最新模型链接: {latest_path}")
        
        logger.info("AI模型训练流程完成")
        
    except Exception as e:
        logger.error(f"训练过程发生错误: {e}", exc_info=True)

if __name__ == "__main__":
    main()
