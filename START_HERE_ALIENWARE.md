# NEXA NLM Alienware Training Pack

This pack contains only the files needed to train and evaluate the NEXA NLM LoRA on the Alienware laptop.

## Target

- Dataset: `datasets\nlm_v1\nlm_v1_pass4_10k_strict.jsonl`
- Eval seed: `datasets\nlm_v1\nlm_v1_eval_seed.jsonl`
- Output adapter: `models\nlm_v1_lora_pass4_10k_strict`
- Dashboard: `http://127.0.0.1:8765`

## Setup

Open PowerShell in this folder, then run:

```powershell
py -3.12 -m venv .venv-nlm
.\.venv-nlm\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install torch==2.10.0+cu128 torchvision==0.25.0+cu128 torchaudio==2.10.0+cu128 --index-url https://download.pytorch.org/whl/cu128
python -m pip install -r tools\nlm\requirements-nlm-training.txt
```

## Check Readiness

```powershell
python tools\nlm\check_training_readiness.py --dataset datasets\nlm_v1\nlm_v1_pass4_10k_strict.jsonl
python tools\nlm\audit_nlm_dataset.py --dataset datasets\nlm_v1\nlm_v1_pass4_10k_strict.jsonl
```

## Optional Dashboard

Open a second PowerShell window:

```powershell
.\.venv-nlm\Scripts\Activate.ps1
python tools\nlm\training_dashboard_server.py --log-dir data\nlm_logs --port 8765
```

Then open:

```text
http://127.0.0.1:8765
```

## Train

```powershell
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$env:HF_XET_HIGH_PERFORMANCE = "1"
$env:PYTHONUNBUFFERED = "1"

python -u tools\nlm\train_nlm_unsloth.py `
  --dataset datasets\nlm_v1\nlm_v1_pass4_10k_strict.jsonl `
  --output-dir models\nlm_v1_lora_pass4_10k_strict `
  --epochs 1 `
  --max-seq-length 2048 `
  --batch-size 1 `
  --grad-accum 8 `
  --logging-steps 5 `
  --save-steps 250 `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_train_pass4_10k_strict_$stamp.log"
```

## Evaluate

```powershell
python -u tools\nlm\run_lora_eval.py `
  --adapter models\nlm_v1_lora_pass4_10k_strict `
  --predictions datasets\nlm_v1\prototype_lora_pass4_10k_strict_predictions.jsonl `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_eval_pass4_10k_strict_$stamp.log"

python tools\nlm\score_nlm_eval.py `
  --eval datasets\nlm_v1\nlm_v1_eval_seed.jsonl `
  --predictions datasets\nlm_v1\prototype_lora_pass4_10k_strict_predictions.jsonl `
  --report-json data\nlm_reports\pass4_10k_strict_$stamp.json `
  --report-md data\nlm_reports\pass4_10k_strict_$stamp.md `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_score_pass4_10k_strict_$stamp.log"
```

## Copy Back After Training

Copy these back to the main NEXA machine:

```text
models\nlm_v1_lora_pass4_10k_strict
datasets\nlm_v1\prototype_lora_pass4_10k_strict_predictions.jsonl
data\nlm_logs
data\nlm_reports
```

## Pass 5 Tiny Repair

Use this only after pass4 exists locally at:

```text
models\nlm_v1_lora_pass4_10k_strict
```

Build or refresh the repair files:

```powershell
python tools\nlm\build_nlm_pass5_repair.py
```

Train pass5 by continuing from pass4:

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

Broad eval:

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

## Pass 6 Repaired 10k

Use this for the reliable promotion candidate. It trains fresh from the base model on a full repaired 10k dataset.

Build or refresh the repaired 10k:

```powershell
python tools\nlm\build_nlm_pass6_repaired_10k.py
```

Train Pass 6:

```powershell
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$env:HF_XET_HIGH_PERFORMANCE = "1"
$env:PYTHONUNBUFFERED = "1"

python -u tools\nlm\train_nlm_unsloth.py `
  --dataset datasets\nlm_v1\nlm_v1_pass6_10k_repaired.jsonl `
  --output-dir models\nlm_v1_lora_pass6_10k_repaired `
  --epochs 1 `
  --learning-rate 2e-4 `
  --max-seq-length 2048 `
  --batch-size 1 `
  --grad-accum 8 `
  --logging-steps 5 `
  --save-steps 250 `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_train_pass6_10k_repaired_$stamp.log"
```

Focused repair eval:

```powershell
python -u tools\nlm\run_lora_eval.py `
  --adapter models\nlm_v1_lora_pass6_10k_repaired `
  --eval datasets\nlm_v1\nlm_v1_pass5_repair_eval.jsonl `
  --predictions datasets\nlm_v1\prototype_lora_pass6_10k_repaired_focused_predictions.jsonl `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_eval_pass6_10k_repaired_focused_$stamp.log"

python tools\nlm\score_nlm_eval.py `
  --eval datasets\nlm_v1\nlm_v1_pass5_repair_eval.jsonl `
  --predictions datasets\nlm_v1\prototype_lora_pass6_10k_repaired_focused_predictions.jsonl `
  --report-json data\nlm_reports\pass6_10k_repaired_focused_$stamp.json `
  --report-md data\nlm_reports\pass6_10k_repaired_focused_$stamp.md `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_score_pass6_10k_repaired_focused_$stamp.log"
```

Broad eval:

```powershell
python -u tools\nlm\run_lora_eval.py `
  --adapter models\nlm_v1_lora_pass6_10k_repaired `
  --eval datasets\nlm_v1\nlm_v1_eval_seed.jsonl `
  --predictions datasets\nlm_v1\prototype_lora_pass6_10k_repaired_broad_predictions.jsonl `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_eval_pass6_10k_repaired_broad_$stamp.log"

python tools\nlm\score_nlm_eval.py `
  --eval datasets\nlm_v1\nlm_v1_eval_seed.jsonl `
  --predictions datasets\nlm_v1\prototype_lora_pass6_10k_repaired_broad_predictions.jsonl `
  --report-json data\nlm_reports\pass6_10k_repaired_broad_$stamp.json `
  --report-md data\nlm_reports\pass6_10k_repaired_broad_$stamp.md `
  2>&1 | Tee-Object -FilePath "data\nlm_logs\nlm_score_pass6_10k_repaired_broad_$stamp.log"
```
