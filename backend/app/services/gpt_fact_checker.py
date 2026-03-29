"""
GPT 事实核查服务
基于 HKBU GenAI Platform (gpt-4.1-mini) 进行联网事实核查和深度语义分析

API 文档: https://genai.hkbu.edu.hk
"""

import os
import json
import time
from typing import Dict, Any, Optional, List
from loguru import logger

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    logger.warning("httpx 未安装，GPT 事实核查不可用")


# HKBU GenAI Platform 配置
HKBU_API_BASE = os.environ.get(
    "HKBU_API_BASE",
    "https://genai.hkbu.edu.hk/api/v0/rest"
)
HKBU_API_KEY = os.environ.get(
    "HKBU_API_KEY",
    "e0d5e784-391d-4d3e-9d10-d6443227d95a"
)
HKBU_MODEL = os.environ.get("HKBU_MODEL", "gpt-4.1")


# 事实核查 System Prompt
FACT_CHECK_SYSTEM_PROMPT = """你是一位专业的事实核查专家，专门为老年人短视频内容做虚假信息检测。

## 核心任务
1. **逐句审查**给定文本中的每一个事实性声明（可能来自视频字幕、语音转写、OCR 识别）
2. **利用你所掌握的知识**（科学常识、医学知识、金融法规、新闻事实、官方数据等）来验证每条声明
3. 对于每条虚假或误导性声明，**必须明确指出原文哪里有问题**，并给出**正确的事实是什么**
4. 识别常见的针对老年人的诈骗模式（金融诈骗、虚假医疗、情感诈骗等）

## 验证方法
- 对比已知的科学研究、官方统计数据、权威机构声明
- 检查数字、日期、人名、机构名是否准确
- 识别逻辑谬误、以偏概全、断章取义等手法
- 判断是否使用了恐吓、诱导、虚假承诺等话术

请以 JSON 格式返回分析结果，包含以下字段：
{
  "verdict": "true" | "false" | "misleading" | "unverifiable",
  "confidence": 0.0-1.0,
  "risk_level": "safe" | "warning" | "danger",
  "summary": "一句话总结判定结果",
  "analysis": "详细分析（2-3句话，解释为什么判定为该结果）",
  "false_claims": [
    {
      "original": "视频中的原始虚假声明（引用原文）",
      "correction": "正确的事实是什么（附简要依据）",
      "severity": "high" | "medium" | "low"
    }
  ],
  "fact_points": ["核查要点1", "核查要点2"],
  "risk_factors": ["风险因素1", "风险因素2"],
  "safety_advice": ["给老年人的安全建议1", "建议2"],
  "related_scam_type": "诈骗类型（如：投资诈骗/虚假医疗/情感诈骗/无）"
}

## 重要规则
- 用简单易懂的中文，方便老年人理解
- **false_claims 是最关键的字段**：必须逐条列出视频中的虚假/误导内容，并给出正确信息
- 如果内容完全属实，false_claims 返回空数组 []
- 对涉及金钱、健康、个人信息的内容要更加警惕
- 即使无法100%核实，也要基于专业知识给出判断，并在 correction 中注明"根据现有证据"
- 对于明显的诈骗话术，要明确指出并给出具体防范建议
- severity: high=严重虚假可能造成经济/健康损害, medium=误导性信息, low=小错误或夸张"""


