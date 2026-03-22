"""
FakeSV和其他数据集加载器
支持多模态数据集的加载和预处理

数据集支持:
1. FakeSV - 短视频虚假信息检测数据集
2. Weibo21 - 中文多模态谣言数据集
3. MCFEND - 多源中文假新闻数据集
4. 自定义数据集
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Generator
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import random
from loguru import logger

try:
    import numpy as np
    import pandas as pd
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False

try:
    import torch
    from torch.utils.data import Dataset, DataLoader
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False

try:
    from PIL import Image
    import cv2
    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False


class DatasetType(Enum):
    """数据集类型"""
    FAKESV = "fakesv"
    WEIBO21 = "weibo21"
    MCFEND = "mcfend"
    CUSTOM = "custom"


@dataclass
class DataSample:
    """数据样本"""
    sample_id: str
    text: str
    label: int  # 0: safe/real, 1: warning, 2: danger/fake
    image_path: Optional[str] = None
    video_path: Optional[str] = None
    audio_path: Optional[str] = None
    metadata: Optional[Dict] = None
    
    # 预提取特征（可选，用于加速训练）
    text_features: Optional[np.ndarray] = None
    visual_features: Optional[np.ndarray] = None
    audio_features: Optional[np.ndarray] = None


@dataclass
class DatasetInfo:
    """数据集信息"""
    name: str
    type: DatasetType
    total_samples: int
    train_samples: int
    val_samples: int
    test_samples: int
    num_classes: int
    class_distribution: Dict[int, int]
    modalities: List[str]
    language: str
    description: str


class FakeSVDataset:
    """
    FakeSV数据集加载器
    
    数据集结构:
    FakeSV/
    ├── train/
    │   ├── videos/
    │   ├── audio/
    │   ├── frames/
    │   └── labels.json
    ├── val/
    ├── test/
    └── features/
        ├── vgg19_features.npy
        ├── c3d_features.npy
        ├── vggish_features.npy
        └── bert_features.npy
    """
    
    def __init__(
        self,
        data_root: str,
        use_precomputed_features: bool = True,
        load_videos: bool = False,
        load_audio: bool = False
    ):
        """
        初始化FakeSV数据集
        
        Args:
            data_root: 数据集根目录
            use_precomputed_features: 是否使用预计算特征
            load_videos: 是否加载原始视频
            load_audio: 是否加载原始音频
        """
        self.data_root = Path(data_root)
        self.use_precomputed_features = use_precomputed_features
        self.load_videos = load_videos
        self.load_audio = load_audio
        
        # 数据分割
        self.train_samples: List[DataSample] = []
        self.val_samples: List[DataSample] = []
        self.test_samples: List[DataSample] = []
        
        # 预计算特征
        self.precomputed_features: Dict[str, np.ndarray] = {}
        
        # 类别映射
        self.label_map = {
            'real': 0,
            'fake': 2,
            'safe': 0,
            'warning': 1,
            'danger': 2
        }
        
        logger.info(f"初始化FakeSV数据集: {data_root}")
    
    def load(self) -> DatasetInfo:
        """加载数据集"""
        # 加载各分割的数据
        self.train_samples = self._load_split('train')
        self.val_samples = self._load_split('val')
        self.test_samples = self._load_split('test')
        
        # 加载预计算特征
        if self.use_precomputed_features:
            self._load_precomputed_features()
        
        # 统计信息
        all_samples = self.train_samples + self.val_samples + self.test_samples
        class_dist = self._calculate_class_distribution(all_samples)
        
        info = DatasetInfo(
            name="FakeSV",
            type=DatasetType.FAKESV,
            total_samples=len(all_samples),
            train_samples=len(self.train_samples),
            val_samples=len(self.val_samples),
            test_samples=len(self.test_samples),
            num_classes=3,
            class_distribution=class_dist,
            modalities=['text', 'video', 'audio'],
            language='zh',
            description="短视频虚假信息检测数据集"
        )
        
        logger.info(f"FakeSV数据集加载完成: {info.total_samples}样本")
        return info
    
    def _load_split(self, split: str) -> List[DataSample]:
        """加载单个数据分割"""
        split_dir = self.data_root / split
        labels_file = split_dir / 'labels.json'
        
        samples = []
        
        if not labels_file.exists():
            logger.warning(f"标签文件不存在: {labels_file}")
            return samples
        
        with open(labels_file, 'r', encoding='utf-8') as f:
            labels_data = json.load(f)
        
        for item in labels_data:
            sample = DataSample(
                sample_id=item['id'],
                text=item.get('text', ''),
                label=self.label_map.get(item['label'], 0),
                image_path=str(split_dir / 'frames' / f"{item['id']}.jpg") if item.get('has_frames') else None,
                video_path=str(split_dir / 'videos' / f"{item['id']}.mp4") if item.get('has_video') else None,
                audio_path=str(split_dir / 'audio' / f"{item['id']}.wav") if item.get('has_audio') else None,
                metadata=item.get('metadata', {})
            )
            samples.append(sample)
        
        return samples
    
    def _load_precomputed_features(self):
        """加载预计算特征"""
        features_dir = self.data_root / 'features'
        
        feature_files = {
            'vgg19': 'vgg19_features.npy',
            'c3d': 'c3d_features.npy',
            'vggish': 'vggish_features.npy',
            'bert': 'bert_features.npy'
        }
        
        for feat_name, feat_file in feature_files.items():
            feat_path = features_dir / feat_file
            if feat_path.exists():
                self.precomputed_features[feat_name] = np.load(feat_path, allow_pickle=True)
                logger.info(f"加载预计算特征: {feat_name}")
    
    def _calculate_class_distribution(self, samples: List[DataSample]) -> Dict[int, int]:
        """计算类别分布"""
        dist = {0: 0, 1: 0, 2: 0}
        for sample in samples:
            dist[sample.label] = dist.get(sample.label, 0) + 1
        return dist
    
    def get_dataloader(
        self,
        split: str = 'train',
        batch_size: int = 16,
        shuffle: bool = True,
        num_workers: int = 4
    ):
        """获取PyTorch DataLoader"""
        if not TORCH_AVAILABLE:
            raise ImportError("需要安装PyTorch")
        
        if split == 'train':
            samples = self.train_samples
        elif split == 'val':
            samples = self.val_samples
        else:
            samples = self.test_samples
        
        dataset = FakeSVTorchDataset(
            samples,
            self.precomputed_features,
            self.use_precomputed_features
        )
        
        return DataLoader(
            dataset,
            batch_size=batch_size,
            shuffle=shuffle,
            num_workers=num_workers,
            collate_fn=self._collate_fn
        )
    
    def _collate_fn(self, batch):
        """自定义批处理函数"""
        texts = [item['text'] for item in batch]
        labels = torch.tensor([item['label'] for item in batch])
        
        result = {
            'texts': texts,
            'labels': labels
        }
        
        # 预计算特征
        if 'text_features' in batch[0]:
            result['text_features'] = torch.stack([item['text_features'] for item in batch])
        if 'visual_features' in batch[0]:
            result['visual_features'] = torch.stack([item['visual_features'] for item in batch])
        if 'audio_features' in batch[0]:
            result['audio_features'] = torch.stack([item['audio_features'] for item in batch])
        
        return result


class FakeSVTorchDataset(Dataset):
    """FakeSV PyTorch数据集"""
    
    def __init__(
        self,
        samples: List[DataSample],
        precomputed_features: Dict[str, np.ndarray],
        use_precomputed: bool = True
    ):
        self.samples = samples
        self.precomputed_features = precomputed_features
        self.use_precomputed = use_precomputed
    
    def __len__(self):
        return len(self.samples)
    
    def __getitem__(self, idx) -> Dict:
        sample = self.samples[idx]
        
        item = {
            'sample_id': sample.sample_id,
            'text': sample.text,
            'label': sample.label
        }
        
        # 添加预计算特征
        if self.use_precomputed and sample.sample_id in self.precomputed_features.get('bert', {}):
            item['text_features'] = torch.tensor(
                self.precomputed_features['bert'][sample.sample_id],
                dtype=torch.float32
            )
        
        return item


class Weibo21Dataset:
    """
    Weibo21数据集加载器
    中文多模态谣言检测数据集
    """
    
    def __init__(self, data_root: str):
        self.data_root = Path(data_root)
        self.samples: List[DataSample] = []
        
    def load(self) -> DatasetInfo:
        """加载Weibo21数据集"""
        rumor_dir = self.data_root / 'rumor'
        nonrumor_dir = self.data_root / 'nonrumor'
        
        # 加载谣言样本
        if rumor_dir.exists():
            self._load_weibo_samples(rumor_dir, label=2)  # fake/danger
        
        # 加载非谣言样本
        if nonrumor_dir.exists():
            self._load_weibo_samples(nonrumor_dir, label=0)  # real/safe
        
        # 随机打乱
        random.shuffle(self.samples)
        
        # 划分数据集
        n = len(self.samples)
        train_end = int(n * 0.8)
        val_end = int(n * 0.9)
        
        return DatasetInfo(
            name="Weibo21",
            type=DatasetType.WEIBO21,
            total_samples=n,
            train_samples=train_end,
            val_samples=val_end - train_end,
            test_samples=n - val_end,
            num_classes=2,
            class_distribution=self._calculate_class_distribution(),
            modalities=['text', 'image'],
            language='zh',
            description="中文微博多模态谣言检测数据集"
        )
    
    def _load_weibo_samples(self, directory: Path, label: int):
        """加载微博样本"""
        for post_dir in directory.iterdir():
            if not post_dir.is_dir():
                continue
            
            # 读取文本
            text_file = post_dir / 'text.txt'
            if text_file.exists():
                text = text_file.read_text(encoding='utf-8').strip()
            else:
                continue
            
            # 查找图片
            image_path = None
            for img_ext in ['.jpg', '.jpeg', '.png']:
                img_file = post_dir / f'image{img_ext}'
                if img_file.exists():
                    image_path = str(img_file)
                    break
            
            sample = DataSample(
                sample_id=post_dir.name,
                text=text,
                label=label,
                image_path=image_path
            )
            self.samples.append(sample)
    
    def _calculate_class_distribution(self) -> Dict[int, int]:
        dist = {}
        for sample in self.samples:
            dist[sample.label] = dist.get(sample.label, 0) + 1
        return dist


class MCFENDDataset:
    """
    MCFEND数据集加载器
    多源中文假新闻检测数据集
    """
    
    def __init__(self, data_root: str):
        self.data_root = Path(data_root)
        self.samples: List[DataSample] = []
    
    def load(self) -> DatasetInfo:
        """加载MCFEND数据集"""
        data_file = self.data_root / 'mcfend_data.json'
        
        if not data_file.exists():
            logger.warning(f"MCFEND数据文件不存在: {data_file}")
            return self._empty_info()
        
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            sample = DataSample(
                sample_id=item['id'],
                text=item['content'],
                label=2 if item['label'] == 'fake' else 0,
                image_path=item.get('image_path'),
                metadata={
                    'source': item.get('source'),
                    'category': item.get('category'),
                    'publish_time': item.get('publish_time')
                }
            )
            self.samples.append(sample)
        
        return DatasetInfo(
            name="MCFEND",
            type=DatasetType.MCFEND,
            total_samples=len(self.samples),
            train_samples=int(len(self.samples) * 0.8),
            val_samples=int(len(self.samples) * 0.1),
            test_samples=int(len(self.samples) * 0.1),
            num_classes=2,
            class_distribution=self._calculate_class_distribution(),
            modalities=['text', 'image'],
            language='zh',
            description="多源中文假新闻检测数据集"
        )
    
    def _calculate_class_distribution(self) -> Dict[int, int]:
        dist = {}
        for sample in self.samples:
            dist[sample.label] = dist.get(sample.label, 0) + 1
        return dist
    
    def _empty_info(self) -> DatasetInfo:
        return DatasetInfo(
            name="MCFEND",
            type=DatasetType.MCFEND,
            total_samples=0,
            train_samples=0,
            val_samples=0,
            test_samples=0,
            num_classes=2,
            class_distribution={},
            modalities=['text', 'image'],
            language='zh',
            description="多源中文假新闻检测数据集（未加载）"
        )


class CustomDataset:
    """
    自定义数据集加载器
    支持用户自己收集的金融诈骗/医疗虚假信息数据
    """
    
    def __init__(self, data_root: str):
        self.data_root = Path(data_root)
        self.samples: List[DataSample] = []
        
        # 预定义的领域类别
        self.domains = ['financial', 'medical', 'general']
    
    def load(self) -> DatasetInfo:
        """加载自定义数据集"""
        # 从JSON文件加载
        data_file = self.data_root / 'custom_dataset.json'
        
        if data_file.exists():
            self._load_from_json(data_file)
        else:
            # 从目录结构加载
            self._load_from_directory()
        
        return DatasetInfo(
            name="Custom",
            type=DatasetType.CUSTOM,
            total_samples=len(self.samples),
            train_samples=int(len(self.samples) * 0.8),
            val_samples=int(len(self.samples) * 0.1),
            test_samples=int(len(self.samples) * 0.1),
            num_classes=3,
            class_distribution=self._calculate_class_distribution(),
            modalities=['text', 'video', 'audio'],
            language='zh',
            description="自定义虚假信息检测数据集"
        )
    
    def _load_from_json(self, json_file: Path):
        """从JSON文件加载"""
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        for item in data:
            label = item.get('label', 0)
            if isinstance(label, str):
                label = {'safe': 0, 'warning': 1, 'danger': 2, 'real': 0, 'fake': 2}.get(label, 0)
            
            sample = DataSample(
                sample_id=item.get('id', str(len(self.samples))),
                text=item['text'],
                label=label,
                video_path=item.get('video_path'),
                audio_path=item.get('audio_path'),
                image_path=item.get('image_path'),
                metadata=item.get('metadata', {})
            )
            self.samples.append(sample)
    
    def _load_from_directory(self):
        """从目录结构加载"""
        for domain in self.domains:
            domain_dir = self.data_root / domain
            if not domain_dir.exists():
                continue
            
            # 加载真实样本
            real_dir = domain_dir / 'real'
            if real_dir.exists():
                self._load_samples_from_dir(real_dir, label=0, domain=domain)
            
            # 加载虚假样本
            fake_dir = domain_dir / 'fake'
            if fake_dir.exists():
                self._load_samples_from_dir(fake_dir, label=2, domain=domain)
    
    def _load_samples_from_dir(self, directory: Path, label: int, domain: str):
        """从目录加载样本"""
        for file_path in directory.glob('*.txt'):
            text = file_path.read_text(encoding='utf-8').strip()
            
            sample = DataSample(
                sample_id=file_path.stem,
                text=text,
                label=label,
                metadata={'domain': domain}
            )
            self.samples.append(sample)
    
    def _calculate_class_distribution(self) -> Dict[int, int]:
        dist = {0: 0, 1: 0, 2: 0}
        for sample in self.samples:
            dist[sample.label] = dist.get(sample.label, 0) + 1
        return dist
    
    def add_sample(
        self,
        text: str,
        label: int,
        video_path: Optional[str] = None,
        audio_path: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> str:
        """添加新样本"""
        sample_id = f"custom_{len(self.samples)}"
        
        sample = DataSample(
            sample_id=sample_id,
            text=text,
            label=label,
            video_path=video_path,
            audio_path=audio_path,
            metadata=metadata or {}
        )
        
        self.samples.append(sample)
        return sample_id
    
    def save(self, output_path: Optional[str] = None):
        """保存数据集"""
        output_file = Path(output_path) if output_path else self.data_root / 'custom_dataset.json'
        
        data = []
        for sample in self.samples:
            data.append({
                'id': sample.sample_id,
                'text': sample.text,
                'label': sample.label,
                'video_path': sample.video_path,
                'audio_path': sample.audio_path,
                'image_path': sample.image_path,
                'metadata': sample.metadata
            })
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        logger.info(f"数据集已保存: {output_file}")


class DatasetManager:
    """
    数据集管理器
    统一管理多个数据集的加载和预处理
    """
    
    def __init__(self, data_root: str = "./data"):
        self.data_root = Path(data_root)
        self.datasets: Dict[str, Any] = {}
        self.dataset_info: Dict[str, DatasetInfo] = {}
    
    def load_dataset(self, dataset_type: DatasetType, **kwargs) -> DatasetInfo:
        """加载指定类型的数据集"""
        if dataset_type == DatasetType.FAKESV:
            dataset = FakeSVDataset(
                self.data_root / 'fakesv',
                **kwargs
            )
        elif dataset_type == DatasetType.WEIBO21:
            dataset = Weibo21Dataset(self.data_root / 'weibo21')
        elif dataset_type == DatasetType.MCFEND:
            dataset = MCFENDDataset(self.data_root / 'mcfend')
        elif dataset_type == DatasetType.CUSTOM:
            dataset = CustomDataset(self.data_root / 'custom')
        else:
            raise ValueError(f"不支持的数据集类型: {dataset_type}")
        
        info = dataset.load()
        self.datasets[dataset_type.value] = dataset
        self.dataset_info[dataset_type.value] = info
        
        return info
    
    def get_combined_samples(
        self,
        dataset_types: List[DatasetType],
        split: str = 'train'
    ) -> List[DataSample]:
        """获取多个数据集的组合样本"""
        samples = []
        
        for dt in dataset_types:
            if dt.value not in self.datasets:
                self.load_dataset(dt)
            
            dataset = self.datasets[dt.value]
            
            if hasattr(dataset, f'{split}_samples'):
                samples.extend(getattr(dataset, f'{split}_samples'))
            elif hasattr(dataset, 'samples'):
                # 按比例划分
                n = len(dataset.samples)
                if split == 'train':
                    samples.extend(dataset.samples[:int(n * 0.8)])
                elif split == 'val':
                    samples.extend(dataset.samples[int(n * 0.8):int(n * 0.9)])
                else:
                    samples.extend(dataset.samples[int(n * 0.9):])
        
        return samples
    
    def get_statistics(self) -> Dict:
        """获取所有数据集的统计信息"""
        stats = {}
        for name, info in self.dataset_info.items():
            stats[name] = asdict(info)
        return stats
    
    def create_balanced_dataset(
        self,
        samples: List[DataSample],
        target_per_class: int = 1000
    ) -> List[DataSample]:
        """创建类别平衡的数据集"""
        # 按类别分组
        class_samples = {0: [], 1: [], 2: []}
        for sample in samples:
            class_samples[sample.label].append(sample)
        
        balanced = []
        for label, class_data in class_samples.items():
            if len(class_data) >= target_per_class:
                balanced.extend(random.sample(class_data, target_per_class))
            else:
                # 过采样
                balanced.extend(class_data)
                while len([s for s in balanced if s.label == label]) < target_per_class:
                    balanced.extend(random.sample(class_data, min(len(class_data), target_per_class - len([s for s in balanced if s.label == label]))))
        
        random.shuffle(balanced)
        return balanced


class VideoFrameExtractor:
    """
    视频帧提取器
    用于从视频中提取关键帧
    """
    
    def __init__(
        self,
        frame_interval: int = 30,  # 每30帧提取一帧
        max_frames: int = 10
    ):
        self.frame_interval = frame_interval
        self.max_frames = max_frames
    
    def extract_frames(self, video_path: str) -> List[np.ndarray]:
        """
        从视频提取帧
        
        Args:
            video_path: 视频文件路径
            
        Returns:
            帧列表
        """
        if not IMAGE_AVAILABLE:
            logger.warning("OpenCV未安装，无法提取视频帧")
            return []
        
        frames = []
        cap = cv2.VideoCapture(video_path)
        
        frame_count = 0
        while cap.isOpened() and len(frames) < self.max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            if frame_count % self.frame_interval == 0:
                # 转换为RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)
            
            frame_count += 1
        
        cap.release()
        return frames
    
    def extract_keyframes(self, video_path: str, num_frames: int = 3) -> List[np.ndarray]:
        """
        提取关键帧（首、中、尾）
        """
        if not IMAGE_AVAILABLE:
            return []
        
        cap = cv2.VideoCapture(video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        if total_frames == 0:
            return []
        
        # 计算关键帧位置
        positions = [0, total_frames // 2, total_frames - 1][:num_frames]
        
        frames = []
        for pos in positions:
            cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
            ret, frame = cap.read()
            if ret:
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frames.append(frame_rgb)
        
        cap.release()
        return frames


# 预置的训练数据样本（用于演示和测试）
DEMO_SAMPLES = [
    # 金融诈骗样本
    DataSample(
        sample_id="demo_fin_1",
        text="投资理财新机会！月入3万不是梦，专业团队指导，保证收益，无任何风险！联系微信xxx",
        label=2,
        metadata={"domain": "financial", "source": "demo"}
    ),
    DataSample(
        sample_id="demo_fin_2",
        text="内部消息，稳赚不赔！股票推荐，包赚不亏，年收益300%！现在加入立享优惠",
        label=2,
        metadata={"domain": "financial", "source": "demo"}
    ),
    DataSample(
        sample_id="demo_fin_3",
        text="银行官方理财产品，年化收益3.5%，R2风险等级。理财有风险，投资需谨慎。",
        label=0,
        metadata={"domain": "financial", "source": "demo"}
    ),
    
    # 医疗虚假信息样本
    DataSample(
        sample_id="demo_med_1",
        text="神奇保健品，包治百病！祖传秘方，三天见效，医院不告诉你的秘密",
        label=2,
        metadata={"domain": "medical", "source": "demo"}
    ),
    DataSample(
        sample_id="demo_med_2",
        text="一次根治高血压、糖尿病！100%有效，永不复发！特价980元，原价3980元",
        label=2,
        metadata={"domain": "medical", "source": "demo"}
    ),
    DataSample(
        sample_id="demo_med_3",
        text="健康饮食小贴士：均衡饮食很重要，如有健康问题请咨询专业医生。",
        label=0,
        metadata={"domain": "medical", "source": "demo"}
    ),
    
    # 可疑内容样本
    DataSample(
        sample_id="demo_warn_1",
        text="限时优惠，原价999现在只要99！数量有限，先到先得！",
        label=1,
        metadata={"domain": "general", "source": "demo"}
    ),
    DataSample(
        sample_id="demo_warn_2",
        text="转发这条消息给10个人，你会有好运！不转发就会倒霉七天！",
        label=1,
        metadata={"domain": "general", "source": "demo"}
    ),
]


def get_demo_dataset() -> List[DataSample]:
    """获取演示数据集"""
    return DEMO_SAMPLES.copy()


# 导出
__all__ = [
    'DatasetType',
    'DataSample',
    'DatasetInfo',
    'FakeSVDataset',
    'Weibo21Dataset',
    'MCFENDDataset',
    'CustomDataset',
    'DatasetManager',
    'VideoFrameExtractor',
    'get_demo_dataset'
]







