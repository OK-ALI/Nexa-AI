"""Build the first NLM spoken-intent fine-tuning dataset.

The generator is intentionally source-based: it parses the FunctionRegistry
registration calls without importing NEXA, which avoids initializing UI,
audio, Ollama, GPU, or OS-control components during dataset creation.
"""

from __future__ import annotations

import argparse
import ast
import json
import random
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTRY = REPO_ROOT / "capabilities" / "function_registry.py"
DEFAULT_OUTPUT = REPO_ROOT / "datasets" / "nlm_v1" / "nlm_v1_prototype.jsonl"

SYSTEM_PROMPT = (
    "You are NLM, the NEXA Large Model: NEXA's local spoken-intent brain. "
    "Understand natural voice transcripts, choose valid NEXA functions when an "
    "action is needed, ask clarification when required, and respond warmly as "
    "NEXA. For function calls, response is only a short intent acknowledgement; "
    "NEXA's runtime will execute the function and produce the final success or "
    "failure message. Return strict JSON only."
)

INTERNET_FUNCTION_HINTS = {
    "weather",
    "forecast",
    "web",
    "youtube",
    "email",
    "transcript",
    "trending",
    "channel",
    "download_youtube",
}


@dataclass(frozen=True)
class FunctionSpec:
    name: str
    description: str
    parameters: dict[str, str]


def _literal_string(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _literal_parameters(node: ast.AST) -> dict[str, str] | None:
    if not isinstance(node, ast.Dict):
        return None

    params: dict[str, str] = {}
    for key, value in zip(node.keys, node.values):
        if key is None:
            return None
        key_text = _literal_string(key)
        value_text = _literal_string(value)
        if key_text is None or value_text is None:
            return None
        params[key_text] = value_text
    return params


def parse_function_registry(registry_path: Path = DEFAULT_REGISTRY) -> list[FunctionSpec]:
    """Extract registered function names, descriptions, and parameters."""
    tree = ast.parse(registry_path.read_text(encoding="utf-8"))
    functions: list[FunctionSpec] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "register":
            continue
        if len(node.args) < 4:
            continue

        name = _literal_string(node.args[0])
        description = _literal_string(node.args[2])
        parameters = _literal_parameters(node.args[3])
        if name and description is not None and parameters is not None:
            functions.append(FunctionSpec(name=name, description=description, parameters=parameters))

    # Keep first registration if a name is repeated.
    seen: set[str] = set()
    unique: list[FunctionSpec] = []
    for spec in functions:
        if spec.name in seen:
            continue
        seen.add(spec.name)
        unique.append(spec)
    return unique


def _humanize_function_name(name: str) -> str:
    return name.replace("_", " ")


def _sample_value(param_name: str, description: str) -> Any:
    p = param_name.lower()
    d = description.lower()

    if p in {"level", "amount", "percent", "percentage"} or "0-100" in d:
        return 50
    if p in {"days", "count", "number", "max_videos"}:
        return 3
    if "audio_only" in p:
        return False
    if "quality" in p:
        return "1080p"
    if "location" in p or "city" in d:
        return "Karachi"
    if "app" in p:
        return "chrome"
    if "window" in p:
        return "chrome"
    if "song" in p:
        return "lofi music"
    if "query" in p:
        return "lofi music"
    if "topic" in p:
        return "favorite music"
    if "fact" in p:
        return "User prefers dark theme"
    if "file" in p or "path" in p:
        return "Documents"
    if "url" in p:
        return "https://www.youtube.com/playlist?list=PLexample"
    if "region" in p:
        return "US"
    if "channel" in p:
        return "mkbhd"
    if "mode" in p:
        return "summarize"
    if "text" in p:
        return "Please improve this paragraph."
    if "device" in p:
        return "AirPods"
    return re.sub(r"[^a-z0-9]+", " ", param_name.lower()).strip() or "value"


def _sample_parameters(spec: FunctionSpec) -> dict[str, Any]:
    return {name: _sample_value(name, desc) for name, desc in spec.parameters.items()}


def _runtime_acknowledgement(function_name: str, response: str) -> str:
    if not response:
        return "I'll ask NEXA to handle that now."
    lowered = response.lower()
    if "then" in lowered:
        return "I'll start with that first, then NEXA can continue with the next step."
    if "confirm" in lowered or lowered.startswith(("which", "what ", "do you mean", "that needs", "weather needs")):
        return response
    return "I'll ask NEXA to handle that now."


def _assistant_json(function_name: str | None = None, params: dict[str, Any] | None = None, response: str = "") -> str:
    payload: dict[str, Any]
    if function_name:
        payload = {
            "function_call": {
                "name": function_name,
                "parameters": params or {},
            },
            "response": _runtime_acknowledgement(function_name, response),
        }
    else:
        payload = {"response": response}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _record(record_id: str, category: str, user: str, assistant: str, *, source_function: str | None = None) -> dict[str, Any]:
    return {
        "id": record_id,
        "category": category,
        "source_function": source_function,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
            {"role": "assistant", "content": assistant},
        ],
    }


