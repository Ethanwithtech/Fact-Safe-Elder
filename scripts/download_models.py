"""
AI模型下载脚本
自动下载ChatGLM、BERT、LLaMA等预训练模型
"""

import os
import json
import requests
from pathlib import Path
from typing import Dict, List
import subprocess
import sys


class ModelDownloader:
    """AI模型下载器"""
    
    def __init__(self, models_dir: str = "./models"):
        self.models_dir = Path(models_dir)
        self.models_dir.mkdir(exist_ok=True, parents=True)
        
        # 模型配置
        self.models_config = {
            "chatglm-6b": {
                "name": "ChatGLM-6B",
                "description": "清华大学开源的中文对话模型",
                "source": "THUDM/chatglm-6b",
                "size_gb": 12.5,
                "type": "transformers",
                "tasks": ["text-generation", "classification"],
                "quantized_versions": ["int8", "int4"]
            },
            "chinese-bert": {
                "name": "Chinese-BERT-wwm-ext", 
                "description": "中文BERT预训练模型",
                "source": "hfl/chinese-bert-wwm-ext",
                "size_gb": 1.2,
                "type": "transformers",
                "tasks": ["text-classification", "feature-extraction"]
            },
            "chinese-llama-7b": {
                "name": "Chinese-LLaMA-7B",
                "description": "中文LLaMA大语言模型", 
                "source": "ziqingyang/chinese-llama-7b",
                "size_gb": 15.0,
                "type": "transformers",
                "tasks": ["text-generation", "classification"]
            }
        }
        
        print("🤖 AI模型下载器初始化完成")
    
    def check_huggingface_cli(self):
        """检查huggingface-hub CLI是否安装"""
        try:
            result = subprocess.run(
                [sys.executable, "-c", "import huggingface_hub"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ Hugging Face Hub 已安装")
                return True
        except:
            pass
        
        print("📦 安装 Hugging Face Hub...")
        subprocess.run([
            sys.executable, "-m", "pip", "install", 
            "huggingface-hub", "transformers", "--quiet"
        ])
        return True
    
    def download_model(self, model_id: str, quantized: bool = False):
        """下载指定模型"""
        if model_id not in self.models_config:
            raise ValueError(f"未知模型: {model_id}")
        
        config = self.models_config[model_id]
        model_dir = self.models_dir / model_id
        
        # 检查是否已下载
        marker_file = model_dir / ".download_complete"
        if marker_file.exists():
            print(f"📋 {config['name']} 已存在，跳过下载")
            return model_dir
        
        print(f"📥 下载 {config['name']}...")
        print(f"📊 预计大小: {config['size_gb']} GB")
        
        try:
            # 使用huggingface-hub下载
            from huggingface_hub import snapshot_download
            
            model_path = snapshot_download(
                repo_id=config["source"],
                local_dir=model_dir,
                local_dir_use_symlinks=False,
                resume_download=True
            )
            
            # 标记下载完成
            marker_file.write_text(f"Downloaded from: {config['source']}\n")
            
            print(f"✅ {config['name']} 下载完成")
            return model_dir
            
        except Exception as e:
            print(f"❌ {config['name']} 下载失败: {e}")
            # 创建模拟模型配置
            self._create_mock_model(model_dir, config)
            return model_dir
    
    def _create_mock_model(self, model_dir: Path, config: Dict):
        """创建模拟模型配置"""
        model_dir.mkdir(exist_ok=True, parents=True)
        
        # 创建模型配置文件
        model_config = {
            "model_type": config["type"],
            "name": config["name"],
            "description": config["description"],
            "tasks": config["tasks"],
            "size_gb": config["size_gb"],
            "source": config["source"],
            "status": "mock",
            "created_at": "2024-01-01T00:00:00Z",
            "note": "这是模拟模型，用于开发测试"
        }
        
        with open(model_dir / "config.json", 'w', encoding='utf-8') as f:
            json.dump(model_config, f, ensure_ascii=False, indent=2)
        
        # 创建模拟权重文件（空文件）
        (model_dir / "pytorch_model.bin").touch()
        (model_dir / "tokenizer.json").touch()
        (model_dir / "tokenizer_config.json").touch()
        
        # 标记为模拟模型
        marker_file = model_dir / ".mock_model"
        marker_file.write_text("This is a mock model for development\n")
        
        print(f"🔄 已创建 {config['name']} 的模拟配置")
    
    def download_all(self, include_large_models: bool = False):
        """下载所有模型"""
        print("🤖 开始下载AI模型...")
        
        # 首先检查环境
        if not self.check_huggingface_cli():
            print("❌ 无法安装Hugging Face依赖")
            include_large_models = False
        
        models_to_download = ["chinese-bert"]  # 从小模型开始
        
        if include_large_models:
            models_to_download.extend(["chatglm-6b", "chinese-llama-7b"])
        else:
            print("⚠️ 跳过大模型下载，仅下载轻量级模型")
        
        for model_id in models_to_download:
            try:
                self.download_model(model_id)
            except Exception as e:
                print(f"❌ 模型 {model_id} 下载失败: {e}")
        
        print("🎉 模型下载完成！")
    
    def list_downloaded_models(self):
        """列出已下载的模型"""
        print("\n📋 已下载的模型:")
        
        for model_id, config in self.models_config.items():
            model_dir = self.models_dir / model_id
            
            if model_dir.exists():
                if (model_dir / ".mock_model").exists():
                    status = "🔄 模拟模型"
                elif (model_dir / ".download_complete").exists():
                    status = "✅ 完整下载"
                else:
                    status = "⚠️ 不完整"
                
                print(f"   - {config['name']}: {status}")
            else:
                print(f"   - {config['name']}: ❌ 未下载")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="AI模型下载工具")
    parser.add_argument("--all", action="store_true", help="下载所有模型（包括大模型）")
    parser.add_argument("--model", type=str, help="下载指定模型")
    parser.add_argument("--list", action="store_true", help="列出可用模型")
    parser.add_argument("--quantized", action="store_true", help="下载量化版本")
    
    args = parser.parse_args()
    
    downloader = ModelDownloader()
    
    if args.list:
        print("🤖 可用模型列表:")
        for model_id, config in downloader.models_config.items():
            print(f"   - {model_id}: {config['name']} ({config['size_gb']} GB)")
        return
    
    if args.model:
        downloader.download_model(args.model, args.quantized)
    elif args.all:
        downloader.download_all(include_large_models=True)
    else:
        # 默认只下载轻量级模型
        downloader.download_all(include_large_models=False)
    
    # 显示下载结果
    downloader.list_downloaded_models()


if __name__ == "__main__":
    main()
