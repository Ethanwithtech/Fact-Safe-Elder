#!/usr/bin/env python3
"""
简单的后端服务测试脚本
"""

import sys
import os

# 添加项目路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

try:
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    
    print("[OK] FastAPI 导入成功")
    
    # 创建简单的应用
    app = FastAPI(
        title="AI守护系统测试",
        description="简单的测试服务",
        version="1.0.0-test"
    )
    
    # CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    @app.get("/")
    async def root():
        return {
            "message": "AI守护系统测试服务",
            "status": "运行中",
            "version": "1.0.0-test"
        }
    
    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "message": "服务运行正常"
        }
    
    @app.post("/detect")
    async def detect(data: dict):
        text = data.get("text", "")
        
        if not text:
            return {
                "success": False,
                "message": "文本内容不能为空"
            }
        
        # 强化的检测逻辑
        danger_keywords = [
            "保证收益", "月入万元", "包治百病", "祖传秘方", "无风险投资", 
            "月入", "万元", "包治", "秘方", "保证", "无风险", "理财秘诀",
            "稳赚不赔", "高收益", "内幕消息", "股票推荐", "虚拟货币",
            "传销", "微商代理", "拉人头", "无抵押贷款", "秒批",
            "神奇疗效", "一次根治", "永不复发", "药到病除"
        ]
        
        warning_keywords = [
            "投资", "理财", "保健品", "偏方", "微信", "联系", "收益", "赚钱",
            "限时", "优惠", "抢购", "特价", "清仓", "促销", "代理", "加盟"
        ]
        
        risk_level = "safe"
        risk_score = 0.1
        reasons = []
        suggestions = []
        confidence = 0.8
        
        # 检测危险关键词
        found_danger = [kw for kw in danger_keywords if kw in text]
        if found_danger:
            risk_level = "danger"
            risk_score = min(0.9, 0.7 + len(found_danger) * 0.05)
            reasons.extend([f"发现高危关键词: '{kw}'" for kw in found_danger[:3]])
            suggestions.extend([
                "建议立即停止观看，谨防诈骗",
                "投资需谨慎，高收益往往伴随高风险",
                "不要轻易相信保证收益的投资项目"
            ])
        else:
            # 检测警告关键词
            found_warning = [kw for kw in warning_keywords if kw in text]
            if found_warning:
                risk_level = "warning"
                risk_score = min(0.7, 0.4 + len(found_warning) * 0.05)
                reasons.extend([f"发现可疑关键词: '{kw}'" for kw in found_warning[:3]])
                suggestions.extend([
                    "请谨慎对待此内容",
                    "购买前请仔细核实信息",
                    "如有疑问请咨询专业人士"
                ])
        
        # 检测联系方式
        import re
        if re.search(r'微信|qq|电话|手机|联系|\d{11}', text):
            if risk_level != "safe":
                reasons.append("含有联系方式且存在其他风险因素")
                suggestions.append("不要轻易添加陌生人联系方式")
        
        # 检测紧急性语言
        urgency_words = ['赶紧', '立即', '马上', '快速', '紧急', '限时', '截止', '最后']
        urgency_count = sum(1 for word in urgency_words if word in text)
        if urgency_count >= 2:
            if risk_level == "safe":
                risk_level = "warning"
                risk_score = max(risk_score, 0.5)
            reasons.append("内容使用大量紧急性语言，可能是诱导手段")
            suggestions.append("冷静思考，不要被紧急性语言误导")
        
        if not reasons:
            reasons.append("未发现明显风险")
            suggestions.append("内容相对安全")
        
        # 通用建议
        if risk_level != "safe":
            suggestions.append("如有疑问，请咨询家人或专业人士")
        
        import time
        return {
            "success": True,
            "message": "AI检测完成",
            "data": {
                "level": risk_level,
                "score": risk_score,
                "confidence": confidence,
                "message": f"检测完成，风险等级：{risk_level}",
                "reasons": reasons,
                "suggestions": suggestions,
                "detection_id": f"ai_det_{hash(text) % 100000}",
                "keywords_found": found_danger + found_warning if 'found_danger' in locals() and 'found_warning' in locals() else [],
                "timestamp": time.time()
            }
        }
    
    print("[OK] 应用创建成功")
    
    if __name__ == "__main__":
        print("[START] 启动测试服务...")
        print("[INFO] 访问地址: http://localhost:8008")
        print("[INFO] 健康检查: http://localhost:8008/health")
        print("[INFO] API文档: http://localhost:8008/docs")
        
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8008,
            log_level="info"
        )

except ImportError as e:
    print(f"[ERROR] 导入错误: {e}")
    print("请确保已安装必要的依赖包")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] 运行错误: {e}")
    sys.exit(1)