def _voice_prompts(spec: FunctionSpec, params: dict[str, Any]) -> list[str]:
    friendly = _humanize_function_name(spec.name)
    desc = spec.description.rstrip(".")
    if params:
        first_value = next(iter(params.values()))
        return [
            f"Nexa, {friendly} {first_value}",
            f"can you {desc.lower()}",
            f"hey nexa please {friendly} for {first_value}",
            f"uh nexa can you just {friendly} {first_value} please",
        ]
    return [
        f"Nexa, {friendly}",
        f"can you {desc.lower()}",
        f"hey nexa please {friendly}",
        f"uh nexa can you just {friendly} please",
    ]


def _targeted_function_records() -> list[dict[str, Any]]:
    """High-value aliases found during prototype eval.

    These are not broad coverage. They are small correction anchors for phrases
    where the base/prototype model preferred invented function names.
    """
    return [
        _record(
            "target-current-time-0001",
            "spoken_command_alias",
            "what time is it",
            _assistant_json("get_current_time", {}, "Checking the current time."),
            source_function="get_current_time",
        ),
        _record(
            "target-current-time-0002",
            "spoken_command_alias",
            "nexa tell me the time",
            _assistant_json("get_current_time", {}, "Checking the current time."),
            source_function="get_current_time",
        ),
        _record(
            "target-battery-0001",
            "spoken_command_alias",
            "show me my battery",
            _assistant_json("get_battery_status", {}, "Checking your battery."),
            source_function="get_battery_status",
        ),
        _record(
            "target-battery-0002",
            "spoken_command_alias",
            "how much battery do I have",
            _assistant_json("get_battery_status", {}, "Checking your battery."),
            source_function="get_battery_status",
        ),
        _record(
            "target-play-music-0001",
            "spoken_command_alias",
            "play lofi music",
            _assistant_json("play_music", {"song_name": "lofi music"}, "Playing lofi music."),
            source_function="play_music",
        ),
        _record(
            "target-play-youtube-result-0001",
            "spoken_command_alias",
            "from the search results play the third one",
            _assistant_json("play_youtube_result", {"number": 3}, "Playing the third result."),
            source_function="play_youtube_result",
        ),
        _record(
            "target-brightness-0001",
            "spoken_command_alias",
            "make my screen brightness 60",
            _assistant_json("set_brightness", {"level": 60}, "Setting brightness to 60."),
            source_function="set_brightness",
        ),
        _record(
            "target-date-0001",
            "spoken_command_alias",
            "what is today's date",
            _assistant_json("get_current_date", {}, "Checking today's date."),
            source_function="get_current_date",
        ),
        _record(
            "target-system-info-0001",
            "spoken_command_alias",
            "what are my full system details",
            _assistant_json("get_system_info", {}, "Checking your system details."),
            source_function="get_system_info",
        ),
        _record(
            "target-unmute-0001",
            "spoken_command_alias",
            "unmute sound",
            _assistant_json("unmute_volume", {}, "Unmuting volume."),
            source_function="unmute_volume",
        ),
        _record(
            "target-brightness-0002",
            "spoken_command_alias",
            "make the screen brighter",
            _assistant_json("increase_brightness", {"amount": 10}, "Increasing brightness."),
            source_function="increase_brightness",
        ),
        _record(
            "target-brightness-0003",
            "spoken_command_alias",
            "what brightness am I on",
            _assistant_json("get_current_brightness", {}, "Checking current brightness."),
            source_function="get_current_brightness",
        ),
        _record(
            "target-app-running-0001",
            "spoken_command_alias",
            "is discord running",
            _assistant_json("is_application_running", {"app_name": "discord"}, "Checking whether Discord is running."),
            source_function="is_application_running",
        ),
        _record(
            "target-app-refresh-0001",
            "spoken_command_alias",
            "refresh my installed apps",
            _assistant_json("refresh_installed_apps", {}, "Refreshing installed apps."),
            source_function="refresh_installed_apps",
        ),
        _record(
            "target-window-0001",
            "spoken_command_alias",
            "minimize chrome",
            _assistant_json("minimize_window", {"app_name": "chrome"}, "Minimizing Chrome."),
            source_function="minimize_window",
        ),
        _record(
            "target-window-0002",
            "spoken_command_alias",
            "maximize the active window",
            _assistant_json("maximize_window", {"app_name": "active"}, "Maximizing the active window."),
            source_function="maximize_window",
        ),
        _record(
            "target-window-0003",
            "spoken_command_alias",
            "close this window",
            _assistant_json("close_active_window", {}, "Closing the active window."),
            source_function="close_active_window",
        ),
        _record(
            "target-wifi-0001",
            "spoken_command_alias",
            "show wifi networks",
            _assistant_json("list_wifi_networks", {}, "Showing available WiFi networks."),
            source_function="list_wifi_networks",
        ),
        _record(
            "target-wifi-0002",
            "spoken_command_alias",
            "show saved wifi profiles",
            _assistant_json("get_saved_wifi_profiles", {}, "Showing saved WiFi profiles."),
            source_function="get_saved_wifi_profiles",
        ),
        _record(
            "target-bluetooth-0001",
            "spoken_command_alias",
            "is bluetooth on",
            _assistant_json("get_bluetooth_status", {}, "Checking Bluetooth status."),
            source_function="get_bluetooth_status",
        ),
        _record(
            "target-bluetooth-0002",
            "spoken_command_alias",
            "list bluetooth devices",
            _assistant_json("list_bluetooth_devices", {}, "Listing Bluetooth devices."),
            source_function="list_bluetooth_devices",
        ),
        _record(
            "target-bluetooth-0003",
            "spoken_command_alias",
            "connect my AirPods",
            _assistant_json("connect_bluetooth_device", {"device_name": "AirPods"}, "Connecting AirPods."),
            source_function="connect_bluetooth_device",
        ),
        _record(
            "target-display-0001",
            "spoken_command_alias",
            "duplicate my display",
            _assistant_json("set_display_projection", {"mode": "clone"}, "Duplicating your display."),
            source_function="set_display_projection",
        ),
        _record(
            "target-display-0002",
            "spoken_command_alias",
            "turn on night light",
            _assistant_json("enable_night_light", {}, "Turning on night light."),
            source_function="enable_night_light",
        ),
        _record(
            "target-display-0003",
            "spoken_command_alias",
            "turn off airplane mode",
            _assistant_json("toggle_airplane_mode", {}, "Toggling airplane mode."),
            source_function="toggle_airplane_mode",
        ),
        _record(
            "target-web-0001",
            "spoken_command_alias",
            "google latest python docs",
            _assistant_json("search_web", {"query": "latest python docs"}, "Searching the web for latest python docs."),
            source_function="search_web",
        ),
        _record(
            "target-web-0002",
            "spoken_command_alias",
            "answer from the web what is qlora",
            _assistant_json("smart_search", {"query": "what is qlora"}, "Searching for an answer about QLoRA."),
            source_function="smart_search",
        ),
        _record(
            "target-web-0003",
            "spoken_command_alias",
            "read this page https://example.com/article",
            _assistant_json("scrape_url", {"url": "https://example.com/article"}, "Reading that page."),
            source_function="scrape_url",
        ),
        _record(
            "target-youtube-0001",
            "spoken_command_alias",
            "play interstellar theme on youtube",
            _assistant_json("play_youtube", {"query": "interstellar theme"}, "Playing Interstellar theme on YouTube."),
            source_function="play_youtube",
        ),
        _record(
            "target-youtube-0002",
            "spoken_command_alias",
            "download this youtube video in 720p",
            _assistant_json("download_youtube", {"query": "this youtube video", "audio_only": False, "quality": "720p"}, "Downloading the YouTube video in 720p."),
            source_function="download_youtube",
        ),
        _record(
            "target-youtube-0003",
            "spoken_command_alias",
            "download audio for lofi beats",
            _assistant_json("download_youtube_audio", {"query": "lofi beats"}, "Downloading audio for lofi beats."),
            source_function="download_youtube_audio",
        ),
        _record(
            "target-youtube-0004",
            "spoken_command_alias",
            "get transcript for this video",
            _assistant_json("get_video_transcript", {"query": "this video"}, "Getting the video transcript."),
            source_function="get_video_transcript",
        ),
        _record(
            "target-youtube-0004b",
            "spoken_command_alias",
            "show trending videos in US",
            _assistant_json("get_trending_videos", {"region": "US", "count": 5}, "Showing trending videos in the US."),
            source_function="get_trending_videos",
        ),
        _record(
            "target-youtube-0005",
            "spoken_command_alias",
            "show latest videos from mkbhd",
            _assistant_json("get_channel_videos", {"channel_name": "mkbhd", "count": 5}, "Showing latest videos from MKBHD."),
            source_function="get_channel_videos",
        ),
        _record(
            "target-files-0001",
            "spoken_command_alias",
            "open downloads folder",
            _assistant_json("open_folder", {"folder_name": "downloads"}, "Opening Downloads."),
            source_function="open_folder",
        ),
        _record(
            "target-files-0002",
            "spoken_command_alias",
            "find my documents folder",
            _assistant_json("find_folder", {"folder_name": "documents"}, "Finding your Documents folder."),
            source_function="find_folder",
        ),
        _record(
            "target-files-0003",
            "spoken_command_alias",
            "clean up downloads",
            _assistant_json("cleanup_downloads", {}, "Cleaning up Downloads."),
            source_function="cleanup_downloads",
        ),
        _record(
            "target-files-0004",
            "spoken_command_alias",
            "show recent files",
            _assistant_json("get_recent_files", {}, "Showing recent files."),
            source_function="get_recent_files",
        ),
        _record(
            "target-games-0001",
            "spoken_command_alias",
            "show my games",
            _assistant_json("list_games", {}, "Showing your games."),
            source_function="list_games",
        ),
        _record(
            "target-music-0001",
            "spoken_command_alias",
            "list my music library",
            _assistant_json("list_music_library", {}, "Listing your music library."),
            source_function="list_music_library",
        ),
        _record(
            "target-music-0002",
            "spoken_command_alias",
            "turn shuffle on",
            _assistant_json("enable_shuffle", {}, "Turning shuffle on."),
            source_function="enable_shuffle",
        ),
        _record(
            "target-content-0001",
            "spoken_command_alias",
            "enter content mode",
            _assistant_json("enter_content_mode", {}, "Entering content mode."),
            source_function="enter_content_mode",
        ),
        _record(
            "target-content-0002",
            "spoken_command_alias",
            "I'm ready with the content",
            _assistant_json("mark_content_ready", {}, "Marking the content as ready."),
            source_function="mark_content_ready",
        ),
        _record(
            "target-content-0003",
            "spoken_command_alias",
            "make this text formal",
            _assistant_json("refine_text", {"mode": "formal"}, "Making the text formal."),
            source_function="refine_text",
        ),
        _record(
            "target-content-0004",
            "spoken_command_alias",
            "summarize this paragraph",
            _assistant_json("refine_text", {"mode": "summarize"}, "Summarizing the paragraph."),
            source_function="refine_text",
        ),
        _record(
            "target-content-0005",
            "spoken_command_alias",
            "make it bold",
            _assistant_json("format_bold", {}, "Making it bold."),
            source_function="format_bold",
        ),
        _record(
            "target-content-0006",
            "spoken_command_alias",
            "align center",
            _assistant_json("format_align", {"alignment": "center"}, "Center aligning the content."),
            source_function="format_align",
        ),
        _record(
            "target-memory-0001",
            "spoken_command_alias",
            "remember that I prefer quiet focus mode",
            _assistant_json("remember_this", {"fact": "User prefers quiet focus mode"}, "I'll remember that."),
            source_function="remember_this",
        ),
        _record(
            "target-memory-0002",
            "spoken_command_alias",
            "forget about my old address",
            _assistant_json("forget_about", {"topic": "old address"}, "Forgetting memories about your old address."),
            source_function="forget_about",
        ),
        _record(
            "target-memory-0003",
            "spoken_command_alias",
            "open memory panel",
            _assistant_json("show_memory_panel", {}, "Opening the memory panel."),
            source_function="show_memory_panel",
        ),
        _record(
            "target-goal-0001",
            "spoken_command_alias",
            "track my goal learn guitar",
            _assistant_json("track_goal", {"goal_name": "learn guitar"}, "Tracking your learn guitar goal."),
            source_function="track_goal",
        ),
        _record(
            "target-goal-0002",
            "spoken_command_alias",
            "mark my guitar goal completed",
            _assistant_json("update_goal", {"goal_name": "guitar", "status": "completed"}, "Marking your guitar goal completed."),
            source_function="update_goal",
        ),
        _record(
            "target-goal-0003",
            "spoken_command_alias",
            "how is my mood today",
            _assistant_json("get_my_mood", {}, "Checking your mood."),
            source_function="get_my_mood",
        ),
        _record(
            "target-capability-0001",
            "spoken_command_alias",
            "list your functions",
            _assistant_json("list_functions", {}, "Listing my functions."),
            source_function="list_functions",
        ),
        _record(
            "target-capability-0002",
            "spoken_command_alias",
            "show capabilities",
            _assistant_json("get_capabilities", {}, "Showing my capabilities."),
            source_function="get_capabilities",
        ),
        _record(
            "target-tts-0001",
            "spoken_command_alias",
            "what tts engine are you using",
            _assistant_json("get_tts_engine", {}, "Checking the current TTS engine."),
            source_function="get_tts_engine",
        ),
        _record(
            "target-tts-0002",
            "spoken_command_alias",
            "switch voice to male",
            _assistant_json("switch_tts_voice", {"voice": "male"}, "Switching voice to male."),
            source_function="switch_tts_voice",
        ),
        _record(
            "target-files-params-0001",
            "spoken_command_alias",
            "create a file called notes.txt",
            _assistant_json("create_file", {"file_path": "notes.txt"}, "Creating notes.txt."),
            source_function="create_file",
        ),
        _record(
            "target-files-params-0002",
            "spoken_command_alias",
            "rename report.txt to final_report.txt",
            _assistant_json("rename_file", {"file_path": "report.txt", "new_name": "final_report.txt"}, "Renaming report.txt."),
            source_function="rename_file",
        ),
        _record(
            "target-files-params-0003",
            "spoken_command_alias",
            "search files for budget pdf",
            _assistant_json("search_files", {"query": "budget", "file_type": "pdf"}, "Searching files for budget PDFs."),
            source_function="search_files",
        ),
        _record(
            "target-content-params-0001",
            "spoken_command_alias",
            "create a pdf called notes",
            _assistant_json("create_pdf", {"filename": "notes"}, "Creating a PDF called notes."),
            source_function="create_pdf",
        ),
    ]


