# 🚀 Nexa AI Assistant - Release Notes

## Version 1.0.0 Beta (December 2025)

**🎉 First Public Beta Release**

We're excited to release the first public beta of **Nexa AI Assistant** — a fully voice-controlled Windows assistant that runs locally on your PC!

---

## ✨ What's New in Beta v1.0

### 🎤 Voice Recognition

- **Wake Word Activation**: Say "Nexa" or "Hey Nexa" to activate
- **Optional Always-Listening**: Disable wake word for continuous listening
- **Local Processing**: Powered by OpenAI Whisper running on your GPU
- **Speaker Verification**: Optional voice authentication for security

### 🧠 AI-Powered Intelligence

- **100% Offline Core**: Runs Llama 3.1 8B locally via Ollama — no internet required for core features
- **Natural Conversations**: Context-aware responses with conversation memory
- **Multi-Step Commands**: "Open Chrome and maximize it"
- **Smart Follow-ups**: "Close it", "Maximize that" after previous actions

### 🖥️ Complete System Control

- **Applications**: Open, close, minimize, maximize any app
- **Volume**: "Set volume to 50", "Volume up", "Mute"
- **Brightness**: "Brightness down", "Set brightness to 80"
- **WiFi**: Connect, disconnect, list available networks
- **Battery**: Check charging status, percentage, time remaining
- **GPU**: Monitor VRAM usage in real-time

### 🎵 Music Player

- **Local Library**: Plays MP3, WAV, FLAC, M4A, OGG, WMA
- **Full Voice Control**: Play, pause, resume, skip, previous
- **Song Search**: "Play Bohemian Rhapsody"
- **Shuffle & Repeat**: Multiple playback modes
- **Smart Auto-Ducking**: Intelligent volume management:
  - Music plays at **full volume** during passive wake word listening
  - Automatically ducks to **8%** when you say "Nexa" and give commands
  - Returns to **full volume** after Nexa finishes responding
  - Works with any audio source (Spotify, YouTube, local files, etc.)

### 🎶 Music Indicator

- **Visual Feedback**: Animated music visualizer bars appear when music is playing
- **Song Display**: Shows current song name with a musical note icon
- **Theme-Aware**: Automatically adapts to your selected theme colors
- **Auto-Hide**: Disappears when music stops playing

### 🎮 Game Launcher

- **Multi-Platform**: Steam, Epic Games, GOG, standalone games
- **Auto-Detection**: Finds your installed games automatically
- **Voice Launch**: "Play Valorant", "Launch Counter-Strike"
- **List Games**: "Show my Steam games"

### 📝 Content Mode (New!)

- **Text Refinement**: Make text formal, casual, shorter, or longer
- **Grammar Check**: Fix spelling and grammar errors
- **Study Tools**: Create flashcards, extract key terms, summarize
- **PDF Generation**: Convert text to formatted PDFs
- **Voice Formatting**: Bold, italic, lists via voice commands

### 📸 Screenshots

- **Voice Capture**: "Take a screenshot"
- **Custom Names**: "Screenshot named meeting notes"
- **Clipboard Mode**: "Screenshot and copy"
- **Organized Storage**: Auto-saved to Pictures/Nexa Screenshots

### 🔍 Web Search (Internet Required)

- **Natural Language**: "Search for Python tutorials", "Look up climate change"
- **Google Search**: "Google best restaurants near me"
- **Default Browser**: Opens search in your preferred browser
- **Offline Protection**: Gracefully informs you to switch to online mode if offline

### 🌤️ Weather (Internet Required)

- **Current Conditions**: "What's the weather?"
- **Forecasts**: "Weather forecast for tomorrow"
- **Any Location**: "Weather in Tokyo"
- **Auto-Location**: Detects your city automatically

---

## 🔄 Mode Switching (Online/Offline)

Nexa gives you full control over internet connectivity with manual mode switching:

### Online Mode 🌐

- Uses internet for weather, web searches, and enhanced AI responses
- Button shows **green** with "🌐 ONLINE" text
- Required for weather updates and web searches

### Offline Mode 🔒

- **100% local processing** — no internet required
- Button shows **purple** with "🔒 OFFLINE" text
- All AI processing happens on your PC via Ollama
- Perfect for privacy-focused use or when offline

### How to Switch

- **Click the Mode Button**: Located in the control bar at the bottom of Nexa's window
- **Voice Command**: "Switch to offline mode" or "Go online"
- Nexa will announce the mode change audibly

---

## 🎯 Nexa States

Nexa uses a visual state system to show you exactly what it's doing. The **animated orb** changes color to indicate the current state:

| State                  | Color             | Description                              |
| ---------------------- | ----------------- | ---------------------------------------- |
| **Idle**         | 🔵 Soft Blue      | Waiting for wake word or command         |
| **Listening**    | 🔷 Electric Cyan  | Actively listening to your voice         |
| **Recognizing**  | 🟣 Purple         | Processing speech / Speaker verification |
| **Thinking**     | 🟪 Vibrant Purple | AI is processing your request            |
| **Speaking**     | 🩵 Bright Teal    | Nexa is speaking the response            |
| **Executing**    | 🔷 Electric Cyan  | Performing an action (opening app, etc.) |
| **Content Mode** | 🟣 Deep Purple    | Text editing or PDF generation active    |
| **Error**        | 🔴 Bright Red     | Something went wrong                     |

