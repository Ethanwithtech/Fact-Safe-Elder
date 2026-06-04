"""
训练"老年人认知特征"多任务模型 (突破点2)

多任务学习:
  - 任务A 风险三分类:  safe / warning / danger      (CrossEntropy)
  - 任务B 操控手法多标签: 情感操控/权威伪造/利益诱导/紧迫感/AI合成 (BCEWithLogits)

输入: data/raw/elder_scam_labeled.json (由 build_elder_cognitive_dataset.py 生成)
输出: elder_cognitive_model.pt (项目根目录, 后端 lifespan 会自动发现并加载)

用法:
  pip install torch transformers scikit-learn
  python scripts/train_elder_cognitive_model.py --epochs 6 --batch_size 8

无 GPU 也可运行（小数据集 + MacBERT，CPU 上数分钟）。
模型结构与 backend/app/services/multimodal_detector.py 的 ElderCognitiveClassifier 完全一致，
保证训练与推理对齐（直接复用同一个类，避免架构漂移）。
"""

import os
import sys
import json
import argparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))

from app.core.manipulation_taxonomy import FEATURE_KEYS, feature_to_multihot  # noqa: E402

DATA_PATH = os.path.join(ROOT, "data", "raw", "elder_scam_labeled.json")
DEFAULT_OUT = os.path.join(ROOT, "elder_cognitive_model.pt")
MODEL_NAME = os.environ.get("COGNITIVE_BASE_MODEL", "hfl/chinese-macbert-base")