def _clarification_and_safety_repairs() -> list[dict[str, Any]]:
    return [
        _record(
            "target-clarify-0001",
            "clarification_missing_target",
            "share this",
            _assistant_json(response="Which file or content should I share?"),
        ),
        _record(
            "target-clarify-0002",
            "clarification_missing_target",
            "connect bluetooth",
            _assistant_json(response="Which Bluetooth device should I connect to?"),
        ),
        _record(
            "target-safety-0001",
            "risky_confirmation",
            "clear all memory",
            _assistant_json(response="Please confirm: do you want me to clear all memory?"),
        ),
        _record(
            "target-safety-0002",
            "risky_confirmation",
            "sign out now",
            _assistant_json(response="Please confirm: do you want me to sign out now?"),
        ),
    ]


def _wake_address_records() -> list[dict[str, Any]]:
    """Post-gate address noise examples.

    The listener owns wake detection. These examples teach NLM to ignore common
    address/mishearing tokens after the runtime has already accepted a transcript.
    """
    return [
        _record(
            "wake-address-0001",
            "spoken_command_address_noise",
            "nexa reduce brightness",
            _assistant_json("decrease_brightness", {"amount": 10}, "Reducing brightness."),
            source_function="decrease_brightness",
        ),
        _record(
            "wake-address-0002",
            "spoken_command_address_noise",
            "hey next open chrome",
            _assistant_json("open_application", {"app_name": "chrome"}, "Opening Chrome."),
            source_function="open_application",
        ),
        _record(
            "wake-address-0003",
            "spoken_command_address_noise",
            "nexus set volume to 50",
            _assistant_json("set_volume", {"level": 50}, "Setting volume to 50."),
            source_function="set_volume",
        ),
        _record(
            "wake-address-0004",
            "spoken_command_address_noise",
            "lexa take a screen shot",
            _assistant_json("take_screenshot", {}, "Taking a screenshot."),
            source_function="take_screenshot",
        ),
    ]


