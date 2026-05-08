#!/usr/bin/env python3
"""
Fine-tune Whisper for Cantonese/Hong Kong short-video ASR.

Expected dataset CSV columns:
  audio_path,text

Example:
  python scripts/train_cantonese_asr.py \
    --train_csv data/cantonese_asr/train.csv \
    --eval_csv data/cantonese_asr/eval.csv \
    --base_model openai/whisper-small \
    --output_dir models/cantonese-whisper-small

Runtime note:
  The current backend supports mixed Mandarin+Cantonese prompting via ASR_LANGUAGE=mixed.
  Use this script when you have labelled Chinese/Cantonese clips and want a fine-tuned model artifact.
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass
from typing import Any, Dict, List


def _check_deps() -> None:
    missing: List[str] = []
    for pkg in ["datasets", "transformers", "evaluate", "torch", "librosa"]:
        try:
            __import__(pkg)
        except ImportError:
            missing.append(pkg)
    if missing:
        raise SystemExit(
            "Missing dependencies: " + ", ".join(missing) + "\n"
            "Install with: pip install datasets transformers evaluate torch librosa jiwer accelerate"
        )


@dataclass
class DataCollatorSpeechSeq2SeqWithPadding:
    processor: Any

    def __call__(self, features: List[Dict[str, Any]]) -> Dict[str, Any]:
        input_features = [{"input_features": f["input_features"]} for f in features]
        batch = self.processor.feature_extractor.pad(input_features, return_tensors="pt")
        label_features = [{"input_ids": f["labels"]} for f in features]
        labels_batch = self.processor.tokenizer.pad(label_features, return_tensors="pt")
        labels = labels_batch["input_ids"].masked_fill(labels_batch.attention_mask.ne(1), -100)
        batch["labels"] = labels
        return batch


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--train_csv", required=True)
    parser.add_argument("--eval_csv", required=True)
    parser.add_argument("--base_model", default="openai/whisper-small")
    parser.add_argument("--output_dir", default="models/cantonese-whisper-small")
    parser.add_argument("--max_steps", type=int, default=1000)
    parser.add_argument("--batch_size", type=int, default=4)
    parser.add_argument("--learning_rate", type=float, default=1e-5)
    args = parser.parse_args()

    _check_deps()

    import evaluate
    import torch
    from datasets import Audio, load_dataset
    from transformers import (
        Seq2SeqTrainer,
        Seq2SeqTrainingArguments,
        WhisperForConditionalGeneration,
        WhisperProcessor,
    )

    if not os.path.exists(args.train_csv):
        raise FileNotFoundError(args.train_csv)
    if not os.path.exists(args.eval_csv):
        raise FileNotFoundError(args.eval_csv)

    dataset = load_dataset("csv", data_files={"train": args.train_csv, "eval": args.eval_csv})
    dataset = dataset.cast_column("audio_path", Audio(sampling_rate=16000))

    processor = WhisperProcessor.from_pretrained(args.base_model, language="Chinese", task="transcribe")
    model = WhisperForConditionalGeneration.from_pretrained(args.base_model)
    model.config.forced_decoder_ids = processor.get_decoder_prompt_ids(language="Chinese", task="transcribe")
    model.config.suppress_tokens = []

    def prepare(batch: Dict[str, Any]) -> Dict[str, Any]:
        audio = batch["audio_path"]
        batch["input_features"] = processor.feature_extractor(
            audio["array"], sampling_rate=audio["sampling_rate"]
        ).input_features[0]
        batch["labels"] = processor.tokenizer(batch["text"]).input_ids
        return batch

    dataset = dataset.map(prepare, remove_columns=dataset["train"].column_names, num_proc=1)
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
        warmup_steps=100,
        max_steps=args.max_steps,
        fp16=torch.cuda.is_available(),
        evaluation_strategy="steps",
        eval_steps=200,
        save_steps=200,
        logging_steps=25,
        predict_with_generate=True,
        generation_max_length=225,
        report_to=[],
    )

    trainer = Seq2SeqTrainer(
        args=training_args,
        model=model,
        train_dataset=dataset["train"],
        eval_dataset=dataset["eval"],
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
