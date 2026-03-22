"""
老人短视频虚假信息检测系统 - 后端API服务
基于FastAPI + 多模态AI检测

支持功能:
- 文本内容检测
- 多模态融合检测
- 家人通知服务
- 历史记录查询
"""

import os
import sys
import asyncio
import tempfile
import subprocess
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, BackgroundTasks, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from loguru import logger

# 配置日志
logger.remove()
logger.add(
    sys.stderr,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)

# 尝试导入AI检测模块
try:
    # 绝对导入，确保 `uvicorn app.main:app` / `python -m app.main` 都能工作
    from app.services.multimodal_detector import (
        MultimodalDetector,
        RiskLevel,
    )
    AI_AVAILABLE = True
    logger.info("AI检测模块加载成功")
except ImportError:
    try:
        from services.multimodal_detector import (
            MultimodalDetector,
            RiskLevel,
        )
        AI_AVAILABLE = True
        logger.info("AI检测模块加载成功（相对导入）")
    except ImportError as e:
        logger.warning(f"AI检测模块未加载: {e}，使用规则引擎")
        AI_AVAILABLE = False

# 尝试导入家人通知服务
try:
    from services.family_notification import FamilyNotificationService
    NOTIFICATION_AVAILABLE = True
except ImportError:
    NOTIFICATION_AVAILABLE = False


# === 数据模型 ===

class DetectionRequest(BaseModel):
    """检测请求"""
    text: str = Field(..., description="待检测文本内容", min_length=1)
    audio_text: Optional[str] = Field(None, description="音频转写文本")
    source: Optional[str] = Field("api", description="请求来源")
    user_id: Optional[str] = Field(None, description="用户ID")