def _sequencing_records() -> list[dict[str, Any]]:
    """Active-mode sequencing examples.

    NLM currently emits one function call, so chained commands should route the
    first step and acknowledge the follow-up step in the response.
    """
    return [
        _record(
            "sequence-0001",
            "follow_up_sequence",
            "reduce the brightness then open steam",
            _assistant_json("decrease_brightness", {"amount": 10}, "Reducing brightness, then I can open Steam."),
            source_function="decrease_brightness",
        ),
        _record(
            "sequence-0002",
            "follow_up_sequence",
            "reduce the brightness next open steam",
            _assistant_json("decrease_brightness", {"amount": 10}, "Reducing brightness, then I can open Steam."),
            source_function="decrease_brightness",
        ),
        _record(
            "sequence-0003",
            "follow_up_sequence",
            "set brightness to 40 after that open steam",
            _assistant_json("set_brightness", {"level": 40}, "Setting brightness to 40, then I can open Steam."),
            source_function="set_brightness",
        ),
        _record(
            "sequence-0004",
            "follow_up_sequence",
            "first open steam then play lofi music",
            _assistant_json("open_application", {"app_name": "steam"}, "Opening Steam, then I can play lofi music."),
            source_function="open_application",
        ),
        _record(
            "sequence-0005",
            "follow_up_sequence",
            "next song",
            _assistant_json("next_song", {}, "Playing the next song."),
            source_function="next_song",
        ),
        _record(
            "sequence-0006",
            "follow_up_sequence",
            "set volume to 30 then open chrome",
            _assistant_json("set_volume", {"level": 30}, "Setting volume to 30, then I can open Chrome."),
            source_function="set_volume",
        ),
        _record(
            "sequence-0007",
            "follow_up_sequence",
            "take a screenshot after that open photos",
            _assistant_json("take_screenshot", {}, "Taking a screenshot, then I can open Photos."),
            source_function="take_screenshot",
        ),
        _record(
            "sequence-0008",
            "follow_up_sequence",
            "close notepad then open calculator",
            _assistant_json("close_application", {"app_name": "notepad"}, "Closing Notepad, then I can open Calculator."),
            source_function="close_application",
        ),
        _record(
            "sequence-0009",
            "follow_up_sequence",
            "search youtube for python tutorials then play the first one",
            _assistant_json("search_youtube", {"query": "python tutorials"}, "Searching YouTube for python tutorials, then I can play the first result."),
            source_function="search_youtube",
        ),
        _record(
            "sequence-0010",
            "follow_up_sequence",
            "first show my battery then tell me the time",
            _assistant_json("get_battery_status", {}, "Checking your battery, then I can tell you the time."),
            source_function="get_battery_status",
        ),
        _record(
            "sequence-0011",
            "follow_up_sequence",
            "make it louder after that play lofi music",
            _assistant_json("increase_volume", {"amount": 10}, "Turning it up, then I can play lofi music."),
            source_function="increase_volume",
        ),
        _record(
            "sequence-0012",
            "follow_up_sequence",
            "open settings next check my battery",
            _assistant_json("open_application", {"app_name": "settings"}, "Opening Settings, then I can check your battery."),
            source_function="open_application",
        ),
        _record(
            "sequence-0013",
            "follow_up_sequence",
            "lower the volume now open discord",
            _assistant_json("decrease_volume", {"amount": 10}, "Lowering the volume, then I can open Discord."),
            source_function="decrease_volume",
        ),
        _record(
            "sequence-0014",
            "follow_up_sequence",
            "open edge and then search the web for weather",
            _assistant_json("open_application", {"app_name": "edge"}, "Opening Edge, then I can search the web for weather."),
            source_function="open_application",
        ),
        _record(
            "sequence-0015",
            "follow_up_sequence",
            "set brightness to 70 now take a screenshot",
            _assistant_json("set_brightness", {"level": 70}, "Setting brightness to 70, then I can take a screenshot."),
            source_function="set_brightness",
        ),
    ]


