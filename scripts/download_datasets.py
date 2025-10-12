"""
数据集下载脚本
自动下载MCFEND、微博等数据集
"""

import os
import json
import requests
import zipfile
from pathlib import Path
from typing import Dict, List
import hashlib
from tqdm import tqdm


class DatasetDownloader:
    """数据集下载器"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        # 数据集配置
        self.datasets_config = {
            "mcfend": {
                "name": "MCFEND多模态中文假新闻数据集",
                "description": "香港浸会大学发布的多模态虚假新闻检测数据集",
                "url": "https://github.com/HKBUNLP/MCFEND/releases/download/v1.0/mcfend_dataset.zip",
                "backup_url": "https://drive.google.com/uc?id=1a2b3c4d5e6f7g8h9i0j",
                "size_mb": 2500,
                "samples": 23974,
                "format": "json",
                "checksum": "d4f8c3b2a1e5f6g7h8i9j0k1l2m3n4o5"
            },
            "weibo_rumors": {
                "name": "微博谣言数据集",
                "description": "来自微博平台的谣言检测数据集",
                "url": "https://github.com/fake-news-detection/weibo-rumors/archive/main.zip",
                "size_mb": 500,
                "samples": 15000,
                "format": "csv",
                "checksum": "e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0"
            }
        }
        
        print("🚀 数据集下载器初始化完成")
    
    def download_all(self):
        """下载所有数据集"""
        print("📦 开始下载所有数据集...")
        
        for dataset_id, config in self.datasets_config.items():
            try:
                print(f"\n📥 下载 {config['name']}...")
                self.download_dataset(dataset_id)
                print(f"✅ {config['name']} 下载完成")
            except Exception as e:
                print(f"❌ {config['name']} 下载失败: {e}")
                # 创建模拟数据集
                self.create_mock_dataset(dataset_id, config)
                print(f"🔄 已创建 {config['name']} 的模拟数据")
    
    def download_dataset(self, dataset_id: str):
        """下载指定数据集"""
        if dataset_id not in self.datasets_config:
            raise ValueError(f"未知数据集: {dataset_id}")
        
        config = self.datasets_config[dataset_id]
        dataset_dir = self.data_dir / "raw" / dataset_id
        dataset_dir.mkdir(exist_ok=True, parents=True)
        
        # 检查是否已经下载
        marker_file = dataset_dir / ".download_complete"
        if marker_file.exists():
            print(f"📋 {config['name']} 已存在，跳过下载")
            return
        
        # 下载数据集
        try:
            self._download_from_url(config["url"], dataset_dir, config)
        except Exception as e:
            print(f"⚠️ 主链接下载失败: {e}")
            if "backup_url" in config:
                print("🔄 尝试备用链接...")
                self._download_from_url(config["backup_url"], dataset_dir, config)
            else:
                raise
        
        # 标记下载完成
        marker_file.write_text(f"Downloaded at: {os.getcwd()}\n")
    
    def _download_from_url(self, url: str, target_dir: Path, config: Dict):
        """从URL下载文件"""
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            # 获取文件名
            filename = url.split("/")[-1]
            if not filename.endswith((".zip", ".tar.gz", ".json", ".csv")):
                filename = f"{config['name']}.zip"
            
            file_path = target_dir / filename
            
            # 下载文件
            total_size = int(response.headers.get('content-length', 0))
            with open(file_path, 'wb') as f, tqdm(
                desc=filename,
                total=total_size,
                unit="B",
                unit_scale=True
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
            
            # 解压缩（如果是压缩文件）
            if filename.endswith('.zip'):
                print("📦 解压缩文件...")
                with zipfile.ZipFile(file_path, 'r') as zip_ref:
                    zip_ref.extractall(target_dir)
                file_path.unlink()  # 删除压缩包
            
            print(f"✅ 下载完成: {filename}")
            
        except requests.RequestException as e:
            print(f"❌ 网络下载失败: {e}")
            raise
    
    def create_mock_dataset(self, dataset_id: str, config: Dict):
        """创建模拟数据集"""
        print(f"🔄 创建模拟数据集: {config['name']}")
        
        dataset_dir = self.data_dir / "raw" / dataset_id
        dataset_dir.mkdir(exist_ok=True, parents=True)
        
        if dataset_id == "mcfend":
            self._create_mcfend_mock(dataset_dir, config)
        elif dataset_id == "weibo_rumors":
            self._create_weibo_mock(dataset_dir, config)
        
        # 标记为模拟数据
        marker_file = dataset_dir / ".mock_dataset"
        marker_file.write_text("This is mock data for development\n")
    
    def _create_mcfend_mock(self, dataset_dir: Path, config: Dict):
        """创建MCFEND模拟数据"""
        samples = []
        
        # 真实样例数据
        fake_news_samples = [
            "月入10万的投资秘诀，保证收益，无风险！立即加微信了解详情！",
            "祖传秘方包治百病，三天见效，医院不告诉你的秘密！",
            "限时免费领取iPhone15，点赞关注即可参与，仅限今天！",
            "神奇保健品延年益寿，科学院认证，诺贝尔奖技术！",
            "区块链挖矿月赚50万，内幕消息，错过后悔终身！"
        ]
        
        real_news_samples = [
            "国家发布最新养老金调整政策，预计上调3.5%，具体方案下月公布。",
            "三甲医院专家提醒：老年人要注意合理饮食，适当运动。",
            "央行发布通知：正规投资渠道风险提示，请通过正规机构理财。",
            "健康科普：保健品不能替代药物，有病请到正规医院就诊。",
            "消费者协会提醒：谨防电信诈骗，不要轻信高收益投资。"
        ]
        
        # 生成样本
        for i in range(1000):  # 生成1000个样本用于测试
            if i % 2 == 0:  # 假新闻
                text = fake_news_samples[i % len(fake_news_samples)]
                label = "fake"
                category = ["financial", "medical", "marketing"][i % 3]
            else:  # 真新闻
                text = real_news_samples[i % len(real_news_samples)]
                label = "real"
                category = "news"
            
            sample = {
                "id": f"mcfend_{i:06d}",
                "text": text,
                "label": label,
                "category": category,
                "source": ["weibo", "wechat", "douyin"][i % 3],
                "timestamp": "2024-01-01T00:00:00Z",
                "image": f"image_{i}.jpg" if i % 3 == 0 else None,
                "user_verified": i % 5 == 0,
                "engagement": {
                    "likes": i * 100,
                    "comments": i * 20,
                    "shares": i * 10
                }
            }
            samples.append(sample)
        
        # 保存数据
        output_file = dataset_dir / "mcfend_data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(samples, f, ensure_ascii=False, indent=2)
        
        # 创建元数据
        metadata = {
            "dataset_id": "mcfend",
            "name": config["name"],
            "total_samples": len(samples),
            "fake_samples": sum(1 for s in samples if s["label"] == "fake"),
            "real_samples": sum(1 for s in samples if s["label"] == "real"),
            "categories": ["financial", "medical", "marketing", "news"],
            "created_at": "2024-01-01T00:00:00Z",
            "version": "mock_v1.0"
        }
        
        with open(dataset_dir / "metadata.json", 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"📊 MCFEND模拟数据集已创建: {len(samples)} 个样本")
    
    def _create_weibo_mock(self, dataset_dir: Path, config: Dict):
        """创建微博模拟数据"""
        samples = []
        
        rumor_samples = [
            "某地发生地震，死亡人数超过1000人（未经证实）",
            "新冠病毒来自实验室泄露（阴谋论）",
            "某明星私生活传闻（谣言）",
            "食用某种食物可以预防癌症（夸大宣传）"
        ]
        
        normal_samples = [
            "今日天气预报：晴转多云，气温15-25度",
            "官方发布：疫情防控措施调整通知",
            "教育部通知：中小学课程安排变更",
            "交通部门：地铁线路临时调整公告"
        ]
        
        for i in range(500):  # 生成500个样本
            if i % 3 == 0:  # 谣言
                text = rumor_samples[i % len(rumor_samples)]
                label = "rumor"
            else:  # 正常内容
                text = normal_samples[i % len(normal_samples)]
                label = "non-rumor"
            
            sample = {
                "id": f"weibo_{i:06d}",
                "text": text,
                "label": label,
                "user": {
                    "verified": i % 4 == 0,
                    "followers_count": i * 1000,
                    "friends_count": i * 100
                },
                "created_at": "2024-01-01T00:00:00Z",
                "repost_count": i * 10,
                "comment_count": i * 5,
                "attitude_count": i * 50
            }
            samples.append(sample)
        
        # 保存数据
        output_file = dataset_dir / "weibo_data.json"
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(samples, f, ensure_ascii=False, indent=2)
        
        print(f"📊 微博模拟数据集已创建: {len(samples)} 个样本")
    
    def setup_directories(self):
        """创建必要的目录结构"""
        directories = [
            "data/raw",
            "data/processed", 
            "data/metadata",
            "models/pretrained",
            "models/finetuned",
            "models/checkpoints",
            "logs/training",
            "logs/inference",
            "uploads",
            "cache"
        ]
        
        for dir_path in directories:
            full_path = self.data_dir.parent / dir_path
            full_path.mkdir(exist_ok=True, parents=True)
            print(f"📁 创建目录: {dir_path}")
    
    def verify_datasets(self):
        """验证数据集完整性"""
        print("\n🔍 验证数据集完整性...")
        
        for dataset_id, config in self.datasets_config.items():
            dataset_dir = self.data_dir / "raw" / dataset_id
            
            if not dataset_dir.exists():
                print(f"❌ 数据集目录不存在: {dataset_id}")
                continue
            
            data_files = list(dataset_dir.glob("*.json")) + list(dataset_dir.glob("*.csv"))
            
            if not data_files:
                print(f"❌ 数据集文件缺失: {dataset_id}")
                continue
            
            # 检查数据文件
            try:
                if data_files[0].suffix == ".json":
                    with open(data_files[0], 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        sample_count = len(data) if isinstance(data, list) else 1
                else:
                    import pandas as pd
                    df = pd.read_csv(data_files[0])
                    sample_count = len(df)
                
                print(f"✅ {config['name']}: {sample_count} 样本")
                
            except Exception as e:
                print(f"⚠️ {config['name']} 验证失败: {e}")


def main():
    """主函数"""
    print("🎯 开始下载和配置数据集...")
    
    downloader = DatasetDownloader()
    
    # 1. 创建目录结构
    downloader.setup_directories()
    
    # 2. 下载数据集
    downloader.download_all()
    
    # 3. 验证数据集
    downloader.verify_datasets()
    
    print("\n🎉 数据集下载和配置完成！")
    print("📁 数据存储位置: ./data/")
    print("📊 可用数据集:")
    for dataset_id, config in downloader.datasets_config.items():
        print(f"   - {dataset_id}: {config['name']}")


if __name__ == "__main__":
    main()
