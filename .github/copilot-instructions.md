# Nexa AI - Copilot Instructions

## Project Overview

Nexa is a **Windows voice-controlled AI desktop assistant** using Llama 3.1 8B (via Ollama) for all text processing. It's 100% local/offline-capable with GPU acceleration.

**Key Technologies:** Python 3.10+, PySide6 (Qt6), Faster-Whisper (STT), Kokoro TTS, Ollama, LanceDB (Smart Memory), PyTorch CUDA

## Architecture

### Core Components (`core/`)

| Component              | Purpose                                                                                                                  |
| ---------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| `brain.py`             | Central orchestrator - manages state machine (`NexaState`), coordinates all components, processes LLM responses          |
| `llm_manager.py`       | Ollama interface - single model architecture (Llama 3.1 8B for both online/offline), response caching, model pre-warming |
| `executor.py`          | Command execution hub - delegates to specialized controllers, inherits `QObject` for thread-safe signals                 |
| `function_registry.py` | 86+ registered functions - maps AI function calls to executor methods with skill tracking                                |
| `listener.py`          | Audio input - Faster-Whisper GPU transcription, Silero VAD, optional speaker verification                                |
| `tts.py`               | Kokoro TTS - af_heart voice, pygame playback, subprocess isolation to avoid CUDA DLL conflicts                           |
| `context_manager.py`   | Memory + history - integrates Smart Memory (LanceDB), action stack, conversation context                                 |
| `prompt_builder.py`    | LLM prompt construction - function catalog injection, error handling rules                                               |
| `youtube_service.py`   | YouTube play/search/download via yt-dlp (no API key), quality presets, progress hooks                                    |
| `web_scraper.py`       | Enhanced web search - DuckDuckGo + BeautifulSoup page scraping, returns actual content                                   |

### Data Flow

```
Microphone → AudioListener → NexaBrain.process_input() → LLMManager.generate()
    → JSON parsing → FunctionRegistry.call() → CommandExecutor → TTS response
```

### Smart Memory System (`core/smart_memory/`)

Uses LanceDB with sentence-transformers for semantic search:

- `SmartMemoryManager` - persistent vector storage
- `IntentState` - tracks multi-turn intent context
- `IntelligentLearner` - auto-learns from successful interactions

## Coding Conventions

### Function Registration Pattern

All system functions **must** be registered in `function_registry.py`:

```python
self.register(
    "function_name",
    self.executor.method_name,
    "Description for LLM",
    {"param_name": "param description"}
)
```

### Controller Modules

System features are split into specialized controllers in `core/`:

- `volume_controller.py`, `brightness_controller.py`, `wifi_controller.py`
- `application_controller.py`, `screen_controller.py`, `game_manager.py`

**Pattern:** Each controller is imported by `executor.py` and methods are registered in `function_registry.py`.

### Error Handling

Use `utils/error_handler.py`:

```python
from utils.error_handler import handle_error, ErrorCategory, ErrorSeverity

user_msg, recovered = handle_error(
    error=e,
    context="function_name",
    category=ErrorCategory.SYSTEM,
    severity=ErrorSeverity.MEDIUM
)
```

### LLM Response Format

The LLM returns JSON in two forms:

```json
// Function call
{"function_call": {"name": "open_application", "parameters": {"app_name": "chrome"}}, "response": "Opening Chrome"}

// Conversation only
{"response": "I'm doing great, thanks for asking!"}
```

## Critical Workflows

### Running the Application

```powershell
# Development
python main.py

# Or use the batch file
.\start_nexa.bat
```

### Prerequisites

1. **Ollama running** with model pulled: `ollama pull llama3.1:8b-instruct-q4_K_M`
2. **NVIDIA GPU** with CUDA 12.x for Faster-Whisper
3. **`.env` file** in project root with API keys (see `docs/NEXA_COMPLETE_DOCUMENTATION.md`)

### Adding New Commands

1. Create method in appropriate controller (or `executor.py`)
2. Register in `function_registry.py` with clear description
3. The LLM will automatically use it based on the description

### Building Executable

```powershell
pyinstaller nexa_build.spec
```

User data writes to `%LOCALAPPDATA%\Nexa AI` (UAC-safe).

## UI Architecture (`ui/`)

- `nexa_modern_window.py` - Main window, voice orb visualization
- `nexa_vision_player.py` - NEXA Vision Player (NVP) — dual-mode video player: YouTube (iframe embed, online) + Local (QMediaPlayer, offline). Movie library scans `D:\Movie`
- `nexa_pet_widget.py` - Desktop Companion (Nexa Companion) with 8 states (idle, listening, thinking, speaking, etc.)
- All UI inherits from PySide6 (Qt6) - use signals for cross-thread communication

## Project-Specific Notes

- **Wake word disabled** - responds to all speech (configurable in `listener.py`)
- **Model pre-warming** - Ollama model loaded at startup with 60-min keep_alive
- **Frozen app paths** - `sys._MEIPASS` for bundled assets, `%LOCALAPPDATA%\Nexa AI` for user data
- **CUDA DLL isolation** - TTS uses subprocess to avoid conflicts with Whisper
- **Phase-based development** - Currently at Phase 24 (100% API-free), see `docs/NEXA_PHASES_ROADMAP.md`
