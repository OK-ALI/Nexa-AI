"""Local dashboard for NLM training, eval, and score logs.

Run this while NLM commands write logs to data/nlm_logs. The server uses only
the Python standard library so it can run inside the same training venv.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_LOG_DIR = REPO_ROOT / "data" / "nlm_logs"
DEFAULT_RUN_HISTORY = REPO_ROOT / "data" / "nlm_runs" / "run_history.json"

LOSS_RE = re.compile(
    r"\{'loss':\s*'?(?P<loss>[0-9.]+)'?.*?'learning_rate':\s*'?(?P<lr>[^',}]+)'?.*?'epoch':\s*'?(?P<epoch>[^',}]+)'?",
    re.I,
)
PROGRESS_RE = re.compile(r"(?P<percent>\d+)%\|.*?\|\s*(?P<step>\d+)/(?P<total>\d+)\s*\[(?P<elapsed>[^\]<]+)")
TRAIN_RESULT_RE = re.compile(
    r"\{'train_runtime':\s*'?(?P<runtime>[^',}]+)'?.*?'train_loss':\s*'?(?P<loss>[^',}]+)'?.*?'epoch':\s*'?(?P<epoch>[^',}]+)'?",
    re.I,
)
EVAL_SCORE_RE = re.compile(
    r"^(?P<name>Total|Valid JSON|Function accuracy|Parameter match|Response text match|Strict pass|Missing predictions|Extra predictions|Failures):\s*(?P<value>[0-9.]+%?)",
    re.M,
)
DATASET_RE = re.compile(r"\[\d\d:\d\d:\d\d\]\s+Dataset:\s*(?P<value>.+)")
OUTPUT_DIR_RE = re.compile(r"\[\d\d:\d\d:\d\d\]\s+Output dir:\s*(?P<value>.+)")
BASE_MODEL_RE = re.compile(r"\[\d\d:\d\d:\d\d\]\s+Base model:\s*(?P<value>.+)")
SAVED_ADAPTER_RE = re.compile(r"Saved LoRA adapter to\s+(?P<value>.+)")
LOADING_ADAPTER_RE = re.compile(r"Loading adapter:\s*(?P<value>.+)")
PREDICTIONS_RE = re.compile(r"Wrote\s+(?P<count>\d+)\s+predictions\s+to\s+(?P<value>.+)")
REPORT_JSON_RE = re.compile(r"^Report JSON:\s*(?P<value>.+)$", re.M)
FAILURE_LINE_RE = re.compile(r"^FAIL\s+(?P<id>[^:]+):\s*(?P<detail>.+)$", re.M)

SCORE_ORDER = ["Valid JSON", "Function accuracy", "Parameter match", "Response text match", "Strict pass"]


@dataclass
class DashboardConfig:
    log_dir: Path
    run_history_path: Path


def _decode_bytes(data: bytes) -> str:
    sample = data[:200]
    if sample.count(b"\x00") > max(8, len(sample) // 8):
        for encoding in ("utf-16", "utf-16-le"):
            try:
                return data.decode(encoding, errors="replace")
            except UnicodeError:
                continue
    return data.decode("utf-8", errors="replace")


def _read_text(path: Path, max_bytes: int | None = None) -> str:
    size = path.stat().st_size
    with path.open("rb") as handle:
        if max_bytes and size > max_bytes:
            handle.seek(size - max_bytes)
        data = handle.read()
    return _decode_bytes(data)


def _tail_text(path: Path, max_bytes: int = 120_000) -> str:
    return _read_text(path, max_bytes=max_bytes)


def _list_logs(log_dir: Path) -> list[Path]:
    if not log_dir.exists():
        return []
    return sorted(
        [path for path in log_dir.glob("*.log") if path.is_file()],
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )


def _safe_log_path(log_dir: Path, requested: str | None) -> Path | None:
    logs = _list_logs(log_dir)
    if requested:
        for log in logs:
            if log.name == requested:
                return log
        return None
    return logs[0] if logs else None


def _percent_to_float(value: str | None) -> float | None:
    if not value:
        return None
    try:
        return float(value.rstrip("%"))
    except ValueError:
        return None


def _parse_scores(text: str) -> dict[str, str]:
    return {match.group("name"): match.group("value") for match in EVAL_SCORE_RE.finditer(text)}


def _parse_failure_preview(text: str, limit: int = 8) -> list[dict[str, str]]:
    failures = []
    for match in FAILURE_LINE_RE.finditer(text):
        failures.append({"id": match.group("id"), "detail": match.group("detail")})
        if len(failures) >= limit:
            break
    return failures


def _parse_field(pattern: re.Pattern[str], text: str) -> str | None:
    match = pattern.search(text)
    return match.group("value").strip() if match else None


def _classify_log(path: Path, text: str) -> str:
    name = path.name.lower()
    if "score" in name or "Function accuracy:" in text:
        return "score"
    if "eval" in name or "Loading adapter:" in text or "predictions" in text:
        return "eval"
    if "train" in name or "Starting training" in text:
        return "train"
    if "readiness" in name:
        return "readiness"
    if "audit" in name:
        return "audit"
    return "log"


def _label_for_run(path: Path, kind: str) -> str:
    stem = path.stem.lower()
    if "baseline" in stem:
        return "Baseline"
    if "pass2" in stem:
        return "Prototype Pass 2"
    if "pass1" in stem:
        return "Prototype Pass 1"
    if "prototype_lora" in stem or "lora" in stem:
        return "Prototype LoRA"
    if kind == "score":
        return path.stem.replace("nlm_score_", "Score ")
    if kind == "train":
        return path.stem.replace("nlm_train_", "Train ")
    if kind == "eval":
        return path.stem.replace("nlm_eval_", "Eval ")
    return path.stem


def _parse_metrics(text: str) -> dict[str, object]:
    losses = []
    for match in LOSS_RE.finditer(text):
        losses.append(
            {
                "loss": float(match.group("loss")),
                "learning_rate": match.group("lr"),
                "epoch": match.group("epoch"),
            }
        )

    progress = None
    normalized = text.replace("\r", "\n")
    for match in PROGRESS_RE.finditer(normalized):
        progress = {
            "percent": int(match.group("percent")),
            "step": int(match.group("step")),
            "total": int(match.group("total")),
            "elapsed": match.group("elapsed"),
        }

    train_result = None
    result_match = TRAIN_RESULT_RE.search(text)
    if result_match:
        train_result = {
            "runtime": result_match.group("runtime"),
            "train_loss": result_match.group("loss"),
            "epoch": result_match.group("epoch"),
        }

    eval_scores = _parse_scores(text)

    predictions = None
    pred_match = PREDICTIONS_RE.search(text)
    if pred_match:
        predictions = {
            "count": int(pred_match.group("count")),
            "path": pred_match.group("value").strip(),
        }

    phase = "Waiting"
    phase_markers = [
        ("Importing Unsloth", "Loading"),
        ("Loading base model", "Loading"),
        ("Applying LoRA", "Preparing"),
        ("Loading JSONL dataset", "Preparing"),
        ("Creating SFTTrainer", "Preparing"),
        ("Starting training", "Training"),
        ("Saving LoRA adapter", "Saving"),
        ("Saved LoRA adapter", "Complete"),
        ("Loading adapter", "Evaluating"),
        ("Wrote 24 predictions", "Eval Complete"),
        ("Wrote 33 predictions", "Eval Complete"),
    ]
    for marker, label in phase_markers:
        if marker in text:
            phase = label
    if train_result:
        phase = "Complete"
    if eval_scores:
        phase = "Scored"

    return {
        "phase": phase,
        "progress": progress,
        "latest_loss": losses[-1] if losses else None,
        "losses": losses[-30:],
        "train_result": train_result,
        "eval_scores": eval_scores,
        "failure_preview": _parse_failure_preview(text),
        "predictions": predictions,
        "dataset": _parse_field(DATASET_RE, text),
        "output_dir": _parse_field(OUTPUT_DIR_RE, text),
        "base_model": _parse_field(BASE_MODEL_RE, text),
        "saved_adapter": _parse_field(SAVED_ADAPTER_RE, text),
        "loaded_adapter": _parse_field(LOADING_ADAPTER_RE, text),
        "report_json": _parse_field(REPORT_JSON_RE, text),
    }


def _build_run_record(path: Path) -> dict[str, object]:
    text = _read_text(path, max_bytes=700_000)
    metrics = _parse_metrics(text)
    kind = _classify_log(path, text)
    stat = path.stat()
    return {
        "id": path.stem,
        "label": _label_for_run(path, kind),
        "kind": kind,
        "log_name": path.name,
        "size": stat.st_size,
        "modified_ts": stat.st_mtime,
        "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
        "phase": metrics["phase"],
        "progress": metrics["progress"],
        "latest_loss": metrics["latest_loss"],
        "train_result": metrics["train_result"],
        "scores": metrics["eval_scores"],
        "failure_preview": metrics["failure_preview"],
        "predictions": metrics["predictions"],
        "dataset": metrics["dataset"],
        "output_dir": metrics["output_dir"],
        "base_model": metrics["base_model"],
        "adapter": metrics["saved_adapter"] or metrics["loaded_adapter"],
        "report_json": metrics["report_json"],
    }


def _load_run_history(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except Exception:
        return []
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict) and isinstance(data.get("runs"), list):
        return [item for item in data["runs"] if isinstance(item, dict)]
    return []


def _all_runs(config: DashboardConfig) -> list[dict[str, object]]:
    runs = [_build_run_record(path) for path in _list_logs(config.log_dir)]
    history_by_id = {str(item.get("id", "")): item for item in _load_run_history(config.run_history_path)}
    merged = []
    for run in runs:
        history = history_by_id.get(str(run["id"]), {})
        merged.append({**history, **run})
    return merged


def _comparison_payload(config: DashboardConfig) -> dict[str, object]:
    score_runs = [run for run in _all_runs(config) if run.get("scores")]
    score_runs.sort(key=lambda run: (float(run.get("modified_ts", 0.0)), str(run.get("log_name", ""))))
    rows = []
    previous: dict[str, object] | None = None
    for run in score_runs:
        scores = run.get("scores", {})
        if not isinstance(scores, dict):
            continue
        deltas = {}
        if previous and isinstance(previous.get("scores"), dict):
            previous_scores = previous["scores"]
            for metric in SCORE_ORDER:
                current_value = _percent_to_float(str(scores.get(metric, "")))
                previous_value = _percent_to_float(str(previous_scores.get(metric, "")))
                if current_value is not None and previous_value is not None:
                    deltas[metric] = round(current_value - previous_value, 2)
        rows.append(
            {
                "id": run["id"],
                "label": run["label"],
                "log_name": run["log_name"],
                "modified": run["modified"],
                "scores": scores,
                "deltas": deltas,
            }
        )
        previous = run
    latest = rows[-1] if rows else None
    return {
        "metrics": SCORE_ORDER,
        "runs": rows,
        "latest": latest,
    }


def _gpu_snapshot() -> dict[str, str] | None:
    try:
        output = subprocess.check_output(
            [
                "nvidia-smi",
                "--query-gpu=name,memory.total,memory.used,utilization.gpu,temperature.gpu",
                "--format=csv,noheader,nounits",
            ],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=2,
        ).strip()
    except Exception:
        return None
    if not output:
        return None
    name, total, used, util, temp = [part.strip() for part in output.split(",", 4)]
    return {
        "name": name,
        "memory_total_mb": total,
        "memory_used_mb": used,
        "utilization_percent": util,
        "temperature_c": temp,
    }


def _json_response(handler: BaseHTTPRequestHandler, payload: object, status: int = 200) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _html_response(handler: BaseHTTPRequestHandler) -> None:
    body = DASHBOARD_HTML.encode("utf-8")
    handler.send_response(200)
    handler.send_header("Content-Type", "text/html; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _make_handler(config: DashboardConfig) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/":
                _html_response(self)
                return
            if parsed.path == "/api/status":
                query = parse_qs(parsed.query)
                requested = query.get("log", [None])[0]
                logs = _list_logs(config.log_dir)
                log_path = _safe_log_path(config.log_dir, requested)
                text = _tail_text(log_path) if log_path else ""
                payload = {
                    "log_dir": str(config.log_dir),
                    "run_history": str(config.run_history_path),
                    "logs": [{"name": path.name, "size": path.stat().st_size} for path in logs[:40]],
                    "active_log": log_path.name if log_path else None,
                    "active_kind": _classify_log(log_path, text) if log_path else None,
                    "metrics": _parse_metrics(text),
                    "gpu": _gpu_snapshot(),
                    "tail": text.splitlines()[-220:],
                }
                _json_response(self, payload)
                return
            if parsed.path == "/api/runs":
                _json_response(self, {"runs": _all_runs(config)})
                return
            if parsed.path == "/api/comparison":
                _json_response(self, _comparison_payload(config))
                return
            _json_response(self, {"error": "not found"}, status=404)

        def log_message(self, format: str, *args: object) -> None:
            return

    return Handler


DASHBOARD_HTML = r"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>NLM Control Room</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #0d0f12;
      --panel: #171a1f;
      --panel-2: #20252c;
      --text: #f7f3ea;
      --muted: #a7adb8;
      --line: #303743;
      --mint: #6ee7b7;
      --coral: #fb7185;
      --amber: #fbbf24;
      --blue: #60a5fa;
      --ink: #0b0d10;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      min-height: 100vh;
      background: var(--bg);
      color: var(--text);
      font: 14px/1.45 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 20px;
      padding: 22px 28px 18px;
      border-bottom: 1px solid var(--line);
      background: #13161a;
    }
    h1 { margin: 0; font-size: 24px; letter-spacing: 0; }
    .sub { color: var(--muted); margin-top: 4px; }
    .status { display: flex; align-items: center; gap: 10px; min-width: 190px; justify-content: flex-end; }
    .dot { width: 10px; height: 10px; border-radius: 999px; background: var(--mint); box-shadow: 0 0 22px var(--mint); }
    main { max-width: 1440px; margin: 0 auto; padding: 22px; }
    .toolbar { display: flex; gap: 12px; align-items: center; margin-bottom: 18px; flex-wrap: wrap; }
    select, button {
      min-height: 38px;
      border: 1px solid var(--line);
      background: var(--panel);
      color: var(--text);
      border-radius: 6px;
      padding: 0 12px;
    }
    select { min-width: 360px; max-width: min(620px, 100%); }
    button { cursor: pointer; }
    .hint { color: var(--muted); margin-top: 4px; }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; margin-bottom: 16px; }
    .card { background: var(--panel); border: 1px solid var(--line); border-radius: 8px; padding: 16px; min-height: 112px; }
    .label { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .08em; }
    .value { font-size: 25px; margin-top: 10px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    .progress { height: 10px; background: #0c0d10; border-radius: 999px; overflow: hidden; margin-top: 12px; border: 1px solid #262b33; }
    .bar { height: 100%; width: 0%; background: linear-gradient(90deg, var(--mint), var(--blue), var(--amber)); transition: width .25s ease; }
    .columns { display: grid; grid-template-columns: minmax(0, 1.15fr) minmax(390px, .85fr); gap: 14px; margin-bottom: 14px; }
    .wide { margin-bottom: 14px; }
    pre {
      margin: 0;
      height: 480px;
      overflow: auto;
      white-space: pre-wrap;
      word-break: break-word;
      color: #d8dee9;
      font: 12px/1.5 "Cascadia Code", "Fira Code", ui-monospace, monospace;
    }
    .mini-list { display: grid; gap: 10px; margin-top: 12px; }
    .metric-row { display: flex; justify-content: space-between; gap: 12px; border-bottom: 1px solid var(--line); padding-bottom: 8px; }
    .metric-row:last-child { border-bottom: 0; }
    .ok { color: var(--mint); }
    .warn { color: var(--amber); }
    .bad { color: var(--coral); }
    table { width: 100%; border-collapse: collapse; margin-top: 12px; }
    th, td { border-bottom: 1px solid var(--line); padding: 10px 8px; text-align: left; vertical-align: top; }
    th { color: var(--muted); font-size: 12px; text-transform: uppercase; letter-spacing: .06em; }
    .delta { font-size: 12px; margin-left: 6px; }
    .pill {
      display: inline-flex;
      align-items: center;
      min-height: 24px;
      padding: 0 8px;
      border-radius: 999px;
      background: var(--panel-2);
      border: 1px solid var(--line);
      color: var(--muted);
      font-size: 12px;
    }
    .runs {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 10px;
      margin-top: 12px;
    }
    .run-card { background: #12151a; border: 1px solid var(--line); border-radius: 8px; padding: 12px; min-height: 110px; }
    .run-card strong { display: block; margin-bottom: 8px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .note-box {
      margin-top: 12px;
      border: 1px dashed #45505e;
      border-radius: 8px;
      padding: 12px;
      color: var(--muted);
      background: #111419;
    }
    @media (max-width: 1050px) {
      header, .toolbar { align-items: flex-start; flex-direction: column; }
      .status { justify-content: flex-start; }
      .grid, .columns, .runs { grid-template-columns: 1fr; }
      .value { white-space: normal; }
      select { min-width: 0; width: 100%; }
    }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>NLM Control Room</h1>
      <div class="sub">Training progress, evaluation scores, and run comparisons.</div>
    </div>
    <div class="status"><span class="dot"></span><span id="phase">Waiting</span></div>
  </header>
  <main>
    <div class="toolbar">
      <select id="logSelect" aria-label="Training log"></select>
      <button id="refreshBtn" type="button">Refresh</button>
      <span class="hint" id="logDir"></span>
    </div>
    <section class="grid">
      <div class="card">
        <div class="label">Progress</div>
        <div class="value" id="progressValue">--</div>
        <div class="progress"><div class="bar" id="progressBar"></div></div>
        <div class="hint" id="progressHint">Waiting for a training log.</div>
      </div>
      <div class="card">
        <div class="label">Latest Loss</div>
        <div class="value" id="lossValue">--</div>
        <div class="hint" id="lossHint">Loss appears every logging step.</div>
      </div>
      <div class="card">
        <div class="label">GPU</div>
        <div class="value" id="gpuValue">--</div>
        <div class="hint" id="gpuHint">nvidia-smi snapshot.</div>
      </div>
      <div class="card">
        <div class="label">Final Result</div>
        <div class="value" id="resultValue">--</div>
        <div class="hint" id="resultHint">Shown after training completes.</div>
      </div>
    </section>

    <section class="card wide">
      <div class="label">Evaluation Comparison</div>
      <table id="comparisonTable"></table>
    </section>

    <section class="columns">
      <div class="card">
        <div class="label">Live Log Tail</div>
        <pre id="tail"></pre>
      </div>
      <aside class="card">
        <div class="label">Selected Log Scores</div>
        <div class="mini-list" id="scores"></div>
        <div style="height:22px"></div>
        <div class="label">Recent Loss Points</div>
        <div class="mini-list" id="lossList"></div>
        <div style="height:22px"></div>
        <div class="label">Failure Preview</div>
        <div class="note-box" id="failurePreview">Select a score log to see strict eval failures.</div>
      </aside>
    </section>

    <section class="card">
      <div class="label">Recent Runs</div>
      <div class="runs" id="runs"></div>
    </section>
  </main>
  <script>
    let selectedLog = "";
    const $ = (id) => document.getElementById(id);

    function metricRow(name, value, cls = "") {
      const row = document.createElement("div");
      row.className = "metric-row";
      row.innerHTML = `<span>${name}</span><strong class="${cls}">${value}</strong>`;
      return row;
    }

    function deltaClass(value) {
      if (value > 0) return "ok";
      if (value < 0) return "bad";
      return "warn";
    }

    function renderComparison(data) {
      const table = $("comparisonTable");
      const runs = data.runs || [];
      const metrics = data.metrics || [];
      if (!runs.length) {
        table.innerHTML = `<tr><td class="hint">No score logs found yet. Run score_nlm_eval.py with Tee-Object to populate this table.</td></tr>`;
        return;
      }
      let html = "<thead><tr><th>Run</th>";
      for (const metric of metrics) html += `<th>${metric}</th>`;
      html += "</tr></thead><tbody>";
      for (const run of runs) {
        html += `<tr><td><strong>${run.label}</strong><div class="hint">${run.log_name}</div></td>`;
        for (const metric of metrics) {
          const value = run.scores[metric] || "--";
          const delta = run.deltas && run.deltas[metric];
          const deltaText = typeof delta === "number" ? `<span class="delta ${deltaClass(delta)}">${delta >= 0 ? "+" : ""}${delta.toFixed(1)}</span>` : "";
          html += `<td>${value}${deltaText}</td>`;
        }
        html += "</tr>";
      }
      html += "</tbody>";
      table.innerHTML = html;
    }

    function renderRuns(data) {
      const box = $("runs");
      const runs = (data.runs || []).slice(0, 9);
      box.innerHTML = "";
      if (!runs.length) {
        box.innerHTML = `<div class="hint">No logs found yet.</div>`;
        return;
      }
      for (const run of runs) {
        const card = document.createElement("div");
        card.className = "run-card";
        const score = run.scores && run.scores["Function accuracy"] ? `Function ${run.scores["Function accuracy"]}` : "";
        const loss = run.train_result ? `Loss ${run.train_result.train_loss}` : "";
        card.innerHTML = `
          <strong title="${run.log_name}">${run.label}</strong>
          <span class="pill">${run.kind}</span>
          <div class="hint">${run.phase || ""}</div>
          <div class="hint">${score || loss || run.modified}</div>
        `;
        box.appendChild(card);
      }
    }

    async function refresh() {
      const statusUrl = selectedLog ? `/api/status?log=${encodeURIComponent(selectedLog)}` : "/api/status";
      const [statusRes, runsRes, comparisonRes] = await Promise.all([
        fetch(statusUrl, { cache: "no-store" }),
        fetch("/api/runs", { cache: "no-store" }),
        fetch("/api/comparison", { cache: "no-store" })
      ]);
      const data = await statusRes.json();
      const runsData = await runsRes.json();
      const comparison = await comparisonRes.json();
      $("phase").textContent = data.metrics.phase || "Waiting";
      $("logDir").textContent = data.log_dir;

      const select = $("logSelect");
      const existing = Array.from(select.options).map((o) => o.value).join("|");
      const incoming = data.logs.map((l) => l.name).join("|");
      if (existing !== incoming) {
        select.innerHTML = "";
        for (const log of data.logs) {
          const option = document.createElement("option");
          option.value = log.name;
          option.textContent = `${log.name} (${Math.round(log.size / 1024)} KB)`;
          select.appendChild(option);
        }
      }
      if (data.active_log) {
        selectedLog = data.active_log;
        select.value = selectedLog;
      }

      const progress = data.metrics.progress;
      if (progress) {
        $("progressValue").textContent = `${progress.percent}%`;
        $("progressHint").textContent = `${progress.step}/${progress.total} steps, elapsed ${progress.elapsed}`;
        $("progressBar").style.width = `${progress.percent}%`;
      } else {
        $("progressValue").textContent = "--";
        $("progressHint").textContent = data.active_kind === "score" ? "Selected log is a score log." : "Waiting for progress lines.";
        $("progressBar").style.width = "0%";
      }

      const latest = data.metrics.latest_loss;
      if (latest) {
        $("lossValue").textContent = latest.loss.toFixed(4);
        $("lossHint").textContent = `epoch ${latest.epoch}, lr ${latest.learning_rate}`;
      } else {
        $("lossValue").textContent = "--";
        $("lossHint").textContent = "Loss appears every logging step.";
      }

      if (data.gpu) {
        $("gpuValue").textContent = `${data.gpu.utilization_percent}%`;
        $("gpuHint").textContent = `${data.gpu.name}, ${data.gpu.memory_used_mb}/${data.gpu.memory_total_mb} MB, ${data.gpu.temperature_c}C`;
      } else {
        $("gpuValue").textContent = "--";
        $("gpuHint").textContent = "nvidia-smi not available.";
      }

      const result = data.metrics.train_result;
      if (result) {
        $("resultValue").textContent = result.train_loss;
        $("resultHint").textContent = `runtime ${result.runtime}s, epoch ${result.epoch}`;
      } else if (data.metrics.predictions) {
        $("resultValue").textContent = `${data.metrics.predictions.count}`;
        $("resultHint").textContent = `predictions written`;
      } else {
        $("resultValue").textContent = "--";
        $("resultHint").textContent = "Shown after training completes.";
      }

      $("tail").textContent = data.tail.join("\n");

      const scores = $("scores");
      scores.innerHTML = "";
      const scoreEntries = Object.entries(data.metrics.eval_scores || {});
      if (scoreEntries.length) {
        for (const [name, value] of scoreEntries) {
          const numeric = Number(String(value).replace("%", ""));
          const cls = name === "Failures" && numeric > 0 ? "bad" : name === "Total" ? "warn" : "ok";
          scores.appendChild(metricRow(name, value, cls));
        }
      } else {
        scores.appendChild(metricRow("No eval scores", "yet", "warn"));
      }

      const failurePreview = $("failurePreview");
      const failures = data.metrics.failure_preview || [];
      const reportJson = data.metrics.report_json;
      if (failures.length) {
        failurePreview.innerHTML = failures.map((failure) => (
          `<div><strong class="bad">${failure.id}</strong><div>${failure.detail}</div></div>`
        )).join("<hr style='border:0;border-top:1px solid #303743;margin:10px 0'>");
        if (reportJson) failurePreview.innerHTML += `<div class="hint" style="margin-top:12px">Report: ${reportJson}</div>`;
      } else if (data.metrics.eval_scores && data.metrics.eval_scores["Failures"] === "0") {
        failurePreview.innerHTML = `<strong class="ok">No strict eval failures in this score log.</strong>`;
        if (reportJson) failurePreview.innerHTML += `<div class="hint" style="margin-top:12px">Report: ${reportJson}</div>`;
      } else {
        failurePreview.textContent = "Select a score log to see strict eval failures.";
      }

      const lossList = $("lossList");
      lossList.innerHTML = "";
      for (const item of (data.metrics.losses || []).slice(-8).reverse()) {
        lossList.appendChild(metricRow(`epoch ${item.epoch}`, item.loss.toFixed(4)));
      }
      if (!lossList.children.length) lossList.appendChild(metricRow("No loss", "yet", "warn"));

      renderComparison(comparison);
      renderRuns(runsData);
    }

    $("refreshBtn").addEventListener("click", refresh);
    $("logSelect").addEventListener("change", (event) => {
      selectedLog = event.target.value;
      refresh();
    });
    refresh();
    setInterval(refresh, 3000);
  </script>
</body>
</html>
"""


def main() -> int:
    parser = argparse.ArgumentParser(description="Serve a local NLM training dashboard.")
    parser.add_argument("--log-dir", type=Path, default=DEFAULT_LOG_DIR)
    parser.add_argument("--run-history", type=Path, default=DEFAULT_RUN_HISTORY)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()

    config = DashboardConfig(log_dir=args.log_dir.resolve(), run_history_path=args.run_history.resolve())
    config.log_dir.mkdir(parents=True, exist_ok=True)
    config.run_history_path.parent.mkdir(parents=True, exist_ok=True)
    server = ThreadingHTTPServer((args.host, args.port), _make_handler(config))
    url = f"http://{args.host}:{args.port}"
    print(f"NLM dashboard: {url}")
    print(f"Watching logs: {config.log_dir}")
    print(f"Run history: {config.run_history_path}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
