"""Check whether the current machine can start NLM Unsloth training."""

from __future__ import annotations

import argparse
import importlib
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = REPO_ROOT / "datasets" / "nlm_v1" / "nlm_v1_prototype.jsonl"


@dataclass
class Check:
    name: str
    ok: bool
    detail: str


def _import_check(module_name: str) -> Check:
    try:
        module = importlib.import_module(module_name)
        version = getattr(module, "__version__", "installed")
        return Check(module_name, True, str(version))
    except Exception as exc:
        return Check(module_name, False, f"{type(exc).__name__}: {exc}")


def _torch_cuda_check() -> list[Check]:
    checks: list[Check] = []
    try:
        import torch

        checks.append(Check("torch", True, str(getattr(torch, "__version__", "installed"))))
        cuda_available = bool(torch.cuda.is_available())
        detail = "available" if cuda_available else "not available"
        if cuda_available:
            detail = f"{torch.cuda.get_device_name(0)}; cuda={torch.version.cuda}"
        checks.append(Check("torch.cuda", cuda_available, detail))
    except Exception as exc:
        checks.append(Check("torch", False, f"{type(exc).__name__}: {exc}"))
        checks.append(Check("torch.cuda", False, "torch unavailable"))
    return checks


def _nvidia_smi_check() -> Check:
    exe = shutil.which("nvidia-smi") or r"C:\Windows\System32\nvidia-smi.exe"
    try:
        result = subprocess.run(
            [exe, "--query-gpu=name,memory.total,memory.used,driver_version", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=15,
            check=True,
        )
        return Check("nvidia-smi", True, result.stdout.strip())
    except Exception as exc:
        return Check("nvidia-smi", False, f"{type(exc).__name__}: {exc}")


def _dataset_check(dataset_path: Path) -> Check:
    if not dataset_path.exists():
        return Check("dataset", False, f"missing: {dataset_path}")

    try:
        count = 0
        with dataset_path.open("r", encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    json.loads(line)
                    count += 1
        return Check("dataset", count > 0, f"{count} JSONL records at {dataset_path}")
    except Exception as exc:
        return Check("dataset", False, f"{type(exc).__name__}: {exc}")


def run_checks(dataset_path: Path) -> list[Check]:
    checks: list[Check] = []
    checks.append(Check("python", True, sys.version.replace("\n", " ")))
    checks.extend(_torch_cuda_check())
    for module_name in ["unsloth", "transformers", "trl", "datasets", "accelerate", "bitsandbytes"]:
        if module_name == "torch":
            continue
        checks.append(_import_check(module_name))
    checks.append(_nvidia_smi_check())
    checks.append(_dataset_check(dataset_path))
    return checks


def main() -> int:
    parser = argparse.ArgumentParser(description="Check NLM Unsloth training readiness.")
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    checks = run_checks(args.dataset)
    if args.json:
        print(json.dumps([asdict(check) for check in checks], indent=2))
    else:
        print("NLM training readiness")
        for check in checks:
            status = "OK" if check.ok else "BLOCKED"
            print(f"- {status}: {check.name}: {check.detail}")

    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())

