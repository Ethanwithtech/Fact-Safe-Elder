"""
AI模型训练和管理API
"""

import os
import json
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from fastapi import APIRouter, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from loguru import logger

from app.services.ai_models import (
    detect_with_chatglm,
    detect_with_bert,
    detect_with_llama,
    detect_with_ensemble,
    get_models_status
)
from app.services.training import TrainingService
from app.services.dataset_manager import DatasetManager


router = APIRouter(prefix="/api/ai", tags=["AI模型"])


# 数据模型定义
class TrainingRequest(BaseModel):
    """训练请求模型"""
    model_type: str = Field(..., description="模型类型: chatglm/bert/llama")
    dataset_id: str = Field(..., description="数据集ID")
    epochs: int = Field(default=10, ge=1, le=100, description="训练轮数")
    batch_size: int = Field(default=8, ge=1, le=64, description="批次大小")
    learning_rate: float = Field(default=5e-5, ge=1e-6, le=1e-3, description="学习率")
    use_lora: bool = Field(default=True, description="是否使用LoRA微调")
    lora_rank: int = Field(default=8, ge=1, le=64, description="LoRA秩")
    validation_split: float = Field(default=0.2, ge=0.1, le=0.5, description="验证集比例")
    
    class Config:
        schema_extra = {
            "example": {
                "model_type": "chatglm",
                "dataset_id": "mcfend_v1",
                "epochs": 10,
                "batch_size": 8,
                "learning_rate": 5e-5,
                "use_lora": True,
                "lora_rank": 8,
                "validation_split": 0.2
            }
        }


class DatasetUploadRequest(BaseModel):
    """数据集上传请求"""
    name: str = Field(..., description="数据集名称")
    description: str = Field(..., description="数据集描述")
    type: str = Field(..., description="数据集类型: mcfend/weibo/custom")
    format: str = Field(default="json", description="数据格式: json/csv")
    
    class Config:
        schema_extra = {
            "example": {
                "name": "custom_fake_news_v1",
                "description": "自定义虚假新闻数据集",
                "type": "custom",
                "format": "json"
            }
        }


class ModelEvaluationRequest(BaseModel):
    """模型评估请求"""
    model_id: str = Field(..., description="模型ID")
    dataset_id: str = Field(..., description="评估数据集ID")
    metrics: List[str] = Field(
        default=["accuracy", "precision", "recall", "f1"],
        description="评估指标"
    )


# 初始化服务
training_service = TrainingService()
dataset_manager = DatasetManager()


@router.post("/train", response_model=Dict)
async def start_training(
    request: TrainingRequest,
    background_tasks: BackgroundTasks
) -> Dict:
    """
    启动模型训练任务
    
    Args:
        request: 训练配置
        background_tasks: 后台任务
    
    Returns:
        训练任务信息
    """
    try:
        # 验证数据集是否存在
        dataset = dataset_manager.get_dataset(request.dataset_id)
        if not dataset:
            raise HTTPException(
                status_code=404,
                detail=f"数据集 {request.dataset_id} 不存在"
            )
        
        # 创建训练任务
        task_id = training_service.create_training_task(
            model_type=request.model_type,
            dataset_id=request.dataset_id,
            config=request.dict()
        )
        
        # 添加到后台任务
        background_tasks.add_task(
            training_service.run_training,
            task_id,
            request.dict()
        )
        
        logger.info(f"训练任务已创建: {task_id}")
        
        return {
            "success": True,
            "message": "训练任务已启动",
            "task_id": task_id,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"启动训练失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"启动训练失败: {str(e)}"
        )


