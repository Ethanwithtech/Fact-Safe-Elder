"""
检测服务API路由
"""

import time
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from loguru import logger

from app.core.logging_config import log_detection_result, log_execution_time
from app.models.detection import DetectionRequest, DetectionResponse, BatchDetectionRequest
from app.services.detection import DetectionEngine


router = APIRouter()


# 依赖注入：获取检测引擎
async def get_detection_engine(request: Request) -> DetectionEngine:
    """获取检测引擎实例"""
    return request.app.state.detection_engine


@router.post("/detect", response_model=DetectionResponse)
@log_execution_time("detection_api")
async def detect_content(
    request: DetectionRequest,
    detection_engine: DetectionEngine = Depends(get_detection_engine),
    background_tasks: BackgroundTasks = None
) -> DetectionResponse:
    """
    检测内容是否为虚假信息
    
    Args:
        request: 检测请求数据
        detection_engine: 检测引擎实例
        background_tasks: 后台任务
    
    Returns:
        DetectionResponse: 检测结果
    """
    try:
        start_time = time.time()
        
        # 参数验证
        if not request.text or not request.text.strip():
            raise HTTPException(
                status_code=400,
                detail="文本内容不能为空"
            )
        
        # 文本长度检查
        if len(request.text) > 5000:
            raise HTTPException(
                status_code=400,
                detail="文本内容过长，最大支持5000字符"
            )
        
        # 执行检测
        result = await detection_engine.detect_text(
            text=request.text,
            user_id=getattr(request, 'user_id', None),
            platform=getattr(request, 'platform', 'unknown')
        )
        
        # 处理时间
        processing_time = time.time() - start_time
        
        # 构建响应
        response = DetectionResponse(
            success=True,
            message="检测完成",
            code=200,
            data=result,
            processing_time=processing_time
        )
        
        # 记录检测日志
        logger.info(
            f"DETECTION | 内容检测完成 | "
            f"风险等级: {result.level} | "
            f"风险评分: {result.score:.3f} | "
            f"处理时间: {processing_time:.3f}秒"
        )
        
        # 添加后台任务（统计、缓存等）
        if background_tasks:
            background_tasks.add_task(
                _post_detection_tasks,
                result,
                request.text,
                processing_time
            )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检测服务发生错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"检测服务暂时不可用: {str(e)}"
        )


@router.post("/detect/batch", response_model=List[DetectionResponse])
@log_execution_time("batch_detection_api")
async def detect_batch_content(
    request: BatchDetectionRequest,
    detection_engine: DetectionEngine = Depends(get_detection_engine)
) -> List[DetectionResponse]:
    """
    批量检测内容
    
    Args:
        request: 批量检测请求
        detection_engine: 检测引擎实例
    
    Returns:
        List[DetectionResponse]: 检测结果列表
    """
    try:
        start_time = time.time()
        
        # 参数验证
        if not request.texts:
            raise HTTPException(
                status_code=400,
                detail="文本列表不能为空"
            )
        
        if len(request.texts) > 10:
            raise HTTPException(
                status_code=400,
                detail="批量检测最多支持10个文本"
            )
        
        # 批量检测
        results = await detection_engine.detect_batch(
            texts=request.texts,
            user_id=getattr(request, 'user_id', None)
        )
        
        processing_time = time.time() - start_time
        
        # 构建响应列表
        responses = []
        for i, result in enumerate(results):
            response = DetectionResponse(
                success=True,
                message=f"批量检测完成 ({i+1}/{len(results)})",
                code=200,
                data=result,
                processing_time=processing_time / len(results)
            )
            responses.append(response)
        
        logger.info(
            f"DETECTION | 批量检测完成 | "
            f"数量: {len(results)} | "
            f"总耗时: {processing_time:.3f}秒"
        )
        
        return responses
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"批量检测服务发生错误: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"批量检测服务暂时不可用: {str(e)}"
        )


