param(
    [string]$VenvPath = ".venv-nlm",
    [string]$TorchIndexUrl = "https://download.pytorch.org/whl/cu128"
)

$ErrorActionPreference = "Stop"

Write-Host "Creating isolated NLM training environment at $VenvPath"
py -3.12 -m venv $VenvPath

$Python = Join-Path $VenvPath "Scripts\python.exe"

Write-Host "Upgrading pip"
& $Python -m pip install --upgrade pip

Write-Host "Installing CUDA PyTorch from $TorchIndexUrl"
& $Python -m pip uninstall -y torch torchvision torchaudio
& $Python -m pip install --no-cache-dir --force-reinstall torch==2.10.0+cu128 torchvision==0.25.0+cu128 torchaudio==2.10.0+cu128 --index-url $TorchIndexUrl

Write-Host "Installing Unsloth training stack"
& $Python -m pip install unsloth trl datasets accelerate bitsandbytes

Write-Host "Checking readiness"
& $Python tools\nlm\check_training_readiness.py

Write-Host "Done. Use this Python for training:"
Write-Host "  $Python tools\nlm\train_nlm_unsloth.py --dataset datasets\nlm_v1\nlm_v1_prototype.jsonl --output-dir models\nlm_v1_lora --epochs 1"
