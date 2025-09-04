"""
老人短视频虚假信息检测系统 - 后端主程序
"""

import os
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.api.detection import router as detection_router
from app.api.health import router as health_router
from app.api.ai_training import router as ai_router
from app.core.config import settings
from app.core.logging_config import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动时初始化
    logger.info("🚀 老人短视频安全检测系统启动中...")
    
    try:
        # 初始化检测引擎
        from app.services.detection import DetectionEngine
        detection_engine = DetectionEngine()
        await detection_engine.initialize()
        
        # 将检测引擎存储到app状态
        app.state.detection_engine = detection_engine
        
        logger.info("✅ 检测引擎初始化完成")
        logger.info(f"🌟 服务器已启动，监听端口: {settings.PORT}")
        
    except Exception as e:
        logger.error(f"❌ 系统初始化失败: {e}")
        raise
    
    yield
    
    # 关闭时清理
    logger.info("🔄 系统正在关闭...")
    
    try:
        if hasattr(app.state, 'detection_engine'):
            await app.state.detection_engine.cleanup()
        logger.info("✅ 系统关闭完成")
    except Exception as e:
        logger.error(f"❌ 系统关闭时发生错误: {e}")


# 创建FastAPI应用
app = FastAPI(
    title="老人短视频虚假信息检测系统",
    description="基于AI的实时短视频内容安全检测服务",
    version="1.0.0",
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan
)

# 设置日志
setup_logging()

# 中间件配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.ALLOWED_HOSTS
)

# 路由注册
app.include_router(health_router, prefix="/api/health", tags=["健康检查"])
app.include_router(detection_router, prefix="/api", tags=["检测服务"])
app.include_router(ai_router, tags=["AI模型"])


# 全局异常处理器
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """全局异常处理"""
    logger.error(f"全局异常: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误",
            "code": 500,
            "data": None
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP异常处理"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "message": exc.detail,
            "code": exc.status_code,
            "data": None
        }
    )


# 根路由
@app.get("/")
async def root():
    """根路径响应"""
    return {
        "message": "老人短视频虚假信息检测系统 API 服务",
        "version": "1.0.0",
        "status": "运行中",
        "docs": "/docs",
        "health": "/api/health"
    }


# API状态检查
@app.get("/api")
async def api_info():
    """API信息"""
    return {
        "success": True,
        "message": "API服务正常运行",
        "version": "1.0.0",
        "endpoints": {
            "检测服务": "/api/detect",
            "健康检查": "/api/health",
            "服务状态": "/api/health/status"
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # 开发环境启动配置
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info",
        access_log=True
    )