@router.get("/train/status/{task_id}")
async def get_training_status(task_id: str) -> Dict:
    """
    获取训练任务状态
    
    Args:
        task_id: 任务ID
    
    Returns:
        训练状态信息
    """
    try:
        status = training_service.get_task_status(task_id)
        
        if not status:
            raise HTTPException(
                status_code=404,
                detail=f"训练任务 {task_id} 不存在"
            )
        
        return {
            "success": True,
            "task_id": task_id,
            "status": status.get("status", "unknown"),
            "progress": status.get("progress", 0),
            "current_epoch": status.get("current_epoch", 0),
            "total_epochs": status.get("total_epochs", 0),
            "metrics": status.get("metrics", {}),
            "logs": status.get("logs", []),
            "started_at": status.get("started_at"),
            "updated_at": status.get("updated_at")
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取训练状态失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取训练状态失败: {str(e)}"
        )


@router.post("/train/stop/{task_id}")
async def stop_training(task_id: str) -> Dict:
    """
    停止训练任务
    
    Args:
        task_id: 任务ID
    
    Returns:
        操作结果
    """
    try:
        success = training_service.stop_training(task_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"训练任务 {task_id} 不存在或已完成"
            )
        
        return {
            "success": True,
            "message": "训练任务已停止",
            "task_id": task_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"停止训练失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"停止训练失败: {str(e)}"
        )


@router.post("/dataset/upload")
async def upload_dataset(
    name: str = Form(...),
    description: str = Form(...),
    type: str = Form(...),
    format: str = Form("json"),
    file: UploadFile = File(...)
) -> Dict:
    """
    上传数据集
    
    Args:
        name: 数据集名称
        description: 数据集描述
        type: 数据集类型
        format: 数据格式
        file: 数据文件
    
    Returns:
        上传结果
    """
    try:
        # 验证文件格式
        if format not in ["json", "csv", "jsonl"]:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的文件格式: {format}"
            )
        
        # 保存文件
        content = await file.read()
        dataset_id = dataset_manager.save_dataset(
            name=name,
            description=description,
            type=type,
            format=format,
            content=content,
            filename=file.filename
        )
        
        # 解析和验证数据
        stats = dataset_manager.validate_dataset(dataset_id)
        
        logger.info(f"数据集已上传: {dataset_id}, 样本数: {stats['total_samples']}")
        
        return {
            "success": True,
            "message": "数据集上传成功",
            "dataset_id": dataset_id,
            "stats": stats
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"数据集上传失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"数据集上传失败: {str(e)}"
        )


@router.get("/dataset/list")
async def list_datasets() -> Dict:
    """
    获取数据集列表
    
    Returns:
        数据集列表
    """
    try:
        datasets = dataset_manager.list_datasets()
        
        return {
            "success": True,
            "datasets": datasets,
            "total": len(datasets)
        }
        
    except Exception as e:
        logger.error(f"获取数据集列表失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取数据集列表失败: {str(e)}"
        )


@router.get("/dataset/{dataset_id}")
async def get_dataset_info(dataset_id: str) -> Dict:
    """
    获取数据集详情
    
    Args:
        dataset_id: 数据集ID
    
    Returns:
        数据集详细信息
    """
    try:
        dataset = dataset_manager.get_dataset(dataset_id)
        
        if not dataset:
            raise HTTPException(
                status_code=404,
                detail=f"数据集 {dataset_id} 不存在"
            )
        
        return {
            "success": True,
            "dataset": dataset
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取数据集详情失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取数据集详情失败: {str(e)}"
        )


@router.post("/evaluate")
async def evaluate_model(request: ModelEvaluationRequest) -> Dict:
    """
    评估模型性能
    
    Args:
        request: 评估请求
    
    Returns:
        评估结果
    """
    try:
        # 执行评估
        results = await training_service.evaluate_model(
            model_id=request.model_id,
            dataset_id=request.dataset_id,
            metrics=request.metrics
        )
        
        return {
            "success": True,
            "model_id": request.model_id,
            "dataset_id": request.dataset_id,
            "results": results,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"模型评估失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"模型评估失败: {str(e)}"
        )