### Visual Feedback

- The orb **pulses** when listening
- The orb **glows** when Nexa is speaking
- Smooth **color transitions** between states
- State changes help you know when to speak and when to wait

---

## 🎛️ UI Controls Overview

Nexa's window features a clean, minimal interface with these controls:

| Control                   | Location | Function                                             |
| ------------------------- | -------- | ---------------------------------------------------- |
| **Voice Orb**       | Center   | Main interaction point — animates based on state    |
| **Mode Toggle**     | Top area | Switch between Online 🌐 and Offline 🔒 modes        |
| **Theme Button**    | Top area | Change Nexa's visual theme (Dark, Light, Neon, etc.) |
| **Music Indicator** | Top area | Animated visualizer showing current song             |
| **Status Text**     | Bottom   | Displays what Nexa is currently doing                |

### System Tray

Nexa runs in the system tray with quick access to:

- Show/Hide main window
- Toggle Online/Offline mode
- Pause/Resume listening
- Exit Nexa

---

## 💻 System Requirements

| Component         | Minimum                    | Recommended                  |
| ----------------- | -------------------------- | ---------------------------- |
| **OS**      | Windows 10 (64-bit)        | Windows 11                   |
| **RAM**     | 8 GB                       | 16 GB                        |
| **Storage** | 10 GB free                 | 15 GB free                   |
| **GPU**     | NVIDIA GTX 1060 (6GB VRAM) | NVIDIA RTX 3060+ (8GB+ VRAM) |
| **Audio**   | Any microphone             | USB/headset microphone       |

> ⚠️ **NVIDIA GPU is required** for real-time AI processing

---

## 📦 Installation

### Download Files (All Required)

| File                              | Size    |
| --------------------------------- | ------- |
| `Nexa_AI_Setup_Beta_v1.0.exe`   | ~10 MB  |
| `Nexa_AI_Setup_Beta_v1.0-1.bin` | ~1.8 GB |
| `Nexa_AI_Setup_Beta_v1.0-2.bin` | ~1.8 GB |
| `Nexa_AI_Setup_Beta_v1.0-3.bin` | ~1.8 GB |

### Steps

1. Download all 4 files from Google Drive
2. **Important**: Place all files in the same folder
3. Run `Nexa_AI_Setup_Beta_v1.0.exe`
4. Follow the installation wizard
5. Launch Nexa from Start Menu or Desktop

### First Run

1. Nexa will check for Ollama (AI engine)
2. If not installed, you'll be prompted to download it
3. Enter your name to personalize the experience
4. (Optional) Add OpenWeatherMap API key for weather
5. Start talking!

---

## ⚠️ Known Limitations

| Limitation                | Details                                              |
| ------------------------- | ---------------------------------------------------- |
| **NVIDIA GPU Only** | AMD/Intel integrated graphics not supported          |
| **Windows Only**    | No macOS or Linux support currently                  |
| **English Only**    | Voice recognition optimized for English              |
| **Ollama Required** | Must install Ollama separately (guided during setup) |

---

## 🐛 Known Issues

1. **First Startup Delay**: Initial load takes 30-60 seconds while AI model initializes
2. **False Wake Words**: May trigger on similar-sounding words in noisy environments — use "Enable wake word" to require "Nexa" prefix
3. **App Name Variations**: Some apps may not be found by nickname — say "List installed apps" to see exact names
4. **Music Folder Scanning**: First music playback may pause briefly while scanning library

---

## 🔜 What's Next?

We're actively developing Nexa based on your feedback! Future updates will bring improvements, bug fixes, and exciting new features. Your suggestions help shape what comes next.

---

## 📝 Feedback & Support

We'd love your feedback to improve Nexa! This is a beta release, and your input helps us make Nexa better for everyone.

### 📋 Beta Feedback Form

**👉 [Click here to submit feedback](https://forms.gle/YOUR_FORM_ID_HERE)**

> ⚠️ **Replace the link above with your actual Google Form URL**

### 📚 Documentation

- 📖 [Command Guide](COMMAND_GUIDE.md) — Full list of voice commands
- 📘 [Before Installation Guide](READ%20ME%20FIRST%20-%20Before%20Installation.md) — Setup instructions

Please share:

- Installation experience
- Features you've tried
- Bugs or issues encountered
- Feature requests
- Overall satisfaction

### 🐛 Bug Reports

If you encounter a bug, please include:

1. What you were trying to do
2. What happened instead
3. Steps to reproduce (if possible)
4. Your system specs (Windows version, GPU, RAM)

### 💡 Feature Requests

Have an idea for Nexa? We're listening! Submit your suggestions via the feedback form.

### 📧 Contact

- **GitHub Issues**: [Report bugs or request features](https://github.com/OK-ALI/Nexa-AI/issues)
- **Email**: aliwasim.12aaa64@gmail.com

---

## 📜 License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.

---

## 🙏 Thank You!

Thank you for trying **Nexa AI Assistant Beta**! Your feedback helps us make Nexa better.

---

*Nexa AI — Your Voice, Your Control*
