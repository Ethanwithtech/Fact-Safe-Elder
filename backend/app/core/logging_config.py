"""
日志配置模块
"""

import os
import sys
from pathlib import Path
from loguru import logger
from .config import settings


def setup_logging():
    """设置应用日志配置"""
    
    # 移除默认的logger配置
    logger.remove()
    
    # 确保日志目录存在
    log_file_path = Path(settings.LOG_FILE)
    log_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 控制台日志配置
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    # 文件日志配置
    file_format = (
        "{time:YYYY-MM-DD HH:mm:ss.SSS} | "
        "{level: <8} | "
        "{name}:{function}:{line} | "
        "{message}"
    )
    
    # 添加控制台日志处理器
    logger.add(
        sys.stdout,
        format=console_format,
        level=settings.LOG_LEVEL,
        colorize=True,
        backtrace=True,
        diagnose=True,
        enqueue=True  # 多进程安全
    )
    
    # 添加文件日志处理器
    logger.add(
        settings.LOG_FILE,
        format=file_format,
        level=settings.LOG_LEVEL,
        rotation=settings.LOG_ROTATION,  # 文件大小轮转
        retention=settings.LOG_RETENTION,  # 保留时间
        compression="zip",  # 压缩旧日志
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=True  # 多进程安全
    )
    
    # 错误日志单独文件
    error_log_path = log_file_path.parent / "error.log"
    logger.add(
        error_log_path,
        format=file_format,
        level="ERROR",
        rotation="100 MB",
        retention="60 days",
        compression="zip",
        encoding="utf-8",
        backtrace=True,
        diagnose=True,
        enqueue=True
    )
    
    # 访问日志（可选）
    if settings.DEBUG:
        access_log_path = log_file_path.parent / "access.log"
        logger.add(
            access_log_path,
            format="{time:YYYY-MM-DD HH:mm:ss} | ACCESS | {message}",
            level="INFO",
            rotation="10 MB",
            retention="7 days",
            encoding="utf-8",
            filter=lambda record: "ACCESS" in record["message"],
            enqueue=True
        )
    
    # 性能日志
    perf_log_path = log_file_path.parent / "performance.log"
    logger.add(
        perf_log_path,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | PERF | {message}",
        level="INFO",
        rotation="50 MB",
        retention="30 days",
        encoding="utf-8",
        filter=lambda record: "PERF" in record["message"],
        enqueue=True
    )
    
    # 检测日志
    detection_log_path = log_file_path.parent / "detection.log"
    logger.add(
        detection_log_path,
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | DETECTION | {message}",
        level="INFO",
        rotation="20 MB",
        retention="90 days",  # 检测记录保留更久
        encoding="utf-8",
        filter=lambda record: "DETECTION" in record["message"],
        enqueue=True
    )
    
    logger.info("✅ 日志系统初始化完成")
    logger.info(f"📝 主日志文件: {settings.LOG_FILE}")
    logger.info(f"📊 日志级别: {settings.LOG_LEVEL}")


def get_logger(name: str = None):
    """获取指定名称的logger实例"""
    if name:
        return logger.bind(name=name)
    return logger


class LoggerMixin:
    """日志混入类，为其他类提供日志功能"""
    
    @property
    def logger(self):
        """获取当前类的logger"""
        return logger.bind(name=self.__class__.__name__)


# 日志装饰器
def log_execution_time(func_name: str = None):
    """记录函数执行时间的装饰器"""
    import time
    from functools import wraps
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            name = func_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"PERF | {name} 执行完成，耗时: {execution_time:.3f}秒")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"PERF | {name} 执行失败，耗时: {execution_time:.3f}秒，错误: {e}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            name = func_name or f"{func.__module__}.{func.__name__}"
            
            try:
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time
                logger.info(f"PERF | {name} 执行完成，耗时: {execution_time:.3f}秒")
                return result
            except Exception as e:
                execution_time = time.time() - start_time
                logger.error(f"PERF | {name} 执行失败，耗时: {execution_time:.3f}秒，错误: {e}")
                raise
        
        # 判断是否是异步函数
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def log_detection_result(user_id: str = None, content_type: str = "text"):
    """记录检测结果的装饰器"""
    from functools import wraps
    import json
    
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                result = await func(*args, **kwargs)
                
                # 记录检测日志
                log_data = {
                    "user_id": user_id,
                    "content_type": content_type,
                    "function": func.__name__,
                    "risk_level": getattr(result, 'level', 'unknown'),
                    "score": getattr(result, 'score', 0),
                    "timestamp": time.time()
                }
                
                logger.info(f"DETECTION | 检测完成: {json.dumps(log_data, ensure_ascii=False)}")
                return result
                
            except Exception as e:
                logger.error(f"DETECTION | 检测失败: {func.__name__}, 错误: {e}")
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                result = func(*args, **kwargs)
                
                # 记录检测日志
                log_data = {
                    "user_id": user_id,
                    "content_type": content_type,
                    "function": func.__name__,
                    "risk_level": getattr(result, 'level', 'unknown'),
                    "score": getattr(result, 'score', 0),
                    "timestamp": time.time()
                }
                
                logger.info(f"DETECTION | 检测完成: {json.dumps(log_data, ensure_ascii=False)}")
                return result
                
            except Exception as e:
                logger.error(f"DETECTION | 检测失败: {func.__name__}, 错误: {e}")
                raise
        
        # 判断是否是异步函数
        if hasattr(func, '__code__') and func.__code__.co_flags & 0x80:
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# API访问日志记录函数
def log_api_access(request, response, duration: float):
    """记录API访问日志"""
    client_ip = request.client.host
    method = request.method
    url = str(request.url)
    status_code = response.status_code
    user_agent = request.headers.get("user-agent", "")
    
    logger.info(
        f"ACCESS | {client_ip} | {method} {url} | {status_code} | "
        f"{duration:.3f}s | {user_agent}"
    )


if __name__ == "__main__":
    # 测试日志配置
    setup_logging()
    
    # 测试各种日志级别
    logger.debug("这是调试信息")
    logger.info("这是普通信息")
    logger.warning("这是警告信息")
    logger.error("这是错误信息")
    logger.critical("这是严重错误信息")
    
    # 测试性能日志
    logger.info("PERF | 测试性能日志")
    
    # 测试检测日志
    logger.info("DETECTION | 测试检测日志")
    
    print("日志测试完成，请检查日志文件")
