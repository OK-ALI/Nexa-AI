"""Run the NLM eval seed through an Ollama model and save predictions."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.nlm.build_nlm_eval_set import DEFAULT_OUTPUT


DEFAULT_PREDICTIONS = REPO_ROOT / "datasets" / "nlm_v1" / "baseline_ollama_predictions.jsonl"


def _prompt_from_case(case: dict[str, Any]) -> str:
    system = case["messages"][0]["content"]
    user = case["messages"][1]["content"]
    return (
        f"{system}\n\n"
        "Return only one strict JSON object.\n"
        "For commands: {\"function_call\":{\"name\":\"function_name\",\"parameters\":{}},\"response\":\"short response\"}\n"
        "For conversation or clarification: {\"response\":\"short response\"}\n\n"
        f"User: {user}\n"
        "Assistant JSON:"
    )


def run_eval(
    eval_path: Path,
    predictions_path: Path,
    *,
    model: str,
    ollama_url: str,
    timeout: int,
) -> int:
    predictions_path.parent.mkdir(parents=True, exist_ok=True)
    cases = [json.loads(line) for line in eval_path.open(encoding="utf-8")]

    with predictions_path.open("w", encoding="utf-8", newline="\n") as handle:
        for index, case in enumerate(cases, start=1):
            prompt = _prompt_from_case(case)
            started = time.perf_counter()
            response = requests.post(
                f"{ollama_url.rstrip('/')}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": "30m",
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 180,
                        "num_ctx": 4096,
                    },
                },
                timeout=timeout,
            )
            response.raise_for_status()
            payload = response.json()
            assistant = payload.get("response", "").strip()
            elapsed = time.perf_counter() - started
            handle.write(
                json.dumps(
                    {
                        "id": case["id"],
                        "category": case["category"],
                        "model": model,
                        "latency_seconds": round(elapsed, 3),
                        "assistant": assistant,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            print(f"[{index}/{len(cases)}] {case['id']} {elapsed:.1f}s")
    return len(cases)


def main() -> int:
    parser = argparse.ArgumentParser(description="Run NLM eval seed through Ollama.")
    parser.add_argument("--eval", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTIONS)
    parser.add_argument("--model", default="llama3.1:8b-instruct-q4_K_M")
    parser.add_argument("--ollama-url", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout", type=int, default=180)
    args = parser.parse_args()

    count = run_eval(
        args.eval,
        args.predictions,
        model=args.model,
        ollama_url=args.ollama_url,
        timeout=args.timeout,
    )
    print(f"Wrote {count} predictions to {args.predictions}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
