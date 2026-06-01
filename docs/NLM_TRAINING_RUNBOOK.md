# NLM Training Runbook

This runbook starts after `datasets/nlm_v1/nlm_v1_prototype.jsonl` has been generated and audited.

## 1. Check Readiness

```powershell
python tools\nlm\check_training_readiness.py
```

Training is ready only when these are OK:

- CUDA-enabled PyTorch, not CPU-only PyTorch;
- `unsloth`;
- `trl`;
- `datasets`;
- `accelerate`;
- `bitsandbytes`;
- NVIDIA GPU visible through `nvidia-smi`;
- NLM JSONL dataset exists.

## 2. Recommended Windows Path

For Windows, Unsloth documents Docker as the least painful route, and also supports direct Windows install when PyTorch is installed first. If training directly on Windows, Unsloth notes that `SFTTrainer` should use `dataset_num_proc=1`.

Because NEXA's app environment is not the same thing as a training environment, keep training dependencies separate from the app runtime.

Recommended options:

1. Docker or WSL training environment.
2. Separate local Python/venv with CUDA PyTorch and Unsloth.
3. Colab/Kaggle for the first prototype if local setup becomes slow.

To create a separate Windows venv:

```powershell
.\tools\nlm\setup_unsloth_windows.ps1
```

If PyTorch changes its CUDA wheel index, pass the current URL:

```powershell
.\tools\nlm\setup_unsloth_windows.ps1 -TorchIndexUrl "https://download.pytorch.org/whl/cu128"
```

Manual install path:

```powershell
py -3.12 -m venv .venv-nlm
.\.venv-nlm\Scripts\python.exe -m pip install --upgrade pip
.\.venv-nlm\Scripts\python.exe -m pip uninstall -y torch torchvision torchaudio
.\.venv-nlm\Scripts\python.exe -m pip install --no-cache-dir --force-reinstall torch==2.10.0+cu128 torchvision==0.25.0+cu128 torchaudio==2.10.0+cu128 --index-url https://download.pytorch.org/whl/cu128
.\.venv-nlm\Scripts\python.exe -m pip install -r tools\nlm\requirements-nlm-training.txt
.\.venv-nlm\Scripts\python.exe tools\nlm\check_training_readiness.py
```

If the PyTorch CUDA wheel index changes, use the current CUDA index from the official PyTorch install selector.

## 3. Start Prototype Training

This first run is **not the final NLM**. It is a prototype/smoke fine-tune:

- Dataset: `datasets/nlm_v1/nlm_v1_prototype.jsonl`
- Size: `2,000` examples
- Epochs: `1`
- Goal: prove the full pipeline works, then compare behavior against the baseline eval.
- Expected output: LoRA adapter in `models/nlm_v1_lora`

Optional live dashboard:

```powershell
python tools\nlm\training_dashboard_server.py --log-dir data\nlm_logs --port 8765
```

Open `http://127.0.0.1:8765` while training or eval commands write logs with `Tee-Object`. The dashboard tails the newest log, shows progress, latest loss, GPU usage, final train loss, eval scores, recent runs, and comparison tables when score logs exist.

Dashboard APIs:

- `http://127.0.0.1:8765/api/status`
- `http://127.0.0.1:8765/api/runs`
- `http://127.0.0.1:8765/api/comparison`

Use the conservative 8GB VRAM command first:

```powershell
$env:HF_XET_HIGH_PERFORMANCE = "1"
$env:PYTHONUNBUFFERED = "1"

python -u tools\nlm\train_nlm_unsloth.py `
  --dataset datasets\nlm_v1\nlm_v1_prototype.jsonl `
  --output-dir models\nlm_v1_lora `
  --epochs 1 `
  --max-seq-length 2048 `
  --batch-size 1 `
  --grad-accum 8 `
  --logging-steps 5 `
  --save-steps 100 `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_train_$stamp.log"
```

Training progress phases:

1. Import Unsloth and patch training libraries.
2. Download/load `unsloth/Llama-3.1-8B-Instruct`.
3. Apply LoRA adapters.
4. Load and format JSONL examples.
5. Start SFT training and print loss every `5` logging steps.
6. Save the adapter and tokenizer to `models/nlm_v1_lora`.

Optional GGUF export:

```powershell
python tools\nlm\train_nlm_unsloth.py --dataset datasets\nlm_v1\nlm_v1_prototype.jsonl --output-dir models\nlm_v1_lora --save-gguf --gguf-dir models\nlm_v1_gguf --gguf-quantization q4_k_m
```

## 4. Evaluate

Build the seed eval set:

```powershell
python tools\nlm\build_nlm_eval_set.py
```

Run the current Ollama model as a baseline:

```powershell
python tools\nlm\run_ollama_eval.py --model llama3.1:8b-instruct-q4_K_M
```

After inference predictions are generated, score them:

```powershell
python tools\nlm\score_nlm_eval.py `
  --eval datasets\nlm_v1\nlm_v1_eval_seed.jsonl `
  --predictions path\to\predictions.jsonl `
  --report-json data\nlm_reports\nscore_report.json `
  --report-md data\nlm_reports\nscore_report.md
