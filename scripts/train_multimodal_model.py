"""
Train (text-first) fake information detector using repo-local datasets under ./data/raw.

This script is designed for this project:
- Loads multiple datasets in ./data/raw (comprehensive_training_set, mcfend, weibo_rumors, real_cases, liar)
- Normalizes labels to 3 classes: safe(0), warning(1), danger(2)
- Stratified train/val/test split
- Strong Chinese encoder default: MacBERT (hfl/chinese-macbert-base)
- Handles class imbalance with weighted CE + label smoothing (prioritize recall for danger)

Run (quick sanity):
  python train_multimodal_model.py --epochs 1 --batch_size 8 --max_samples_per_source 2000 --device cpu

Run (better):
  python train_multimodal_model.py --epochs 5 --batch_size 16 --device cuda --fp16
"""

from __future__ import annotations

import argparse
import json
import os
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Dataset
    from torch.cuda.amp import GradScaler, autocast
    TORCH_AVAILABLE = True
except Exception:  # pragma: no cover
    TORCH_AVAILABLE = False

try:
    from transformers import AutoModel, AutoTokenizer, get_linear_schedule_with_warmup
    TRANSFORMERS_AVAILABLE = True
except Exception:  # pragma: no cover
    TRANSFORMERS_AVAILABLE = False

try:
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score
    SKLEARN_AVAILABLE = True
except Exception:  # pragma: no cover
    SKLEARN_AVAILABLE = False

try:
    from loguru import logger
except Exception:  # pragma: no cover
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger("train")

try:
    from tqdm import tqdm
except Exception:  # pragma: no cover
    def tqdm(x, **kwargs):
        return x


LABEL_SAFE = 0
LABEL_WARNING = 1
LABEL_DANGER = 2


def set_seed(seed: int = 42) -> None:
    random.seed(seed)
    np.random.seed(seed)
    if TORCH_AVAILABLE:
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)


def normalize_label(label: Any) -> Optional[int]:
    if label is None:
        return None
    if isinstance(label, int):
        return label if label in (0, 1, 2) else None
    if isinstance(label, str):
        s = label.strip().lower()
        if s in ("real", "true", "genuine", "safe", "normal"):
            return LABEL_SAFE
        if s in ("rumor", "fake", "false", "danger"):
            return LABEL_DANGER
        if s in ("warning", "uncertain", "unverified"):
            return LABEL_WARNING
        # LIAR
        if s in ("pants-fire", "pants on fire", "barely-true", "false"):
            return LABEL_DANGER
        if s in ("half-true",):
            return LABEL_WARNING
        if s in ("mostly-true", "true"):
            return LABEL_SAFE
    return None


