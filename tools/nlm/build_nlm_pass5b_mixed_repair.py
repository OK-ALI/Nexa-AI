"""Build Pass 5B mixed repair + rehearsal data for NLM.

Pass 5 overfit a tiny repair-only dataset. Pass 5B keeps the same repair
examples but mixes them with broad rehearsal examples from the successful
Pass 4 10k dataset to reduce forgetting.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.nlm.build_nlm_dataset import _bucket_for_record
from tools.nlm.build_nlm_pass5_repair import build_repair_dataset


DEFAULT_REHEARSAL = REPO_ROOT / "datasets" / "nlm_v1" / "nlm_v1_pass4_10k_strict.jsonl"
DEFAULT_OUTPUT = REPO_ROOT / "datasets" / "nlm_v1" / "nlm_v1_pass5b_mixed_repair_3k.jsonl"

REHEARSAL_TARGETS = {
    "function": 1080,
    "follow_up": 480,
    "conversation": 360,
    "capability": 240,
    "clarification": 120,
    "safety": 120,
}


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.open(encoding="utf-8")]


def _write_jsonl(records: Iterable[dict[str, Any]], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def _renumber_rehearsal(record: dict[str, Any], index: int) -> dict[str, Any]:
    clone = json.loads(json.dumps(record, ensure_ascii=False))
    clone["id"] = f"pass5b-rehearsal-{index:05d}-{clone['id']}"
    clone["category"] = f"{clone['category']}_pass5b_rehearsal"
    return clone


def _sample_rehearsal(records: list[dict[str, Any]], rng: random.Random) -> list[dict[str, Any]]:
    by_bucket: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_bucket[_bucket_for_record(record)].append(record)

    selected: list[dict[str, Any]] = []
    for bucket, target in REHEARSAL_TARGETS.items():
        source = list(by_bucket.get(bucket, []))
        if not source:
            continue
        if len(source) >= target:
            picks = rng.sample(source, target)
        else:
            picks = [rng.choice(source) for _ in range(target)]
        selected.extend(_renumber_rehearsal(record, len(selected) + idx) for idx, record in enumerate(picks))
    return selected


def build_mixed_dataset(
    *,
    rehearsal_path: Path = DEFAULT_REHEARSAL,
    repair_count: int = 600,
    seed: int = 23,
) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    repair_records = build_repair_dataset(count=repair_count, seed=17)
    rehearsal_records = _sample_rehearsal(_load_jsonl(rehearsal_path), rng)
    records = repair_records + rehearsal_records
    rng.shuffle(records)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description="Build NLM Pass 5B mixed repair dataset.")
    parser.add_argument("--rehearsal", type=Path, default=DEFAULT_REHEARSAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--repair-count", type=int, default=600)
    parser.add_argument("--seed", type=int, default=23)
    args = parser.parse_args()

    if not args.rehearsal.exists():
        raise SystemExit(f"Rehearsal dataset not found: {args.rehearsal}")

    records = build_mixed_dataset(
        rehearsal_path=args.rehearsal,
        repair_count=args.repair_count,
        seed=args.seed,
    )
    count = _write_jsonl(records, args.output)
    print(f"Wrote {count} mixed repair records to {args.output}")
    print(f"Repair records: {args.repair_count}")
    print(f"Rehearsal records: {count - args.repair_count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
