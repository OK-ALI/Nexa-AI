"""Score NLM eval predictions against the golden eval JSONL.

Predictions are expected as JSONL with:

{"id":"eval-function-0001","assistant":"{\"function_call\":...,\"response\":\"...\"}"}

The script is model-agnostic; later we can feed it outputs from Ollama, Unsloth,
or any inference harness.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.nlm.build_nlm_eval_set import DEFAULT_OUTPUT


@dataclass
class Score:
    total: int = 0
    valid_json: int = 0
    function_correct: int = 0
    parameter_matches: int = 0
    response_matches: int = 0
    strict_passes: int = 0
    missing_predictions: int = 0
    extra_predictions: int = 0
    failures: list[dict[str, Any]] | None = None


def _load_eval(path: Path) -> dict[str, dict[str, Any]]:
    return {record["id"]: record for record in (json.loads(line) for line in path.open(encoding="utf-8"))}


def _load_predictions(path: Path) -> dict[str, str]:
    predictions: dict[str, str] = {}
    for line in path.open(encoding="utf-8"):
        record = json.loads(line)
        predictions[record["id"]] = record["assistant"]
    return predictions


def _params_match(expected: dict[str, Any], actual: dict[str, Any], *, lenient: bool = False) -> bool:
    if not lenient:
        return expected == actual
    for key, expected_value in expected.items():
        if key not in actual:
            return False
        actual_value = actual[key]
        if isinstance(expected_value, str):
            if str(expected_value).lower() not in str(actual_value).lower():
                return False
        elif actual_value != expected_value:
            return False
    return True


def _percent(part: int, total: int) -> str:
    if total <= 0:
        return "0.0%"
    return f"{part / total:.1%}"


def _jsonish(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def score_predictions(eval_path: Path, predictions_path: Path, *, lenient_params: bool = False) -> Score:
    eval_cases = _load_eval(eval_path)
    predictions = _load_predictions(predictions_path)
    score = Score(
        total=len(eval_cases),
        missing_predictions=len(set(eval_cases) - set(predictions)),
        extra_predictions=len(set(predictions) - set(eval_cases)),
        failures=[],
    )

    for case_id, case in eval_cases.items():
        raw_assistant = predictions.get(case_id, "")
        failure: dict[str, Any] = {
            "id": case_id,
            "category": case.get("category"),
            "user": case.get("messages", [{}])[-1].get("content"),
            "expected": case["expected"],
            "actual": None,
            "reasons": [],
        }
        if not raw_assistant:
            failure["reasons"].append("missing_prediction")
            score.failures.append(failure)
            continue

        try:
            payload = json.loads(raw_assistant)
        except json.JSONDecodeError as exc:
            failure["actual"] = raw_assistant
            failure["reasons"].append(f"invalid_json:{exc.msg}")
            score.failures.append(failure)
            continue
        if not isinstance(payload, dict):
            failure["actual"] = payload
            failure["reasons"].append("assistant_payload_not_object")
            score.failures.append(failure)
            continue
        score.valid_json += 1
        failure["actual"] = payload

        expected = case["expected"]
        expected_function = expected["function_name"]
        actual_call = payload.get("function_call")
        actual_function = actual_call.get("name") if isinstance(actual_call, dict) else None
        function_ok = False
        params_ok = False

        if expected_function == actual_function:
            score.function_correct += 1
            function_ok = True
            actual_params = actual_call.get("parameters", {}) if isinstance(actual_call, dict) else {}
            if isinstance(actual_params, dict) and _params_match(
                expected["parameters"],
                actual_params,
                lenient=lenient_params,
            ):
                score.parameter_matches += 1
                params_ok = True
        elif expected_function is None and actual_function is None:
            score.function_correct += 1
            score.parameter_matches += 1
            function_ok = True
            params_ok = True
        else:
            failure["reasons"].append("function_mismatch")

        if function_ok and not params_ok:
            actual_params = actual_call.get("parameters", {}) if isinstance(actual_call, dict) else {}
            failure["reasons"].append("parameter_mismatch")
            failure["expected_parameters"] = expected["parameters"]
            failure["actual_parameters"] = actual_params

        response = str(payload.get("response", "")).lower()
        response_ok = all(fragment.lower() in response for fragment in expected["response_contains"])
        if response_ok:
            score.response_matches += 1
        else:
            failure["reasons"].append("response_mismatch")
            failure["expected_response_contains"] = expected["response_contains"]
            failure["actual_response"] = payload.get("response")

        if function_ok and params_ok and response_ok:
            score.strict_passes += 1
        elif failure["reasons"]:
            score.failures.append(failure)

    return score


def _write_json_report(path: Path, eval_path: Path, predictions_path: Path, score: Score) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "eval": str(eval_path),
        "predictions": str(predictions_path),
        "summary": {
            "total": score.total,
            "valid_json": score.valid_json,
            "function_correct": score.function_correct,
            "parameter_matches": score.parameter_matches,
            "response_matches": score.response_matches,
            "strict_passes": score.strict_passes,
            "missing_predictions": score.missing_predictions,
            "extra_predictions": score.extra_predictions,
            "failure_count": len(score.failures or []),
            "valid_json_percent": _percent(score.valid_json, score.total),
            "function_accuracy_percent": _percent(score.function_correct, score.total),
            "parameter_match_percent": _percent(score.parameter_matches, score.total),
            "response_text_match_percent": _percent(score.response_matches, score.total),
            "strict_pass_percent": _percent(score.strict_passes, score.total),
        },
        "failures": score.failures or [],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _write_markdown_report(path: Path, score: Score) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# NLM Evaluation Report",
        "",
        f"- Total: {score.total}",
        f"- Valid JSON: {_percent(score.valid_json, score.total)}",
        f"- Function accuracy: {_percent(score.function_correct, score.total)}",
        f"- Parameter match: {_percent(score.parameter_matches, score.total)}",
        f"- Response text match: {_percent(score.response_matches, score.total)}",
        f"- Strict pass: {_percent(score.strict_passes, score.total)}",
        f"- Failures: {len(score.failures or [])}",
        "",
    ]
    if score.failures:
        lines.append("## Failures")
        lines.append("")
        for failure in score.failures:
            lines.extend(
                [
                    f"### {failure['id']}",
                    "",
                    f"- Reasons: {', '.join(failure['reasons'])}",
                    f"- User: {failure.get('user')}",
                    f"- Expected: `{_jsonish(failure.get('expected'))}`",
                    f"- Actual: `{_jsonish(failure.get('actual'))}`",
                    "",
                ]
            )
    path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Score NLM eval predictions.")
    parser.add_argument("--eval", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--predictions", type=Path, required=True)
    parser.add_argument("--report-json", type=Path, help="Write a structured strict eval report.")
    parser.add_argument("--report-md", type=Path, help="Write a Markdown strict eval report.")
    parser.add_argument("--show-failures", type=int, default=12, help="Number of failures to print.")
    parser.add_argument("--lenient-params", action="store_true", help="Use legacy partial string matching for parameters.")
    args = parser.parse_args()

    score = score_predictions(args.eval, args.predictions, lenient_params=args.lenient_params)
    print(f"Total: {score.total}")
    print(f"Valid JSON: {_percent(score.valid_json, score.total)}")
    print(f"Function accuracy: {_percent(score.function_correct, score.total)}")
    print(f"Parameter match: {_percent(score.parameter_matches, score.total)}")
    print(f"Response text match: {_percent(score.response_matches, score.total)}")
    print(f"Strict pass: {_percent(score.strict_passes, score.total)}")
    print(f"Missing predictions: {score.missing_predictions}")
    print(f"Extra predictions: {score.extra_predictions}")
    print(f"Failures: {len(score.failures or [])}")

    for failure in (score.failures or [])[: max(0, args.show_failures)]:
        reasons = ", ".join(failure["reasons"])
        expected = failure["expected"]
        actual = failure["actual"]
        actual_call = actual.get("function_call") if isinstance(actual, dict) else None
        actual_name = actual_call.get("name") if isinstance(actual_call, dict) else None
        print(
            f"FAIL {failure['id']}: {reasons}; "
            f"expected={expected.get('function_name')} {expected.get('parameters')}; "
            f"actual={actual_name} {actual_call.get('parameters', {}) if isinstance(actual_call, dict) else ''}"
        )

    if args.report_json:
        _write_json_report(args.report_json, args.eval, args.predictions, score)
        print(f"Report JSON: {args.report_json}")
    if args.report_md:
        _write_markdown_report(args.report_md, score)
        print(f"Report MD: {args.report_md}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
