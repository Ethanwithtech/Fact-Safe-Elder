#!/usr/bin/env python3
"""
Fine-tune Whisper on public Cantonese ASR datasets from Hugging Face.

Default target:
  ming030890/cantonese_asr_eval_mdcc_long, an openly accessible Cantonese ASR parquet dataset on Hugging Face.

Why this script exists:
  - longmaodata/Cantonese-ASR is useful but gated and license-gated.
  - WenetSpeech-Yue is very large and mainly metadata/raw-link based.
  - Mozilla Common Voice Cantonese is useful, but recent HF Common Voice repos may require legacy loading scripts or external download flows.

Quick smoke train:
  python scripts/train_cantonese_asr_hf.py --base_model openai/whisper-tiny --max_train_samples 80 --max_eval_samples 20 --max_steps 20

Better fine-tune:
  python scripts/train_cantonese_asr_hf.py --base_model openai/whisper-small --max_train_samples 2000 --max_eval_samples 300 --max_steps 1000
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def check_deps() -> None:
    missing = []
    for pkg in ["datasets", "transformers", "evaluate", "torch", "librosa", "jiwer", "accelerate", "soundfile"]:
        try:
            __import__(pkg)
        except Exception:
            missing.append(pkg)
    if missing:
        raise SystemExit(
            "Missing dependencies: " + ", ".join(missing) + "\n"
            "Install with:\n"
            "  python3 -m pip install --user datasets evaluate librosa jiwer accelerate soundfile\n"
        )


@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: Any

    def __call__(self, features: List[Dict[str, Any]]) -> Dict[str, Any]:
        input_features = [{"input_features": feature["input_features"]} for feature in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")
        label_features = [{"input_ids": feature["labels"]} for feature in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)
        batch["labels"] = labels
        return batch


def pick_column(columns: List[str], candidates: List[str]) -> Optional[str]:
    for c in candidates:
        if c in columns:
            return c
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="ming030890/cantonese_asr_eval_mdcc_long")
    parser.add_argument("--config", default=None)
    parser.add_argument("--data_files", default="data/test-00000-of-00008.parquet")
    parser.add_argument("--train_split", default="train")
    parser.add_argument("--eval_split", default="validation")
    parser.add_argument("--base_model", default="openai/whisper-tiny")
    parser.add_argument("--output_dir", default="models/cantonese-whisper-tiny")
    parser.add_argument("--max_train_samples", type=int, default=200)
    parser.add_argument("--max_eval_samples", type=int, default=50)
    parser.add_argument("--max_steps", type=int, default=50)
    parser.add_argument("--batch_size", type=int, default=2)
    parser.add_argument("--learning_rate", type=float, default=1e-5)
    args = parser.parse_args()

    check_deps()

    import evaluate
    import torch
    from datasets import Audio, load_dataset
    from transformers import (
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
        WhisperForConditionalGeneration,
        WhisperProcessor,
    )

    print(f"Loading dataset: {args.dataset} / {args.config or 'default'}")
    load_kwargs = {}
    if args.data_files:
        load_kwargs["data_files"] = args.data_files
    if args.config:
        dataset = load_dataset(args.dataset, args.config, verification_mode="no_checks", **load_kwargs)
    else:
        dataset = load_dataset(args.dataset, verification_mode="no_checks", **load_kwargs)

    # If only one shard/split is loaded, split a small subset locally for smoke/fine-tuning.
    if args.train_split in dataset and args.eval_split in dataset:
        train = dataset[args.train_split]
        eval_ds = dataset[args.eval_split]
    else:
        base_split = dataset[args.train_split] if args.train_split in dataset else dataset[list(dataset.keys())[0]]
        needed = max(args.max_train_samples + args.max_eval_samples, 2)
        base_split = base_split.select(range(min(needed, len(base_split))))
        split = base_split.train_test_split(test_size=min(args.max_eval_samples, max(1, len(base_split) // 5)), seed=42)
        train = split["train"]
        eval_ds = split["test"]

    if args.max_train_samples > 0:
        train = train.select(range(min(args.max_train_samples, len(train))))
    if args.max_eval_samples > 0:
        eval_ds = eval_ds.select(range(min(args.max_eval_samples, len(eval_ds))))

    columns = list(train.column_names)
    audio_col = pick_column(columns, ["audio", "audio_path", "path", "file", "wav"])
    text_col = pick_column(columns, ["sentence", "text", "transcription", "transcript", "normalized_text"])
    if not audio_col or not text_col:
        raise RuntimeError(f"Cannot infer audio/text columns from: {columns}")

    # Decode manually with soundfile/librosa to avoid torchcodec/FFmpeg dylib issues on macOS.
    if audio_col != "audio":
        train = train.cast_column(audio_col, Audio(sampling_rate=16000, decode=False))
        eval_ds = eval_ds.cast_column(audio_col, Audio(sampling_rate=16000, decode=False))
    else:
        train = train.cast_column("audio", Audio(sampling_rate=16000, decode=False))
        eval_ds = eval_ds.cast_column("audio", Audio(sampling_rate=16000, decode=False))

    processor = WhisperProcessor.from_pretrained(args.base_model, language="Chinese", task="transcribe")
    model = WhisperForConditionalGeneration.from_pretrained(args.base_model)
    model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(language="Chinese", task="transcribe")
    model.config.suppress_tokens = []

    def prepare(batch: Dict[str, Any]) -> Dict[str, Any]:
        import io
        import librosa
        import numpy as np
        import soundfile as sf

        audio = batch[audio_col]
        if isinstance(audio, dict) and audio.get("bytes") is not None:
            array, sr = sf.read(io.BytesIO(audio["bytes"]), dtype="float32")
        elif isinstance(audio, dict) and audio.get("path"):
            array, sr = sf.read(audio["path"], dtype="float32")
        else:
            raise RuntimeError(f"Unsupported audio object: {type(audio)}")

        if getattr(array, "ndim", 1) > 1:
            array = np.mean(array, axis=1)
        if sr != 16000:
            array = librosa.resample(array, orig_sr=sr, target_sr=16000)
            sr = 16000

        batch["input_features"] = processor.feature_extractor(array, sampling_rate=sr).input_features[0]
        batch["labels"] = processor.tokenizer(str(batch[text_col])).input_ids
        return batch

    keep_cols = train.column_names
    train = train.map(prepare, remove_columns=keep_cols, num_proc=1)
    eval_ds = eval_ds.map(prepare, remove_columns=eval_ds.column_names, num_proc=1)

    data_collator = DataCollatorSpeechSeq2SeqWithPadding(processor=processor)
    wer_metric = evaluate.load("wer")

    def compute_metrics(pred):
        pred_ids = pred.predictions
        label_ids = pred.label_ids
        label_ids[label_ids == -100] = processor.tokenizer.pad_token_id
        pred_str = processor.tokenizer.batch_decode(pred_ids, skip_special_tokens=True)
        label_str = processor.tokenizer.batch_decode(label_ids, skip_special_tokens=True)
        return {"wer": 100 * wer_metric.compute(predictions=pred_str, references=label_str)}

    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=2,
        learning_rate=args.learning_rate,
        warmup_steps=min(20, max(1, args.max_steps // 10)),
        max_steps=args.max_steps,
        fp16=torch.cuda.is_available(),
        eval_strategy="steps",
        eval_steps=max(10, args.max_steps // 2),
        save_steps=max(10, args.max_steps // 2),
        logging_steps=5,
        predict_with_generate=True,
        generation_max_length=225,
        report_to=[],
        remove_unused_columns=False,
    )

    trainer = Seq2SeqTrainer(
        args=training_args,
        model=model,
        train_dataset=train,
        eval_dataset=eval_ds,
        data_collator=data_collator,
        compute_metrics=compute_metrics,
        tokenizer=processor.feature_extractor,
    )
    trainer.train()
    trainer.save_model(args.output_dir)
    processor.save_pretrained(args.output_dir)
    print(f"Saved Cantonese ASR model to {args.output_dir}")


if __name__ == "__main__":
    main()
