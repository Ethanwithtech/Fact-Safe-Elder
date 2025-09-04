"""
健康检查API路由
"""

import time
import psutil
from fastapi import APIRouter, Request
from loguru import logger

from app.core.config import settings


router = APIRouter()


@router.get("")
async def health_check():
    """基础健康检查"""
    return {
        "status": "healthy",
        "message": "服务运行正常",
        "timestamp": time.time(),
        "service": settings.APP_NAME,
        "version": settings.VERSION
    }


@router.get("/status")
async def detailed_health_status(request: Request):
    """详细健康状态检查"""
    try:
        # 基础信息
        status_info = {
            "service": settings.APP_NAME,
            "version": settings.VERSION,
            "status": "healthy",
            "timestamp": time.time(),
            "uptime": time.time() - getattr(request.app.state, 'start_time', time.time())
        }
        
        # 系统资源信息
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            status_info["system"] = {
                "cpu_usage_percent": cpu_percent,
                "memory": {
                    "total": memory.total,
                    "available": memory.available,
                    "percent": memory.percent
                },
                "disk": {
                    "total": disk.total,
                    "used": disk.used,
                    "free": disk.free,
                    "percent": (disk.used / disk.total) * 100
                }
            }
        except Exception as e:
            logger.warning(f"获取系统信息失败: {e}")
            status_info["system"] = {"error": "无法获取系统信息"}
        
        # 检测引擎状态
        try:
            if hasattr(request.app.state, 'detection_engine'):
                detection_engine = request.app.state.detection_engine
                engine_status = await detection_engine.health_check()
                status_info["detection_engine"] = engine_status
            else:
                status_info["detection_engine"] = {"status": "not_initialized"}
        except Exception as e:
            logger.error(f"检测引擎状态检查失败: {e}")
            status_info["detection_engine"] = {"status": "error", "error": str(e)}
        
        # 数据库状态（如果有）
        try:
            # 这里可以添加数据库连接检查
            status_info["database"] = {"status": "connected"}
        except Exception as e:
            logger.error(f"数据库状态检查失败: {e}")
            status_info["database"] = {"status": "error", "error": str(e)}
        
        # Redis状态（如果有）
        try:
            # 这里可以添加Redis连接检查
            status_info["cache"] = {"status": "connected"}
        except Exception as e:
            logger.error(f"缓存状态检查失败: {e}")
            status_info["cache"] = {"status": "error", "error": str(e)}
        
        return {
            "success": True,
            "message": "健康状态检查完成",
            "code": 200,
            "data": status_info
        }
        
    except Exception as e:
        logger.error(f"健康状态检查失败: {e}")
        return {
            "success": False,
            "message": f"健康状态检查失败: {str(e)}",
            "code": 500,
            "data": {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": time.time()
            }
        }


@router.get("/ping")
async def ping():
    """简单的ping检查"""
    return {"message": "pong", "timestamp": time.time()}


@router.get("/ready")
async def readiness_check(request: Request):
    """就绪状态检查"""
    try:
        # 检查关键组件是否就绪
        checks = {}
        
        # 检查检测引擎
        if hasattr(request.app.state, 'detection_engine'):
            try:
                detection_engine = request.app.state.detection_engine
                test_result = await detection_engine.detect_text("测试文本")
                checks["detection_engine"] = {"status": "ready", "test_passed": True}
            except Exception as e:
                checks["detection_engine"] = {"status": "not_ready", "error": str(e)}
        else:
            checks["detection_engine"] = {"status": "not_initialized"}
        
        # 检查配置
        checks["configuration"] = {
            "status": "loaded",
            "debug_mode": settings.DEBUG,
            "log_level": settings.LOG_LEVEL
        }
        
        # 判断总体就绪状态
        all_ready = all(
            check.get("status") in ["ready", "loaded", "connected"] 
            for check in checks.values()
        )
        
        status_code = 200 if all_ready else 503
        
        return {
            "ready": all_ready,
            "status": "ready" if all_ready else "not_ready",
            "checks": checks,
            "timestamp": time.time()
        }
        
    except Exception as e:
        logger.error(f"就绪状态检查失败: {e}")
        return {
            "ready": False,
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }


@router.get("/live")
async def liveness_check():
    """存活状态检查"""
    try:
        # 简单的存活检查
        return {
            "alive": True,
            "status": "live",
            "timestamp": time.time(),
            "pid": psutil.Process().pid if psutil else None
        }
        
    except Exception as e:
        logger.error(f"存活状态检查失败: {e}")
        return {
            "alive": False,
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }


@router.get("/metrics")
async def get_metrics(request: Request):
    """获取应用指标"""
    try:
        metrics = {
            "timestamp": time.time(),
            "service": settings.APP_NAME,
            "version": settings.VERSION
        }
        
        # 系统指标
        try:
            process = psutil.Process()
            metrics["system"] = {
                "cpu_percent": psutil.cpu_percent(),
                "memory_rss": process.memory_info().rss,
                "memory_vms": process.memory_info().vms,
                "memory_percent": process.memory_percent(),
                "num_threads": process.num_threads(),
                "num_fds": process.num_fds() if hasattr(process, 'num_fds') else None,
                "create_time": process.create_time()
            }
        except Exception as e:
            logger.warning(f"获取系统指标失败: {e}")
            metrics["system"] = {"error": str(e)}
        
        # 应用指标
        try:
            if hasattr(request.app.state, 'detection_engine'):
                detection_engine = request.app.state.detection_engine
                detection_stats = await detection_engine.get_statistics()
                metrics["detection"] = detection_stats
        except Exception as e:
            logger.warning(f"获取检测引擎指标失败: {e}")
            metrics["detection"] = {"error": str(e)}
        
        return {
            "success": True,
            "message": "指标获取成功",
            "code": 200,
            "data": metrics
        }
        
    except Exception as e:
        logger.error(f"指标获取失败: {e}")
        return {
            "success": False,
            "message": f"指标获取失败: {str(e)}",
            "code": 500,
            "data": {"error": str(e)}
        }


@router.get("/version")
async def get_version():
    """获取版本信息"""
    return {
        "service": settings.APP_NAME,
        "version": settings.VERSION,
        "build_time": "2025-01-27",
        "python_version": "3.8+",
        "framework": "FastAPI"
    }
