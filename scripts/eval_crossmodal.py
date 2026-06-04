"""
跨模态联合推理对照实验 (突破点1)

对比两种范式在"跨模态错位"诈骗上的检出能力:
  A. 平台式"单模态独立分析 + 简单融合": 把 OCR 文字与 ASR 语音合并成一段文本后整体判险
  B. FactSafe"意图导向联合推理": 分通道评估 + 语义散度 + 错位判定 (cross_modal_reason)

评测集: data/raw/crossmodal_mismatch_eval.json (由 gen_test_videos.py --eval-set 生成)
输出:   scripts/crossmodal_eval_results.json

用法:
  python scripts/eval_crossmodal.py
（会加载根目录 best_text_model.pt / simple_ai_model.joblib / elder_cognitive_model.pt，如存在）
"""

import os
import sys
import json
import asyncio

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

EVAL_PATH = os.path.join(ROOT, "data", "raw", "crossmodal_mismatch_eval.json")
OUT_PATH = os.path.join(ROOT, "scripts", "crossmodal_eval_results.json")
DANGER_THRESHOLD = 0.5


def find_model(name):
    p = os.path.join(ROOT, name)
    return p if os.path.exists(p) else None


async def run():
    from app.services.multimodal_detector import MultimodalDetector

    detector = MultimodalDetector(
        model_path=find_model("best_text_model.pt"),
        simple_model_path=find_model("simple_ai_model.joblib") or find_model("models/trained/simple_ai_model.joblib"),
        cognitive_model_path=find_model("elder_cognitive_model.pt"),
    )

    with open(EVAL_PATH, "r", encoding="utf-8") as f:
        samples = json.load(f)

    rows = []
    # 统计量
    base_correct = joint_correct = 0
    mismatch_total = base_mismatch_hit = joint_mismatch_hit = 0

    for s in samples:
        ocr, asr = s.get("ocr_text", ""), s.get("asr_text", "")
        expected_danger = s.get("expected_risk") == "danger"
        is_mismatch = s.get("label") == "mismatch"

        # A. 单模态独立 + 简单融合（合并文本整体判险）
        merged = f"{ocr}\n{asr}".strip()
        base = await detector.detect({"text": merged})
        base_danger = base.risk_score >= DANGER_THRESHOLD

        # B. 联合推理
        jr = await detector.cross_modal_reason(ocr, asr)
        joint_danger = (jr["joint_risk"] >= DANGER_THRESHOLD) or jr["mismatch"]

        base_correct += int(base_danger == expected_danger)
        joint_correct += int(joint_danger == expected_danger)
        if is_mismatch:
            mismatch_total += 1
            base_mismatch_hit += int(base_danger)
            joint_mismatch_hit += int(joint_danger)

        rows.append({
            "ocr": ocr[:40], "asr": asr[:40], "label": s.get("label"),
            "expected_danger": expected_danger,
            "baseline": {"risk": round(base.risk_score, 3), "danger": base_danger},
            "joint": {
                "visual_risk": jr["visual_risk"], "audio_risk": jr["audio_risk"],
                "divergence": jr["divergence"], "joint_risk": jr["joint_risk"],
                "mismatch": jr["mismatch"], "method": jr["method"], "danger": joint_danger,
            },
        })

    n = len(samples)
    summary = {
        "n_samples": n,
        "baseline_accuracy": round(base_correct / n, 4) if n else 0,
        "joint_accuracy": round(joint_correct / n, 4) if n else 0,
        "mismatch_total": mismatch_total,
        "baseline_mismatch_recall": round(base_mismatch_hit / mismatch_total, 4) if mismatch_total else 0,
        "joint_mismatch_recall": round(joint_mismatch_hit / mismatch_total, 4) if mismatch_total else 0,
        "method": rows[0]["joint"]["method"] if rows else "n/a",
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump({"summary": summary, "rows": rows}, f, ensure_ascii=False, indent=2)

    print("=" * 64)
    print("跨模态联合推理对照实验结果")
    print("-" * 64)
    print(f"样本数: {n} | 错位样本: {mismatch_total} | 散度方法: {summary['method']}")
    print(f"整体准确率   单模态融合={summary['baseline_accuracy']:.3f}  联合推理={summary['joint_accuracy']:.3f}")
    print(f"错位检出率   单模态融合={summary['baseline_mismatch_recall']:.3f}  联合推理={summary['joint_mismatch_recall']:.3f}")
    print(f"✅ 结果已保存: {OUT_PATH}")
    print("=" * 64)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(run())
