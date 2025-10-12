"""
老人短视频虚假信息检测系统 - 简化版后端
暂时跳过AI模型依赖，优先让基础服务运行起来
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

# 创建FastAPI应用
app = FastAPI(
    title="老人短视频虚假信息检测系统 (简化版)",
    description="基础API服务，用于测试和开发",
    version="1.0.0-simple"
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# 基础路由
@app.get("/")
async def root():
    """根路径响应"""
    return {
        "message": "老人短视频虚假信息检测系统 API 服务 (简化版)",
        "version": "1.0.0-simple",
        "status": "运行中",
        "endpoints": {
            "健康检查": "/health",
            "检测服务": "/detect",
            "API信息": "/api"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "message": "服务运行正常",
        "service": "简化版检测系统"
    }

@app.get("/api")
async def api_info():
    """API信息"""
    return {
        "success": True,
        "message": "API服务正常运行",
        "version": "1.0.0-simple",
        "note": "这是简化版本，用于测试基础功能"
    }

@app.post("/detect")
async def detect_simple(text_data: dict):
    """简化版检测服务"""
    text = text_data.get("text", "")
    
    if not text:
        return {
            "success": False,
            "message": "文本内容不能为空"
        }
    
    # 强化的关键词检测
    danger_keywords = ["保证收益", "月入万元", "包治百病", "祖传秘方", "无风险投资", 
                      "月入", "万元", "包治", "秘方", "保证", "无风险", "理财秘诀"]
    warning_keywords = ["投资", "理财", "保健品", "偏方", "微信", "联系", "收益", "赚钱"]
    
    risk_level = "safe"
    risk_score = 0.1
    reasons = []
    suggestions = []
    
    # 检测危险关键词
    for keyword in danger_keywords:
        if keyword in text:
            risk_level = "danger"
            risk_score = 0.9
            reasons.append(f"发现高危关键词: {keyword}")
            suggestions.append("建议立即停止观看，谨防诈骗")
            break
    
    # 检测警告关键词
    if risk_level == "safe":
        for keyword in warning_keywords:
            if keyword in text:
                risk_level = "warning"
                risk_score = 0.6
                reasons.append(f"发现可疑关键词: {keyword}")
                suggestions.append("请谨慎对待此内容")
                break
    
    if not reasons:
        reasons.append("未发现明显风险")
        suggestions.append("内容相对安全")
    
    return {
        "success": True,
        "message": "检测完成",
        "data": {
            "level": risk_level,
            "score": risk_score,
            "confidence": 0.8,
            "message": f"检测到{risk_level}级别内容",
            "reasons": reasons,
            "suggestions": suggestions,
            "detection_id": f"simple_{hash(text) % 10000}",
            "note": "这是简化版检测结果"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
