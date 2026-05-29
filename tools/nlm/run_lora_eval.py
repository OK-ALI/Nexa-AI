"""Run the NLM eval seed through a trained Unsloth LoRA adapter."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.nlm.build_nlm_eval_set import DEFAULT_OUTPUT


DEFAULT_ADAPTER = REPO_ROOT / "models" / "nlm_v1_lora"
DEFAULT_PREDICTIONS = REPO_ROOT / "datasets" / "nlm_v1" / "prototype_lora_predictions.jsonl"


def _prompt_from_case(tokenizer: Any, case: dict[str, Any]) -> str:
    messages = case["messages"] + [
        {
            "role": "assistant",
            "content": "",
        }
    ]
    # Keep eval close to training format but do not include an assistant answer.
    text = tokenizer.apply_chat_template(case["messages"], tokenize=False, add_generation_prompt=True)
    if text:
        return text
    system = case["messages"][0]["content"]
    user = case["messages"][1]["content"]
    return f"{system}\n\nUser: {user}\nAssistant JSON:"


def run_eval(
    eval_path: Path,
    predictions_path: Path,
    *,
    adapter_path: Path,
    base_model: str,
    max_seq_length: int,
    max_new_tokens: int,
) -> int:
    from unsloth import FastLanguageModel
    import torch

    print(f"Loading adapter: {adapter_path}", flush=True)
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(adapter_path),
        max_seq_length=max_seq_length,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(model)

    cases = [json.loads(line) for line in eval_path.open(encoding="utf-8")]
    predictions_path.parent.mkdir(parents=True, exist_ok=True)

    with predictions_path.open("w", encoding="utf-8", newline="\n") as handle:
        for index, case in enumerate(cases, start=1):
            prompt = _prompt_from_case(tokenizer, case)
            inputs = tokenizer([prompt], return_tensors="pt").to("cuda")
            started = time.perf_counter()
            with torch.inference_mode():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=max_new_tokens,
                    max_length=None,
                    temperature=0.0,
                    do_sample=False,
                    use_cache=True,
                )
            elapsed = time.perf_counter() - started
            generated = tokenizer.batch_decode(outputs[:, inputs["input_ids"].shape[1] :], skip_special_tokens=True)[0]
            assistant = generated.strip()
            handle.write(
                json.dumps(
                    {
                        "id": case["id"],
                        "category": case["category"],
                        "model": str(adapter_path),
                        "base_model": base_model,
                        "latency_seconds": round(elapsed, 3),
                        "assistant": assistant,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            print(f"[{index}/{len(cases)}] {case['id']} {elapsed:.1f}s => {assistant[:120]}", flush=True)
    return len(cases)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NLM eval seed through a LoRA adapter.")
    parser.add_argument("--eval", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--adapter", type=Path, default=DEFAULT_ADAPTER)
    parser.add_argument("--base-model", default="unsloth/Llama-3.1-8B-Instruct")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--max-seq-length", type=int, default=2048)
    parser.add_argument("--max-new-tokens", type=int, default=180)
    args = parser.parse_args()

    if not args.adapter.exists():
        raise SystemExit(f"Adapter not found: {args.adapter}")

    count = run_eval(
        args.eval,
        args.predictions,
        adapter_path=args.adapter,
        base_model=args.base_model,
        max_seq_length=args.max_seq_length,
        max_new_tokens=args.max_new_tokens,
    )
    print(f"Wrote {count} predictions to {args.predictions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