```

Scoring is strict by default. Function names must match the registry contract exactly, parameters must match exactly, and required response fragments must be present. Use the failure list and JSON report to add targeted repair examples back into the dataset generator.

## Current Local Status

As of the latest readiness check:

- GPU exists: NVIDIA GeForce RTX 3080 Laptop GPU, 8GB VRAM.
- `.venv-nlm` uses CUDA PyTorch: `torch 2.10.0+cu128`.
- `torch.cuda` sees the RTX 3080 Laptop GPU.
- `unsloth`, `trl`, `datasets`, `accelerate`, and `bitsandbytes` are installed.
- Dataset audit passes.

The prototype run can start. After it finishes, evaluate it before expanding the dataset.

## 5. Next Steps After Prototype

1. Confirm `models/nlm_v1_lora` was created. Done.
2. Run inference over `datasets/nlm_v1/nlm_v1_eval_seed.jsonl`. Done.
3. Score prototype predictions against the baseline. Done.
4. Inspect wrong function names, wrong parameter names, unsafe calls, and weak assistant behavior.
5. Add failure cases back into the dataset generator.
6. Expand from 2k prototype to the 20k-30k V1 dataset.
7. Train V1, export GGUF, import into Ollama as `nexa-nlm:8b-q4_k_m`.

Wake-word policy before dataset expansion:

- Wake-word detection is a listener/runtime responsibility, not an NLM responsibility.
- NLM may learn to understand text after activation, including address noise like `hey nexa`, `nexa please`, `hey next`, or `nexus`.
- NLM should not decide whether an unaddressed transcript should wake NEXA.
- Keep fuzzy wake words conservative because `next` can mean both a misheard `Nexa` and a real command such as `next song`.
- Add explicit eval/test coverage for wake positives and false positives before widening the wake-word alias list.
- Treat `next`, `then`, `after that`, and `now` as sequencing words once NEXA is active.
- Add dataset/eval examples for chained commands such as `reduce the brightness, next open Steam`.
- Add listener tests for passive false positives such as `next work item`, `next song`, and `next open Steam`.

Prototype score:

- Valid JSON: 100.0%
- Function accuracy: 83.3%
- Parameter match: 79.2%
- Response text match: 95.8%

Prototype pass 2 score:

- Eval cases: 33-case repair eval
- Valid JSON: 100.0%
- Function accuracy: 100.0%
- Parameter match: 100.0%
- Response text match: 93.9%
- Notes: pass 2 fixed the prior wrong-function and wrong-parameter failures on the expanded eval seed, including time, battery, music, YouTube result, wake/address noise, and active-mode sequencing cases.

Current broad eval seed:

- Eval cases: 137
- Coverage: system, apps, windows, network, Bluetooth, display, web, YouTube, files, games, music, content mode, clipboard, memory, goals, theme, TTS, sequencing, correction, clarification, safety, offline boundaries, capability Q&A, and assistant behavior.
- Pass 2 broad score: valid JSON `100.0%`, function accuracy `63.5%`, parameter match `60.6%`, response text match `94.9%`.
- Pass 3 5k broad score: valid JSON `100.0%`, function accuracy `97.8%`, parameter match `97.8%`, response text match `99.3%`.
- Pass 3 5k strict score: valid JSON `100.0%`, function accuracy `97.8%`, exact parameter match `92.0%`, response text match `99.3%`, strict pass `91.2%`.
- Remaining pass 3 misses: `summarize this paragraph` chose `summarize_text` instead of `refine_text`; `how is my mood today` chose `what_do_you_know` instead of `get_my_mood`; `switch voice to male` chose `set_tts_voice` instead of `switch_tts_voice`.
- Strict scoring also caught extra-parameter drift, such as adding `count`, `query`, `text`, or `description` fields when the eval contract expected an empty or smaller parameter object.
- Status: pass 3 5k is a strong prototype checkpoint; next session should decide whether to add a tiny repair pass or expand toward 10k.
- Next scoring pass should include `--report-json` so the dashboard can show strict failure details.

Baseline score:

- Valid JSON: 100.0%
- Function accuracy: 41.7%
- Parameter match: 33.3%
- Response text match: 70.8%

Prototype LoRA eval:

```powershell
python -u tools\nlm\run_lora_eval.py `
  --adapter models\nlm_v1_lora `
  --predictions datasets\nlm_v1\prototype_lora_predictions.jsonl `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_eval_lora_$stamp.log"

python tools\nlm\score_nlm_eval.py `
  --eval datasets\nlm_v1\nlm_v1_eval_seed.jsonl `
  --predictions datasets\nlm_v1\prototype_lora_predictions.jsonl `
  --report-json data\nlm_reports\nprototype_lora_score_$stamp.json `
  --report-md data\nlm_reports\prototype_lora_score_$stamp.md `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_score_lora_$stamp.log"
