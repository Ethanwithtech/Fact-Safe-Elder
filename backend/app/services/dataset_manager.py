"""
数据集管理服务
处理MCFEND、Weibo等多种数据集
"""

import os
import json
import uuid
import pandas as pd
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from loguru import logger


class DatasetManager:
    """数据集管理器"""
    
    def __init__(self):
        self.datasets_dir = Path("./data/datasets")
        self.processed_dir = Path("./data/processed")
        self.metadata_dir = Path("./data/metadata")
        
        # 创建必要的目录
        self.datasets_dir.mkdir(exist_ok=True, parents=True)
        self.processed_dir.mkdir(exist_ok=True, parents=True)
        self.metadata_dir.mkdir(exist_ok=True, parents=True)
        
        # 初始化预置数据集
        self._init_prebuilt_datasets()
        
        logger.info("数据集管理器已初始化")
    
    def _init_prebuilt_datasets(self):
        """初始化预置数据集信息"""
        self.prebuilt_datasets = {
            'mcfend_v1': {
                'id': 'mcfend_v1',
                'name': 'MCFEND多源中文假新闻数据集',
                'description': '香港浸会大学和香港中文大学发布的多模态虚假新闻数据集',
                'type': 'mcfend',
                'format': 'json',
                'size': '23974',
                'features': ['text', 'image', 'metadata'],
                'labels': ['real', 'fake'],
                'source': 'https://github.com/HKBUNLP/MCFEND',
                'created_at': '2024-01-01'
            },
            'weibo_rumors': {
                'id': 'weibo_rumors',
                'name': '微博谣言检测数据集',
                'description': '包含微博平台的谣言和非谣言样本',
                'type': 'weibo',
                'format': 'json',
                'size': '15000',
                'features': ['text', 'user_info', 'propagation'],
                'labels': ['rumor', 'non-rumor'],
                'source': 'Weibo API',
                'created_at': '2024-01-15'
            },
            'financial_fraud': {
                'id': 'financial_fraud',
                'name': '金融诈骗文本数据集',
                'description': '专门收集的金融诈骗相关文本',
                'type': 'custom',
                'format': 'csv',
                'size': '8500',
                'features': ['text', 'category', 'risk_level'],
                'labels': ['safe', 'warning', 'danger'],
                'source': 'Custom Collection',
                'created_at': '2024-02-01'
            },
            'medical_misinfo': {
                'id': 'medical_misinfo',
                'name': '医疗虚假信息数据集',
                'description': '医疗健康领域的虚假信息样本',
                'type': 'custom',
                'format': 'json',
                'size': '6200',
                'features': ['text', 'claim', 'evidence'],
                'labels': ['true', 'false', 'misleading'],
                'source': 'Fact-checking Organizations',
                'created_at': '2024-02-15'
            }
        }
    
    def save_dataset(
        self, 
        name: str, 
        description: str, 
        type: str, 
        format: str, 
        content: bytes,
        filename: str
    ) -> str:
        """保存数据集"""
        dataset_id = f"dataset_{uuid.uuid4().hex[:8]}"
        dataset_path = self.datasets_dir / dataset_id
        dataset_path.mkdir(exist_ok=True)
        
        # 保存数据文件
        data_file = dataset_path / f"data.{format}"
        with open(data_file, 'wb') as f:
            f.write(content)
        
        # 解析数据统计信息
        stats = self._parse_dataset_stats(data_file, format)
        
        # 创建元数据
        metadata = {
            'id': dataset_id,
            'name': name,
            'description': description,
            'type': type,
            'format': format,
            'original_filename': filename,
            'path': str(data_file),
            'size': len(content),
            'stats': stats,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        # 保存元数据
        metadata_file = self.metadata_dir / f"{dataset_id}.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        logger.info(f"数据集已保存: {dataset_id}")
        return dataset_id
    
    def get_dataset(self, dataset_id: str) -> Optional[Dict]:
        """获取数据集信息"""
        # 检查预置数据集
        if dataset_id in self.prebuilt_datasets:
            return self.prebuilt_datasets[dataset_id]
        
        # 检查用户上传的数据集
        metadata_file = self.metadata_dir / f"{dataset_id}.json"
        if metadata_file.exists():
            with open(metadata_file, 'r') as f:
                return json.load(f)
        
        return None
    
    def list_datasets(self) -> List[Dict]:
        """列出所有数据集"""
        datasets = []
        
        # 添加预置数据集
        datasets.extend(list(self.prebuilt_datasets.values()))
        
        # 添加用户上传的数据集
        for metadata_file in self.metadata_dir.glob("*.json"):
            try:
                with open(metadata_file, 'r') as f:
                    metadata = json.load(f)
                    datasets.append(metadata)
            except Exception as e:
                logger.error(f"加载数据集元数据失败 {metadata_file}: {e}")
        
        return datasets
    
    def validate_dataset(self, dataset_id: str) -> Dict:
        """验证数据集"""
        dataset = self.get_dataset(dataset_id)
        
        if not dataset:
            raise ValueError(f"数据集 {dataset_id} 不存在")
        
        # 如果是预置数据集，返回预定义的统计信息
        if dataset_id in self.prebuilt_datasets:
            return {
                'valid': True,
                'total_samples': int(dataset.get('size', 0)),
                'features': dataset.get('features', []),
                'labels': dataset.get('labels', []),
                'message': '预置数据集验证通过'
            }
        
        # 验证用户上传的数据集
        data_path = Path(dataset['path'])
        
        if not data_path.exists():
            return {
                'valid': False,
                'message': '数据文件不存在'
            }
        
        stats = self._parse_dataset_stats(data_path, dataset['format'])
        
        return {
            'valid': stats['valid'],
            'total_samples': stats['total_samples'],
            'features': stats.get('features', []),
            'labels': stats.get('labels', []),
            'message': stats.get('message', 'OK')
        }
    
    def load_dataset(self, dataset_id: str, split: str = 'train', ratio: float = 0.8) -> Dict:
        """加载数据集用于训练"""
        dataset = self.get_dataset(dataset_id)
        
        if not dataset:
            raise ValueError(f"数据集 {dataset_id} 不存在")
        
        # 如果是预置数据集，生成模拟数据
        if dataset_id in self.prebuilt_datasets:
            return self._generate_mock_data(dataset, split, ratio)
        
        # 加载真实数据
        data_path = Path(dataset['path'])
        format = dataset['format']
        
        if format == 'json':
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        elif format == 'jsonl':
            data = []
            with open(data_path, 'r', encoding='utf-8') as f:
                for line in f:
                    data.append(json.loads(line))
        elif format == 'csv':
            df = pd.read_csv(data_path)
            data = df.to_dict('records')
        else:
            raise ValueError(f"不支持的数据格式: {format}")
        
        # 分割数据集
        total = len(data)
        train_size = int(total * ratio)
        
        if split == 'train':
            return {
                'data': data[:train_size],
                'size': train_size
            }
        elif split == 'val':
            return {
                'data': data[train_size:],
                'size': total - train_size
            }
        else:
            return {
                'data': data,
                'size': total
            }
    
    def preprocess_dataset(self, dataset_id: str, config: Dict = None) -> str:
        """预处理数据集"""
        dataset = self.get_dataset(dataset_id)
        
        if not dataset:
            raise ValueError(f"数据集 {dataset_id} 不存在")
        
        processed_id = f"processed_{dataset_id}_{uuid.uuid4().hex[:4]}"
        processed_path = self.processed_dir / processed_id
        processed_path.mkdir(exist_ok=True)
        
        logger.info(f"开始预处理数据集: {dataset_id}")
        
        # 加载数据
        raw_data = self.load_dataset(dataset_id, split='all')['data']
        
        # 预处理步骤
        processed_data = []
        for item in raw_data:
            processed_item = self._preprocess_item(item, dataset.get('type', 'custom'), config)
            processed_data.append(processed_item)
        
        # 保存预处理后的数据
        output_file = processed_path / 'data.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)
        
        # 保存预处理配置
        config_file = processed_path / 'config.json'
        with open(config_file, 'w') as f:
            json.dump({
                'original_dataset': dataset_id,
                'processed_id': processed_id,
                'config': config or {},
                'timestamp': datetime.now().isoformat(),
                'size': len(processed_data)
            }, f, indent=2)
        
        logger.info(f"数据集预处理完成: {processed_id}")
        return processed_id
    
    def _parse_dataset_stats(self, data_path: Path, format: str) -> Dict:
        """解析数据集统计信息"""
        try:
            if format == 'json':
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    
                    if isinstance(data, list):
                        total_samples = len(data)
                        if data:
                            features = list(data[0].keys()) if isinstance(data[0], dict) else []
                            labels = list(set(item.get('label', 'unknown') for item in data if isinstance(item, dict)))
                        else:
                            features = []
                            labels = []
                    else:
                        total_samples = 1
                        features = list(data.keys()) if isinstance(data, dict) else []
                        labels = []
                        
            elif format == 'csv':
                df = pd.read_csv(data_path, nrows=1000)  # 只读前1000行进行分析
                total_samples = len(df)
                features = df.columns.tolist()
                
                # 尝试识别标签列
                label_columns = ['label', 'target', 'class', 'category']
                labels = []
                for col in label_columns:
                    if col in df.columns:
                        labels = df[col].unique().tolist()
                        break
                        
            elif format == 'jsonl':
                total_samples = 0
                features = set()
                labels = set()
                
                with open(data_path, 'r', encoding='utf-8') as f:
                    for i, line in enumerate(f):
                        if i >= 1000:  # 只分析前1000行
                            break
                        try:
                            item = json.loads(line)
                            total_samples += 1
                            if isinstance(item, dict):
                                features.update(item.keys())
                                if 'label' in item:
                                    labels.add(item['label'])
                        except:
                            continue
                
                features = list(features)
                labels = list(labels)
                
            else:
                return {
                    'valid': False,
                    'message': f'不支持的格式: {format}'
                }
            
            return {
                'valid': True,
                'total_samples': total_samples,
                'features': features,
                'labels': labels,
                'message': 'OK'
            }
            
        except Exception as e:
            logger.error(f"解析数据集统计信息失败: {e}")
            return {
                'valid': False,
                'message': str(e)
            }
    
    def _preprocess_item(self, item: Dict, dataset_type: str, config: Dict = None) -> Dict:
        """预处理单个数据项"""
        processed = {}
        
        # 提取文本
        text_fields = ['text', 'content', 'message', 'title', 'description']
        text = ''
        for field in text_fields:
            if field in item:
                text += str(item[field]) + ' '
        
        processed['text'] = self._clean_text(text.strip())
        
        # 提取标签
        label_fields = ['label', 'target', 'class', 'category']
        for field in label_fields:
            if field in item:
                processed['label'] = item[field]
                break
        
        # 根据数据集类型进行特定处理
        if dataset_type == 'mcfend':
            processed['has_image'] = 'image' in item and item['image'] is not None
            processed['source'] = item.get('source', 'unknown')
            processed['timestamp'] = item.get('timestamp', '')
            
        elif dataset_type == 'weibo':
            processed['user_verified'] = item.get('user', {}).get('verified', False)
            processed['repost_count'] = item.get('repost_count', 0)
            processed['comment_count'] = item.get('comment_count', 0)
            
        elif dataset_type == 'custom':
            # 保留所有原始字段
            processed.update(item)
        
        return processed
    
    def _clean_text(self, text: str) -> str:
        """清理文本"""
        # 移除多余的空格
        text = ' '.join(text.split())
        
        # 移除特殊字符（保留中文、英文、数字和基本标点）
        import re
        text = re.sub(r'[^\u4e00-\u9fff\w\s.,!?;:()（）！？；：、。，]', '', text)
        
        return text.strip()
    
    def _generate_mock_data(self, dataset: Dict, split: str, ratio: float) -> Dict:
        """生成模拟数据"""
        total_size = int(dataset.get('size', 1000))
        
        # 生成模拟样本
        mock_data = []
        for i in range(total_size):
            if dataset['type'] == 'mcfend':
                sample = {
                    'id': f"sample_{i}",
                    'text': f"这是第{i}条新闻内容...",
                    'label': 'fake' if i % 3 == 0 else 'real',
                    'image': f"image_{i}.jpg" if i % 2 == 0 else None,
                    'source': ['weibo', 'wechat', 'news'][i % 3],
                    'timestamp': datetime.now().isoformat()
                }
            elif dataset['type'] == 'weibo':
                sample = {
                    'id': f"weibo_{i}",
                    'text': f"这是第{i}条微博内容...",
                    'label': 'rumor' if i % 4 == 0 else 'non-rumor',
                    'user': {
                        'verified': i % 5 == 0,
                        'followers': 1000 * (i % 100)
                    },
                    'repost_count': i * 10,
                    'comment_count': i * 5
                }
            else:
                sample = {
                    'id': f"sample_{i}",
                    'text': f"这是第{i}条文本内容...",
                    'label': ['safe', 'warning', 'danger'][i % 3]
                }
            
            mock_data.append(sample)
        
        # 分割数据
        train_size = int(total_size * ratio)
        
        if split == 'train':
            return {
                'data': mock_data[:train_size],
                'size': train_size
            }
        elif split == 'val':
            return {
                'data': mock_data[train_size:],
                'size': total_size - train_size
            }
        else:
            return {
                'data': mock_data,
                'size': total_size
            }
    
    def augment_dataset(self, dataset_id: str, augmentation_config: Dict) -> str:
        """数据增强"""
        logger.info(f"开始数据增强: {dataset_id}")
        
        # 加载原始数据
        data = self.load_dataset(dataset_id, split='all')['data']
        
        augmented_data = []
        for item in data:
            # 保留原始数据
            augmented_data.append(item)
            
            # 根据配置进行增强
            if augmentation_config.get('synonym_replacement', False):
                augmented_item = self._synonym_replacement(item)
                augmented_data.append(augmented_item)
            
            if augmentation_config.get('random_insertion', False):
                augmented_item = self._random_insertion(item)
                augmented_data.append(augmented_item)
            
            if augmentation_config.get('random_deletion', False):
                augmented_item = self._random_deletion(item)
                augmented_data.append(augmented_item)
        
        # 保存增强后的数据集
        augmented_id = f"augmented_{dataset_id}_{uuid.uuid4().hex[:4]}"
        augmented_path = self.processed_dir / augmented_id
        augmented_path.mkdir(exist_ok=True)
        
        output_file = augmented_path / 'data.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(augmented_data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"数据增强完成: {augmented_id}, 样本数: {len(augmented_data)}")
        return augmented_id
    
    def _synonym_replacement(self, item: Dict) -> Dict:
        """同义词替换"""
        # 简单的同义词替换示例
        augmented = item.copy()
        text = augmented.get('text', '')
        
        replacements = {
            '投资': '理财',
            '收益': '回报',
            '风险': '危险',
            '保证': '确保',
            '医院': '医疗机构',
            '治疗': '医治'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        augmented['text'] = text
        augmented['augmentation'] = 'synonym_replacement'
        
        return augmented
    
    def _random_insertion(self, item: Dict) -> Dict:
        """随机插入"""
        import random
        
        augmented = item.copy()
        text = augmented.get('text', '')
        words = text.split()
        
        insert_words = ['可能', '大概', '似乎', '据说', '听说']
        
        if words:
            pos = random.randint(0, len(words))
            words.insert(pos, random.choice(insert_words))
        
        augmented['text'] = ' '.join(words)
        augmented['augmentation'] = 'random_insertion'
        
        return augmented
    
    def _random_deletion(self, item: Dict) -> Dict:
        """随机删除"""
        import random
        
        augmented = item.copy()
        text = augmented.get('text', '')
        words = text.split()
        
        if len(words) > 5:
            # 随机删除10%的词
            num_delete = max(1, int(len(words) * 0.1))
            for _ in range(num_delete):
                if words:
                    pos = random.randint(0, len(words) - 1)
                    words.pop(pos)
        
        augmented['text'] = ' '.join(words)
        augmented['augmentation'] = 'random_deletion'
        
        return augmented
