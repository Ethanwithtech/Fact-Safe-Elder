"""
一键检查并补齐 FactSafe 后端所需的全部本地模型权重。

目标文件（项目根目录，.gitignore 已忽略）:
  - best_text_model.pt          MacBERT 三分类 (~391MB)
  - simple_ai_model.joblib      TF-IDF + 集成分类器
  - elder_cognitive_model.pt    认知特征多任务模型 (~391MB)

用法:
  python scripts/bootstrap_all_models.py              # 仅训练缺失项
  python scripts/bootstrap_all_models.py --train-all  # 全部重训（耗时）
  python scripts/bootstrap_all_models.py --status-only

PowerShell 建议（避免把 stderr 警告当成错误）:
  $env:PYTHONWARNINGS="ignore"; python -u scripts/bootstrap_all_models.py
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

MODELS = {
    "best_text_model.pt": "MacBERT 文本三分类",
    "simple_ai_model.joblib": "TF-IDF 集成分类器",
    "elder_cognitive_model.pt": "老年人认知多任务模型",
}


def status() -> dict[str, bool]:
    return {name: (ROOT / name).is_file() for name in MODELS}


def print_status() -> None:
    print("=" * 60)
    print("FactSafe 本地模型状态")
    print("=" * 60)
    for name, desc in MODELS.items():
        p = ROOT / name
        if p.is_file():
            mb = p.stat().st_size / 1024 / 1024
            print(f"  ✅ {name:<28} {mb:6.1f} MB  — {desc}")
        else:
            print(f"  ❌ {name:<28} 缺失     — {desc}")
    print("=" * 60)


def train_simple() -> None:
    """从 elder_scam_labeled.json 快速训练 TF-IDF 模型并保存到根目录。"""
    import joblib
    import jieba
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    from sklearn.ensemble import VotingClassifier
    from sklearn.svm import LinearSVC
    from sklearn.calibration import CalibratedClassifierCV
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, f1_score

    jieba.setLogLevel(jieba.logging.WARNING)

    data_path = ROOT / "data" / "raw" / "elder_scam_labeled.json"
    if not data_path.is_file():
        raise FileNotFoundError(f"缺少标注数据: {data_path}")

    with open(data_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    texts, labels = [], []
    for item in data:
        t = (item.get("text") or "").strip()
        if not t:
            continue
        texts.append(t)
        labels.append(1 if int(item.get("label", 0)) >= 1 else 0)

    def tok(s: str) -> str:
        return " ".join(jieba.lcut(s))

    X = [tok(t) for t in texts]
    y = labels
    X_tr, X_va, y_tr, y_va = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)

    vectorizer = TfidfVectorizer(max_features=8000, ngram_range=(1, 2), min_df=2)
    X_tr_v = vectorizer.fit_transform(X_tr)
    X_va_v = vectorizer.transform(X_va)

    svm = CalibratedClassifierCV(LinearSVC(max_iter=3000), cv=3)
    lr = LogisticRegression(max_iter=500, class_weight="balanced")
    ensemble = VotingClassifier(
        estimators=[("svm", svm), ("lr", lr)],
        voting="soft",
    )
    ensemble.fit(X_tr_v, y_tr)
    pred = ensemble.predict(X_va_v)
    acc = accuracy_score(y_va, pred)
    f1 = f1_score(y_va, pred, zero_division=0)
    print(f"  simple 验证 acc={acc:.3f} f1={f1:.3f} (n={len(texts)})")

    out = ROOT / "simple_ai_model.joblib"
    joblib.dump(
        {
            "model": ensemble,
            "vectorizer": vectorizer,
            "version": "bootstrap_v1",
            "training_data_size": len(texts),
            "tokenizer": "jieba",
            "needs_jieba_tokenize": True,
            "metrics": {"accuracy": round(acc, 4), "f1_score": round(f1, 4)},
        },
        out,
    )
    print(f"  ✅ 已保存 {out}")


def train_cognitive(epochs: int, batch_size: int) -> None:
    import subprocess

    cmd = [
        sys.executable,
        "-u",
        str(ROOT / "scripts" / "train_elder_cognitive_model.py"),
        "--epochs",
        str(epochs),
        "--batch_size",
        str(batch_size),
    ]
    subprocess.check_call(cmd, cwd=str(ROOT))


def train_bert(epochs: int, batch_size: int) -> None:
    import subprocess

    cmd = [
        sys.executable,
        "-u",
        str(ROOT / "scripts" / "train_multimodal_model.py"),
        "--epochs",
        str(epochs),
        "--batch_size",
        str(batch_size),
        "--output_dir",
        str(ROOT),
        "--device",
        "cpu",
        "--max_samples_per_source",
        "5000",
    ]
    subprocess.check_call(cmd, cwd=str(ROOT))
    # train_multimodal 默认写到 ./models，复制到根目录
    src = ROOT / "models" / "best_text_model.pt"
    dst = ROOT / "best_text_model.pt"
    if src.is_file() and not dst.is_file():
        import shutil
        shutil.copy2(src, dst)


def main() -> None:
    warnings.filterwarnings("ignore", category=FutureWarning)
    ap = argparse.ArgumentParser()
    ap.add_argument("--status-only", action="store_true")
    ap.add_argument("--train-all", action="store_true", help="重训全部（很慢）")
    ap.add_argument("--cognitive-epochs", type=int, default=4)
    ap.add_argument("--bert-epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=16)
    args = ap.parse_args()

    print_status()
    if args.status_only:
        return

    st = status()
    if args.train_all or not st["simple_ai_model.joblib"]:
        print("\n[1/3] 训练 TF-IDF 模型 (simple_ai_model.joblib)...")
        train_simple()

    if args.train_all or not st["elder_cognitive_model.pt"]:
        print("\n[2/3] 训练认知多任务模型 (elder_cognitive_model.pt)...")
        train_cognitive(args.cognitive_epochs, args.batch_size)
    else:
        print("\n[2/3] 认知模型已存在，跳过")

    if args.train_all or not st["best_text_model.pt"]:
        print("\n[3/3] 训练 MacBERT 文本模型 (best_text_model.pt)...")
        train_bert(args.bert_epochs, args.batch_size)
    else:
        print("\n[3/3] MacBERT 模型已存在，跳过")

    print("\n完成。最终状态:")
    print_status()
    missing = [k for k, v in status().items() if not v]
    if missing:
        sys.exit(1)


if __name__ == "__main__":
    main()
