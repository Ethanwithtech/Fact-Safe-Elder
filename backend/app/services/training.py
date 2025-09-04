"""
模型训练服务
"""

import os
import uuid
import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path
from dataclasses import dataclass, asdict
from enum import Enum
from loguru import logger


class TrainingStatus(Enum):
    """训练状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class TrainingTask:
    """训练任务"""
    task_id: str
    model_type: str
    dataset_id: str
    status: TrainingStatus
    config: Dict
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    current_epoch: int = 0
    total_epochs: int = 0
    best_metric: float = 0.0
    metrics_history: List[Dict] = None
    logs: List[str] = None
    error: Optional[str] = None
    
    def __post_init__(self):
        if self.metrics_history is None:
            self.metrics_history = []
        if self.logs is None:
            self.logs = []


class TrainingService:
    """训练服务"""
    
    def __init__(self):
        self.tasks: Dict[str, TrainingTask] = {}
        self.models_dir = Path("./models")
        self.checkpoints_dir = Path("./checkpoints")
        self.logs_dir = Path("./logs/training")
        
        # 创建必要的目录
        self.models_dir.mkdir(exist_ok=True, parents=True)
        self.checkpoints_dir.mkdir(exist_ok=True, parents=True)
        self.logs_dir.mkdir(exist_ok=True, parents=True)
        
        logger.info("训练服务已初始化")
    
    def create_training_task(self, model_type: str, dataset_id: str, config: Dict) -> str:
        """创建训练任务"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        
        task = TrainingTask(
            task_id=task_id,
            model_type=model_type,
            dataset_id=dataset_id,
            status=TrainingStatus.PENDING,
            config=config,
            created_at=datetime.now(),
            total_epochs=config.get('epochs', 10)
        )
        
        self.tasks[task_id] = task
        
        # 保存任务信息到文件
        self._save_task(task)
        
        logger.info(f"训练任务已创建: {task_id}")
        return task_id
    
    async def run_training(self, task_id: str, config: Dict):
        """执行训练任务"""
        if task_id not in self.tasks:
            logger.error(f"任务 {task_id} 不存在")
            return
        
        task = self.tasks[task_id]
        
        try:
            # 更新任务状态
            task.status = TrainingStatus.RUNNING
            task.started_at = datetime.now()
            self._save_task(task)
            
            logger.info(f"开始训练任务: {task_id}")
            
            # 根据模型类型选择训练方法
            if task.model_type == "chatglm":
                await self._train_chatglm(task)
            elif task.model_type == "bert":
                await self._train_bert(task)
            elif task.model_type == "llama":
                await self._train_llama(task)
            else:
                raise ValueError(f"不支持的模型类型: {task.model_type}")
            
            # 训练完成
            task.status = TrainingStatus.COMPLETED
            task.completed_at = datetime.now()
            self._save_task(task)
            
            logger.info(f"训练任务完成: {task_id}")
            
        except Exception as e:
            logger.error(f"训练任务失败 {task_id}: {e}")
            task.status = TrainingStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now()
            self._save_task(task)
    
    async def _train_chatglm(self, task: TrainingTask):
        """训练ChatGLM模型"""
        logger.info(f"开始ChatGLM训练: {task.task_id}")
        
        # 模拟训练过程
        for epoch in range(task.total_epochs):
            if task.status == TrainingStatus.STOPPED:
                logger.info(f"训练被停止: {task.task_id}")
                break
            
            task.current_epoch = epoch + 1
            
            # 模拟训练步骤
            await asyncio.sleep(2)  # 模拟训练时间
            
            # 模拟指标
            metrics = {
                'epoch': epoch + 1,
                'loss': 2.5 - (epoch * 0.2),
                'accuracy': 0.6 + (epoch * 0.03),
                'val_loss': 2.8 - (epoch * 0.15),
                'val_accuracy': 0.55 + (epoch * 0.025)
            }
            
            task.metrics_history.append(metrics)
            task.logs.append(f"Epoch {epoch+1}/{task.total_epochs}: loss={metrics['loss']:.4f}, acc={metrics['accuracy']:.4f}")
            
            # 更新最佳指标
            if metrics['val_accuracy'] > task.best_metric:
                task.best_metric = metrics['val_accuracy']
                # 保存检查点
                self._save_checkpoint(task, epoch)
            
            # 保存任务状态
            self._save_task(task)
            
            logger.info(f"任务 {task.task_id} - Epoch {epoch+1}: {metrics}")
    
    async def _train_bert(self, task: TrainingTask):
        """训练BERT模型"""
        logger.info(f"开始BERT训练: {task.task_id}")
        
        # 这里应该实现真实的BERT训练逻辑
        # 现在使用模拟训练
        for epoch in range(task.total_epochs):
            if task.status == TrainingStatus.STOPPED:
                break
            
            task.current_epoch = epoch + 1
            await asyncio.sleep(1)
            
            metrics = {
                'epoch': epoch + 1,
                'loss': 1.8 - (epoch * 0.15),
                'accuracy': 0.7 + (epoch * 0.02),
                'f1_score': 0.65 + (epoch * 0.025)
            }
            
            task.metrics_history.append(metrics)
            task.logs.append(f"BERT训练 - Epoch {epoch+1}: {metrics}")
            
            self._save_task(task)
    
    async def _train_llama(self, task: TrainingTask):
        """训练LLaMA模型"""
        logger.info(f"开始LLaMA训练: {task.task_id}")
        
        # 模拟LLaMA训练
        for epoch in range(task.total_epochs):
            if task.status == TrainingStatus.STOPPED:
                break
            
            task.current_epoch = epoch + 1
            await asyncio.sleep(1.5)
            
            metrics = {
                'epoch': epoch + 1,
                'loss': 2.0 - (epoch * 0.18),
                'perplexity': 15 - (epoch * 1.2),
                'bleu_score': 0.3 + (epoch * 0.04)
            }
            
            task.metrics_history.append(metrics)
            task.logs.append(f"LLaMA训练 - Epoch {epoch+1}: {metrics}")
            
            self._save_task(task)
    
    def stop_training(self, task_id: str) -> bool:
        """停止训练任务"""
        if task_id not in self.tasks:
            return False
        
        task = self.tasks[task_id]
        if task.status == TrainingStatus.RUNNING:
            task.status = TrainingStatus.STOPPED
            task.completed_at = datetime.now()
            self._save_task(task)
            logger.info(f"训练任务已停止: {task_id}")
            return True
        
        return False
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        if task_id not in self.tasks:
            # 尝试从文件加载
            task = self._load_task(task_id)
            if task:
                self.tasks[task_id] = task
            else:
                return None
        
        task = self.tasks[task_id]
        
        return {
            'task_id': task.task_id,
            'model_type': task.model_type,
            'dataset_id': task.dataset_id,
            'status': task.status.value,
            'progress': (task.current_epoch / task.total_epochs * 100) if task.total_epochs > 0 else 0,
            'current_epoch': task.current_epoch,
            'total_epochs': task.total_epochs,
            'best_metric': task.best_metric,
            'metrics': task.metrics_history[-1] if task.metrics_history else {},
            'logs': task.logs[-10:],  # 最近10条日志
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'error': task.error
        }
    
    async def evaluate_model(self, model_id: str, dataset_id: str, metrics: List[str]) -> Dict:
        """评估模型"""
        logger.info(f"评估模型 {model_id} 在数据集 {dataset_id}")
        
        # 模拟评估过程
        await asyncio.sleep(3)
        
        results = {}
        
        if 'accuracy' in metrics:
            results['accuracy'] = 0.87 + (hash(model_id) % 10) / 100
        
        if 'precision' in metrics:
            results['precision'] = 0.85 + (hash(model_id) % 8) / 100
        
        if 'recall' in metrics:
            results['recall'] = 0.83 + (hash(model_id) % 7) / 100
        
        if 'f1' in metrics:
            if 'precision' in results and 'recall' in results:
                p = results['precision']
                r = results['recall']
                results['f1'] = 2 * (p * r) / (p + r)
            else:
                results['f1'] = 0.84
        
        # 添加混淆矩阵
        results['confusion_matrix'] = [
            [850, 50, 20],   # 真实: safe
            [30, 780, 40],   # 真实: warning
            [10, 20, 890]    # 真实: danger
        ]
        
        return results
    
    def list_models(self) -> List[Dict]:
        """列出所有模型"""
        models = []
        
        # 扫描模型目录
        for model_path in self.models_dir.glob("*"):
            if model_path.is_dir():
                model_info = self._load_model_info(model_path)
                if model_info:
                    models.append(model_info)
        
        # 添加预训练模型
        models.extend([
            {
                'id': 'chatglm_base',
                'name': 'ChatGLM-6B Base',
                'type': 'chatglm',
                'status': 'available',
                'created_at': '2024-01-01',
                'metrics': {'accuracy': 0.85}
            },
            {
                'id': 'bert_finetuned_v1',
                'name': 'BERT Finetuned V1',
                'type': 'bert',
                'status': 'available',
                'created_at': '2024-01-15',
                'metrics': {'accuracy': 0.88, 'f1': 0.86}
            }
        ])
        
        return models
    
    def deploy_model(self, model_id: str) -> bool:
        """部署模型"""
        logger.info(f"部署模型: {model_id}")
        
        # 这里应该实现真实的部署逻辑
        # 比如：复制模型到生产目录，更新配置，重启服务等
        
        # 模拟部署
        deployment_path = self.models_dir / "production" / model_id
        deployment_path.mkdir(exist_ok=True, parents=True)
        
        # 创建部署配置
        deployment_config = {
            'model_id': model_id,
            'deployed_at': datetime.now().isoformat(),
            'status': 'active',
            'endpoint': f'/api/ai/{model_id}/predict'
        }
        
        with open(deployment_path / 'deployment.json', 'w') as f:
            json.dump(deployment_config, f, indent=2)
        
        logger.info(f"模型 {model_id} 已部署")
        return True
    
    def get_metrics(self) -> Dict:
        """获取训练服务指标"""
        total_tasks = len(self.tasks)
        running_tasks = sum(1 for t in self.tasks.values() if t.status == TrainingStatus.RUNNING)
        completed_tasks = sum(1 for t in self.tasks.values() if t.status == TrainingStatus.COMPLETED)
        failed_tasks = sum(1 for t in self.tasks.values() if t.status == TrainingStatus.FAILED)
        
        return {
            'total_tasks': total_tasks,
            'running_tasks': running_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'success_rate': completed_tasks / total_tasks if total_tasks > 0 else 0,
            'active_models': len(self.list_models()),
            'storage_used_gb': self._get_storage_usage()
        }
    
    def _save_task(self, task: TrainingTask):
        """保存任务到文件"""
        task_file = self.logs_dir / f"{task.task_id}.json"
        
        task_dict = {
            'task_id': task.task_id,
            'model_type': task.model_type,
            'dataset_id': task.dataset_id,
            'status': task.status.value,
            'config': task.config,
            'created_at': task.created_at.isoformat(),
            'started_at': task.started_at.isoformat() if task.started_at else None,
            'completed_at': task.completed_at.isoformat() if task.completed_at else None,
            'current_epoch': task.current_epoch,
            'total_epochs': task.total_epochs,
            'best_metric': task.best_metric,
            'metrics_history': task.metrics_history,
            'logs': task.logs,
            'error': task.error
        }
        
        with open(task_file, 'w') as f:
            json.dump(task_dict, f, indent=2)
    
    def _load_task(self, task_id: str) -> Optional[TrainingTask]:
        """从文件加载任务"""
        task_file = self.logs_dir / f"{task_id}.json"
        
        if not task_file.exists():
            return None
        
        try:
            with open(task_file, 'r') as f:
                task_dict = json.load(f)
            
            task = TrainingTask(
                task_id=task_dict['task_id'],
                model_type=task_dict['model_type'],
                dataset_id=task_dict['dataset_id'],
                status=TrainingStatus(task_dict['status']),
                config=task_dict['config'],
                created_at=datetime.fromisoformat(task_dict['created_at']),
                started_at=datetime.fromisoformat(task_dict['started_at']) if task_dict['started_at'] else None,
                completed_at=datetime.fromisoformat(task_dict['completed_at']) if task_dict['completed_at'] else None,
                current_epoch=task_dict['current_epoch'],
                total_epochs=task_dict['total_epochs'],
                best_metric=task_dict['best_metric'],
                metrics_history=task_dict['metrics_history'],
                logs=task_dict['logs'],
                error=task_dict['error']
            )
            
            return task
            
        except Exception as e:
            logger.error(f"加载任务失败 {task_id}: {e}")
            return None
    
    def _save_checkpoint(self, task: TrainingTask, epoch: int):
        """保存模型检查点"""
        checkpoint_path = self.checkpoints_dir / task.task_id / f"epoch_{epoch}.pt"
        checkpoint_path.parent.mkdir(exist_ok=True, parents=True)
        
        # 这里应该保存真实的模型权重
        # 现在只保存元信息
        checkpoint_info = {
            'task_id': task.task_id,
            'epoch': epoch,
            'metrics': task.metrics_history[-1] if task.metrics_history else {},
            'saved_at': datetime.now().isoformat()
        }
        
        with open(checkpoint_path.with_suffix('.json'), 'w') as f:
            json.dump(checkpoint_info, f, indent=2)
        
        logger.info(f"保存检查点: {checkpoint_path}")
    
    def _load_model_info(self, model_path: Path) -> Optional[Dict]:
        """加载模型信息"""
        info_file = model_path / 'model_info.json'
        
        if not info_file.exists():
            return None
        
        try:
            with open(info_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载模型信息失败 {model_path}: {e}")
            return None
    
    def _get_storage_usage(self) -> float:
        """获取存储使用量（GB）"""
        total_size = 0
        
        for path in [self.models_dir, self.checkpoints_dir, self.logs_dir]:
            if path.exists():
                for file in path.rglob('*'):
                    if file.is_file():
                        total_size += file.stat().st_size
        
        return total_size / (1024 ** 3)  # 转换为GB