def load_dataset():
    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    texts, risk_labels, manip_targets = [], [], []
    for d in data:
        text = (d.get("text") or "").strip()
        if not text:
            continue
        texts.append(text)
        risk_labels.append(int(d.get("label", 0)))
        manip_targets.append(feature_to_multihot(d.get("manipulation_features", [])))
    return texts, risk_labels, manip_targets


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=8)
    parser.add_argument("--batch_size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=2e-5)
    parser.add_argument("--max_len", type=int, default=96)
    parser.add_argument("--manip_weight", type=float, default=1.0, help="多标签损失权重")
    parser.add_argument("--output", type=str, default=DEFAULT_OUT)
    parser.add_argument("--threshold", type=float, default=0.4)
    args = parser.parse_args()

    try:
        import torch
        import torch.nn as nn
        from torch.utils.data import DataLoader, Dataset
        from transformers import AutoTokenizer
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import f1_score, accuracy_score
    except ImportError as e:
        print(f"❌ 缺少依赖: {e}\n   请先: pip install torch transformers scikit-learn")
        sys.exit(1)

    from app.services.multimodal_detector import ElderCognitiveClassifier

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"设备: {device} | 基座模型: {MODEL_NAME}")

    texts, risk_labels, manip_targets = load_dataset()
    print(f"数据集: {len(texts)} 条 | 手法标签维度: {len(FEATURE_KEYS)} {FEATURE_KEYS}")

    # 分层切分（数据少时尽量分层，失败则随机）
    idx = list(range(len(texts)))
    try:
        tr_idx, va_idx = train_test_split(idx, test_size=0.2, random_state=42, stratify=risk_labels)
    except ValueError:
        tr_idx, va_idx = train_test_split(idx, test_size=0.2, random_state=42)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    class DS(Dataset):
        def __init__(self, indices):
            self.indices = indices

        def __len__(self):
            return len(self.indices)

        def __getitem__(self, i):
            j = self.indices[i]
            enc = tokenizer(texts[j], max_length=args.max_len, truncation=True,
                            padding="max_length", return_tensors="pt")
            return {
                "input_ids": enc["input_ids"].squeeze(0),
                "attention_mask": enc["attention_mask"].squeeze(0),
                "token_type_ids": enc.get("token_type_ids", enc["attention_mask"]).squeeze(0),
                "risk": torch.tensor(risk_labels[j], dtype=torch.long),
                "manip": torch.tensor(manip_targets[j], dtype=torch.float),
            }

    train_loader = DataLoader(DS(tr_idx), batch_size=args.batch_size, shuffle=True)
    val_loader = DataLoader(DS(va_idx), batch_size=args.batch_size)

    model = ElderCognitiveClassifier(
        model_name=MODEL_NAME, num_risk=3, num_features=len(FEATURE_KEYS), dropout=0.3
    ).to(device)

    # 类别不平衡时给风险类加权
    from collections import Counter
    risk_counts = Counter(risk_labels[j] for j in tr_idx)
    weights = torch.tensor(
        [1.0 / max(risk_counts.get(c, 1), 1) for c in range(3)], dtype=torch.float
    ).to(device)
    weights = weights / weights.sum() * 3
    ce_loss = nn.CrossEntropyLoss(weight=weights)

    # 多标签正样本权重（缓解每个手法标签的正负不平衡）
    pos = torch.zeros(len(FEATURE_KEYS))
    for j in tr_idx:
        pos += torch.tensor(manip_targets[j], dtype=torch.float)
    n_tr = max(len(tr_idx), 1)
    neg = n_tr - pos
    pos_weight = (neg / pos.clamp(min=1)).clamp(max=10.0).to(device)
    bce_loss = nn.BCEWithLogitsLoss(pos_weight=pos_weight)
    optim = torch.optim.AdamW(model.parameters(), lr=args.lr)

    best_score = -1.0
    best_state = None

    for epoch in range(1, args.epochs + 1):
        model.train()
        total = 0.0
        for batch in train_loader:
            optim.zero_grad()
            risk_logits, manip_logits = model(
                batch["input_ids"].to(device),
                batch["attention_mask"].to(device),
                batch["token_type_ids"].to(device),
            )
            loss = ce_loss(risk_logits, batch["risk"].to(device)) \
                + args.manip_weight * bce_loss(manip_logits, batch["manip"].to(device))
            loss.backward()
            optim.step()
            total += loss.item()

        # 验证
        model.eval()
        risk_pred, risk_true, manip_pred, manip_true = [], [], [], []
        with torch.no_grad():
            for batch in val_loader:
                rl, ml = model(
                    batch["input_ids"].to(device),
                    batch["attention_mask"].to(device),
                    batch["token_type_ids"].to(device),
                )
                risk_pred += rl.argmax(-1).cpu().tolist()
                risk_true += batch["risk"].tolist()
                manip_pred += (torch.sigmoid(ml).cpu() >= args.threshold).int().tolist()
                manip_true += batch["manip"].int().tolist()

        risk_acc = accuracy_score(risk_true, risk_pred) if risk_true else 0.0
        risk_f1 = f1_score(risk_true, risk_pred, average="macro", zero_division=0) if risk_true else 0.0
        manip_f1 = f1_score(manip_true, manip_pred, average="micro", zero_division=0) if manip_true else 0.0
        combined = (risk_f1 + manip_f1) / 2
        print(f"Epoch {epoch}/{args.epochs} | loss={total/max(len(train_loader),1):.4f} "
              f"| risk_acc={risk_acc:.3f} risk_F1={risk_f1:.3f} manip_microF1={manip_f1:.3f}")

        if combined > best_score:
            best_score = combined
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            best_metrics = {
                "risk_accuracy": round(risk_acc, 4),
                "risk_macro_f1": round(risk_f1, 4),
                "manip_micro_f1": round(manip_f1, 4),
            }

    torch.save({
        "model_state_dict": best_state or model.state_dict(),
        "model_name": MODEL_NAME,
        "num_risk": 3,
        "num_features": len(FEATURE_KEYS),
        "feature_keys": FEATURE_KEYS,
        "manip_threshold": args.threshold,
        "metrics": best_metrics if best_state else {},
    }, args.output)
    print("=" * 60)
    print(f"✅ 认知特征多任务模型已保存: {args.output}")
    print(f"   最优指标: {best_metrics if best_state else 'N/A'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