class GPTFactChecker:
    """
    基于 HKBU GenAI Platform 的 GPT 事实核查器
    """

    def __init__(
        self,
        api_base: str = HKBU_API_BASE,
        api_key: str = HKBU_API_KEY,
        model: str = HKBU_MODEL,
        timeout: float = 30.0,
    ):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self._available = bool(HTTPX_AVAILABLE and api_key)

        if self._available:
            logger.info(
                f"✅ GPT 事实核查器初始化 | model={model} | api_base={api_base[:40]}..."
            )
        else:
            logger.warning("GPT 事实核查器不可用（缺少 httpx 或 API key）")

    @property
    def available(self) -> bool:
        return self._available

    async def fact_check(
        self,
        content: str,
        context: Optional[str] = None,
        detection_result: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        对内容进行 GPT 事实核查

        Args:
            content: 待核查的文本内容（字幕/转写/OCR）
            context: 可选的上下文信息（视频标题等）
            detection_result: 可选的已有 AI 检测结果（用于增强分析）

        Returns:
            事实核查结果字典
        """
        if not self._available:
            return self._fallback_result("GPT 服务不可用")

        if not content or not content.strip():
            return self._fallback_result("无文本内容可供核查")

        # 构建用户消息
        user_message = self._build_user_message(content, context, detection_result)

        try:
            start_time = time.time()

            # 调用 HKBU GenAI Platform API
            url = f"{self.api_base}/deployments/{self.model}/chat/completions"

            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key,
            }

            payload = {
                "messages": [
                    {"role": "system", "content": FACT_CHECK_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                "max_tokens": 2048,
            }

            # gpt-5 系列和 o3 系列不支持自定义 temperature
            if not any(tag in self.model for tag in ("gpt-5", "o3", "o4")):
                payload["temperature"] = 0.3

            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(url, json=payload, headers=headers)

                if resp.status_code != 200:
                    logger.warning(
                        f"GPT API 返回 {resp.status_code}: {resp.text[:200]}"
                    )
                    return self._fallback_result(
                        f"API 返回错误 (HTTP {resp.status_code})"
                    )

                data = resp.json()

            elapsed = time.time() - start_time

            # 解析响应
            choice = data.get("choices", [{}])[0]
            reply_text = choice.get("message", {}).get("content", "")

            if not reply_text:
                return self._fallback_result("GPT 返回空响应")

            # 尝试解析 JSON
            result = self._parse_gpt_response(reply_text)
            result["gpt_model"] = self.model
            result["gpt_latency"] = round(elapsed, 2)
            result["raw_response"] = reply_text[:500]

            usage = data.get("usage", {})
            result["tokens_used"] = {
                "prompt": usage.get("prompt_tokens", 0),
                "completion": usage.get("completion_tokens", 0),
                "total": usage.get("total_tokens", 0),
            }

            logger.info(
                f"GPT 事实核查完成 | verdict={result.get('verdict')} | "
                f"risk={result.get('risk_level')} | latency={elapsed:.1f}s | "
                f"tokens={result['tokens_used'].get('total', 0)}"
            )

            return result

        except httpx.TimeoutException:
            logger.warning(f"GPT API 超时 ({self.timeout}s)")
            return self._fallback_result("GPT API 请求超时")
        except Exception as e:
            logger.error(f"GPT 事实核查异常: {e}", exc_info=True)
            return self._fallback_result(f"GPT 服务异常: {str(e)}")

    def _build_user_message(
        self,
        content: str,
        context: Optional[str],
        detection_result: Optional[Dict[str, Any]],
    ) -> str:
        """构建发送给 GPT 的用户消息"""
        parts = []

        if context:
            parts.append(f"【视频上下文】\n{context}")

        parts.append(f"【待核查内容】\n{content[:2000]}")

        if detection_result:
            level = detection_result.get("level", "unknown")
            score = detection_result.get("score", 0)
            reasons = detection_result.get("reasons", [])
            parts.append(
                f"【AI 预检测结果】\n"
                f"风险等级: {level}\n"
                f"风险评分: {score:.2f}\n"
                f"风险因素: {'; '.join(reasons[:3]) if reasons else '无'}"
            )

        return "\n\n".join(parts)

    def _parse_gpt_response(self, text: str) -> Dict[str, Any]:
        """解析 GPT 返回的 JSON 响应"""
        # 尝试提取 JSON
        try:
            # 直接解析
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 尝试从 markdown code block 中提取
        import re
        json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass

        # 尝试找到第一个 { 到最后一个 }
        start = text.find("{")
        end = text.rfind("}")
        if start >= 0 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                pass

        # 解析失败，返回原始文本作为分析
        logger.warning("GPT 返回非 JSON 格式，使用原始文本")
        return {
            "verdict": "unverifiable",
            "confidence": 0.5,
            "risk_level": "warning",
            "summary": "AI 分析完成（非结构化结果）",
            "analysis": text[:500],
            "false_claims": [],
            "fact_points": [],
            "risk_factors": [],
            "safety_advice": ["建议谨慎对待该内容"],
            "related_scam_type": "未知",
        }

    def _fallback_result(self, reason: str) -> Dict[str, Any]:
        """降级结果"""
        return {
            "verdict": "unverifiable",
            "confidence": 0.0,
            "risk_level": "warning",
            "summary": f"事实核查暂不可用: {reason}",
            "analysis": "",
            "false_claims": [],
            "fact_points": [],
            "risk_factors": [],
            "safety_advice": ["建议谨慎对待该内容", "如遇可疑情况请咨询家人"],
            "related_scam_type": "未知",
            "gpt_model": self.model,
            "gpt_latency": 0,
            "fallback": True,
            "fallback_reason": reason,
        }


# 全局实例
_fact_checker: Optional[GPTFactChecker] = None


def get_fact_checker() -> GPTFactChecker:
    """获取 GPT 事实核查器单例"""
    global _fact_checker
    if _fact_checker is None:
        _fact_checker = GPTFactChecker()
    return _fact_checker


__all__ = ["GPTFactChecker", "get_fact_checker"]