def _noisy_prompt(prompt: str) -> str:
    replacements = {
        "youtube": "you tube",
        "brightness": "bright nest",
        "volume": "volum",
        "chrome": "crome",
        "weather": "whether",
        "screenshot": "screen shot",
        "application": "app",
    }
    noisy = prompt.lower()
    for old, new in replacements.items():
        noisy = noisy.replace(old, new)
    if not noisy.startswith(("uh", "um")):
        noisy = "uh " + noisy
    return noisy.replace(",", "")


def generate_function_records(functions: list[FunctionSpec]) -> Iterable[dict[str, Any]]:
    for index, spec in enumerate(functions):
        params = _sample_parameters(spec)
        response = f"Okay, I'll handle {_humanize_function_name(spec.name)}."
        prompts = _voice_prompts(spec, params)

        yield _record(
            f"func-clean-{index:04d}",
            "spoken_command_clean",
            prompts[0],
            _assistant_json(spec.name, params, response),
            source_function=spec.name,
        )
        yield _record(
            f"func-natural-{index:04d}",
            "spoken_command_natural",
            prompts[1],
            _assistant_json(spec.name, params, response),
            source_function=spec.name,
        )
        yield _record(
            f"func-noisy-{index:04d}",
            "spoken_command_asr_noise",
            _noisy_prompt(prompts[2]),
            _assistant_json(spec.name, params, response),
            source_function=spec.name,
        )