@router.get("/detect/stats")
async def get_detection_stats(
    detection_engine: DetectionEngine = Depends(get_detection_engine)
) -> dict:
    """
    获取检测统计信息
    
    Returns:
        dict: 统计信息
    """
    try:
        stats = await detection_engine.get_statistics()
        
        return {
            "success": True,
            "message": "统计信息获取成功",
            "code": 200,
            "data": stats
        }
        
    except Exception as e:
        logger.error(f"获取统计信息失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="统计信息获取失败"
        )


@router.post("/detect/feedback")
async def submit_feedback(
    feedback_request: dict,
    detection_engine: DetectionEngine = Depends(get_detection_engine)
):
    """
    提交检测结果反馈
    
    Args:
        detection_id: 检测ID
        feedback: 反馈内容
        rating: 评分
        detection_engine: 检测引擎实例
    
    Returns:
        dict: 反馈提交结果
    """
    try:
        detection_id = feedback_request.get("detection_id", "")
        feedback = feedback_request.get("feedback", "")
        rating = feedback_request.get("rating", 3)
        
        # 记录反馈
        await detection_engine.record_feedback(
            detection_id=detection_id,
            feedback=feedback,
            rating=rating
        )
        
        logger.info(f"收到用户反馈 | ID: {detection_id} | 评分: {rating}")
        
        return {
            "success": True,
            "message": "反馈提交成功，谢谢您的意见",
            "code": 200
        }
        
    except Exception as e:
        logger.error(f"反馈提交失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="反馈提交失败"
        )


@router.get("/detect/history")
async def get_detection_history(
    user_id: Optional[str] = None,
    limit: int = Query(default=20, le=100, description="返回数量限制"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    detection_engine: DetectionEngine = Depends(get_detection_engine)
):
    """
    获取检测历史记录
    
    Args:
        user_id: 用户ID（可选）
        limit: 返回数量限制
        offset: 偏移量
        detection_engine: 检测引擎实例
    
    Returns:
        dict: 历史记录
    """
    try:
        history = await detection_engine.get_detection_history(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "message": "历史记录获取成功",
            "code": 200,
            "data": history
        }
        
    except Exception as e:
        logger.error(f"获取历史记录失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="历史记录获取失败"
        )


@router.delete("/detect/history/{detection_id}")
async def delete_detection_record(
    detection_id: str,
    detection_engine: DetectionEngine = Depends(get_detection_engine)
):
    """
    删除检测记录
    
    Args:
        detection_id: 检测记录ID
        detection_engine: 检测引擎实例
    
    Returns:
        dict: 删除结果
    """
    try:
        success = await detection_engine.delete_detection_record(detection_id)
        
        if success:
            return {
                "success": True,
                "message": "记录删除成功",
                "code": 200
            }
        else:
            raise HTTPException(
                status_code=404,
                detail="记录不存在"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除记录失败: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="删除记录失败"
        )


# 后台任务函数
async def _post_detection_tasks(result, text: str, processing_time: float):
    """检测后的后台任务"""
    try:
        # 更新统计信息
        # 这里可以添加更多后台处理逻辑
        logger.debug(f"执行检测后台任务 | 风险等级: {result.level}")
        
    except Exception as e:
        logger.error(f"检测后台任务失败: {str(e)}")


# 健康检查端点
@router.get("/detect/health")
async def detection_health_check(
    detection_engine: DetectionEngine = Depends(get_detection_engine)
):
    """检测服务健康检查"""
    try:
        # 执行简单的检测测试
        test_text = "这是一个测试文本"
        result = await detection_engine.detect_text(test_text)
        
        return {
            "success": True,
            "message": "检测服务运行正常",
            "code": 200,
            "data": {
                "service": "detection",
                "status": "healthy",
                "test_result": result.level,
                "timestamp": time.time()
            }
        }
        
    except Exception as e:
        logger.error(f"检测服务健康检查失败: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "message": "检测服务不可用",
                "code": 503,
                "error": str(e)
            }
        )
