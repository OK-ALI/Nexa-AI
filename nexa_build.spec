# -*- mode: python ; coding: utf-8 -*-
"""
Nexa AI Assistant - PyInstaller Build Specification
Created: December 1, 2025
Author: Ali Adil Waseem

This spec file bundles all necessary data files, models, and dependencies
for the Nexa AI Desktop Assistant.
"""

import os
import sys
from pathlib import Path

# Get the project root
PROJECT_ROOT = Path(SPECPATH)

# ============================================================================
# FIND PACKAGE PATHS FOR DATA FILES
# ============================================================================
import importlib.util

def find_package_dir(package_name):
    """Find package directory, return None if not found."""
    try:
        spec = importlib.util.find_spec(package_name)
        if spec and spec.origin:
            return Path(spec.origin).parent
    except:
        pass
    return None

# espeakng_loader - needs espeak-ng.dll AND espeak-ng-data folder
espeakng_dir = find_package_dir('espeakng_loader')

# kokoro_onnx - needs config.json
kokoro_dir = find_package_dir('kokoro_onnx')

# language_tags - needs data/json/*.json files
lang_tags_dir = find_package_dir('language_tags')

# phonemizer - needs share folder with .scm and .g2p files
phonemizer_dir = find_package_dir('phonemizer')

# DeepFilterNet - for noise cancellation (model files from AppData)
deepfilter_dir = find_package_dir('df')
deepfilter_model_path = Path.home() / 'AppData' / 'Local' / 'DeepFilterNet' / 'DeepFilterNet' / 'Cache' / 'DeepFilterNet3'

# ============================================================================
# DATA FILES TO BUNDLE
# ============================================================================
datas = []

# --- espeakng_loader: DLL + data folder (CRITICAL for Kokoro TTS) ---
if espeakng_dir:
    # The espeak-ng.dll
    dll_path = espeakng_dir / 'espeak-ng.dll'
    if dll_path.exists():
        datas.append((str(dll_path), 'espeakng_loader'))
    # The espeak-ng-data folder
    data_path = espeakng_dir / 'espeak-ng-data'
    if data_path.exists():
        datas.append((str(data_path), 'espeakng_loader/espeak-ng-data'))

# --- kokoro_onnx: config.json ---
if kokoro_dir:
    config_path = kokoro_dir / 'config.json'
    if config_path.exists():
        datas.append((str(config_path), 'kokoro_onnx'))

# --- language_tags: data/json folder ---
if lang_tags_dir:
    data_path = lang_tags_dir / 'data'
    if data_path.exists():
        datas.append((str(data_path), 'language_tags/data'))

# --- phonemizer: share folder ---
if phonemizer_dir:
    share_path = phonemizer_dir / 'share'
    if share_path.exists():
        datas.append((str(share_path), 'phonemizer/share'))

# --- DeepFilterNet: Python package + model files ---
if deepfilter_dir:
    # Bundle the entire df package
    datas.append((str(deepfilter_dir), 'df'))
    
# Bundle DeepFilterNet model files to the correct AppData-like location
if deepfilter_model_path.exists():
    # Bundle to _internal/df_models so we can set DF_MODELS environment variable
    datas.append((str(deepfilter_model_path), 'df_models/DeepFilterNet3'))

# --- Application data files ---
datas.extend([
    # Application assets
    (str(PROJECT_ROOT / 'assets'), 'assets'),
    
    # Themes (entire folder)
    (str(PROJECT_ROOT / 'Themes'), 'Themes'),
    
    # Config files
    (str(PROJECT_ROOT / 'config'), 'config'),
    
    # Voice models (Kokoro TTS)
    (str(PROJECT_ROOT / 'voice' / 'kokoro_models'), 'voice/kokoro_models'),
    
    # Whisper models directory (models will be downloaded on first run if not present)
    (str(PROJECT_ROOT / 'models' / 'whisper'), 'models/whisper'),
    
    # Data directory structure (empty dirs for runtime)
    (str(PROJECT_ROOT / 'data' / 'logs'), 'data/logs'),
    (str(PROJECT_ROOT / 'data' / 'speaker_profiles'), 'data/speaker_profiles'),
    (str(PROJECT_ROOT / 'data' / 'weather_cache'), 'data/weather_cache'),
])

# Filter out non-existent paths
datas = [(src, dst) for src, dst in datas if Path(src).exists()]

# ============================================================================
# HIDDEN IMPORTS
# ============================================================================
hiddenimports = [
    # Core dependencies
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    
    # Audio processing
    'pygame',
    'pygame.mixer',
    'soundfile',
    'pyaudio',
    
    # AI/ML
    'faster_whisper',
    'ctranslate2',
    'torch',
    'torchaudio',
    'onnxruntime',
    
    # Kokoro TTS
    'kokoro_onnx',
    'espeakng_loader',
    'phonemizer_fork',
    
    # DeepFilterNet noise cancellation
    'df',
    'df.enhance',
    'df.config',
    'df.io',
    'df.model',
    'deepfilternet',
    'deepfilterlib',
    
    # Windows integration
    'win32api',
    'win32con',
    'win32gui',
    'win32process',
    'pycaw',
    'pycaw.pycaw',
    'comtypes',
    'psutil',
    
    # Utilities
    'dotenv',
    'requests',
    'numpy',
    'colorama',
    'coloredlogs',
    'loguru',
    'pydantic',
    'reportlab',
    'reportlab.lib',
    'reportlab.lib.pagesizes',
    'reportlab.platypus',
    'reportlab.lib.styles',
    
    # Deep learning
    'deepfilternet',
    'df',
    'df.enhance',
    
    # Standard library that might be missed
    'encodings',
    'encodings.utf_8',
    'encodings.cp1252',
    'encodings.ascii',
]

# ============================================================================
# BINARY FILES
# ============================================================================
binaries = []

# ============================================================================
# ANALYSIS
# ============================================================================
a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'tkinter',
        'matplotlib',
        'IPython',
        'jupyter',
        'notebook',
        'pytest',
        'sphinx',
        # Exclude PyQt5 - we use PySide6
        'PyQt5',
        'PyQt5.sip',
        'PyQt5.QtCore',
        'PyQt5.QtGui',
        'PyQt5.QtWidgets',
        'PyQt6',
        'PyQt6.sip',
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
    ],
    noarchive=False,
    optimize=0,
)

# ============================================================================
# PYZ (Python bytecode archive)
# ============================================================================
pyz = PYZ(a.pure)

# ============================================================================
# EXECUTABLE
# ============================================================================
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Nexa AI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # BETA: Console enabled for privacy-safe status messages
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / 'assets' / 'icon.ico'),
    # Version info
    version=None,  # Can add version_info.txt for detailed version
)

# ============================================================================
# COLLECT (Bundle everything together)
# ============================================================================
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[
        # Don't compress these as it can cause issues
        'vcruntime140.dll',
        'python*.dll',
        'api-ms-win*.dll',
    ],
    name='Nexa AI',
)
