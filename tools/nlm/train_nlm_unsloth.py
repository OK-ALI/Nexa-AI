"""Train NLM with Unsloth QLoRA.

This script is the handoff point from NEXA dataset generation to actual model
fine-tuning. It intentionally imports Unsloth and training libraries inside
main() so normal repo checks can run without a GPU training environment.
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = REPO_ROOT / "datasets" / "nlm_v1" / "nlm_v1_prototype.jsonl"
DEFAULT_OUTPUT = REPO_ROOT / "models" / "nlm_v1_lora"


def log_step(message: str) -> None:
    timestamp = time.strftime("%H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fine-tune NEXA NLM with Unsloth QLoRA.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--base-model", default="unsloth/Llama-3.1-8B-Instruct")
    parser.add_argument(
        "--adapter-model",
        type=Path,
        help="Optional saved LoRA adapter directory to continue training from.",
    )
    parser.add_argument("--max-seq-length", type=int, default=4096)
    parser.add_argument("--load-in-4bit", action="store_true", default=True)
    parser.add_argument("--lora-r", type=int, default=16)
    parser.add_argument("--lora-alpha", type=int, default=16)
    parser.add_argument("--lora-dropout", type=float, default=0.0)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--epochs", type=float, default=1.0)
    parser.add_argument("--batch-size", type=int, default=2)
    parser.add_argument("--grad-accum", type=int, default=4)
    parser.add_argument("--warmup-steps", type=int, default=20)
    parser.add_argument("--logging-steps", type=int, default=10)
    parser.add_argument("--save-steps", type=int, default=200)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--save-gguf", action="store_true")
    parser.add_argument("--gguf-dir", type=Path, default=REPO_ROOT / "models" / "nlm_v1_gguf")
    parser.add_argument("--gguf-quantization", default="q4_k_m")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.dataset.exists():
        raise SystemExit(f"Dataset not found: {args.dataset}")
    if args.adapter_model and not args.adapter_model.exists():
        raise SystemExit(f"Adapter model not found: {args.adapter_model}")
    if args.adapter_model and args.output_dir.resolve() == args.adapter_model.resolve():
        raise SystemExit("Refusing to overwrite --adapter-model. Choose a different --output-dir.")

    log_step(f"Python: {sys.executable}")
    log_step(f"Dataset: {args.dataset}")
    log_step(f"Output dir: {args.output_dir}")
    log_step(f"Base model: {args.base_model}")
    if args.adapter_model:
        log_step(f"Continuing from adapter: {args.adapter_model}")
    log_step("Importing Unsloth and training libraries...")
    try:
        from unsloth import FastLanguageModel, is_bfloat16_supported
        from datasets import load_dataset
        from transformers import TrainingArguments
        from trl import SFTTrainer
    except ImportError as exc:
        raise SystemExit(
            "Missing training dependency. Install the Unsloth training environment "
            "before running this script. Original error: "
            f"{exc}"
        ) from exc

    model_name = str(args.adapter_model) if args.adapter_model else args.base_model
    if args.adapter_model:
        log_step("Loading saved LoRA adapter and tokenizer for continued training...")
    else:
        log_step("Loading base model and tokenizer. First run may download several GB...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=args.max_seq_length,
        load_in_4bit=args.load_in_4bit,
    )

    if args.adapter_model:
        log_step("Using existing LoRA adapters from --adapter-model.")
    else:
        log_step("Applying LoRA adapters...")
        model = FastLanguageModel.get_peft_model(
            model,
            r=args.lora_r,
            target_modules=[
                "q_proj",
                "k_proj",
                "v_proj",
                "o_proj",
                "gate_proj",
                "up_proj",
                "down_proj",
            ],
            lora_alpha=args.lora_alpha,
            lora_dropout=args.lora_dropout,
            bias="none",
            use_gradient_checkpointing="unsloth",
            random_state=args.seed,
        )

    log_step("Loading JSONL dataset...")
    dataset = load_dataset("json", data_files=str(args.dataset), split="train")

    def format_chat(batch):
        texts = [
            tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=False)
            for messages in batch["messages"]
        ]
        return {"text": texts}

    log_step("Formatting chat examples with tokenizer chat template...")
    dataset = dataset.map(format_chat, batched=True, remove_columns=dataset.column_names)

    log_step("Preparing training arguments...")
    training_args = TrainingArguments(
        output_dir=str(args.output_dir),
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        warmup_steps=args.warmup_steps,
        num_train_epochs=args.epochs,
        learning_rate=args.learning_rate,
        logging_steps=args.logging_steps,
        save_steps=args.save_steps,
        optim="adamw_8bit",
        weight_decay=0.01,
        lr_scheduler_type="linear",
        seed=args.seed,
        report_to="none",
        fp16=not is_bfloat16_supported(),
        bf16=is_bfloat16_supported(),
        dataloader_num_workers=0,
        save_total_limit=2,
    )

    log_step("Creating SFTTrainer...")
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=args.max_seq_length,
        dataset_num_proc=1,
        args=training_args,
        packing=False,
    )

    log_step("Starting training...")
    trainer.train()
    log_step("Saving LoRA adapter and tokenizer...")
    model.save_pretrained(str(args.output_dir))
    tokenizer.save_pretrained(str(args.output_dir))
    log_step(f"Saved LoRA adapter to {args.output_dir}")

    if args.save_gguf:
        log_step("Saving GGUF export...")
        args.gguf_dir.mkdir(parents=True, exist_ok=True)
        model.save_pretrained_gguf(
            str(args.gguf_dir),
            tokenizer,
            quantization_method=args.gguf_quantization,
        )
        log_step(f"Saved GGUF export to {args.gguf_dir}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
