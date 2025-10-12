"""
真实数据集下载脚本
提供真实可用的数据集下载链接和处理方法
"""

import os
import json
import requests
import git
from pathlib import Path
from typing import Dict, List
import subprocess
import sys


class RealDatasetDownloader:
    """真实数据集下载器"""
    
    def __init__(self, data_dir: str = "./data"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(exist_ok=True, parents=True)
        
        # 真实可用的数据集配置
        self.real_datasets = {
            "chinese_rumor": {
                "name": "中文谣言检测数据集",
                "description": "清华大学NLP组发布的中文谣言数据集",
                "repo_url": "https://github.com/thunlp/Chinese_Rumor_Dataset.git",
                "paper_url": "https://arxiv.org/abs/1701.09657",
                "size_mb": 50,
                "samples": 31669,
                "format": "json",
                "license": "MIT"
            },
            "fakenewsnet": {
                "name": "FakeNewsNet数据集",
                "description": "ASU发布的多平台虚假新闻数据集",
                "repo_url": "https://github.com/KaiDMML/FakeNewsNet.git",
                "paper_url": "https://arxiv.org/abs/1809.01286",
                "size_mb": 1200,
                "samples": 23196,
                "format": "json",
                "license": "Apache-2.0"
            },
            "liar": {
                "name": "LIAR虚假信息数据集",
                "description": "UCSB发布的事实检查数据集",
                "download_url": "https://www.cs.ucsb.edu/~william/data/liar_dataset.zip",
                "paper_url": "https://arxiv.org/abs/1705.00648",
                "size_mb": 50,
                "samples": 12836,
                "format": "tsv",
                "license": "CC BY-SA"
            },
            "weibo_rumors": {
                "name": "微博谣言传播数据集",
                "description": "香港中文大学微博谣言传播研究数据",
                "repo_url": "https://github.com/majingCUHK/Rumor_RvNN.git",
                "paper_url": "https://www.ijcai.org/Proceedings/2018/0619.pdf", 
                "size_mb": 200,
                "samples": 15000,
                "format": "json",
                "license": "GPL-3.0"
            }
        }
        
        print("🔗 真实数据集下载器初始化完成")
        self._print_dataset_info()
    
    def _print_dataset_info(self):
        """打印数据集信息"""
        print("\n📊 可下载的真实数据集:")
        for dataset_id, config in self.real_datasets.items():
            print(f"   🔹 {dataset_id}: {config['name']}")
            print(f"      📖 描述: {config['description']}")
            print(f"      📏 大小: {config['size_mb']}MB")
            print(f"      📈 样本: {config['samples']:,}条")
            if 'repo_url' in config:
                print(f"      🔗 仓库: {config['repo_url']}")
            if 'download_url' in config:
                print(f"      📥 下载: {config['download_url']}")
            print(f"      📜 论文: {config['paper_url']}")
            print()
    
    def download_chinese_rumor(self):
        """下载中文谣言数据集"""
        print("📥 下载中文谣言数据集...")
        
        dataset_dir = self.data_dir / "raw" / "chinese_rumor"
        
        try:
            # 克隆仓库
            print("🔄 克隆GitHub仓库...")
            git.Repo.clone_from(
                "https://github.com/thunlp/Chinese_Rumor_Dataset.git",
                dataset_dir,
                depth=1  # 只下载最新版本
            )
            
            print("✅ 中文谣言数据集下载成功")
            return dataset_dir
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            print("🔗 请手动访问: https://github.com/thunlp/Chinese_Rumor_Dataset")
            return None
    
    def download_fakenewsnet(self):
        """下载FakeNewsNet数据集"""
        print("📥 下载FakeNewsNet数据集...")
        
        dataset_dir = self.data_dir / "raw" / "fakenewsnet"
        
        try:
            print("🔄 克隆GitHub仓库...")
            git.Repo.clone_from(
                "https://github.com/KaiDMML/FakeNewsNet.git",
                dataset_dir,
                depth=1
            )
            
            print("✅ FakeNewsNet数据集下载成功")
            return dataset_dir
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            print("🔗 请手动访问: https://github.com/KaiDMML/FakeNewsNet")
            return None
    
    def download_liar_dataset(self):
        """下载LIAR数据集"""
        print("📥 下载LIAR数据集...")
        
        dataset_dir = self.data_dir / "raw" / "liar"
        dataset_dir.mkdir(exist_ok=True, parents=True)
        
        try:
            # 直接下载zip文件
            url = "https://www.cs.ucsb.edu/~william/data/liar_dataset.zip"
            
            print("🔄 下载zip文件...")
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            zip_path = dataset_dir / "liar_dataset.zip"
            with open(zip_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            # 解压
            print("📦 解压文件...")
            import zipfile
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(dataset_dir)
            
            zip_path.unlink()  # 删除zip文件
            
            print("✅ LIAR数据集下载成功")
            return dataset_dir
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            print("🔗 请手动下载: https://www.cs.ucsb.edu/~william/data/liar_dataset.zip")
            return None
    
    def download_weibo_rumors(self):
        """下载微博谣言数据集"""
        print("📥 下载微博谣言数据集...")
        
        dataset_dir = self.data_dir / "raw" / "weibo_rumors"
        
        try:
            print("🔄 克隆GitHub仓库...")
            git.Repo.clone_from(
                "https://github.com/majingCUHK/Rumor_RvNN.git",
                dataset_dir,
                depth=1
            )
            
            print("✅ 微博谣言数据集下载成功")
            return dataset_dir
            
        except Exception as e:
            print(f"❌ 下载失败: {e}")
            print("🔗 请手动访问: https://github.com/majingCUHK/Rumor_RvNN")
            return None
    
    def download_all_available(self):
        """下载所有可用的真实数据集"""
        print("🎯 开始下载所有真实数据集...")
        
        results = {}
        
        # 依次尝试下载
        datasets_methods = [
            ("chinese_rumor", self.download_chinese_rumor),
            ("fakenewsnet", self.download_fakenewsnet), 
            ("liar", self.download_liar_dataset),
            ("weibo_rumors", self.download_weibo_rumors)
        ]
        
        for dataset_id, download_method in datasets_methods:
            try:
                result = download_method()
                results[dataset_id] = "success" if result else "failed"
            except Exception as e:
                print(f"❌ {dataset_id} 下载异常: {e}")
                results[dataset_id] = "error"
        
        # 显示下载结果
        print("\n📊 下载结果汇总:")
        for dataset_id, status in results.items():
            config = self.real_datasets.get(dataset_id, {})
            name = config.get('name', dataset_id)
            
            if status == "success":
                print(f"   ✅ {name}: 下载成功")
            else:
                print(f"   ❌ {name}: 下载失败")
                if 'repo_url' in config:
                    print(f"      📎 手动访问: {config['repo_url']}")
                elif 'download_url' in config:
                    print(f"      📎 手动下载: {config['download_url']}")
        
        return results
    
    def install_git_if_needed(self):
        """检查并安装Git（如果需要）"""
        try:
            subprocess.run(["git", "--version"], 
                         capture_output=True, check=True)
            print("✅ Git 已安装")
            return True
        except:
            print("❌ Git 未安装或不可用")
            print("🔗 请安装Git: https://git-scm.com/download/win")
            print("   或者使用手动下载方式")
            return False


def print_manual_download_guide():
    """打印手动下载指南"""
    print("""
🔗 手动下载指南

如果自动下载失败，请按以下步骤手动下载：

📊 优先推荐（按重要性排序）：

1. 🇨🇳 中文谣言数据集 (最重要)
   - 访问: https://github.com/thunlp/Chinese_Rumor_Dataset
   - 点击绿色"Code"按钮 → Download ZIP
   - 解压到: D:\\Projects\\Fact-Safe-Elder\\data\\raw\\chinese_rumor\\

2. 📰 LIAR数据集 (推荐)
   - 直接下载: https://www.cs.ucsb.edu/~william/data/liar_dataset.zip
   - 解压到: D:\\Projects\\Fact-Safe-Elder\\data\\raw\\liar\\

3. 🌐 FakeNewsNet (可选)
   - 访问: https://github.com/KaiDMML/FakeNewsNet
   - 下载数据文件到: D:\\Projects\\Fact-Safe-Elder\\data\\raw\\fakenewsnet\\

4. 📱 微博谣言数据集 (可选)
   - 访问: https://github.com/majingCUHK/Rumor_RvNN
   - 下载到: D:\\Projects\\Fact-Safe-Elder\\data\\raw\\weibo_rumors\\

📁 目录结构示例:
D:\\Projects\\Fact-Safe-Elder\\data\\
├── raw\\
│   ├── chinese_rumor\\
│   │   ├── train.json
│   │   ├── test.json
│   │   └── val.json
│   ├── liar\\
│   │   ├── train.tsv
│   │   ├── test.tsv
│   │   └── valid.tsv
│   └── fakenewsnet\\
│       ├── politifact_fake.json
│       └── politifact_real.json

🔧 下载完成后运行:
python scripts/process_real_data.py --verify
""")


def main():
    """主函数"""
    print("🎯 真实数据集下载工具")
    
    downloader = RealDatasetDownloader()
    
    # 检查Git
    if not downloader.install_git_if_needed():
        print_manual_download_guide()
        return
    
    # 尝试下载
    try:
        results = downloader.download_all_available()
        
        success_count = sum(1 for status in results.values() if status == "success")
        
        if success_count > 0:
            print(f"\n🎉 成功下载 {success_count} 个数据集！")
        else:
            print("\n⚠️ 自动下载全部失败，请使用手动下载:")
            print_manual_download_guide()
            
    except Exception as e:
        print(f"❌ 下载过程发生错误: {e}")
        print_manual_download_guide()


if __name__ == "__main__":
    main()
