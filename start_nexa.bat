@echo off
REM ============================================
REM   NEXA AI Launcher v3.0
REM   Layered Architecture + Core AI Kernel
REM ============================================

echo.
echo ================================
echo   Starting NEXA AI v3.0...
echo   Core AI Kernel:    ACTIVE
echo   Priority System:   ACTIVE
echo   GPU Scheduler:     ACTIVE
echo   Layered Arch:      ACTIVE
echo ================================
echo.

cd /d "%~dp0"

REM Check virtual environment
if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo.
    echo Please run the following commands:
    echo   python -m venv .venv
    echo   .venv\Scripts\pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Activate virtual environment
call .venv\Scripts\activate

REM Set UTF-8 encoding for kernel logs
set PYTHONIOENCODING=utf-8

echo [OK] Virtual environment activated
echo [OK] Architecture: config/ + core/ + capabilities/ + ui/
echo [OK] Kernel layers: kernel/ cognition/ memory/ interface/
echo [OK] Starting NEXA...
echo.

REM Use explicit venv python to avoid system Python conflicts
.venv\Scripts\python.exe main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] NEXA exited with error code: %ERRORLEVEL%
    pause
)
