# NLM Dataset Tools

Utilities for building NEXA Large Model fine-tuning datasets.

The first builder reads `capabilities/function_registry.py` with Python's AST parser, so it does not import or initialize the full NEXA app. It emits JSONL chat records suitable for Unsloth SFT workflows.

Quick start:

```powershell
python tools\nlm\build_nlm_dataset.py --count 2000
```

Default output:

```text
datasets/nlm_v1/nlm_v1_prototype.jsonl
```

Audit the generated dataset before training:

```powershell
python tools\nlm\audit_nlm_dataset.py --dataset datasets\nlm_v1\nlm_v1_prototype.jsonl
```

Check whether the current machine can train:

```powershell
python tools\nlm\check_training_readiness.py
```

Watch training and eval logs in a local dashboard:

```powershell
python tools\nlm\training_dashboard_server.py --log-dir data\nlm_logs --port 8765
```

Then open `http://127.0.0.1:8765`.

Create an isolated Windows training venv:

```powershell
.\tools\nlm\setup_unsloth_windows.ps1
```

Or install manually:

```powershell
.\.venv-nlm\Scripts\python.exe -m pip uninstall -y torch torchvision torchaudio
.\.venv-nlm\Scripts\python.exe -m pip install --no-cache-dir --force-reinstall torch==2.10.0+cu128 torchvision==0.25.0+cu128 torchaudio==2.10.0+cu128 --index-url https://download.pytorch.org/whl/cu128
.\.venv-nlm\Scripts\python.exe -m pip install -r tools\nlm\requirements-nlm-training.txt
.\.venv-nlm\Scripts\python.exe tools\nlm\check_training_readiness.py
```

Build the seed eval set:

```powershell
python tools\nlm\build_nlm_eval_set.py
```

Run the current Ollama baseline and score it:

```powershell
python tools\nlm\run_ollama_eval.py --model llama3.1:8b-instruct-q4_K_M
python tools\nlm\score_nlm_eval.py `
  --predictions datasets\nlm_v1\baseline_ollama_predictions.jsonl `
  --report-json data\nlm_reports\baseline_score.json `
  --report-md data\nlm_reports\baseline_score.md
```

Run the trained LoRA prototype and score it:

```powershell
python -u tools\nlm\run_lora_eval.py --adapter models\nlm_v1_lora --predictions datasets\nlm_v1\prototype_lora_predictions.jsonl
python tools\nlm\score_nlm_eval.py `
  --predictions datasets\nlm_v1\prototype_lora_predictions.jsonl `
  --report-json data\nlm_reports\prototype_lora_score.json `
  --report-md data\nlm_reports\prototype_lora_score.md
```

Scoring is strict by default: exact function name, exact parameter object, and required response text fragments. The JSON report is intended for dashboard/failure review; the Markdown report is for human notes.

Training entrypoint:

```powershell
python tools\nlm\train_nlm_unsloth.py --dataset datasets\nlm_v1\nlm_v1_prototype.jsonl --output-dir models\nlm_v1_lora
```

Optional GGUF export after training:

```powershell
python tools\nlm\train_nlm_unsloth.py --save-gguf --gguf-quantization q4_k_m
```
