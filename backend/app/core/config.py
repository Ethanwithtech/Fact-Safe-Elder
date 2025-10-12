"""
应用配置文件
"""

import os
from typing import List, Optional
from pydantic import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """应用设置类"""
    
    # 基础配置
    APP_NAME: str = "老人短视频虚假信息检测系统"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=True, description="调试模式")
    
    # 服务器配置
    HOST: str = Field(default="0.0.0.0", description="服务器主机")
    PORT: int = Field(default=8000, description="服务器端口")
    
    # 跨域配置
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        description="允许的跨域来源"
    )
    ALLOWED_HOSTS: List[str] = Field(
        default=["localhost", "127.0.0.1", "*"],
        description="允许的主机"
    )
    
    # 数据库配置
    DATABASE_URL: str = Field(
        default="sqlite:///./elder_safety.db",
        description="数据库连接URL"
    )
    
    # Redis配置
    REDIS_URL: str = Field(
        default="redis://localhost:6379/0",
        description="Redis连接URL"
    )
    REDIS_CACHE_TTL: int = Field(default=300, description="Redis缓存TTL（秒）")
    
    # AI模型配置
    MODEL_PATH: str = Field(
        default="./models/",
        description="模型文件路径"
    )
    USE_GPU: bool = Field(default=False, description="是否使用GPU")
    MODEL_CACHE_SIZE: int = Field(default=10, description="模型缓存大小")
    
    # 检测配置
    MAX_TEXT_LENGTH: int = Field(default=5000, description="最大文本长度")
    MIN_CONFIDENCE_THRESHOLD: float = Field(default=0.6, description="最小置信度阈值")
    BATCH_SIZE: int = Field(default=8, description="批处理大小")
    
    # 语音处理配置
    WHISPER_MODEL: str = Field(default="base", description="Whisper模型版本")
    AUDIO_MAX_DURATION: int = Field(default=300, description="音频最大时长（秒）")
    AUDIO_SAMPLE_RATE: int = Field(default=16000, description="音频采样率")
    
    # 安全配置
    SECRET_KEY: str = Field(
        default="your-secret-key-change-in-production",
        description="密钥"
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=30,
        description="访问令牌过期时间（分钟）"
    )
    
    # 限流配置
    RATE_LIMIT_REQUESTS: int = Field(default=100, description="限流请求数")
    RATE_LIMIT_WINDOW: int = Field(default=60, description="限流时间窗口（秒）")
    
    # 日志配置
    LOG_LEVEL: str = Field(default="INFO", description="日志级别")
    LOG_FILE: str = Field(default="logs/app.log", description="日志文件路径")
    LOG_ROTATION: str = Field(default="10 MB", description="日志轮转大小")
    LOG_RETENTION: str = Field(default="30 days", description="日志保留时间")
    
    # 外部API配置
    BAIDU_APP_ID: Optional[str] = Field(default=None, description="百度语音API ID")
    BAIDU_API_KEY: Optional[str] = Field(default=None, description="百度语音API Key")
    BAIDU_SECRET_KEY: Optional[str] = Field(default=None, description="百度语音Secret Key")
    
    # 通知配置
    EMAIL_ENABLED: bool = Field(default=False, description="是否启用邮件通知")
    SMTP_HOST: Optional[str] = Field(default=None, description="SMTP主机")
    SMTP_PORT: int = Field(default=587, description="SMTP端口")
    SMTP_USERNAME: Optional[str] = Field(default=None, description="SMTP用户名")
    SMTP_PASSWORD: Optional[str] = Field(default=None, description="SMTP密码")
    
    # 监控配置
    ENABLE_METRICS: bool = Field(default=True, description="是否启用指标收集")
    METRICS_PORT: int = Field(default=8001, description="指标端口")
    
    # 数据存储配置
    UPLOAD_DIR: str = Field(default="./uploads", description="文件上传目录")
    MAX_UPLOAD_SIZE: int = Field(default=50*1024*1024, description="最大上传文件大小（字节）")
    
    # 缓存配置
    CACHE_ENABLED: bool = Field(default=True, description="是否启用缓存")
    CACHE_DEFAULT_TTL: int = Field(default=3600, description="缓存默认TTL（秒）")
    
    # 开发配置
    RELOAD_ON_CHANGE: bool = Field(default=True, description="文件变更时重载")
    API_DOCS_ENABLED: bool = Field(default=True, description="是否启用API文档")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
    
    def get_database_url(self) -> str:
        """获取数据库URL"""
        return self.DATABASE_URL
    
    def get_redis_url(self) -> str:
        """获取Redis URL"""
        return self.REDIS_URL
    
    def is_production(self) -> bool:
        """判断是否为生产环境"""
        return not self.DEBUG
    
    def get_allowed_origins(self) -> List[str]:
        """获取允许的跨域来源"""
        if self.DEBUG:
            # 开发环境允许所有来源
            return ["*"]
        return self.ALLOWED_ORIGINS
    
    def get_log_config(self) -> dict:
        """获取日志配置"""
        return {
            "level": self.LOG_LEVEL,
            "file": self.LOG_FILE,
            "rotation": self.LOG_ROTATION,
            "retention": self.LOG_RETENTION
        }


# 创建全局设置实例
settings = Settings()


# 环境变量示例 (.env 文件)
ENV_EXAMPLE = """
# 基础配置
DEBUG=true
HOST=0.0.0.0
PORT=8000

# 数据库
DATABASE_URL=postgresql://user:password@localhost:5432/elder_safety
REDIS_URL=redis://localhost:6379/0

# AI模型
USE_GPU=false
WHISPER_MODEL=base

# 安全配置
SECRET_KEY=your-very-secure-secret-key-here

# 百度API（可选）
BAIDU_APP_ID=your-baidu-app-id
BAIDU_API_KEY=your-baidu-api-key
BAIDU_SECRET_KEY=your-baidu-secret-key

# 邮件配置（可选）
EMAIL_ENABLED=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-email-password

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
"""


if __name__ == "__main__":
    # 测试配置
    print("当前配置:")
    print(f"应用名称: {settings.APP_NAME}")
    print(f"版本: {settings.VERSION}")
    print(f"调试模式: {settings.DEBUG}")
    print(f"服务器: {settings.HOST}:{settings.PORT}")
    print(f"数据库: {settings.DATABASE_URL}")
    print(f"Redis: {settings.REDIS_URL}")
    print(f"允许的来源: {settings.ALLOWED_ORIGINS}")
    
    # 生成示例环境文件
    with open(".env.example", "w", encoding="utf-8") as f:
        f.write(ENV_EXAMPLE)
