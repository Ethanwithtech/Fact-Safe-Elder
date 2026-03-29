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
        logger.info(f"EasyOCR 识别结果: {merged[:200] if merged else '(空)'}")
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
    语音转写：如果环境有 whisper + ffmpeg，则直接对视频文件转写；否则返回空字符串。
    """
    try:
        # 确保 ffmpeg 在 PATH 中（imageio-ffmpeg 提供的二进制）
        try:
            import imageio_ffmpeg  # type: ignore
            ffmpeg_dir = os.path.dirname(imageio_ffmpeg.get_ffmpeg_exe())
            if ffmpeg_dir not in os.environ.get("PATH", ""):
                os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")
                logger.info(f"ffmpeg 路径已添加: {ffmpeg_dir}")
        except ImportError:
            pass
        # ~/bin/ffmpeg 也加上
        home_bin = os.path.expanduser("~/bin")
        if home_bin not in os.environ.get("PATH", ""):
            os.environ["PATH"] = home_bin + os.pathsep + os.environ.get("PATH", "")

        import whisper  # type: ignore
        model = whisper.load_model("base")
        logger.info(f"Whisper 开始转写: {video_path}")

        # 先检查是否有音频流
        try:
            import subprocess as _sp
            probe = _sp.run(
                ["ffmpeg", "-i", video_path, "-hide_banner"],
                capture_output=True, text=True, timeout=5,
            )
            stderr_out = probe.stderr or ""
            if "Audio:" not in stderr_out:
                logger.info("视频无音频流，跳过 ASR")
                return ""
        except Exception:
            pass  # ffmpeg 检查失败时让 whisper 自行处理

        result = model.transcribe(video_path, language="zh")
        text = (result.get("text") or "").strip()
        logger.info(f"Whisper 转写结果: {text[:200] if text else '(空)'}")
        return text
    except Exception as e:
        logger.warning(f"Whisper 转写失败: {e}")
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
    
    # 初始化 GPT 事实核查器
    try:
        from app.services.gpt_fact_checker import get_fact_checker
        _gpt_checker = get_fact_checker()
        logger.info(f"GPT 事实核查器: {'可用' if _gpt_checker.available else '不可用'}")
    except Exception as e:
        logger.warning(f"GPT 事实核查器初始化失败: {e}")

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


def _build_content_summary(
    level: str,
    merged_text: str,
    transcript: str,
    ocr_text: str,
    fallback_explanation: str,
    reasons: List[str],
) -> str:
    """
    基于视频实际识别内容生成 AI 结论摘要，而不是模板化的说明。
    """
    parts: List[str] = []
    snippet = (merged_text or "").strip()[:120]

    if level == "danger":
        parts.append("🚨 高风险警告：视频内容存在严重安全隐患")
    elif level == "warning":
        parts.append("⚠️ 注意：视频内容存在可疑信息")
    else:
        parts.append("✅ 视频内容相对安全")

    # 标记内容来源
    sources: List[str] = []
    if transcript:
        sources.append("语音转写(ASR)")
    if ocr_text:
        sources.append("画面文字(OCR)")
    if sources:
        parts.append(f"识别来源：{' + '.join(sources)}")

    # 摘要视频内容
    if snippet:
        parts.append(f"内容摘要：「{snippet}{'…' if len(merged_text or '') > 120 else ''}」")

    # 关键风险
    if reasons:
        parts.append(f"主要风险：{reasons[0]}")

    return "\n".join(parts)


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
            # 选取"信息量最大"的帧：优先OCR文本最多的帧，否则用第一帧
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

            # 生成基于实际内容的 AI 结论（替代模板化 explanation）
            ai_message = _build_content_summary(
                result.risk_level.value, merged_text, transcript, ocr_text,
                result.explanation or "", list(result.reasons),
            )

            detection_result = {
                "level": result.risk_level.value,
                "score": float(result.risk_score),
                "confidence": float(result.confidence),
                "message": ai_message,
                "reasons": list(result.reasons),
                "suggestions": list(result.suggestions),
                "text_risk": float(result.text_risk),
                "visual_risk": float(result.visual_risk),
                "audio_risk": float(result.audio_risk),
                "detection_method": "ai_video_upload",
                "inference_time": float(result.inference_time),
                "transcript": transcript[:500] if transcript else "",
                "ocr_text": ocr_text[:800] if ocr_text else "",
                "frames_used": len(frames),
                "bert_score": round(result.bert_score, 4) if result.bert_score is not None else None,
                "tfidf_score": round(result.tfidf_score, 4) if result.tfidf_score is not None else None,
            }
        else:
            detection_result = rule_detector.detect(merged_text or "")
            detection_result.update({
                "detection_method": "rule_engine_video_upload",
                "transcript": transcript[:500] if transcript else "",
                "ocr_text": ocr_text[:800] if ocr_text else "",
                "frames_used": len(frames),
            })

        # GPT 事实核查已拆到独立端点 POST /api/fact-check，前端异步调用
        # 这里只返回 merged_text 供前端二次请求
        detection_result["merged_text"] = merged_text[:2000] if merged_text else ""

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


class FactCheckRequest(BaseModel):
    """事实核查请求"""
    text: str = Field(..., description="待核查文本", min_length=1)
    context: Optional[str] = Field(None, description="上下文（视频名等）")
    detection_result: Optional[Dict[str, Any]] = Field(None, description="AI 预检测结果")


@app.post("/api/fact-check")
async def api_fact_check(request: FactCheckRequest):
    """
    独立的 GPT 事实核查端点（前端异步调用）
    先由 BERT/TF-IDF 快速出结果，再调此接口做 GPT 深度分析
    """
    try:
        from app.services.gpt_fact_checker import get_fact_checker
        checker = get_fact_checker()
        if not checker.available:
            raise HTTPException(status_code=503, detail="GPT 事实核查服务不可用")
        
        result = await checker.fact_check(
            content=request.text,
            context=request.context,
            detection_result=request.detection_result,
        )
        return {"success": True, "message": "事实核查完成", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"事实核查失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"事实核查异常: {str(e)}")


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
    "webhook_url": os.environ.get("QCLAW_WEBHOOK_URL", "http://127.0.0.1:28789/hooks/factsafe"),
    "auth_token": os.environ.get("QCLAW_AUTH_TOKEN", "factsafe-secret-token-2024"),
    "enabled": True,
}

# 全局配置：飞书 Webhook
_feishu_config: Dict[str, Any] = {
    "webhook_url": os.environ.get("FEISHU_WEBHOOK_URL", ""),
    "enabled": False,
}


# ============================================================
#  飞书 (Feishu / Lark) 推送接口
# ============================================================

class FeishuWebhookConfig(BaseModel):
    """飞书 Webhook 配置"""
    webhook_url: Optional[str] = Field(None, description="飞书自定义机器人 Webhook URL")
    enabled: bool = Field(True, description="是否启用飞书推送")


@app.post("/api/feishu/push")
async def feishu_push(request: QClawPushRequest):
    """
    推送风险告警到飞书自定义机器人
    
    飞书 Webhook URL 格式: https://open.feishu.cn/open-apis/bot/v2/hook/{webhook_id}
    """
    if not _feishu_config.get("enabled"):
        return {"success": False, "message": "飞书推送未启用", "pushed": False}

    webhook_url = _feishu_config.get("webhook_url", "")
    if not webhook_url:
        return {
            "success": False,
            "message": "未配置飞书 Webhook URL。请在飞书群中添加自定义机器人，获取 Webhook URL 后填入设置。",
            "pushed": False,
        }

    # 构建飞书卡片消息
    level_emoji = "🔴" if request.level == "danger" else "🟡" if request.level == "warning" else "🟢"
    level_text = "高风险" if request.level == "danger" else "注意" if request.level == "warning" else "安全"
    score_pct = round(request.score * 100)
    reasons_text = "\n".join(f"  • {r}" for r in (request.reasons or [])) or "无"
    suggestions_text = "\n".join(f"  • {s}" for s in (request.suggestions or [])) or "无"

    feishu_payload = {
        "msg_type": "interactive",
        "card": {
            "config": {"wide_screen_mode": True},
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"{level_emoji} 短视频风险告警 — {level_text}",
                },
                "template": "red" if request.level == "danger" else "orange" if request.level == "warning" else "green",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            f"**📹 视频**: {request.video_title or '未知视频'}\n"
                            f"**⚠️ 风险等级**: {level_emoji} {level_text}\n"
                            f"**📊 风险评分**: {score_pct}/100\n"
                            f"**🔍 检测方式**: {request.detection_method or 'AI多模态'}\n"
                            f"**⏰ 时间**: {request.timestamp or 'N/A'}"
                        ),
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**⚡ 风险因素**:\n{reasons_text}",
                    },
                },
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**💡 建议**:\n{suggestions_text}",
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": "🛡️ FactSafe AI 守护系统 | 如遇可疑情况请拨打 96110 反诈热线",
                        }
                    ],
                },
            ],
        },
    }

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                webhook_url,
                json=feishu_payload,
                headers={"Content-Type": "application/json"},
            )

            if resp.status_code >= 400:
                logger.warning(f"Feishu webhook failed: {resp.status_code} {resp.text}")
                return {"success": False, "message": f"飞书返回 {resp.status_code}", "pushed": False}

            result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
            # 飞书正常返回 {"code":0,"msg":"success","data":{}}
            feishu_code = result.get("code", -1)
            if feishu_code != 0:
                logger.warning(f"Feishu push error: {result}")
                return {"success": False, "message": f"飞书返回错误: {result.get('msg', 'unknown')}", "pushed": False}

            logger.info(f"Feishu push success: level={request.level}, score={score_pct}")
            return {"success": True, "message": "告警已推送到飞书", "pushed": True, "data": result}

    except ImportError:
        return {"success": False, "message": "httpx 未安装", "pushed": False}
    except Exception as e:
        logger.warning(f"Feishu push error: {e}")
        return {"success": False, "message": f"飞书不可达: {str(e)}", "pushed": False}


@app.post("/api/feishu/config")
async def update_feishu_config(config: FeishuWebhookConfig):
    """配置飞书 Webhook URL"""
    global _feishu_config
    if config.webhook_url is not None:
        _feishu_config["webhook_url"] = config.webhook_url
    _feishu_config["enabled"] = config.enabled
    logger.info(f"Feishu config updated: url={'***' + _feishu_config['webhook_url'][-20:] if _feishu_config['webhook_url'] else '(empty)'}, enabled={config.enabled}")
    return {
        "success": True,
        "message": "飞书配置已更新",
        "data": {
            "webhook_url_set": bool(_feishu_config.get("webhook_url")),
            "enabled": _feishu_config["enabled"],
        },
    }


@app.get("/api/feishu/status")
async def feishu_status():
    """查看飞书集成状态"""
    webhook_url = _feishu_config.get("webhook_url", "")
    result = {
        "enabled": _feishu_config.get("enabled", False),
        "webhook_configured": bool(webhook_url),
    }
    if webhook_url:
        try:
            import httpx
            async with httpx.AsyncClient(timeout=5.0) as client:
                # 发一个空消息测试连通性
                resp = await client.post(webhook_url, json={"msg_type": "text", "content": {"text": ""}}, headers={"Content-Type": "application/json"})
                result["reachable"] = resp.status_code < 500
        except Exception as e:
            result["reachable"] = False
            result["error"] = str(e)
    else:
        result["reachable"] = False
    return {"success": True, "data": result}


@app.post("/api/feishu/test")
async def feishu_test():
    """测试飞书连接 — 发送一条测试消息"""
    webhook_url = _feishu_config.get("webhook_url", "")
    if not webhook_url:
        return {
            "success": False,
            "message": "未配置飞书 Webhook URL",
            "hint": "请在飞书群中添加自定义机器人，获取 Webhook URL 后填入设置",
        }

    test_payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {"tag": "plain_text", "content": "🧪 FactSafe 测试消息"},
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": "✅ **FactSafe AI 守护系统** 与飞书连接成功！\n\n当检测到短视频风险内容时，告警将自动推送到此群。",
                    },
                },
                {
                    "tag": "note",
                    "elements": [{"tag": "plain_text", "content": "🛡️ FactSafe — 守护老人上网安全"}],
                },
            ],
        },
    }

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=test_payload, headers={"Content-Type": "application/json"})
            result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            feishu_code = result.get("code", -1)
            return {
                "success": resp.status_code < 400 and feishu_code == 0,
                "message": f"测试消息已发送 (HTTP {resp.status_code})" if feishu_code == 0 else f"飞书返回错误: {result.get('msg', resp.text[:200])}",
                "status_code": resp.status_code,
            }
    except ImportError:
        return {"success": False, "message": "httpx 未安装"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


# ============================================================
#  企业微信 (WeCom) 群机器人推送接口
# ============================================================

_wecom_config: Dict[str, Any] = {
    "webhook_url": os.environ.get(
        "WECOM_WEBHOOK_URL",
        "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=7376df88-8f78-4e90-a05a-6b8d01ca8017",
    ),
    "enabled": True,
}


class WecomWebhookConfig(BaseModel):
    webhook_url: Optional[str] = Field(None)
    enabled: bool = Field(True)


@app.post("/api/wecom/push")
async def wecom_push(request: QClawPushRequest):
    """推送风险告警到企业微信群机器人"""
    if not _wecom_config.get("enabled"):
        return {"success": False, "message": "企业微信推送未启用", "pushed": False}

    webhook_url = _wecom_config.get("webhook_url", "")
    if not webhook_url:
        return {"success": False, "message": "未配置企业微信 Webhook URL", "pushed": False}

    level_emoji = "🔴" if request.level == "danger" else "🟡" if request.level == "warning" else "🟢"
    level_text = "高风险" if request.level == "danger" else "注意" if request.level == "warning" else "安全"
    score_pct = round(request.score * 100)
    reasons_text = "\n  • ".join(request.reasons or []) or "无"
    suggestions_text = "\n  • ".join(request.suggestions or []) or "无"
    font_color = "warning" if request.level == "danger" else "comment"

    # 企业微信 markdown 消息格式
    wecom_payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": (
                f"## {level_emoji} 短视频风险告警\n"
                f"> **AI守护系统** 检测到可疑内容\n\n"
                f"**视频**: {request.video_title or '未知视频'}\n"
                f'**风险等级**: <font color="{font_color}">{level_emoji} {level_text}</font>\n'
                f"**风险评分**: {score_pct}/100\n"
                f"**检测方式**: {request.detection_method or 'AI多模态'}\n"
                f"**时间**: {request.timestamp or 'N/A'}\n\n"
                f"**⚡ 风险因素**:\n  • {reasons_text}\n\n"
                f"**💡 建议**:\n  • {suggestions_text}\n\n"
                f"> 🛡️ FactSafe AI守护系统 | 如遇可疑情况请拨打 96110 反诈热线"
            ),
        },
    }

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=wecom_payload, headers={"Content-Type": "application/json"})

            if resp.status_code >= 400:
                logger.warning(f"WeCom webhook failed: {resp.status_code} {resp.text}")
                return {"success": False, "message": f"企业微信返回 {resp.status_code}", "pushed": False}

            result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
            errcode = result.get("errcode", -1)
            if errcode != 0:
                logger.warning(f"WeCom push error: {result}")
                return {"success": False, "message": f"企业微信返回错误: {result.get('errmsg', 'unknown')}", "pushed": False}

            logger.info(f"WeCom push success: level={request.level}, score={score_pct}")
            return {"success": True, "message": "告警已推送到企业微信", "pushed": True, "data": result}

    except ImportError:
        return {"success": False, "message": "httpx 未安装", "pushed": False}
    except Exception as e:
        logger.warning(f"WeCom push error: {e}")
        return {"success": False, "message": f"企业微信不可达: {str(e)}", "pushed": False}


@app.post("/api/wecom/config")
async def update_wecom_config(config: WecomWebhookConfig):
    """配置企业微信 Webhook URL"""
    global _wecom_config
    if config.webhook_url is not None:
        _wecom_config["webhook_url"] = config.webhook_url
    _wecom_config["enabled"] = config.enabled
    return {
        "success": True,
        "message": "企业微信配置已更新",
        "data": {"webhook_url_set": bool(_wecom_config.get("webhook_url")), "enabled": _wecom_config["enabled"]},
    }


@app.get("/api/wecom/status")
async def wecom_status():
    """查看企业微信集成状态"""
    return {
        "success": True,
        "data": {
            "enabled": _wecom_config.get("enabled", False),
            "webhook_configured": bool(_wecom_config.get("webhook_url")),
        },
    }


@app.post("/api/wecom/test")
async def wecom_test():
    """发送企业微信测试消息"""
    webhook_url = _wecom_config.get("webhook_url", "")
    if not webhook_url:
        return {"success": False, "message": "未配置企业微信 Webhook URL"}

    test_payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": (
                "## 🧪 FactSafe 测试消息\n\n"
                "✅ **FactSafe AI守护系统** 与企业微信连接成功！\n\n"
                "当检测到短视频风险内容时，告警将自动推送到此群。\n\n"
                "> 🛡️ FactSafe — 守护老人上网安全"
            ),
        },
    }

    try:
        import httpx
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=test_payload, headers={"Content-Type": "application/json"})
            result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
            errcode = result.get("errcode", -1)
            return {
                "success": resp.status_code < 400 and errcode == 0,
                "message": f"测试消息已发送 (HTTP {resp.status_code})" if errcode == 0 else f"企业微信返回错误: {result.get('errmsg', resp.text[:200])}",
                "status_code": resp.status_code,
            }
    except ImportError:
        return {"success": False, "message": "httpx 未安装"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}"}


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

        headers = {"Content-Type": "application/json"}
        auth_token = _qclaw_webhook.get("auth_token", "")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                webhook_url,
                json=payload,
                headers=headers,
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


@app.post("/api/qclaw/webhook")
async def qclaw_webhook_receiver(request: Dict[str, Any] = None):
    """
    QClaw 回调端点 — 接收来自 QClaw 的消息/状态更新
    
    QClaw 安装 Skill 后可以通过此端点与 FactSafe 后端通信：
    - 通知 webhook URL 已分配
    - 接收 Skill 执行结果
    - 健康检查
    """
    if not request:
        return {"success": True, "message": "FactSafe QClaw Webhook Receiver is running", "version": "1.0.0"}
    
    action = request.get("action", "")
    
    # QClaw 通知 webhook URL 已分配
    if action == "webhook_registered":
        webhook_url = request.get("webhook_url", "")
        if webhook_url:
            global _qclaw_webhook
            _qclaw_webhook["webhook_url"] = webhook_url
            _qclaw_webhook["enabled"] = True
            logger.info(f"QClaw webhook registered: {webhook_url[:50]}...")
            return {"success": True, "message": "Webhook URL 已接收并保存"}
    
    # QClaw 推送 Skill 执行结果
    if action == "skill_result":
        logger.info(f"QClaw skill result: {request.get('data', {})}")
        return {"success": True, "message": "收到 Skill 执行结果"}
    
    # QClaw 健康检查
    if action == "ping":
        return {"success": True, "message": "pong", "ai_available": ai_detector is not None}
    
    logger.info(f"QClaw webhook received: {request}")
    return {"success": True, "message": "已接收"}


@app.post("/api/qclaw/test")
async def qclaw_test():
    """
    测试 QClaw 连接 — 发送一条模拟告警
    """
    webhook_url = _qclaw_webhook.get("webhook_url", "")
    
    if not webhook_url:
        return {
            "success": False,
            "message": "未配置 QClaw Webhook URL",
            "hint": "请先让 QClaw 为 factsafe-elder-alert Skill 注册 webhook，然后配置到系统设置中",
            "our_callback_url": "http://localhost:8000/api/qclaw/webhook",
        }
    
    test_payload = {
        "level": "warning",
        "score": 0.75,
        "video_title": "🧪 测试视频 - AI守护系统连接测试",
        "reasons": ["这是一条测试告警，验证 QClaw 连接是否正常"],
        "suggestions": ["如果您看到此消息，说明 FactSafe → QClaw 链路正常！"],
        "detection_method": "test",
        "timestamp": datetime.now().isoformat(),
    }
    
    try:
        import httpx

        headers = {"Content-Type": "application/json"}
        auth_token = _qclaw_webhook.get("auth_token", "")
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(webhook_url, json=test_payload, headers=headers)
            
            return {
                "success": resp.status_code < 400,
                "message": f"测试告警已发送到 QClaw (HTTP {resp.status_code})",
                "status_code": resp.status_code,
                "response": resp.text[:500],
                "webhook_url": webhook_url[:50] + "...",
            }
    except ImportError:
        return {"success": False, "message": "httpx 未安装，请 pip install httpx"}
    except Exception as e:
        return {"success": False, "message": f"连接失败: {str(e)}", "webhook_url": webhook_url[:50] + "..."}


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