@router.get("/models/list")
async def list_models() -> Dict:
    """
    获取所有可用模型列表
    
    Returns:
        模型列表
    """
    try:
        models = training_service.list_models()
        
        return {
            "success": True,
            "models": models,
            "total": len(models)
        }
        
    except Exception as e:
        logger.error(f"获取模型列表失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取模型列表失败: {str(e)}"
        )


@router.post("/models/deploy/{model_id}")
async def deploy_model(model_id: str) -> Dict:
    """
    部署模型到生产环境
    
    Args:
        model_id: 模型ID
    
    Returns:
        部署结果
    """
    try:
        success = training_service.deploy_model(model_id)
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"模型 {model_id} 不存在或无法部署"
            )
        
        return {
            "success": True,
            "message": "模型已部署到生产环境",
            "model_id": model_id,
            "deployed_at": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"模型部署失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"模型部署失败: {str(e)}"
        )


# AI检测端点
@router.post("/chatglm/detect")
async def detect_chatglm(
    text: str = Form(...),
    text_features: Optional[Dict] = None,
    behavior_features: Optional[Dict] = None,
    metadata: Optional[Dict] = None
) -> Dict:
    """使用ChatGLM进行检测"""
    try:
        result = await detect_with_chatglm(text, {
            'text_features': text_features,
            'behavior_features': behavior_features,
            'metadata': metadata
        })
        
        return result
        
    except Exception as e:
        logger.error(f"ChatGLM检测失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"ChatGLM检测失败: {str(e)}"
        )


@router.post("/bert/detect")
async def detect_bert(
    text: str = Form(...),
    text_features: Optional[Dict] = None,
    behavior_features: Optional[Dict] = None,
    metadata: Optional[Dict] = None
) -> Dict:
    """使用BERT进行检测"""
    try:
        result = await detect_with_bert(text, {
            'text_features': text_features,
            'behavior_features': behavior_features,
            'metadata': metadata
        })
        
        return result
        
    except Exception as e:
        logger.error(f"BERT检测失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"BERT检测失败: {str(e)}"
        )


@router.post("/llama/detect")
async def detect_llama(
    text: str = Form(...),
    text_features: Optional[Dict] = None,
    behavior_features: Optional[Dict] = None,
    metadata: Optional[Dict] = None
) -> Dict:
    """使用LLaMA进行检测"""
    try:
        result = await detect_with_llama(text, {
            'text_features': text_features,
            'behavior_features': behavior_features,
            'metadata': metadata
        })
        
        return result
        
    except Exception as e:
        logger.error(f"LLaMA检测失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"LLaMA检测失败: {str(e)}"
        )


@router.post("/ensemble/detect")
async def detect_ensemble(
    text: str = Form(...),
    text_features: Optional[Dict] = None,
    behavior_features: Optional[Dict] = None,
    metadata: Optional[Dict] = None
) -> Dict:
    """使用集成方法进行检测"""
    try:
        result = await detect_with_ensemble(text, {
            'text_features': text_features,
            'behavior_features': behavior_features,
            'metadata': metadata
        })
        
        return result
        
    except Exception as e:
        logger.error(f"集成检测失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"集成检测失败: {str(e)}"
        )


@router.get("/status")
async def get_ai_status() -> Dict:
    """
    获取AI服务状态
    
    Returns:
        AI服务状态信息
    """
    try:
        models_status = get_models_status()
        
        return {
            "success": True,
            "status": "operational",
            "models": models_status,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取AI状态失败: {str(e)}")
        return {
            "success": False,
            "status": "error",
            "message": str(e),
            "timestamp": datetime.now().isoformat()
        }


@router.get("/metrics")
async def get_ai_metrics() -> Dict:
    """
    获取AI服务指标
    
    Returns:
        AI服务性能指标
    """
    try:
        metrics = training_service.get_metrics()
        
        return {
            "success": True,
            "metrics": metrics,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"获取AI指标失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"获取AI指标失败: {str(e)}"
        )