def generate_behavior_records() -> list[dict[str, Any]]:
    examples: list[dict[str, Any]] = [
        _record(
            "follow-up-0001",
            "follow_up_pronoun",
            "I opened chrome earlier now close it",
            _assistant_json("close_application", {"app_name": "chrome"}, "Closing Chrome."),
            source_function="close_application",
        ),
        _record(
            "follow-up-0002",
            "follow_up_ordinal",
            "from the youtube results play the second one",
            _assistant_json("play_youtube_result", {"number": 2}, "Playing the second result."),
            source_function="play_youtube_result",
        ),
        _record(
            "follow-up-0003",
            "follow_up_correction",
            "open chrome no wait open edge",
            _assistant_json("open_application", {"app_name": "edge"}, "Opening Edge."),
            source_function="open_application",
        ),
        _record(
            "follow-up-0004",
            "follow_up_context",
            "make it louder",
            _assistant_json("increase_volume", {"amount": 10}, "Turning it up."),
            source_function="increase_volume",
        ),
        _record(
            "follow-up-0005",
            "follow_up_multi_step",
            "open notepad and make it full screen",
            _assistant_json("open_application", {"app_name": "notepad"}, "Opening Notepad, then I can maximize it."),
            source_function="open_application",
        ),
        _record(
            "clarify-0001",
            "clarification_missing_target",
            "nexa open it",
            _assistant_json(response="Which app should I open?"),
        ),
        _record(
            "clarify-0002",
            "clarification_missing_value",
            "set the volume",
            _assistant_json(response="What volume level should I set?"),
        ),
        _record(
            "clarify-0003",
            "clarification_ambiguous_context",
            "make it brighter",
            _assistant_json(response="Do you mean increase the screen brightness or brighten an image?"),
        ),
        _record(
            "clarify-0004",
            "clarification_partial_speech",
            "nexa can you just open the uh",
            _assistant_json(response="Which app or file should I open?"),
        ),
        _record(
            "memory-0001",
            "memory_first_question",
            "who is my study partner",
            _assistant_json("what_do_you_know", {"topic": "study partner"}, "Let me check my memory."),
            source_function="what_do_you_know",
        ),
        _record(
            "memory-0002",
            "memory_first_question",
            "do you remember my favorite color",
            _assistant_json("what_do_you_know", {"topic": "favorite color"}, "Let me check my memory."),
            source_function="what_do_you_know",
        ),
        _record(
            "capability-0001",
            "nexa_capability_qa",
            "what can you do right now",
            _assistant_json(
                response=(
                    "I can help with Windows apps, window control, volume and brightness, "
                    "music, YouTube when online, weather, screenshots, memory, and content mode."
                )
            ),
        ),
        _record(
            "capability-0002",
            "nexa_capability_qa",
            "can you work without internet",
            _assistant_json(
                response="Yes. I can still handle local apps, windows, system controls, music, memory, and conversation. Web features need online mode."
            ),
        ),
        _record(
            "capability-0003",
            "nexa_capability_qa",
            "what are your brain features",
            _assistant_json(
                response="I understand voice-style requests, route commands to NEXA functions, use memory when needed, handle follow-ups, and ask clarification when intent is unclear."
            ),
        ),
        _record(
            "conversation-0001",
            "assistant_behavior",
            "I'm tired and confused about what to study",
            _assistant_json(
                response="I hear you. Tell me what subject is stressing you most, and we can break it into a small first step."
            ),
        ),
        _record(
            "conversation-0002",
            "assistant_behavior",
            "thanks nexa you're helping me a lot",
            _assistant_json(response="Always, Boss. I'm glad I'm helping. What should we handle next?"),
        ),
        _record(
            "conversation-0002b",
            "assistant_behavior",
            "thanks nexa",
            _assistant_json(response="You're welcome, Boss. I'm glad I'm helping."),
        ),
        _record(
            "conversation-0003",
            "assistant_behavior",
            "I don't know what I was trying to do",
            _assistant_json(response="That's okay. Tell me the last thing you remember, and I'll help you find the next step."),
        ),
        _record(
            "conversation-0004",
            "assistant_behavior",
            "talk to me like an assistant not a search engine",
            _assistant_json(response="Understood. I'll keep it direct, helpful, and focused on what you need."),
        ),
        _record(
            "safety-0001",
            "risky_confirmation",
            "shutdown my laptop",
            _assistant_json(response="Please confirm: do you want me to shut down the computer?"),
        ),
        _record(
            "offline-0001",
            "offline_boundary",
            "search youtube for relaxing music while offline",
            _assistant_json(response="That needs online mode. I can play local music instead if you want."),
        ),
        _record(
            "safety-0002",
            "risky_confirmation",
            "restart the pc right now",
            _assistant_json(response="Please confirm: do you want me to restart the computer now?"),
        ),
        _record(
            "offline-0002",
            "offline_boundary",
            "what is the weather outside if internet is off",
            _assistant_json(response="Weather needs online mode. I can help with local system tasks while offline."),
        ),
    ]
    return (
        examples
        + _targeted_function_records()
        + _clarification_and_safety_repairs()
        + _wake_address_records()
        + _sequencing_records()
    )


