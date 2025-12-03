@echo off
REM Nexa Launcher Script for Windows
REM This script activates the virtual environment and runs Nexa

echo.
echo ========================
echo   Starting Nexa AI...
echo ========================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv .venv
    echo Then run: .venv\Scripts\pip install -r requirements.txt
    pause
    exit /b 1
)

echo [OK] Using virtual environment Python
echo.

".venv\Scripts\python.exe" main.py

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] Nexa exited with error code: %ERRORLEVEL%
    pause
)