```

Broad pass 2 eval:

```powershell
python -u tools\nlm\run_lora_eval.py `
  --adapter models\nlm_v1_lora_pass2 `
  --predictions datasets\nlm_v1\prototype_lora_pass2_broad_predictions.jsonl `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_eval_lora_pass2_broad_$stamp.log"

python tools\nlm\score_nlm_eval.py `
  --eval datasets\nlm_v1\nlm_v1_eval_seed.jsonl `
  --predictions datasets\nlm_v1\prototype_lora_pass2_broad_predictions.jsonl `
  --report-json data\nlm_reports\pass2_broad_score_$stamp.json `
  --report-md data\nlm_reports\pass2_broad_score_$stamp.md `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_score_pass2_broad_$stamp.log"
```

## Pass 5 Tiny Adapter Repair

Pass 4 10k strict on Alienware reached:

- Valid JSON: `100.0%`
- Function accuracy: `98.5%`
- Parameter match: `97.1%`
- Response text match: `99.3%`
- Strict pass: `96.4%`
- Failures: `5`

Pass 5 repairs only those five themes by continuing from the saved pass4 LoRA adapter.

Build or refresh the repair files:

```powershell
python tools\nlm\build_nlm_pass5_repair.py
```

Expected outputs:

```text
datasets\nlm_v1\nlm_v1_pass5_repair_600.jsonl
datasets\nlm_v1\nlm_v1_pass5_repair_eval.jsonl
```

Train pass5 from pass4:

```powershell
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$env:HF_XET_HIGH_PERFORMANCE = "1"
$env:PYTHONUNBUFFERED = "1"

python -u tools\nlm\train_nlm_unsloth.py `
  --adapter-model models\nlm_v1_lora_pass4_10k_strict `
  --dataset datasets\nlm_v1\nlm_v1_pass5_repair_600.jsonl `
  --output-dir models\nlm_v1_lora_pass5_repair `
  --epochs 2 `
  --learning-rate 5e-5 `
  --max-seq-length 2048 `
  --batch-size 1 `
  --grad-accum 8 `
  --logging-steps 5 `
  --save-steps 50 `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_train_pass5_repair_$stamp.log"
```

Focused repair eval:

```powershell
python -u tools\nlm\run_lora_eval.py `
  --adapter models\nlm_v1_lora_pass5_repair `
  --eval datasets\nlm_v1\nlm_v1_pass5_repair_eval.jsonl `
  --predictions datasets\nlm_v1\prototype_lora_pass5_repair_focused_predictions.jsonl `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_eval_pass5_repair_focused_$stamp.log"

python tools\nlm\score_nlm_eval.py `
  --eval datasets\nlm_v1\nlm_v1_pass5_repair_eval.jsonl `
  --predictions datasets\nlm_v1\prototype_lora_pass5_repair_focused_predictions.jsonl `
  --report-json data\nlm_reports\pass5_repair_focused_$stamp.json `
  --report-md data\nlm_reports\pass5_repair_focused_$stamp.md `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_score_pass5_repair_focused_$stamp.log"
```

Broad eval after focused eval passes:

```powershell
python -u tools\nlm\run_lora_eval.py `
  --adapter models\nlm_v1_lora_pass5_repair `
  --eval datasets\nlm_v1\nlm_v1_eval_seed.jsonl `
  --predictions datasets\nlm_v1\prototype_lora_pass5_repair_broad_predictions.jsonl `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_eval_pass5_repair_broad_$stamp.log"

python tools\nlm\score_nlm_eval.py `
  --eval datasets\nlm_v1\nlm_v1_eval_seed.jsonl `
  --predictions datasets\nlm_v1\prototype_lora_pass5_repair_broad_predictions.jsonl `
  --report-json data\nlm_reports\pass5_repair_broad_$stamp.json `
  --report-md data\nlm_reports\pass5_repair_broad_$stamp.md `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_score_pass5_repair_broad_$stamp.log"
```

Promotion criteria:

- Focused repair eval: `100%` strict pass.
- Broad eval: strict pass `>= 98.5%`.
- No new broad failures outside the original five unless the report shows an eval wording issue.