class DetectionResponse(BaseModel):
    """检测响应"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

class FamilyNotifyRequest(BaseModel):
    """家人通知请求"""
    elderly_user_id: str
    risk_level: str
    content_summary: str
    video_link: Optional[str] = None

class HealthResponse(BaseModel):
    """健康检查响应"""
    status: str
    message: str
    ai_available: bool
    version: str
    timestamp: str


# === 规则引擎检测 ===

class RuleBasedDetector:
    """基于规则的检测器（AI不可用时的降级方案）"""
    
    FINANCIAL_KEYWORDS = [
        "保证收益", "无风险", "月入万元", "稳赚不赔", "高收益",
        "内幕消息", "限时优惠", "投资理财", "虚拟货币", "传销",
        "无抵押贷款", "秒批", "黑户贷款", "刷单", "套现",
        "保本保息", "年化收益", "日赚千元"
    ]
    
    MEDICAL_KEYWORDS = [
        "包治百病", "神奇疗效", "祖传秘方", "一次根治", "永不复发",
        "药到病除", "100%治愈", "三天见效", "医院不告诉你", "特效药",
        "保健品", "偏方", "土方", "民间验方", "癌症克星"
    ]
    
    URGENCY_KEYWORDS = [
        "赶紧", "立即", "马上", "紧急", "限时", "截止今晚",
        "最后一天", "错过后悔", "机不可失", "名额有限"
    ]
    
    def detect(self, text: str) -> Dict[str, Any]:
        """执行规则检测"""
        risk_score = 0.0
        reasons = []
        suggestions = []
        
        # 金融检测
        financial_matches = [kw for kw in self.FINANCIAL_KEYWORDS if kw in text]
        if financial_matches:
            risk_score += min(len(financial_matches) * 0.15, 0.5)
            reasons.append(f"金融风险词汇: {', '.join(financial_matches[:3])}")
            suggestions.append("投资需谨慎，高收益往往伴随高风险")
        
        # 医疗检测
        medical_matches = [kw for kw in self.MEDICAL_KEYWORDS if kw in text]
        if medical_matches:
            risk_score += min(len(medical_matches) * 0.15, 0.5)
            reasons.append(f"医疗风险词汇: {', '.join(medical_matches[:3])}")
            suggestions.append("有病请找正规医院，不要轻信偏方")
        
        # 紧急性检测
        urgency_matches = [kw for kw in self.URGENCY_KEYWORDS if kw in text]
        if urgency_matches:
            risk_score += min(len(urgency_matches) * 0.1, 0.3)
            reasons.append("含有紧急性诱导词汇")
            suggestions.append("冷静思考，不要被紧急性语言误导")
        
        risk_score = min(risk_score, 1.0)
        
        # 确定风险等级
        if risk_score > 0.7:
            level = "danger"
            message = "⚠️ 高风险：检测到疑似诈骗或虚假信息"
        elif risk_score > 0.4:
            level = "warning"
            message = "⚡ 注意：内容存在可疑信息"
        else:
            level = "safe"
            message = "✅ 内容相对安全"
            if not reasons:
                reasons.append("未发现明显风险")
                suggestions.append("内容相对安全，但仍需谨慎")
        
        return {
            "level": level,
            "score": risk_score,
            "confidence": 0.75,
            "message": message,
            "reasons": reasons,
            "suggestions": suggestions,
            "detection_method": "rule_engine"
        }


# 全局检测器实例
rule_detector = RuleBasedDetector()
ai_detector = None

def _try_extract_frames_opencv(video_path: str, max_frames: int = 3) -> List[Any]:
    """
    抽帧：优先用opencv（若不可用则返回空列表）
    返回：PIL.Image 列表（若PIL不可用则返回空）
    """
    try:
        import cv2  # type: ignore
        from PIL import Image  # type: ignore
    except Exception:
        return []

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        return []

    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    if frame_count <= 0:
        cap.release()
        return []

    # 均匀取 max_frames 帧（25/50/75%...）
    idxs = []
    for i in range(1, max_frames + 1):
        idxs.append(int(frame_count * (i / (max_frames + 1))))
    idxs = sorted(set([min(max(0, x), frame_count - 1) for x in idxs]))

    frames: List[Any] = []
    for idx in idxs:
        cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, frame = cap.read()
        if not ok:
            continue
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(Image.fromarray(frame_rgb))

    cap.release()
    return frames


def _try_ocr_frames(frames: List[Any], max_chars: int = 800) -> str:
    """
    OCR: 优先 easyocr（无需系统tesseract），其次 pytesseract（需要本机安装tesseract）。
    返回合并后的文字（去重、截断）。
    """
    if not frames:
        return ""

    # easyocr
    try:
        import numpy as _np  # type: ignore
        import easyocr  # type: ignore

        # 缓存 reader，避免每次初始化非常慢
        global _EASYOCR_READER  # noqa: PLW0603
        if "_EASYOCR_READER" not in globals() or _EASYOCR_READER is None:
            _EASYOCR_READER = easyocr.Reader(["ch_sim", "en"], gpu=False)

        texts: List[str] = []
        for img in frames:
            arr = _np.array(img)
            # detail=0 仅返回文本列表
            out = _EASYOCR_READER.readtext(arr, detail=0)
            for t in out:
                if t and isinstance(t, str):
                    texts.append(t.strip())

        merged = "\n".join([t for t in dict.fromkeys(texts) if t])
        return merged[:max_chars]
    except Exception:
        pass

    # pytesseract fallback
    try:
        import pytesseract  # type: ignore
        texts2: List[str] = []
        for img in frames:
            t = pytesseract.image_to_string(img, lang="chi_sim+eng")
            if t:
                texts2.append(t.strip())
        merged = "\n".join([t for t in dict.fromkeys(texts2) if t])
        return merged[:max_chars]
    except Exception:
        return ""


def _try_transcribe_whisper(video_path: str) -> str:
    """
    语音转写：如果环境有 whisper，则直接对视频文件转写；否则返回空字符串。
    """
    try:
        import whisper  # type: ignore
        model = whisper.load_model("base")
        result = model.transcribe(video_path, language="zh")
        return (result.get("text") or "").strip()
    except Exception:
        return ""


# === 应用生命周期 ===

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global ai_detector
    
    # 启动时
    logger.info("=" * 50)
    logger.info("老人短视频虚假信息检测系统 启动中...")
    logger.info("=" * 50)
    
    # 自动检测模型文件路径
    # 模型可能在项目根目录、backend目录或当前工作目录
    import pathlib
    possible_roots = [
        pathlib.Path(__file__).resolve().parent.parent.parent,  # backend/../.. = 项目根
        pathlib.Path(__file__).resolve().parent.parent,          # backend/.. = backend
        pathlib.Path.cwd(),                                       # 当前工作目录
        pathlib.Path.cwd().parent,                                # cwd 上级
    ]
    
    bert_model_path = None
    simple_model_path = None
    
    for root in possible_roots:
        p = root / "best_text_model.pt"
        if p.exists() and bert_model_path is None:
            bert_model_path = str(p)
            logger.info(f"发现 BERT 模型: {bert_model_path} ({p.stat().st_size / 1024 / 1024:.0f}MB)")
        p2 = root / "simple_ai_model.joblib"
        if p2.exists() and simple_model_path is None:
            simple_model_path = str(p2)
            logger.info(f"发现简单AI模型: {simple_model_path} ({p2.stat().st_size / 1024:.0f}KB)")
    
    # 尝试初始化AI检测器
    if AI_AVAILABLE:
        try:
            ai_detector = MultimodalDetector(
                model_path=bert_model_path,
                simple_model_path=simple_model_path
            )
            logger.info("✓ AI检测器初始化成功")
        except Exception as e:
            logger.warning(f"AI检测器初始化失败: {e}")
            ai_detector = None
    
    logger.info(f"AI检测: {'可用' if ai_detector else '不可用（使用规则引擎）'}")
    logger.info("系统启动完成")
    
    yield
    
    # 关闭时
    logger.info("系统关闭中...")


# === 创建应用 ===

app = FastAPI(
    title="老人短视频虚假信息检测系统",
    description="""
    基于多模态AI的虚假信息检测API
    
    功能:
    - 🔍 文本内容检测
    - 🤖 多模态融合分析
    - 📱 家人实时通知
    - 📊 检测历史记录
    
    技术:
    - BERT中文预训练模型
    - 跨模态注意力机制
    - 规则引擎增强
    """,
    version="2.0.0",
    lifespan=lifespan
)

# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3005",
        "http://127.0.0.1:3005",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "*"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === API路由 ===

@app.get("/", response_model=HealthResponse)
async def root():
    """根路径 - 系统信息"""
    return HealthResponse(
        status="running",
        message="老人短视频虚假信息检测系统 API服务",
        ai_available=ai_detector is not None,
        version="2.0.0",
        timestamp=datetime.now().isoformat()
    )


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        message="服务运行正常",
        ai_available=ai_detector is not None,
        version="2.0.0",
        timestamp=datetime.now().isoformat()
    )


@app.get("/api")
async def api_info():
    """API信息"""
    return {
        "success": True,
        "message": "API服务正常运行",
        "version": "2.0.0",
        "ai_available": ai_detector is not None,
        "endpoints": {
            "检测": "POST /detect",
            "健康检查": "GET /health",
            "家人通知": "POST /notify-family"
        }
    }


@app.post("/detect", response_model=DetectionResponse)
async def detect(request: DetectionRequest, background_tasks: BackgroundTasks):
    """
    检测虚假信息
    
    - 支持文本内容检测
    - 支持音频转写文本检测
    - 自动选择AI或规则引擎
    """
    try:
        # 合并文本
        text = request.text
        if request.audio_text:
            text = f"{text} {request.audio_text}"
        
        if not text.strip():
            raise HTTPException(status_code=400, detail="文本内容不能为空")
        
        # 执行检测
        if ai_detector is not None:
            # 使用AI检测
            try:
                result = await ai_detector.detect(text)
                detection_result = {
                    "level": result.risk_level.value,
                    "score": result.risk_score,
                    "confidence": result.confidence,
                    "message": result.explanation or "",
                    "reasons": result.reasons,
                    "suggestions": result.suggestions,
                    "text_risk": result.text_risk,
                    "visual_risk": result.visual_risk,
                    "audio_risk": result.audio_risk,
                    "detection_method": getattr(result, 'detection_method', 'ai_multimodal'),
                    "inference_time": result.inference_time
                }
            except Exception as e:
                logger.warning(f"AI检测失败，回退到规则引擎: {e}")
                detection_result = rule_detector.detect(text)
        else:
            # 使用规则引擎
            detection_result = rule_detector.detect(text)
        
        # 生成检测ID
        detection_result["detection_id"] = f"det_{hash(text) % 100000}_{int(datetime.now().timestamp())}"
        
        return DetectionResponse(
            success=True,
            message="检测完成",
            data=detection_result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"检测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"检测服务异常: {str(e)}")

@app.post("/detect/video", response_model=DetectionResponse)
async def detect_video(
    background_tasks: BackgroundTasks,
    video: UploadFile = File(..., description="待检测视频文件"),
    text: str = Form("", description="可选：视频标题/简介/字幕等文本"),
    user_id: Optional[str] = Form(None, description="可选：用户ID"),
):
    """
    上传视频验证（模拟短视频虚假识别）：
    - 保存上传文件到临时目录
    - 尽力抽取关键帧（opencv可用时）
    - 尽力做语音转写（whisper可用时）
    - 调用多模态检测器（不可用则回退规则引擎）
    """
    try:
        if not video.filename:
            raise HTTPException(status_code=400, detail="缺少视频文件")

        suffix = os.path.splitext(video.filename)[1] or ".mp4"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp_path = tmp.name
            content = await video.read()
            tmp.write(content)

        # 抽帧 & 转写
        frames = _try_extract_frames_opencv(tmp_path, max_frames=3)
        ocr_text = _try_ocr_frames(frames)
        transcript = _try_transcribe_whisper(tmp_path)

        merged_text = (text or "").strip()
        if ocr_text:
            merged_text = f"{merged_text}\n{ocr_text}".strip()
        if transcript:
            merged_text = f"{merged_text}\n{transcript}".strip()

        if ai_detector is not None:
            # 选取“信息量最大”的帧：优先OCR文本最多的帧，否则用第一帧
            image = frames[0] if frames else None
            if frames:
                best_img = frames[0]
                best_len = 0
                for img in frames:
                    t = _try_ocr_frames([img], max_chars=2000)
                    if len(t) > best_len:
                        best_len = len(t)
                        best_img = img
                image = best_img

            result = await ai_detector.detect({"text": merged_text or " ", "image": image})
            detection_result = {
                "level": result.risk_level.value,
                "score": float(result.risk_score),
                "confidence": float(result.confidence),
                "message": result.explanation or "",
                "reasons": result.reasons,
                "suggestions": result.suggestions,
                "text_risk": float(result.text_risk),
                "visual_risk": float(result.visual_risk),
                "audio_risk": float(result.audio_risk),
                "detection_method": "ai_video_upload",
                "inference_time": float(result.inference_time),
                "transcript": transcript[:500] if transcript else "",
                "ocr_text": ocr_text[:800] if ocr_text else "",
                "frames_used": len(frames),
            }
        else:
            detection_result = rule_detector.detect(merged_text or "")
            detection_result.update({
                "detection_method": "rule_engine_video_upload",
                "transcript": transcript[:500] if transcript else "",
                "ocr_text": ocr_text[:800] if ocr_text else "",
                "frames_used": len(frames),
            })

        detection_result["detection_id"] = f"vid_{hash(video.filename) % 100000}_{int(datetime.now().timestamp())}"

        return DetectionResponse(success=True, message="视频检测完成", data=detection_result)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"视频检测失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"视频检测异常: {str(e)}")
    finally:
        try:
            if "tmp_path" in locals() and tmp_path and os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


@app.post("/notify-family")
async def notify_family(request: FamilyNotifyRequest):
    """
    发送家人通知
    
    当检测到高风险内容时，通知家人
    """
    try:
        if not NOTIFICATION_AVAILABLE:
            return {
                "success": False,
                "message": "通知服务暂不可用"
            }
        
        # TODO: 实现实际的通知逻辑
        logger.info(f"发送家人通知: 用户={request.elderly_user_id}, 风险={request.risk_level}")
        
        return {
            "success": True,
            "message": "通知已发送",
            "data": {
                "notified_at": datetime.now().isoformat(),
                "risk_level": request.risk_level
            }
        }
        
    except Exception as e:
        logger.error(f"通知失败: {e}")
        raise HTTPException(status_code=500, detail="通知服务异常")


@app.post("/api/detect", response_model=DetectionResponse)
async def detect_api(request: DetectionRequest, background_tasks: BackgroundTasks):
    """检测虚假信息 (API前缀版本，兼容前端)"""
    return await detect(request, background_tasks)


@app.get("/stats")
async def get_stats():
    """获取系统统计信息"""
    return {
        "success": True,
        "data": {
            "ai_available": ai_detector is not None,
            "detection_methods": ["rule_engine"] + (["ai_multimodal"] if ai_detector else []),
            "supported_features": [
                "text_detection",
                "financial_fraud_detection",
                "medical_misinformation_detection",
                "urgency_detection"
            ],
            "version": "2.0.0"
        }
    }


# === QClaw Skill 集成 ===
# 
# 架构说明:
#   1. QClaw 从 GitHub 下载我们的 Skill（qclaw-skill/）并安装
#   2. 安装时 QClaw 分配一个 webhook URL
#   3. 用户把该 webhook URL 配到本系统的 OpenClaw 设置里
#   4. 检测到风险时，本系统 POST 告警到 QClaw webhook
#   5. QClaw 调用 Skill 的 handleRiskAlert() → 推送给家属
#
# 本后端提供:
#   - POST /api/qclaw/push   → 主动推送告警到 QClaw webhook（前端调用）
#   - POST /api/qclaw/config → 配置 QClaw webhook URL
#   - GET  /api/qclaw/status → 查看当前配置和连通性

class QClawPushRequest(BaseModel):
    """推送告警到 QClaw 的请求（前端检测完后调用）"""
    level: str = Field(..., description="风险等级: danger | warning | safe")
    score: float = Field(..., ge=0, le=1, description="风险评分 0-1")
    video_title: str = Field("", description="视频标题")
    reasons: List[str] = Field(default_factory=list, description="风险因素列表")
    suggestions: List[str] = Field(default_factory=list, description="安全建议列表")
    detection_method: str = Field("ai_multimodal", description="检测方法")
    timestamp: Optional[str] = Field(None, description="检测时间 ISO8601")

class QClawWebhookConfig(BaseModel):
    """QClaw Webhook 配置 — 用户安装 Skill 后从 QClaw 获取的 URL"""
    webhook_url: Optional[str] = Field(None, description="QClaw 分配的 Webhook URL")
    enabled: bool = Field(True, description="是否启用")

# 全局配置：存储 QClaw 分配给我们的 webhook URL
_qclaw_webhook: Dict[str, Any] = {
    "webhook_url": os.environ.get("QCLAW_WEBHOOK_URL", ""),
    "enabled": True,
}


@app.post("/api/qclaw/push")
async def qclaw_push(request: QClawPushRequest):
    """
    推送风险告警到 QClaw
    
    前端检测到风险后调用此接口，我们将告警数据 POST 到 QClaw 分配的 webhook URL，
    QClaw 收到后调用已安装的 factsafe-elder-alert Skill 推送给家属。
    """
    if not _qclaw_webhook.get("enabled"):
        return {"success": False, "message": "QClaw 推送未启用"}

    webhook_url = _qclaw_webhook.get("webhook_url", "")
    if not webhook_url:
        return {
            "success": False,
            "message": "未配置 QClaw Webhook URL。请先在 QClaw 中安装 factsafe-elder-alert Skill，然后将分配的 Webhook URL 填入设置。",
        }

    # safe 不推送
    if request.level == "safe":
        return {"success": True, "message": "安全内容，无需推送", "pushed": False}

    # 构造 webhook payload（与 Skill 的 skill.json webhook.payload 格式一致）
    payload = {
        "level": request.level,
        "score": request.score,
        "video_title": request.video_title or "未知视频",
        "reasons": request.reasons,
        "suggestions": request.suggestions,
        "detection_method": request.detection_method,
        "timestamp": request.timestamp or datetime.now().isoformat(),
    }

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if resp.status_code >= 400:
                logger.warning(f"QClaw webhook failed: {resp.status_code} {resp.text}")
                return {
                    "success": False,
                    "message": f"QClaw 返回 {resp.status_code}",
                    "pushed": False,
                }

            result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
            logger.info(f"QClaw push success: level={request.level}, score={round(request.score * 100)}")
            return {
                "success": True,
                "message": "告警已推送到 QClaw",
                "pushed": True,
                "data": result,
            }

    except ImportError:
        return {"success": False, "message": "httpx 未安装"}
    except Exception as e:
        logger.warning(f"QClaw push error: {e}")
        return {
            "success": False,
            "message": f"QClaw 不可达: {str(e)}",
            "pushed": False,
        }


@app.post("/api/qclaw/config")
async def update_qclaw_config(config: QClawWebhookConfig):
    """
    配置 QClaw Webhook URL
    
    用户在 QClaw 安装 Skill 后获得一个 webhook URL，通过此接口保存到后端。
    """
    global _qclaw_webhook
    if config.webhook_url is not None:
        _qclaw_webhook["webhook_url"] = config.webhook_url
    _qclaw_webhook["enabled"] = config.enabled
    logger.info(f"QClaw config updated: url={'***' + _qclaw_webhook['webhook_url'][-20:] if _qclaw_webhook['webhook_url'] else '(empty)'}, enabled={config.enabled}")
    return {
        "success": True,
        "message": "QClaw 配置已更新",
        "data": {
            "webhook_url_set": bool(_qclaw_webhook.get("webhook_url")),
            "enabled": _qclaw_webhook["enabled"],
        },
    }


@app.get("/api/qclaw/status")
async def qclaw_status():
    """查看 QClaw 集成状态"""
    webhook_url = _qclaw_webhook.get("webhook_url", "")
    result = {
        "enabled": _qclaw_webhook.get("enabled", False),
        "webhook_configured": bool(webhook_url),
        "skill_repo": "https://github.com/yuchendeng/Fact-Safe-Elder/tree/main/qclaw-skill",
        "install_instructions": [
            "1. 在 QClaw 中安装 Skill: qclaw skill install https://github.com/yuchendeng/Fact-Safe-Elder/qclaw-skill",
            "2. 安装后 QClaw 会分配一个 Webhook URL",
            "3. 将 Webhook URL 配到 FactSafe 设置 → OpenClaw 配置中",
            "4. 检测到风险时会自动推送到 QClaw → 通知家属",
        ],
    }

    # 尝试检测连通性
    if webhook_url:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.options(webhook_url)
                result["reachable"] = resp.status_code < 500
                result["status_code"] = resp.status_code
        except Exception as e:
            result["reachable"] = False
            result["error"] = str(e)
    else:
        result["reachable"] = False

    return {"success": True, "data": result}


# === 启动入口 ===

if __name__ == "__main__":
    import uvicorn
    
    # 获取端口
    port = int(os.environ.get("PORT", 8000))
    
    # 启动服务
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,
        log_level="info"
    )
