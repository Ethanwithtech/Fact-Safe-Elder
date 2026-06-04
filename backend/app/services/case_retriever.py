"""
真实诈骗案例库语义检索 (突破点4: 证据链可解释)

平台给老人的提示通常只有"该内容可能有风险"，无法回答"为什么"和"别人是怎么被骗的"。
本模块把检测到的内容关联到结构化的真实诈骗案例库，输出可解释证据：
  "这类套路已有 X 位老人被骗，平均损失 Y 元，来源：官方通报"。

检索策略（自适应、无强依赖）:
  1. 优先 scikit-learn TF-IDF 字符 n-gram 余弦相似度（中文无需分词即可工作）
  2. 退化为关键词/字符重叠打分

可选: 传入一个 embed_fn(text)->vector 即可升级为 BERT 句向量语义检索。
"""

import os
import json
import math
from typing import Dict, List, Any, Optional, Callable

from loguru import logger

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

# 手法分类法（用于把案例手法展开成中文说明）
try:
    from app.core.manipulation_taxonomy import describe_features
except ImportError:
    try:
        from core.manipulation_taxonomy import describe_features
    except ImportError:
        def describe_features(keys, lang="zh"):
            return []


def _default_library_path() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    # backend/app/services -> 项目根/data/raw/scam_case_library.json
    root = os.path.abspath(os.path.join(here, "..", "..", ".."))
    return os.path.join(root, "data", "raw", "scam_case_library.json")


class CaseRetriever:
    """诈骗案例库语义检索器"""

    def __init__(self, library_path: Optional[str] = None,
                 embed_fn: Optional[Callable[[str], Any]] = None):
        self.library_path = library_path or _default_library_path()
        self.embed_fn = embed_fn
        self.cases: List[Dict[str, Any]] = []
        self._docs: List[str] = []
        self._vectorizer = None
        self._matrix = None
        self._load()

    def _case_doc(self, case: Dict[str, Any]) -> str:
        kw = " ".join(case.get("keywords", []))
        return f"{case.get('title','')} {kw} {case.get('typical_scripts','')}"

    def _load(self):
        try:
            with open(self.library_path, "r", encoding="utf-8") as f:
                self.cases = json.load(f)
        except Exception as e:
            logger.warning(f"案例库加载失败: {e}")
            self.cases = []
            return

        self._docs = [self._case_doc(c) for c in self.cases]

        if SKLEARN_AVAILABLE and self._docs:
            try:
                # 字符级 2-3 gram，对中文友好，无需分词
                self._vectorizer = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 3))
                self._matrix = self._vectorizer.fit_transform(self._docs)
                logger.info(f"✅ 案例检索器就绪 | {len(self.cases)} 个案例 | TF-IDF(char n-gram)")
            except Exception as e:
                logger.warning(f"TF-IDF 初始化失败，退化关键词检索: {e}")
                self._vectorizer = None
        else:
            logger.info(f"✅ 案例检索器就绪 | {len(self.cases)} 个案例 | 关键词检索(无 sklearn)")

    def _keyword_score(self, query: str, case: Dict[str, Any]) -> float:
        """关键词/字符重叠打分兜底。"""
        q = query.lower()
        kws = case.get("keywords", [])
        if not kws:
            return 0.0
        hit = sum(1 for kw in kws if kw.lower() in q)
        # 命中关键词比例 + 一点字符重叠
        kw_ratio = hit / max(len(kws), 1)
        qs, ds = set(q), set(self._case_doc(case).lower())
        char_overlap = len(qs & ds) / max(len(qs | ds), 1)
        return min(1.0, 0.7 * kw_ratio + 0.3 * char_overlap)

    def retrieve(self, text: str, top_k: int = 3, min_score: float = 0.06) -> List[Dict[str, Any]]:
        """
        返回与文本最相似的诈骗案例（已含相似度/受害人数/平均损失）。
        """
        text = (text or "").strip()
        if not text or not self.cases:
            return []

        scored: List[tuple] = []

        # 1) embedding 语义检索（若提供 embed_fn）
        if self.embed_fn is not None:
            try:
                import numpy as np
                qv = np.asarray(self.embed_fn(text), dtype=float)
                for i, doc in enumerate(self._docs):
                    dv = np.asarray(self.embed_fn(doc), dtype=float)
                    denom = (np.linalg.norm(qv) * np.linalg.norm(dv)) or 1.0
                    scored.append((i, float(np.dot(qv, dv) / denom)))
            except Exception as e:
                logger.debug(f"embedding 检索失败，回退 TF-IDF: {e}")
                scored = []

        # 2) TF-IDF 余弦
        if not scored and self._vectorizer is not None and self._matrix is not None:
            try:
                qv = self._vectorizer.transform([text])
                sims = cosine_similarity(qv, self._matrix)[0]
                scored = list(enumerate(sims.tolist()))
            except Exception as e:
                logger.debug(f"TF-IDF 检索失败，回退关键词: {e}")
                scored = []

        # 3) 关键词兜底
        if not scored:
            scored = [(i, self._keyword_score(text, c)) for i, c in enumerate(self.cases)]

        scored.sort(key=lambda x: x[1], reverse=True)
        out: List[Dict[str, Any]] = []
        for idx, sim in scored[:top_k]:
            if sim < min_score:
                continue
            c = self.cases[idx]
            out.append({
                "case_id": c.get("case_id"),
                "title": c.get("title"),
                "category": c.get("category"),
                "similarity": round(float(sim), 4),
                "victims": c.get("victims"),
                "avg_loss": c.get("avg_loss"),
                "source": c.get("source"),
                "manipulation_features": c.get("manipulation_features", []),
                "typical_scripts": c.get("typical_scripts", ""),
            })
        return out

    def build_evidence_chain(
        self,
        text: str,
        manipulation_features: Optional[List[str]] = None,
        gpt_fact_check: Optional[Dict[str, Any]] = None,
        top_k: int = 3,
    ) -> Dict[str, Any]:
        """
        统一"证据链报告": 手法标注 + (可选)GPT 声明纠正 + 关联真实案例。
        """
        cases = self.retrieve(text, top_k=top_k)
        techniques = describe_features(manipulation_features or [], lang="zh")

        claims = []
        if gpt_fact_check and isinstance(gpt_fact_check, dict):
            claims = gpt_fact_check.get("false_claims", []) or []

        # 生成一句话证据摘要
        summary_parts = []
        if techniques:
            summary_parts.append("识别到诈骗手法：" + "、".join(t["name"] for t in techniques))
        if cases:
            top = cases[0]
            if top.get("victims") and top.get("avg_loss"):
                summary_parts.append(
                    f"与「{top['title']}」高度相似，此类已有约 {top['victims']:,} 位老人受骗，"
                    f"平均损失 {top['avg_loss']:,} 元"
                )
            else:
                summary_parts.append(f"与真实案例「{top['title']}」相似")

        return {
            "techniques": techniques,
            "claims": claims,
            "cases": cases,
            "summary": "；".join(summary_parts),
        }


# 单例
_retriever: Optional[CaseRetriever] = None


def get_case_retriever(embed_fn: Optional[Callable[[str], Any]] = None) -> CaseRetriever:
    global _retriever
    if _retriever is None:
        _retriever = CaseRetriever(embed_fn=embed_fn)
    return _retriever


__all__ = ["CaseRetriever", "get_case_retriever"]
