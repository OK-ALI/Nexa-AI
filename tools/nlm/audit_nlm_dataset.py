"""Audit NLM JSONL datasets before fine-tuning.

This script checks the things that matter before spending GPU time:

- every line is JSON;
- every record has system/user/assistant chat messages;
- assistant content is strict JSON;
- function calls reference live FunctionRegistry names;
- function call parameters are objects;
- category mix roughly matches the NLM V1 plan.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.nlm.build_nlm_dataset import DEFAULT_OUTPUT, parse_function_registry


EXPECTED_BUCKET_RATIOS = {
    "function": 0.45,
    "follow_up": 0.20,
    "conversation": 0.15,
    "capability": 0.10,
    "clarification": 0.05,
    "safety": 0.05,
}


@dataclass
class AuditResult:
    total: int = 0
    categories: Counter[str] = field(default_factory=Counter)
    buckets: Counter[str] = field(default_factory=Counter)
    functions: Counter[str] = field(default_factory=Counter)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors


def bucket_for_category(category: str) -> str:
    if category.startswith("spoken_command"):
        return "function"
    if category.startswith(("follow_up", "memory_first")):
        return "follow_up"
    if category.startswith("assistant_behavior"):
        return "conversation"
    if category.startswith("nexa_capability"):
        return "capability"
    if category.startswith("clarification"):
        return "clarification"
    if category.startswith(("risky", "offline")):
        return "safety"
    return "other"


def _error(result: AuditResult, line_no: int, message: str) -> None:
    result.errors.append(f"line {line_no}: {message}")


def _validate_messages(result: AuditResult, line_no: int, record: dict[str, Any]) -> list[dict[str, Any]] | None:
    messages = record.get("messages")
    if not isinstance(messages, list) or len(messages) != 3:
        _error(result, line_no, "messages must be a 3-item chat list")
        return None

    expected_roles = ["system", "user", "assistant"]
    for index, expected_role in enumerate(expected_roles):
        message = messages[index]
        if not isinstance(message, dict):
            _error(result, line_no, f"message {index} must be an object")
            return None
        if message.get("role") != expected_role:
            _error(result, line_no, f"message {index} role must be {expected_role!r}")
        if not isinstance(message.get("content"), str) or not message["content"].strip():
            _error(result, line_no, f"message {index} content must be non-empty text")
    return messages


def audit_dataset(dataset_path: Path, *, registry_path: Path | None = None, ratio_tolerance: float = 0.03) -> AuditResult:
    registry_functions = parse_function_registry(registry_path) if registry_path else parse_function_registry()
    valid_functions = {spec.name for spec in registry_functions}
    result = AuditResult()

    with dataset_path.open("r", encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                _error(result, line_no, "blank line")
                continue

            try:
                record = json.loads(stripped)
            except json.JSONDecodeError as exc:
                _error(result, line_no, f"invalid JSONL record: {exc}")
                continue

            if not isinstance(record, dict):
                _error(result, line_no, "record must be a JSON object")
                continue

            result.total += 1
            category = record.get("category")
            if not isinstance(category, str) or not category:
                _error(result, line_no, "category must be non-empty text")
                category = "other"
            result.categories[category] += 1
            result.buckets[bucket_for_category(category)] += 1

            messages = _validate_messages(result, line_no, record)
            if not messages:
                continue

            assistant_text = messages[-1]["content"]
            try:
                assistant_payload = json.loads(assistant_text)
            except json.JSONDecodeError as exc:
                _error(result, line_no, f"assistant content must be strict JSON: {exc}")
                continue

            if not isinstance(assistant_payload, dict):
                _error(result, line_no, "assistant JSON must be an object")
                continue
            if "response" not in assistant_payload or not isinstance(assistant_payload["response"], str):
                _error(result, line_no, "assistant JSON must include string response")

            function_call = assistant_payload.get("function_call")
            if function_call is None:
                continue
            if not isinstance(function_call, dict):
                _error(result, line_no, "function_call must be an object")
                continue

            name = function_call.get("name")
            params = function_call.get("parameters")
            if not isinstance(name, str) or not name:
                _error(result, line_no, "function_call.name must be non-empty text")
                continue
            if name not in valid_functions:
                _error(result, line_no, f"unknown function_call.name: {name}")
            if not isinstance(params, dict):
                _error(result, line_no, "function_call.parameters must be an object")
            result.functions[name] += 1

    if result.total == 0:
        result.errors.append("dataset is empty")
        return result

    for bucket, expected_ratio in EXPECTED_BUCKET_RATIOS.items():
        observed = result.buckets[bucket] / result.total
        if abs(observed - expected_ratio) > ratio_tolerance:
            result.warnings.append(
                f"{bucket} ratio {observed:.2%} differs from expected {expected_ratio:.2%}"
            )

    if result.buckets["other"]:
        result.warnings.append(f"found {result.buckets['other']} records in unknown category bucket")

    missing_functions = sorted(valid_functions - set(result.functions))
    if missing_functions:
        preview = ", ".join(missing_functions[:10])
        result.warnings.append(f"{len(missing_functions)} registry functions have no function-call examples: {preview}")

    return result


def print_report(result: AuditResult) -> None:
    print(f"Records: {result.total}")
    print("Buckets:")
    for bucket, count in result.buckets.most_common():
        print(f"  {bucket}: {count}")
    print("Top categories:")
    for category, count in result.categories.most_common(12):
        print(f"  {category}: {count}")
    print("Top functions:")
    for function_name, count in result.functions.most_common(12):
        print(f"  {function_name}: {count}")

    if result.warnings:
        print("Warnings:")
        for warning in result.warnings:
            print(f"  - {warning}")
    if result.errors:
        print("Errors:")
        for error in result.errors[:50]:
            print(f"  - {error}")
        if len(result.errors) > 50:
            print(f"  ... {len(result.errors) - 50} more errors")


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit an NLM JSONL dataset.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--registry", type=Path, default=None)
    parser.add_argument("--ratio-tolerance", type=float, default=0.03)
    args = parser.parse_args()

    result = audit_dataset(args.dataset, registry_path=args.registry, ratio_tolerance=args.ratio_tolerance)
    print_report(result)
    return 0 if result.ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
