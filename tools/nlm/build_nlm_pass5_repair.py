"""Build Pass 5 tiny repair data for NLM.

Pass 5 is intentionally small and targeted. It repairs the five remaining
Pass 4 strict-eval failures without replacing the broad 10k dataset.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.nlm.build_nlm_dataset import SYSTEM_PROMPT, _assistant_json, _record


DEFAULT_DATASET_OUTPUT = REPO_ROOT / "datasets" / "nlm_v1" / "nlm_v1_pass5_repair_600.jsonl"
DEFAULT_EVAL_OUTPUT = REPO_ROOT / "datasets" / "nlm_v1" / "nlm_v1_pass5_repair_eval.jsonl"


def _case(
    case_id: str,
    category: str,
    user: str,
    *,
    expected_function: str | None = None,
    expected_parameters: dict[str, Any] | None = None,
    expected_response_contains: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "id": case_id,
        "category": category,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
        "expected": {
            "function_name": expected_function,
            "parameters": expected_parameters or {},
            "response_contains": expected_response_contains or [],
        },
    }


def _repair_templates() -> list[dict[str, Any]]:
    templates: list[dict[str, Any]] = []

    offline_prompts = [
        "can you work offline",
        "can you still help me offline",
        "what can you do offline",
        "do you work in offline mode",
        "if internet is off can you still help",
        "nexa can you work without internet",
        "tell me what works offline",
        "are local tasks available offline",
        "what is available when you are offline",
        "can you control my laptop offline",
    ]
    for idx, prompt in enumerate(offline_prompts):
        templates.append(
            _record(
                f"pass5-offline-{idx:04d}",
                "nexa_capability_qa_pass5_repair",
                prompt,
                _assistant_json(
                    response="Yes. I can work offline for local apps, windows, system controls, music, memory, and conversation. Web features need online mode."
                ),
            )
        )

    volume_prompts = [
        "turn it up",
        "turn the volume up",
        "make it louder",
        "volume up",
        "raise the volume",
        "increase volume",
        "increase the volume",
        "nexa turn it up",
        "can you make sound louder",
        "louder please",
    ]
    for idx, prompt in enumerate(volume_prompts):
        templates.append(
            _record(
                f"pass5-volume-{idx:04d}",
                "spoken_command_alias_pass5_repair",
                prompt,
                _assistant_json("increase_volume", {"amount": 10}, "Turning it up."),
                source_function="increase_volume",
            )
        )

    installed_app_prompts = [
        "list installed apps",
        "show installed apps",
        "what apps are installed",
        "show my installed applications",
        "list installed applications",
        "which programs are installed",
        "show applications installed on this pc",
        "nexa list installed apps",
        "can you list my installed apps",
        "installed apps list",
    ]
    for idx, prompt in enumerate(installed_app_prompts):
        templates.append(
            _record(
                f"pass5-installed-apps-{idx:04d}",
                "spoken_command_alias_pass5_repair",
                prompt,
                _assistant_json("get_installed_applications", {}, "Listing installed apps."),
                source_function="get_installed_applications",
            )
        )

    trending_prompts = [
        "show trending videos in US",
        "show trending videos in the US",
        "what is trending on youtube in US",
        "youtube trending US",
        "show popular videos in US",
        "show five trending videos in US",
        "get trending videos for US",
        "nexa show trending youtube videos in US",
        "show youtube trends in US",
        "popular youtube videos US",
    ]
    for idx, prompt in enumerate(trending_prompts):
        templates.append(
            _record(
                f"pass5-trending-{idx:04d}",
                "spoken_command_alias_pass5_repair",
                prompt,
                _assistant_json("get_trending_videos", {"region": "US", "count": 5}, "Showing trending videos in the US."),
                source_function="get_trending_videos",
            )
        )

    font_size_prompts = [
        "set font size to 14",
        "make font size 14",
        "change font size to 14",
        "font size fourteen",
        "set the font size at 14",
        "nexa set font size to 14",
        "make text size 14",
        "set font to size 14",
        "use font size 14",
        "change the text size to 14",
    ]
    for idx, prompt in enumerate(font_size_prompts):
        templates.append(
            _record(
                f"pass5-font-size-{idx:04d}",
                "spoken_command_alias_pass5_repair",
                prompt,
                _assistant_json("set_font_size", {"size": 14}, "Setting font size to 14."),
                source_function="set_font_size",
            )
        )

    return templates


def _augment_prompt(prompt: str, rng: random.Random) -> str:
    wrappers = [
        "{}",
        "nexa {}",
        "hey nexa {}",
        "can you {}",
        "please {}",
        "uh nexa please {}",
    ]
    noisy = {
        "volume": ["volum", "sound"],
        "youtube": ["you tube", "yt"],
        "installed": ["installed", "instaled"],
        "applications": ["applications", "apps"],
        "offline": ["offline", "off line"],
        "fourteen": ["fourteen", "14"],
    }
    text = prompt
    for source, replacements in noisy.items():
        if source in text and rng.random() < 0.35:
            text = text.replace(source, rng.choice(replacements))
    return rng.choice(wrappers).format(text)


def build_repair_dataset(count: int = 600, seed: int = 17) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    templates = _repair_templates()
    target_per_theme = count // 5
    records: list[dict[str, Any]] = []

    themes = [
        templates[0:10],
        templates[10:20],
        templates[20:30],
        templates[30:40],
        templates[40:50],
    ]
    for theme_index, theme_templates in enumerate(themes):
        selected = list(theme_templates)
        records.extend(selected)
        while len(selected) < target_per_theme:
            template = rng.choice(theme_templates)
            clone = json.loads(json.dumps(template, ensure_ascii=False))
            clone["id"] = f"{template['id']}-aug-{len(selected):04d}"
            clone["messages"][1]["content"] = _augment_prompt(clone["messages"][1]["content"], rng)
            clone["category"] = f"{template['category']}_aug"
            selected.append(clone)
            records.append(clone)

    while len(records) < count:
        template = rng.choice(templates)
        clone = json.loads(json.dumps(template, ensure_ascii=False))
        clone["id"] = f"{template['id']}-extra-{len(records):04d}"
        clone["messages"][1]["content"] = _augment_prompt(clone["messages"][1]["content"], rng)
        clone["category"] = f"{template['category']}_aug"
        records.append(clone)

    return records[:count]


def build_repair_eval() -> list[dict[str, Any]]:
    return [
        _case("pass5-eval-offline-0001", "capability_qa", "can you work offline", expected_response_contains=["offline"]),
        _case("pass5-eval-offline-0002", "capability_qa", "what can you do offline", expected_response_contains=["offline"]),
        _case("pass5-eval-offline-0003", "capability_qa", "can you help without internet", expected_response_contains=["offline"]),
        _case("pass5-eval-offline-0004", "capability_qa", "tell me what works offline", expected_response_contains=["offline"]),
        _case("pass5-eval-offline-0005", "capability_qa", "are local tasks available offline", expected_response_contains=["offline"]),
        _case("pass5-eval-volume-0001", "function_routing", "turn it up", expected_function="increase_volume", expected_parameters={"amount": 10}),
        _case("pass5-eval-volume-0002", "function_routing", "make it louder", expected_function="increase_volume", expected_parameters={"amount": 10}),
        _case("pass5-eval-volume-0003", "function_routing", "volume up", expected_function="increase_volume", expected_parameters={"amount": 10}),
        _case("pass5-eval-volume-0004", "function_routing", "raise the volume", expected_function="increase_volume", expected_parameters={"amount": 10}),
        _case("pass5-eval-volume-0005", "function_routing", "nexa turn it up", expected_function="increase_volume", expected_parameters={"amount": 10}),
        _case("pass5-eval-installed-apps-0001", "function_routing", "list installed apps", expected_function="get_installed_applications"),
        _case("pass5-eval-installed-apps-0002", "function_routing", "show installed apps", expected_function="get_installed_applications"),
        _case("pass5-eval-installed-apps-0003", "function_routing", "what apps are installed", expected_function="get_installed_applications"),
        _case("pass5-eval-installed-apps-0004", "function_routing", "list installed applications", expected_function="get_installed_applications"),
        _case("pass5-eval-installed-apps-0005", "function_routing", "which programs are installed", expected_function="get_installed_applications"),
        _case("pass5-eval-trending-0001", "function_routing", "show trending videos in US", expected_function="get_trending_videos", expected_parameters={"region": "US", "count": 5}),
        _case("pass5-eval-trending-0002", "function_routing", "what is trending on youtube in US", expected_function="get_trending_videos", expected_parameters={"region": "US", "count": 5}),
        _case("pass5-eval-trending-0003", "function_routing", "youtube trending US", expected_function="get_trending_videos", expected_parameters={"region": "US", "count": 5}),
        _case("pass5-eval-trending-0004", "function_routing", "show popular videos in US", expected_function="get_trending_videos", expected_parameters={"region": "US", "count": 5}),
        _case("pass5-eval-trending-0005", "function_routing", "show five trending videos in US", expected_function="get_trending_videos", expected_parameters={"region": "US", "count": 5}),
        _case("pass5-eval-font-size-0001", "function_routing", "set font size to 14", expected_function="set_font_size", expected_parameters={"size": 14}),
        _case("pass5-eval-font-size-0002", "function_routing", "make font size 14", expected_function="set_font_size", expected_parameters={"size": 14}),
        _case("pass5-eval-font-size-0003", "function_routing", "change font size to 14", expected_function="set_font_size", expected_parameters={"size": 14}),
        _case("pass5-eval-font-size-0004", "function_routing", "font size fourteen", expected_function="set_font_size", expected_parameters={"size": 14}),
        _case("pass5-eval-font-size-0005", "function_routing", "use font size 14", expected_function="set_font_size", expected_parameters={"size": 14}),
    ]


def write_jsonl(records: Iterable[dict[str, Any]], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Build NLM Pass 5 tiny repair data.")
    parser.add_argument("--dataset-output", type=Path, default=DEFAULT_DATASET_OUTPUT)
    parser.add_argument("--eval-output", type=Path, default=DEFAULT_EVAL_OUTPUT)
    parser.add_argument("--count", type=int, default=600)
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()

    dataset_count = write_jsonl(build_repair_dataset(count=args.count, seed=args.seed), args.dataset_output)
    eval_count = write_jsonl(build_repair_eval(), args.eval_output)
    print(f"Wrote {dataset_count} repair records to {args.dataset_output}")
    print(f"Wrote {eval_count} repair eval cases to {args.eval_output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
