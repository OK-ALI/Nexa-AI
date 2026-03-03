# 🤖 Nexa AI - Complete Documentation

**Version:** 2.0  
**Last Updated:** February 15, 2026  
**Project Completion:** 67.74% (21/31 Phases)  
**Status:** Production Ready with Active Development  
**Latest:** 🎨 Phase 17 (Particle Orb) ✅ | 🧠 Phase 20 (Smart Memory) ✅ | � Phase 21 (File Management) ✅ | 🔐 Login System ✅  
**Next Priority:** 🔄 Phase 15 - Universal Sharing Expansion

---

## 📑 Table of Contents

1. [Overview](#overview)
2. [Installation & Setup](#installation--setup)
3. [Features Overview](#features-overview)
4. [Voice Commands Reference](#voice-commands-reference)
5. [Configuration Guide](#configuration-guide)
6. [Content Mode Guide](#content-mode-guide)
7. [Music System](#music-system)
8. [Network Management](#network-management)
9. [System Control](#system-control)
10. [Games Integration](#games-integration)
11. [Screenshots](#screenshots)
12. [Weather Service](#weather-service)
13. [GPU Monitoring](#gpu-monitoring)
14. [Window Management](#window-management)
15. [Smart Memory](#smart-memory)
16. [Companion Mode (Coming Soon)](#companion-mode)
17. [Troubleshooting](#troubleshooting)
18. [API Reference](#api-reference)
19. [Performance Metrics](#performance-metrics)

---

## 🎯 Overview

### What is Nexa?

Nexa is a **hybrid AI desktop assistant** built for Windows that combines the power of voice control with intelligent system automation. Unlike cloud-dependent assistants, Nexa works **both online and offline**, ensuring privacy and functionality regardless of internet connectivity.

### Key Highlights

- **🎤 Voice-First Interface:** Natural language processing with 95%+ accuracy
- **🌐 Hybrid Mode:** Works online (Ollama) and offline (same model, limited features)
- **🔒 Privacy-Focused:** Speaker verification, local processing, no cloud dependency
- **⚡ Lightning Fast:** Sub-2 second response times, GPU-optimized
- **🎨 Beautiful UI:** Modern dark/light themes, customizable interface
- **🧠 Context-Aware:** Remembers recent actions, learns preferences
- **📚 Student-Focused:** Content Mode with 16 AI refinement tools
- **🎮 Gaming Ready:** Multi-platform game launcher (Steam, Epic, GOG)
- **🎵 Music Control:** Local music library management
- **📊 System Integration:** Deep Windows integration (WiFi, apps, volume, brightness)

### System Requirements

**Minimum:**
- Windows 10/11 (64-bit)
- 8GB RAM
- 4GB VRAM (NVIDIA GPU recommended)
- 10GB free disk space
- Microphone (for voice input)

**Recommended:**
- Windows 11
- 16GB RAM
- 8GB VRAM (NVIDIA RTX 3060 or better)
- 20GB free disk space
- Quality microphone (USB recommended)

---

## 🚀 Installation & Setup

### 1. Prerequisites

```powershell
# Install Python 3.10+
winget install Python.Python.3.10

# Install Ollama (for AI model)
winget install Ollama.Ollama

# Pull Llama 3.1 8B model
ollama pull llama3.1:8b-instruct-q4_K_M
```

### 2. Clone Repository

```powershell
git clone https://github.com/yourusername/Nexa-MyAI.git
cd Nexa-MyAI
```

### 3. Create Virtual Environment

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies

```powershell
pip install -r requirements.txt
```

### 5. Configure Environment

Create `.env` file in project root:

```env
# API Keys (Optional but Recommended)
WEATHER_API_KEY=your_openweathermap_api_key_here
WEATHER_DEFAULT_LOCATION=Karachi,PK

# Model Configuration
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=llama3.1:8b-instruct-q4_K_M

# Audio Settings
WHISPER_MODEL=large-v3-turbo
TTS_VOICE=af_heart

# Performance
WHISPER_DEVICE=cuda
WHISPER_COMPUTE_TYPE=float16
```

### 6. Download Models

```powershell
# Faster-Whisper downloads automatically on first run
# Kokoro TTS models included in repo
# SpeechBrain models download on first enrollment
```

### 7. Launch Nexa

```powershell
.\start_nexa.bat
```

### 8. First-Time Setup

1. **Speaker Enrollment** (Recommended):
   - Say "Enroll speaker" or "Setup speaker verification"
   - Speak 5 enrollment phrases clearly
   - Verification enabled automatically

2. **Wake Word Configuration**:
   - Default: "Hey Nexa" or just speak directly
   - Adjustable confidence threshold in config

3. **Music Library Setup**:
   - Add music to `data/music/` folder
   - Supported: MP3, WAV, FLAC, OGG, M4A
   - Nexa indexes automatically

---

## ✨ Features Overview

### Current Features (64.52% Complete)

| Category | Features | Status |
|----------|----------|--------|
| **Voice Control** | Speech recognition, TTS, Speaker verification | ✅ Complete |
| **Time & System** | Date/time queries, Battery status, GPU monitoring | ✅ Complete |
| **Application Control** | Open/close apps, Running apps list, Window management | ✅ Complete |
| **Volume Control** | Set/increase/decrease, Mute/unmute, Get current level | ✅ Complete |
| **Brightness** | Set/increase/decrease, Get current level | ✅ Complete |
| **Network (WiFi)** | Status, Connect/disconnect, List networks, Saved profiles | ✅ Complete |
| **Screenshots** | Full screen, Clipboard, Custom names, Open folder | ✅ Complete |
| **Music System** | Play/pause/stop, Next/previous, Shuffle/repeat, Library stats | ✅ Complete |
| **Weather** | Current weather, 5-day forecast, Auto-location | ✅ Complete |
| **Content Mode** | 16 AI refinement modes, PDF generation, Study tools | ✅ Complete |
| **Games** | Multi-platform launcher (Steam/Epic/GOG), Game detection | ✅ Complete |
| **Screen Reading** | OCR text extraction, Screen description | ✅ Complete |
| **Window Management** | Minimize/maximize/restore, Active window detection | ✅ Complete |
| **Notifications** | Read Action Center notifications | ✅ Complete |
| **Clipboard** | Copy/paste/cut, Select all, Delete selection | ✅ Complete |
| **Theme Control** | Dark/light themes, Manual toggle | ✅ Complete |
| **System Control** | Bluetooth, Display, Power plans, Night light (Phase 16) | ✅ Complete |
| **Modern Orb UI** | HTML5 Canvas particle orb, state transitions (Phase 17) | ✅ Complete |
| **Smart Memory** | LanceDB vectors, semantic search, memory panel (Phase 20) | ✅ Complete |
| **Login & Security** | User registration, password auth, lock screen | ✅ Complete |
| **File Management** | Create/move/copy/delete/rename, search, organize, compress (Phase 21) | ✅ Complete |
| **Companion Mode** | Thinking feedback, proactive engagement, emotional intelligence (Phases 28-30) | ✅ Complete |
| **YouTube Integration** | Play, search, download (quality options), progress bar (Phase 18) | ✅ Complete |
| **Enhanced Web Search** | Intelligent search with Wikipedia API, IMDB/SO extractors, intent routing (Phase 18) | ✅ Complete |

### Total Function Count: **180+ Registered Functions**

---

## 🎤 Voice Commands Reference

### Time & Information

```
"What time is it?"
"Tell me the date"
"What's the battery percentage?"
"Show battery status"
"What's the GPU usage?"
```

### Application Control

```
"Open Chrome"
"Launch Notepad"
"Close Chrome"
"Close this window"
"What apps are running?"
"Is Chrome running?"
"Minimize Chrome"
"Maximize this window"
"What's the active window?"
```

### Volume Control

```
"Set volume to 50"
"Increase volume"
"Decrease volume by 20"
"Mute"
"Unmute"
"What's the current volume?"
```

### Brightness Control

```
"Set brightness to 70"
"Increase brightness"
"Decrease brightness by 15"
"What's the brightness level?"
```

### Network (WiFi)

```
"What's my WiFi status?"
"Disconnect WiFi"
"List WiFi networks"
"Connect to [network name]"
"Show saved WiFi profiles"
```

### Screenshots

```
"Take a screenshot"
"Screenshot to clipboard"
"Take screenshot named bug_report"
"Open screenshots folder"
```

### Music Control

```
"Play music"
"Play [song name]"
"Play random music"
"Pause"
"Resume"
"Next song"
"Previous song"
"What's playing?"
"Stop music"
"Enable shuffle"
"Disable shuffle"
"Repeat one"
"Repeat all"
"Repeat off"
"How many songs do I have?"
"Suggest 5 songs"
"Play entire library"
"List all songs"
```

### Weather

```
"What's the weather?"
"Weather in London"
"Get forecast"
"Weather forecast for 3 days in Tokyo"
```

### Content Mode

```
"Open Content Mode"
"Enter Content Mode"

# Once in Content Mode:
"I'm ready" / "Content ready" / "Done pasting"
"Extract key terms"
"Make flashcards"
"Create study questions"
"Check difficulty"
"Fix grammar"
"Make it shorter"
"Improve this"
"Summarize"
"Make it formal"
"Make it casual"
"Paraphrase"
"Expand this"
"Simplify"
"Make it academic"
"Create outline"
"Add headings"
"Create PDF"
"Create PDF with bullets"
"Create formatted PDF"

"Exit Content Mode"
```

### YouTube (Online Mode Only)

```
"Play [song/video name] on YouTube"
"Play Thunder on YouTube"
"Search YouTube for cooking tutorials"
"Play number 3" (after search)
"Get video info"
"Download this video"
"Download this video in 4K"
"Download this video in 720p"
"Download the song as MP3"
"Download audio from [video name]"
"What's the download status?"
"Show YouTube queue"
"Clear YouTube queue"
```

### Smart Web Search (Online Mode Only)

```
"What is quantum computing?"
"Who won the World Cup 2024?"
"Tell me about [topic]"
"Read this page: [URL]"
"Scrape [URL]"
```

### Games

```
"Launch [game name]"
"Open [game name]"
"List all games"
"Show Steam games"
"List Epic games"
```

### Screen Reading

```
"Read the screen"
"What's on screen?"
"Describe screen"
```

### Window Management

```
"Close active window"
"Close this"
"Minimize active window"
"Maximize active window"
"Restore window"
```

### Notifications

```
"Read notifications"
"Check notifications"
```

### Clipboard

```
"Select all"
"Copy this"
"Paste"
"Cut this"
"Delete selection"
```

### File Management

```
"Create a file called notes.txt"
"Move report.pdf to documents"
"Copy this file to desktop"
"Delete old_backup.zip"
"Rename budget.xlsx to budget_2026.xlsx"
"Find all PDF files in documents"
"What did I download recently?"
"Check for duplicate files"
"Organize my downloads"
"Clean up downloads folder"
"Zip the project folder"
"Extract archive.zip"
"How big is this file?"
"List files in my documents"
```

### Theme

```
"Switch theme"
"Dark theme"
"Light theme"
"Toggle theme"
```

### System

```
"Clear conversation history"
"Forget our conversation"
"Open downloads folder"
"Open documents folder"
```

---

## ⚙️ Configuration Guide

### Configuration Files

#### 1. `.env` - Environment Variables

```env
# API Keys
WEATHER_API_KEY=your_key_here
WEATHER_DEFAULT_LOCATION=City,Country

# Model Settings
OLLAMA_BASE_URL=http://localhost:11434
MODEL_NAME=llama3.1:8b-instruct-q4_K_M

# Audio
WHISPER_MODEL=large-v3-turbo
TTS_VOICE=af_heart  # Options: af_heart, af, am, bf, bm

# Performance
WHISPER_DEVICE=cuda  # or 'cpu'
WHISPER_COMPUTE_TYPE=float16  # or 'int8', 'float32'
MAX_CONVERSATION_HISTORY=10
```

#### 2. `config/ui_preferences.json` - UI Settings

```json
{
  "theme": "dark",
  "window_size": {"width": 900, "height": 800},
  "always_on_top": false,
  "startup_position": "center"
}
```

#### 3. `data/user_prefs.json` - User Preferences

```json
{
  "speaker_verification_enabled": true,
  "wake_word_enabled": false,
  "auto_announce_songs": true,
  "weather_units": "metric"
}
```

### Advanced Configuration

#### Adjust Confidence Thresholds

In `core/listener.py`:

```python
# Line ~50
CONFIDENCE_THRESHOLD = 0.55  # Increase for stricter recognition (0.0-1.0)
```

#### Change Wake Word

In `core/listener.py`:

```python
# Line ~30
WAKE_WORDS = ["hey nexa", "hey alexa", "hey google"]  # Add your custom wake words
```

#### Modify TTS Voice

Available voices in `voice/kokoro_models/`:
- `af_heart` - American Female (Warm)
- `af` - American Female
- `am` - American Male
- `bf` - British Female
- `bm` - British Male

Set in `.env`:
```env
TTS_VOICE=bf  # British Female
```

#### GPU Memory Optimization

In `.env`:

```env
WHISPER_COMPUTE_TYPE=int8  # Lower memory usage
OLLAMA_GPU_LAYERS=35  # Reduce for less VRAM usage (default: 40)
```

---

## 📚 Content Mode Guide

### What is Content Mode?

Content Mode is Nexa's **text refinement workspace** designed specifically for students. It provides:

- ✍️ Large text editor window
- 🤖 16 AI-powered refinement modes
- 📄 PDF generation (3 formats)
- 📊 Real-time word count
- 🎯 Content status indicators

### Refinement Modes (16 Total)

#### Study Tools (4 modes)

| Mode | Command | Purpose |
|------|---------|---------|
| `extract_terms` | "Extract key terms" | Generate vocabulary list |
| `flashcards` | "Make flashcards" | Create Q&A study cards |
| `study_questions` | "Create study questions" | Generate test questions |
| `difficulty_check` | "Check difficulty" | Analyze reading level |

#### Writing Enhancement (6 modes)

| Mode | Command | Purpose |
|------|---------|---------|
| `formal` | "Make it formal" | Professional tone |
| `casual` | "Make it casual" | Conversational style |
| `grammar_only` | "Fix grammar" | Correct errors only |
| `improve` | "Improve this" | Overall enhancement |
| `shorter` | "Make it shorter" | Reduce length |
| `summarize` | "Summarize" | Key points extraction |

#### Content Transformation (4 modes)

| Mode | Command | Purpose |
|------|---------|---------|
| `paraphrase` | "Paraphrase" | Rewrite differently |
| `expand` | "Expand this" | Add more detail |
| `simplify` | "Simplify" | Easier to understand |
| `academic` | "Make it academic" | Scholarly writing |

#### Organization (2 modes)

| Mode | Command | Purpose |
|------|---------|---------|
| `outline` | "Create outline" | Hierarchical structure |
| `add_headings` | "Add headings" | Section titles |

### Word Limits

- **Minimum:** 50 words (required before processing)
- **Maximum:** 500 words (upper limit)

### PDF Generation Formats

1. **Simple Text** (`simple_text`):
   - Plain paragraph formatting
   - Basic styling
   - Quick generation

2. **With Bullets** (`with_bullets`):
   - Bullet point lists
   - Better readability
   - Structured content

3. **Formatted Paragraphs** (`formatted_paragraphs`):
   - Advanced formatting
   - Headings and sections
   - Professional appearance

### Usage Workflow

1. **Enter Content Mode:**
   ```
   "Open Content Mode"
   ```

2. **Paste/Type Content:**
   - Click text area
   - Paste or type your content
   - Minimum 50 words required

3. **Mark Ready:**
   ```
   "I'm ready"
   "Content ready"
   "Done pasting"
   ```

4. **Refine Content:**
   ```
   "Extract key terms"
   "Fix grammar"
   "Make it academic"
   ```

5. **Generate PDF (Optional):**
   ```
   "Create PDF"
   "Create PDF with bullets"
   "Create formatted PDF named Essay_Final"
   ```

6. **Exit:**
   ```
   "Exit Content Mode"
   ```

### PDF Storage Location

PDFs saved to: `C:\Users\[YourName]\Documents\Nexa PDFs\`

---

## 🎵 Music System

### Supported Formats

- MP3
- WAV
- FLAC
- OGG
- M4A

### Setup Music Library

1. Create folder structure:
   ```
   data/music/
   ├── Artist 1/
   │   ├── Album 1/
   │   │   └── song1.mp3
   │   └── song2.mp3
   └── song3.mp3
   ```

2. Nexa automatically indexes all music files

3. Verify library:
   ```
   "How many songs do I have?"
   ```

### Playback Modes

#### Repeat Modes

- **Off:** Play through library once
- **One:** Repeat current song
- **All:** Loop entire library

```
"Repeat off"
"Repeat one"
"Repeat all"
```

#### Shuffle Mode

```
"Enable shuffle"  # Random order
"Disable shuffle"  # Sequential order
```

### Music Commands

| Command | Action |
|---------|--------|
| `play music` | Play random song |
| `play [song name]` | Play specific song |
| `pause` | Pause playback |
| `resume` / `continue` | Resume paused song |
| `stop` | Stop completely |
| `next song` | Skip to next |
| `previous song` | Go back |
| `what's playing?` | Current song info |
| `suggest 5 songs` | Random recommendations |

### Music Library Stats

```
"How many songs?"
# Returns: Total songs, artists, total playtime
```

### Auto-Announcement

Nexa automatically announces song names when tracks change (configurable in `data/user_prefs.json`)

---

## 🌐 Network Management

### WiFi Commands

#### Get Status

```
"What's my WiFi status?"
"Check WiFi connection"
```

Returns:
- Connection state (Connected/Disconnected)
- Network name (SSID)
- Signal strength

#### List Available Networks

```
"List WiFi networks"
"Show available WiFi"
```

Shows all networks in range with signal strength.

#### Connect to Network

```
"Connect to [network name]"
"Join [network name]"
```

**Note:** Network must have saved credentials or be open.

#### Disconnect

```
"Disconnect WiFi"
"Turn off WiFi"
```

#### Saved Profiles

```
"Show saved WiFi profiles"
"List WiFi profiles"
```

Lists all saved network configurations.

---

## 🖥️ System Control

### Volume Control

| Command | Result |
|---------|--------|
| `set volume to 50` | Set to 50% |
| `increase volume` | +10% |
| `increase volume by 20` | +20% |
| `decrease volume` | -10% |
| `mute` | Mute audio |
| `unmute` | Restore volume |
| `what's the volume?` | Get current level |

### Brightness Control

| Command | Result |
|---------|--------|
| `set brightness to 70` | Set to 70% |
| `increase brightness` | +10% |
| `decrease brightness by 15` | -15% |
| `what's the brightness?` | Get current level |

### Battery Information

```
"Battery status"  # Full details + time remaining
"Battery percentage"  # Just the percentage
```

### GPU Monitoring

```
"What's the GPU usage?"
"GPU memory"
```

Returns:
- Current VRAM usage
- Total VRAM
- Percentage used
- Free memory
- Loaded models

---

## 🎮 Games Integration

### Supported Platforms

- ✅ **Steam** - Full support
- ✅ **Epic Games** - Full support
- ✅ **GOG Galaxy** - Full support
- ✅ **Standalone** - Manual executable paths

### Launch Games

```
"Launch Cyberpunk 2077"
"Open Witcher 3"
"Play Fortnite"
```

Nexa automatically detects the correct platform.

### List Games

```
"List all games"  # All platforms
"Show Steam games"  # Steam only
"List Epic games"  # Epic only
"Show GOG games"  # GOG only
```

### Game Detection

Nexa scans:
- Steam library folders
- Epic Games manifests
- GOG Galaxy database
- Common installation directories

### Manual Game Addition

For standalone games, add to `core/game_manager.py`:

```python
STANDALONE_GAMES = {
    "Game Name": r"C:\Path\To\Game.exe"
}
```

---

## 📸 Screenshots

### Basic Screenshot

```
"Take a screenshot"
```

Saves to: `Pictures/Nexa Screenshots/screenshot_YYYYMMDD_HHMMSS.png`

### Screenshot to Clipboard

```
"Screenshot to clipboard"
"Copy screenshot"
```

Copies image to clipboard for pasting.

### Named Screenshots

```
"Take screenshot named bug_report"
"Screenshot named meeting_notes"
```

Saves as: `bug_report_YYYYMMDD_HHMMSS.png`

### Open Screenshots Folder

```
"Open screenshots folder"
"Show screenshots"
```

Opens: `C:\Users\[YourName]\Pictures\Nexa Screenshots\`

---

## 🌤️ Weather Service

### Setup

1. Get free API key from [OpenWeatherMap](https://openweathermap.org/api)
2. Add to `.env`:
   ```env
   WEATHER_API_KEY=your_key_here
   WEATHER_DEFAULT_LOCATION=Karachi,PK
   ```

### Current Weather

```
"What's the weather?"  # Uses default location
"Weather in London"  # Specific city
"Weather in Tokyo, Japan"  # City + country
```

Returns:
- Temperature
- Conditions (sunny, cloudy, rainy, etc.)
- Humidity
- Wind speed
- "Feels like" temperature

### Weather Forecast

```
"Get forecast"  # 3-day default
"Weather forecast for 5 days"
"Forecast for New York"
"3-day forecast in Paris"
```

Returns daily forecast:
- High/low temperatures
- Weather conditions
- Precipitation chance

### Location Detection

If location not specified, uses:
1. Command-specified location
2. Default from `.env`
3. Auto-detection (if enabled)

### Caching

Weather data cached for 30 minutes to reduce API calls.

---

## 📊 GPU Monitoring

### Real-Time Monitoring

Nexa continuously monitors GPU usage in the background.

### Get GPU Info

```
"What's the GPU usage?"
"GPU memory"
"Check VRAM"
```

Returns:
- Current VRAM usage (MB)
- Total VRAM (MB)
- Usage percentage
- Free memory
- Currently loaded models

### GPU Reports

Automatically generated on shutdown:
- Usage graph (PNG)
- Detailed report (Markdown)
- Session statistics

Location: `data/logs/gpu_reports/`

### Models Tracked

- Faster-Whisper (large-v3-turbo)
- Llama 3.1 8B
- SpeechBrain ECAPA-TDNN

---

## 🪟 Window Management

### Window Operations

| Command | Action |
|---------|--------|
| `close this` | Close active window |
| `close active window` | Close foreground window |
| `minimize Chrome` | Minimize specific app |
| `maximize active window` | Maximize current window |
| `restore window` | Return to normal size |
| `what's the active window?` | Get window title |

### Smart Window Detection

Nexa can:
- Detect active/foreground windows
- Find windows by application name
- Handle multiple instances
- Work with minimized apps

---

## 🔧 Troubleshooting

### Common Issues

#### 1. Nexa Not Recognizing Voice

**Solutions:**
- Check microphone permissions in Windows Settings
- Increase confidence threshold: `core/listener.py` line ~50
- Test microphone in Windows Sound Settings
- Ensure microphone is default recording device

#### 2. Slow AI Responses

**Solutions:**
- Check GPU usage: `"What's the GPU usage?"`
- Reduce VRAM usage: Set `WHISPER_COMPUTE_TYPE=int8` in `.env`
- Close other GPU-intensive apps
- Ensure Ollama is running: `ollama list`

#### 3. "Model Not Found" Error

**Solution:**
```powershell
ollama pull llama3.1:8b-instruct-q4_K_M
```

#### 4. Music Not Playing

**Solutions:**
- Verify music files in `data/music/`
- Check supported formats (MP3, WAV, FLAC, OGG, M4A)
- Restart Nexa to re-index library
- Check system audio not muted

#### 5. Weather Not Working

**Solutions:**
- Verify `WEATHER_API_KEY` in `.env`
- Check API key is active at OpenWeatherMap
- Test internet connection
- Check logs for API errors

#### 6. Content Mode Window Not Closing

**Solution:**
Fixed in latest version. Signal/Slot mechanism ensures thread-safe closing.

### Log Files

Logs location: `data/logs/`

Key logs:
- `nexa_info.log` - Main application log
- `gpu_reports/` - GPU usage reports

### Performance Tips

1. **Reduce VRAM Usage:**
   ```env
   WHISPER_COMPUTE_TYPE=int8
   OLLAMA_GPU_LAYERS=30
   ```

2. **Improve Recognition:**
   - Use quality USB microphone
   - Reduce background noise
   - Speak clearly at normal pace

3. **Faster Responses:**
   - Keep GPU usage under 90%
   - Close unnecessary apps
   - Use SSD for faster model loading

---

## 📖 API Reference

### Core Classes

#### NexaBrain

Main AI processing engine.

```python
from core.brain import NexaBrain, NexaState
from core.config import Config

config = Config()
brain = NexaBrain(config)
brain.start()
```

**States:**
- `IDLE` - Ready for input
- `LISTENING` - Capturing audio
- `THINKING` - Processing AI
- `RESPONDING` - Speaking output
- `WORKING` - Executing task

#### CommandExecutor

Executes system-level commands.

```python
from core.executor import CommandExecutor

executor = CommandExecutor(config)
result = executor.open_application("chrome")
```

#### FunctionRegistry

Manages callable functions.

```python
from core.function_registry import FunctionRegistry

registry = FunctionRegistry(executor)
result = registry.call("get_current_time", {})
```

### Function Categories

**Time & System:**
- `get_current_time()`
- `get_current_date()`
- `get_battery_status()`
- `get_battery_percentage()`
- `get_gpu_usage()`

**Application Control:**
- `open_application(app_name)`
- `close_application(app_name)`
- `close_active_window()`
- `get_running_applications()`
- `is_application_running(app_name)`

**Volume:**
- `set_volume(level)`
- `get_current_volume()`
- `increase_volume(amount=10)`
- `decrease_volume(amount=10)`
- `mute_volume()`
- `unmute_volume()`

**Brightness:**
- `set_brightness(level)`
- `get_current_brightness()`
- `increase_brightness(amount=10)`
- `decrease_brightness(amount=10)`

**Network:**
- `get_wifi_status()`
- `disconnect_wifi()`
- `connect_wifi(network_name)`
- `list_wifi_networks()`
- `get_saved_wifi_profiles()`

**Screenshots:**
- `take_screenshot(custom_name=None)`
- `take_screenshot_clipboard(custom_name=None)`
- `open_screenshots_folder()`

**Music:**
- `play_music(song_name=None)`
- `play_random_music()`
- `pause_music()`
- `resume_music()`
- `stop_music()`
- `next_song()`
- `previous_song()`
- `whats_playing()`
- `enable_shuffle()`
- `disable_shuffle()`
- `set_repeat_mode(mode)`

**Weather:**
- `get_weather(location=None)`
- `get_forecast(location=None, days=3)`

**Content Mode:**
- `enter_content_mode()`
- `exit_content_mode()`
- `mark_content_ready()`
- `refine_text(mode, text=None)`
- `create_pdf(pdf_format='simple_text', filename=None, text=None, title=None)`

**Games:**
- `launch_game(game_name)`
- `list_games(platform=None)`

**Window Management:**
- `minimize_window(app_name)`
- `maximize_window(app_name)`
- `restore_window(app_name)`
- `get_active_window()`

**Screen Reading:**
- `read_screen_content()`
- `describe_screen()`

**Clipboard:**
- `select_all_text()`
- `copy_selected_text()`
- `paste_clipboard()`
- `cut_selected_text()`
- `delete_selected_text()`

---

## 📈 Performance Metrics

### Response Times

| Operation | Average Time | Target |
|-----------|--------------|--------|
| Wake word detection | 0.3s | < 0.5s |
| Speech recognition | 0.8s | < 1.0s |
| AI processing (online) | 1.2s | < 2.0s |
| AI processing (offline) | 1.5s | < 2.5s |
| TTS generation | 0.6s | < 1.0s |
| Function execution | 0.1s | < 0.2s |
| **Total (user request → response)** | **1.8s** | **< 2.5s** |

### Accuracy Metrics

| Metric | Current | Target |
|--------|---------|--------|
| Speech recognition accuracy | 95%+ | 95%+ ✅ |
| Command understanding | 93%+ | 90%+ ✅ |
| Function execution success | 98%+ | 95%+ ✅ |
| Test suite pass rate | 98.7% (150/152) | 90%+ ✅ |

### Resource Usage

| Resource | Typical | Peak |
|----------|---------|------|
| RAM | 1.2GB | 1.8GB |
| VRAM | 7.0GB | 7.6GB |
| CPU | 5-10% | 25% |
| Disk I/O | Minimal | Moderate |

### System Stability

- **Uptime:** 3+ hours continuous operation
- **Crashes:** < 1 per 100 commands
- **Memory leaks:** None detected
- **GPU stability:** Excellent (93% usage sustained)

---

## 🎓 Educational Resources

### For Students

Content Mode provides:
- **Vocabulary extraction** for studying
- **Flashcard generation** for memorization
- **Study questions** for self-testing
- **Difficulty analysis** for comprehension
- **Academic writing** transformation

### For Developers

- **Open Source:** Full codebase available
- **Modular Design:** Easy to extend
- **Well-Documented:** Comprehensive comments
- **Test Coverage:** 98.7% pass rate (150/152)
- **Active Development:** Regular updates

---

## 📞 Support

### Documentation

- This complete documentation
- Phase-specific guides in `docs/`
- Code comments throughout codebase
- Test suite examples in `tests/` (planned)

### Community

- GitHub Issues: Bug reports and feature requests
- Discussions: General questions and ideas
- Pull Requests: Contributions welcome

### Version History

- **v2.1** (Current) - 70.97% feature complete, production ready
- Phase 30: Emotional Intelligence (mood tracking, goals, journal, event check-ins)
- Phase 18: YouTube + Web Intelligence (12 functions, quality presets, smart search)
- Phase 17: Modern Particle Orb UI (HTML5 Canvas + QWebEngineView)
- Phase 20: Smart Memory & Learning (LanceDB + sentence-transformers)
- Phase 21: File Management (15 functions, Recycle Bin safety, auto-organization)
- Phases 28-29: Companion Mode (Thinking Feedback, Proactive Engagement)
- Phase 29 Extended: TTS LRU Cache, YouTube Expansion, Priority Manager
- Bonus: Login System, Lock Screen, Breathing Glow, Sir/Boss Addressing
- **v1.0** - Initial release with core functionality
- Focus: Core functionality, stability, performance

---

## 🎯 Project Status

**Current Completion:** 70.97% (22/31 Phases)

**Completed Phases:** 22 (including Companion P1-P7, Companion 28-30, File Management 21, YouTube+Web 18)
**Next Up:** Phase 31 - Personality & Fun
**Paused:** Phase 15 (Sharing), Companion P8
**Remaining:** 6 planned phases (19, 22-26, 31)

**Production Status:** ✅ **Ready for Daily Use**

All critical features implemented and tested. 180+ registered functions. 150/152 tests passing (98.7%).

---

## 🔐 Login & Lock Screen System

### Overview
NEXA includes a secure local authentication system with PBKDF2-HMAC-SHA256 password hashing.

### First Launch
1. On first launch, the **Create Account** screen appears automatically
2. Enter a username (minimum 2 characters)
3. Enter a password (minimum 4 characters) and confirm it
4. Click **Create Account** — you're automatically logged in

### Subsequent Launches
1. The **Login** screen appears with your username
2. Enter your password and click **Login**

### Lock Screen
- Click the 🔒 button in the window title bar to lock NEXA
- Or say **"Lock Nexa"** / **"Lock screen"** / **"Lock yourself"**
- Enter your password to unlock
- Lock screen features a breathing glow animation

### Security Details
- **Hashing:** PBKDF2-HMAC-SHA256 with 100,000 iterations
- **Salt:** 32-byte random salt per user
- **Storage:** `data/users.json` (dev) or `%LOCALAPPDATA%/Nexa AI/data/users.json` (compiled)
- **No plaintext passwords** are ever stored

---

## 🎨 Modern Particle Orb (Phase 17)

### Overview
The voice orb has been completely redesigned using HTML5 Canvas with a custom vanilla JavaScript particle engine, embedded in Qt via QWebEngineView.

### Visual
- 140 particles with connection lines
- Smooth lerp-based state transitions
- Audio-reactive animations during TTS playback
- Purple/cyan/pink color scheme

### States
| State | Visual |
|-------|--------|
| **Idle** | Gentle particle drift, slow connections |
| **Listening** | Particles pull inward, cyan glow |
| **Thinking** | Fast swirl, golden tones |
| **Speaking** | Audio-reactive expansion, pink accents |
| **Error** | Red scatter, shaking |

### Breathing Glow Title
The "NEXA" title features a breathing glow effect (QGraphicsDropShadowEffect with sine-wave modulation) that follows the orb's state color.

---

## 🧠 Smart Memory System (Phase 20)

### Overview
LanceDB vector database with sentence-transformers (all-MiniLM-L6-v2) for semantic memory storage and retrieval.

### Voice Commands
```
"Remember that I like dark theme"     → Stores as knowledge memory
"Forget about my password"            → Deletes matching memories
"What do you know about me?"          → Recalls relevant memories
"Show my memories"                    → Opens Memory Panel GUI
```

### Memory Types
- **ConversationMemory** — Full interaction history with embeddings
- **KnowledgeMemory** — Facts about the user (preferences, stated info)
- **SkillMemory** — Action patterns and usage frequencies

---

## 💜 Companion Mode

Nexa is evolving from a reactive assistant to a **proactive AI companion**.

### Phase 28: Thinking State Feedback ✅ COMPLETED
- ✅ Immediate acknowledgment: "On it!", "Got it!", "Let me check!"
- ✅ Task-type classification (general/search/system/complex/creative)
- ✅ Progress updates for long operations
- ✅ Slower speech speed (0.95x) for longer responses
- ✅ Past tense responses for completed actions

### Phase 29: Proactive Engagement ✅ COMPLETED
- ✅ Idle detection and smart suggestions
- ✅ Break reminders after long work sessions
- ✅ Time-based greetings (morning/evening)
- ✅ Activity pattern learning from Smart Memory

### Phase 30: Emotional Intelligence ✅ COMPLETED
- ✅ Text-based mood detection (9 moods: happy, excited, calm, neutral, tired, sad, stressed, frustrated, angry)
- ✅ Keyword + punctuation + CAPS analysis with EMA smoothing
- ✅ Emotional memory (events, mood snapshots, preferences, milestones, journal)
- ✅ Event tracking & check-ins ("How did your exam go?")
- ✅ Goal/dream tracking with milestone celebrations
- ✅ 5 new functions: journal_thought, track_goal, update_goal, get_my_goals, get_my_mood
- ✅ Files: `core/companion/mood_tracker.py`, `emotional_memory.py`, `event_tracker.py`

### Phase 31: Personality & Fun 📋 PLANNED
- NEXA opinions and preferences
- Mini-games (trivia, 20 questions)
- Compliments and encouragement
- Nickname system

---

**Documentation Version:** 2.1  
**Last Updated:** March 3, 2026  
**Maintained By:** Ali Adil Waseem  
**Project:** Nexa AI Desktop Assistant