def _bucket_for_record(record: dict[str, Any]) -> str:
    category = record["category"]
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
    return "function"


def _augment_record(record: dict[str, Any], new_id: str, rng: random.Random) -> dict[str, Any]:
    clone = json.loads(json.dumps(record, ensure_ascii=False))
    clone["id"] = new_id
    user_msg = clone["messages"][1]["content"]
    if rng.random() < 0.45:
        clone["messages"][1]["content"] = _noisy_prompt(user_msg)
        clone["category"] = f"{record['category']}_aug_noise"
    else:
        starters = ["hey nexa", "nexa please", "can you", "uh nexa"]
        clone["messages"][1]["content"] = f"{rng.choice(starters)} {user_msg}"
        clone["category"] = f"{record['category']}_aug_natural"
    return clone


def build_dataset(functions: list[FunctionSpec], count: int, seed: int) -> list[dict[str, Any]]:
    rng = random.Random(seed)
    base_records = list(generate_function_records(functions)) + generate_behavior_records()
    buckets: dict[str, list[dict[str, Any]]] = {
        "function": [],
        "follow_up": [],
        "conversation": [],
        "capability": [],
        "clarification": [],
        "safety": [],
    }
    for record in base_records:
        buckets[_bucket_for_record(record)].append(record)

    ratios = {
        "function": 0.45,
        "follow_up": 0.20,
        "conversation": 0.15,
        "capability": 0.10,
        "clarification": 0.05,
        "safety": 0.05,
    }
    target_counts = {bucket: int(count * ratio) for bucket, ratio in ratios.items()}
    target_counts["function"] += count - sum(target_counts.values())

    records: list[dict[str, Any]] = []
    for bucket, target in target_counts.items():
        source = buckets[bucket]
        if not source:
            continue
        selected = source[:target]
        records.extend(selected)
        while len(selected) < target:
            template = rng.choice(source)
            augmented = _augment_record(template, f"{template['id']}-aug-{bucket}-{len(selected):05d}", rng)
            selected.append(augmented)
            records.append(augmented)

    return records[:count]


def write_jsonl(records: Iterable[dict[str, Any]], output_path: Path) -> int:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            count += 1
    return count


def main() -> int:
    parser = argparse.ArgumentParser(description="Build NLM V1 JSONL fine-tuning data.")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--count", type=int, default=2000)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()

    functions = parse_function_registry(args.registry)
    if not functions:
        raise SystemExit(f"No functions found in registry: {args.registry}")

    records = build_dataset(functions, count=args.count, seed=args.seed)
    written = write_jsonl(records, args.output)
    print(f"Parsed {len(functions)} functions")
    print(f"Wrote {written} records to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