def _load_json_array(path: str) -> List[Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_liar_tsv(path: str, limit: Optional[int] = None) -> List[Dict[str, Any]]:
    samples: List[Dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if limit is not None and len(samples) >= limit:
                break
            parts = line.rstrip("\n").split("\t")
            if len(parts) < 3:
                continue
            lab = normalize_label(parts[1])
            text = (parts[2] or "").strip()
            if lab is None or not text:
                continue
            samples.append({"text": text, "label": lab, "category": "liar"})
    return samples


def discover_data_paths(repo_root: str) -> Dict[str, str]:
    base = Path(repo_root) / "data" / "raw"
    candidates = {
        "comprehensive": base / "comprehensive_training_set.json",
        "mcfend": base / "mcfend" / "mcfend_data.json",
        "weibo": base / "weibo_rumors" / "weibo_data.json",
        "real_cases": base / "real_cases" / "real_case_dataset.json",
        "liar_train": base / "liar" / "train.tsv",
        "liar_valid": base / "liar" / "valid.tsv",
        "liar_test": base / "liar" / "test.tsv",
    }
    out: Dict[str, str] = {}
    for k, p in candidates.items():
        if p.exists():
            out[k] = str(p)
    return out


def build_samples(repo_root: str, max_samples_per_source: int = 0) -> List[Dict[str, Any]]:
    paths = discover_data_paths(repo_root)
    logger.info(f"data sources: {list(paths.keys())}")

    def limit_list(arr: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if max_samples_per_source and max_samples_per_source > 0:
            return arr[:max_samples_per_source]
        return arr

    samples: List[Dict[str, Any]] = []

    if "comprehensive" in paths:
        for item in limit_list(_load_json_array(paths["comprehensive"])):
            text = (item.get("text") or "").strip()
            lab = normalize_label(item.get("label"))
            if text and lab is not None:
                samples.append({"text": text, "label": lab, "category": item.get("category", "comprehensive")})

    if "mcfend" in paths:
        for item in limit_list(_load_json_array(paths["mcfend"])):
            text = (item.get("text") or "").strip()
            lab = normalize_label(item.get("label"))
            if text and lab is not None:
                samples.append({"text": text, "label": lab, "category": item.get("category", "mcfend")})

    if "weibo" in paths:
        for item in limit_list(_load_json_array(paths["weibo"])):
            text = (item.get("text") or item.get("content") or "").strip()
            lab = normalize_label(item.get("label"))
            if text and lab is not None:
                samples.append({"text": text, "label": lab, "category": item.get("category", "weibo")})

    if "real_cases" in paths:
        for item in limit_list(_load_json_array(paths["real_cases"])):
            text = (item.get("text") or "").strip()
            lab = normalize_label(item.get("label"))
            if text and lab is not None:
                samples.append({"text": text, "label": lab, "category": item.get("category", "real_cases")})

    liar_limit = max_samples_per_source if max_samples_per_source and max_samples_per_source > 0 else None
    for k in ("liar_train", "liar_valid", "liar_test"):
        if k in paths:
            samples.extend(_load_liar_tsv(paths[k], limit=liar_limit))

    # dedupe by text
    dedup: Dict[str, Dict[str, Any]] = {}
    for s in samples:
        if s["text"] not in dedup:
            dedup[s["text"]] = s
    samples = list(dedup.values())
    random.shuffle(samples)

    cnt = {0: 0, 1: 0, 2: 0}
    for s in samples:
        cnt[int(s["label"])] += 1
    logger.info(f"samples={len(samples)} | safe={cnt[0]} warning={cnt[1]} danger={cnt[2]}")
    return samples


class UnifiedTextDataset(Dataset):
    def __init__(self, samples: List[Dict[str, Any]], tokenizer, max_length: int):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        s = self.samples[idx]
        enc = self.tokenizer(
            s["text"],
            truncation=True,
            padding="max_length",
            max_length=self.max_length,
            return_tensors="pt",
        )
        return {
            "input_ids": enc["input_ids"].squeeze(0),
            "attention_mask": enc["attention_mask"].squeeze(0),
            "label": torch.tensor(int(s["label"]), dtype=torch.long),
        }


class TextClassifier(nn.Module):
    def __init__(self, model_name: str, num_labels: int, dropout: float):
        super().__init__()
        self.encoder = AutoModel.from_pretrained(model_name)
        hidden = self.encoder.config.hidden_size
        self.dropout = nn.Dropout(dropout)
        self.head = nn.Sequential(
            nn.Linear(hidden, hidden // 2),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden // 2, num_labels),
        )

    def forward(self, input_ids, attention_mask):
        out = self.encoder(input_ids=input_ids, attention_mask=attention_mask)
        cls = out.last_hidden_state[:, 0, :]
        cls = self.dropout(cls)
        return self.head(cls)


def compute_class_weights(labels: List[int]) -> torch.Tensor:
    # inverse freq, with extra emphasis on danger
    cnt = np.bincount(np.array(labels), minlength=3).astype(np.float32)
    cnt = np.maximum(cnt, 1.0)
    w = (cnt.sum() / cnt)
    w = w / w.mean()
    w[2] *= 1.2
    return torch.tensor(w, dtype=torch.float32)


@dataclass
class TrainConfig:
    model_name: str
    max_length: int
    epochs: int
    batch_size: int
    lr: float
    weight_decay: float
    warmup_ratio: float
    fp16: bool
    freeze_epochs: int
    max_samples_per_source: int
    output_dir: str
    device: str


def train(cfg: TrainConfig) -> None:
    if not TORCH_AVAILABLE or not TRANSFORMERS_AVAILABLE:
        raise RuntimeError("Missing torch/transformers")

    set_seed(42)
    device = torch.device("cuda" if (cfg.device == "auto" and torch.cuda.is_available()) else cfg.device)
    if cfg.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    repo_root = os.path.abspath(os.path.dirname(__file__))
    samples = build_samples(repo_root, max_samples_per_source=cfg.max_samples_per_source)
    if not samples:
        raise RuntimeError("No samples found under ./data/raw")

    y = [int(s["label"]) for s in samples]
    if SKLEARN_AVAILABLE:
        train_s, tmp_s = train_test_split(samples, test_size=0.2, random_state=42, stratify=y)
        tmp_y = [int(s["label"]) for s in tmp_s]
        val_s, test_s = train_test_split(tmp_s, test_size=0.5, random_state=42, stratify=tmp_y)
    else:
        random.shuffle(samples)
        n = len(samples)
        train_s, val_s, test_s = samples[: int(n * 0.8)], samples[int(n * 0.8): int(n * 0.9)], samples[int(n * 0.9):]

    tokenizer = AutoTokenizer.from_pretrained(cfg.model_name, use_fast=True)
    train_ds = UnifiedTextDataset(train_s, tokenizer, cfg.max_length)
    val_ds = UnifiedTextDataset(val_s, tokenizer, cfg.max_length)

    train_loader = DataLoader(train_ds, batch_size=cfg.batch_size, shuffle=True, num_workers=0)
    val_loader = DataLoader(val_ds, batch_size=cfg.batch_size * 2, shuffle=False, num_workers=0)

    model = TextClassifier(cfg.model_name, num_labels=3, dropout=cfg.dropout if hasattr(cfg, "dropout") else 0.3)  # type: ignore
    model.to(device)

    # freeze
    if cfg.freeze_epochs > 0:
        for p in model.encoder.parameters():
            p.requires_grad = False

    optimizer = optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=cfg.lr, weight_decay=cfg.weight_decay)
    total_steps = len(train_loader) * cfg.epochs
    warmup_steps = int(total_steps * cfg.warmup_ratio)
    scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    class_w = compute_class_weights([int(s["label"]) for s in train_s]).to(device)
    loss_fn = nn.CrossEntropyLoss(weight=class_w, label_smoothing=0.05)

    scaler = GradScaler() if (cfg.fp16 and device.type == "cuda") else None

    best_f1 = 0.0
    out_dir = Path(cfg.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "config.json").write_text(json.dumps(cfg.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")

    for epoch in range(cfg.epochs):
        model.train()
        if cfg.freeze_epochs > 0 and epoch == cfg.freeze_epochs:
            for p in model.encoder.parameters():
                p.requires_grad = True
            optimizer = optim.AdamW(model.parameters(), lr=cfg.lr * 0.5, weight_decay=cfg.weight_decay)
            scheduler = get_linear_schedule_with_warmup(optimizer, warmup_steps, total_steps)
            logger.info("encoder unfrozen")

        total_loss = 0.0
        for batch in tqdm(train_loader, desc=f"train epoch {epoch+1}/{cfg.epochs}"):
            input_ids = batch["input_ids"].to(device)
            attention_mask = batch["attention_mask"].to(device)
            labels = batch["label"].to(device)
            optimizer.zero_grad()
            if scaler is not None:
                with autocast():
                    logits = model(input_ids, attention_mask)
                    loss = loss_fn(logits, labels)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                logits = model(input_ids, attention_mask)
                loss = loss_fn(logits, labels)
                loss.backward()
                optimizer.step()
            scheduler.step()
            total_loss += float(loss.item())

        # eval
        model.eval()
        preds: List[int] = []
        gts: List[int] = []
        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                attention_mask = batch["attention_mask"].to(device)
                labels = batch["label"].to(device)
                logits = model(input_ids, attention_mask)
                pred = torch.argmax(logits, dim=-1)
                preds.extend(pred.cpu().tolist())
                gts.extend(labels.cpu().tolist())

        if SKLEARN_AVAILABLE:
            acc = accuracy_score(gts, preds)
            f1 = f1_score(gts, preds, average="macro")
            p = precision_score(gts, preds, average="macro", zero_division=0)
            r = recall_score(gts, preds, average="macro", zero_division=0)
        else:
            acc = sum(int(a == b) for a, b in zip(gts, preds)) / max(1, len(gts))
            f1 = acc
            p = acc
            r = acc

        logger.info(f"epoch={epoch+1} loss={total_loss/len(train_loader):.4f} val_acc={acc:.4f} val_f1={f1:.4f} val_p={p:.4f} val_r={r:.4f}")

        if f1 > best_f1:
            best_f1 = f1
            torch.save({"model_state_dict": model.state_dict(), "best_f1": best_f1}, out_dir / "best_text_model.pt")

    logger.info(f"done. best_f1={best_f1:.4f} saved to {out_dir/'best_text_model.pt'}")


def parse_args() -> TrainConfig:
    ap = argparse.ArgumentParser(description="Train text-first detector (repo ./data/raw)")
    ap.add_argument("--model_name", type=str, default="hfl/chinese-macbert-base")
    ap.add_argument("--max_length", type=int, default=256)
    ap.add_argument("--epochs", type=int, default=5)
    ap.add_argument("--batch_size", type=int, default=16)
    ap.add_argument("--learning_rate", type=float, default=2e-5)
    ap.add_argument("--weight_decay", type=float, default=0.01)
    ap.add_argument("--warmup_ratio", type=float, default=0.1)
    ap.add_argument("--fp16", action="store_true")
    ap.add_argument("--freeze_epochs", type=int, default=1)
    ap.add_argument("--max_samples_per_source", type=int, default=0)
    ap.add_argument("--output_dir", type=str, default="./models")
    ap.add_argument("--device", type=str, default="auto", choices=["auto", "cpu", "cuda"])
    args = ap.parse_args()
    return TrainConfig(
        model_name=args.model_name,
        max_length=args.max_length,
        epochs=args.epochs,
        batch_size=args.batch_size,
        lr=args.learning_rate,
        weight_decay=args.weight_decay,
        warmup_ratio=args.warmup_ratio,
        fp16=bool(args.fp16),
        freeze_epochs=int(args.freeze_epochs),
        max_samples_per_source=int(args.max_samples_per_source),
        output_dir=args.output_dir,
        device=args.device,
    )


if __name__ == "__main__":
    cfg = parse_args()
    train(cfg)

 