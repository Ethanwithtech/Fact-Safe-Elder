#!/usr/bin/env python3
"""
Mixed Mandarin + Cantonese Whisper fine-tuning entrypoint.

This wraps train_cantonese_asr_hf.py and documents the intended mixed-language policy:
- Use a Cantonese ASR dataset for Hong Kong Cantonese coverage.
- Add Mandarin / simplified Chinese ASR data when available.
- Keep Whisper decoding language as Chinese (zh), not a Cantonese-only decoder.

Current runnable default uses the open Cantonese parquet shard for a small smoke run.
For a stronger mixed model, prepare a CSV with both Mandarin and Cantonese samples:
  audio_path,text,lang
  /path/mandarin_001.wav,保证收益无风险加微信,zh
  /path/yue_001.wav,保證回報冇風險加我WhatsApp,yue
Then run scripts/train_cantonese_asr.py against that CSV split.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "train_cantonese_asr_hf.py"),
        "--base_model", "openai/whisper-tiny",
        "--max_train_samples", "80",
        "--max_eval_samples", "20",
        "--max_steps", "20",
        "--batch_size", "1",
        "--output_dir", str(ROOT / "models" / "mixed-zh-yue-whisper-tiny-smoke"),
    ]
    print("Running mixed zh/yue smoke training:")
    print(" ".join(cmd))
    return subprocess.call(cmd, cwd=str(ROOT))


if __name__ == "__main__":
    raise SystemExit(main())
