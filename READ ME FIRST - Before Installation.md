# 🌟 Nexa AI Assistant

<div align="center">

<img src="assets/icon.ico" alt="Nexa Logo" width="128" height="128">

**Your Personal Voice-Controlled Windows Assistant**

[![Beta](https://img.shields.io/badge/Status-Beta%20v1.0-blue.svg)]()
[![Windows](https://img.shields.io/badge/Platform-Windows%2010%2F11-0078D6.svg)]()
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

*Control your PC with just your voice — works 100% offline!*

[Download](#-download) • [Features](#-features) • [Commands](#-voice-commands) • [FAQ](#-faq)

</div>

---

## 🎯 What is Nexa?

**Nexa** is a voice-controlled AI assistant for Windows that lets you control your computer using natural speech. Unlike cloud-based assistants, Nexa runs **locally on your machine**, ensuring your privacy and providing instant responses.

Simply speak naturally, and Nexa will:
- 📂 Open and close applications
- 🎵 Play your local music library
- 🎮 Launch your favorite games
- 🔊 Adjust volume and brightness
- 📸 Take screenshots
- 📝 Create PDFs and refine text
- 💡 Answer questions and have conversations
- ...and much more!

---

## ✨ Features

### 🎤 Voice Control
- **Wake Word Activation** — Say "Nexa" or "Hey Nexa" to activate
- **Natural Language** — Speak naturally, no rigid commands required
- **Instant Response** — Local AI processing, no cloud latency
- **Speaker Verification** — Optional voice recognition for security

### 🖥️ System Control
- **Application Management** — Open, close, and switch between apps
- **Window Control** — Minimize, maximize, restore windows by voice
- **Volume & Brightness** — Adjust system settings naturally
- **WiFi Management** — Connect, disconnect, list networks
- **Battery Status** — Check charging status and time remaining

### 🎵 Music Player
- **Local Library** — Plays MP3, WAV, FLAC, M4A, OGG, WMA
- **Voice Controls** — Play, pause, skip, previous track
- **Smart Search** — Find songs by name or artist
- **Shuffle & Repeat** — Multiple playback modes
- **Smart Auto-Ducking** — Music stays at full volume during passive listening, automatically lowers to 8% when you say "Nexa" or give commands, and returns to full volume after responses complete

### 🎮 Game Launcher
- **Multi-Platform** — Steam, Epic Games, GOG, standalone games
- **Auto-Detection** — Automatically finds your installed games
- **Voice Launch** — "Play Counter-Strike" or "Launch Fortnite"

### 📝 Content Mode
- **Text Refinement** — Make text formal, casual, or shorter
- **Grammar Check** — Fix spelling and grammar errors
- **PDF Creation** — Generate formatted PDF documents
- **Study Tools** — Create flashcards, summaries, and outlines

### 📸 Screenshots
- **Voice Capture** — "Take a screenshot"
- **Auto-Save** — Organized in Pictures/Nexa Screenshots
- **Clipboard Copy** — Optional clipboard mode

### 🔄 Mode Switching
- **Online Mode 🌐** — Internet enabled for weather, web search
- **Offline Mode 🔒** — 100% local processing, complete privacy
- **Manual Toggle** — Click the mode button or say "Switch to offline mode"

### 🎯 Nexa States (Orb Colors)
The animated orb shows Nexa's current state:
| State | Color | Meaning |
|-------|-------|---------|
| Idle | 🔵 Blue | Waiting for wake word |
| Listening | 🔷 Cyan | Hearing your voice |
| Thinking | 🟣 Purple | Processing request |
| Speaking | 🩵 Teal | Responding to you |
| Error | 🔴 Red | Something went wrong |

### 🎶 Music Indicator
- **Visual Feedback** — Animated bars when music plays
- **Song Display** — Shows current track name
- **Auto-Hide** — Disappears when music stops

---

## 💻 System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| **OS** | Windows 10 (64-bit) | Windows 11 |
| **RAM** | 8 GB | 16 GB |
| **Storage** | 10 GB free | 15 GB free |
| **GPU** | NVIDIA GTX 1060 (6GB VRAM) | NVIDIA RTX 3060+ (8GB+ VRAM) |
| **Audio** | Microphone | Quality USB/headset microphone |

> ⚠️ **NVIDIA GPU Required** — Nexa uses local AI models that require CUDA-compatible graphics cards for real-time performance.

---

## 📥 Download

### Full Installer (Recommended)

**Download all files from Google Drive:**

| File | Required |
|------|----------|
| `Nexa_AI_Setup_Beta_v1.0.exe` | ✅ Yes |
| `Nexa_AI_Setup_Beta_v1.0-1.bin` | ✅ Yes |
| `Nexa_AI_Setup_Beta_v1.0-2.bin` | ✅ Yes |
| `Nexa_AI_Setup_Beta_v1.0-3.bin` | ✅ Yes |

**Installation Steps:**
1. Download all 4 files and place them in the **same folder**
2. Run `Nexa_AI_Setup_Beta_v1.0.exe`
3. Follow the installation wizard
4. Launch Nexa from the Start Menu or Desktop shortcut

---

## 🚀 Getting Started

### First Launch
1. **Install Ollama** — Nexa will guide you to install Ollama (the AI engine) if not already installed
2. **Pull the AI Model** — Open a terminal and run:
   ```
   ollama pull llama3.1:8b-instruct-q4_K_M
   ```
   This downloads the AI model (~4.7 GB) that powers Nexa's intelligence.
3. **Enter Your Name** — Personalize your experience
4. **Configure API Keys** (Optional) — Add OpenWeatherMap key for weather features
5. **Start Talking!** — Say "Hey Nexa" followed by your command

### Quick Test Commands
Try these to get started:
- "What time is it?"
- "Open Calculator"
- "Set volume to 50 percent"
- "What's my battery status?"
- "Play some music"

---

## 🗣️ Voice Commands

See the complete **[Command Guide](COMMAND_GUIDE.md)** for all available commands.

### Quick Reference

| Category | Example Commands |
|----------|-----------------|
| **Apps** | "Open Chrome", "Close Notepad", "List running apps" |
| **Windows** | "Minimize this", "Maximize Chrome", "Close active window" |
| **Volume** | "Volume up", "Set volume to 70", "Mute" |
| **Brightness** | "Brightness down", "Set brightness to 50" |
| **Music** | "Play music", "Next song", "Pause", "What's playing?" |
| **Games** | "List my games", "Play Valorant", "Launch the first one" |
| **Screenshots** | "Take a screenshot", "Open screenshots folder" |
| **System** | "Battery status", "WiFi status", "What time is it?" |
| **Web Search** | "Search for Python tutorials", "Google best restaurants" |
| **Weather** | "What's the weather?", "Forecast for tomorrow" |
| **Content Mode** | "Enter content mode", "Make it formal", "Create PDF" |

---

## ⚙️ Settings & Customization

### Music Library
Nexa automatically scans your Windows Music folder (`C:\Users\[YourName]\Music`). Simply add your audio files there.

### Weather (Optional)
To enable weather features:
1. Get a free API key from [OpenWeatherMap](https://openweathermap.org/api)
2. Enter it during first-run setup

### Wake Word Mode
- **Default**: Wake word enabled — say "Nexa" or "Hey Nexa" before commands
- **Disable Wake Word**: Say "Disable wake word" for always-listening mode
- **Re-enable Wake Word**: Say "Enable wake word" to return to wake word mode

### Music During Listening
Nexa has smart audio ducking that works with any music source:
- **Passive listening** (waiting for "Nexa"): Music plays at **full volume**
- **After wake word**: Music ducks to **8%** while you give commands
- **During responses**: Music stays ducked so you can hear Nexa
- **After response ends**: Music returns to **full volume** automatically

This means you can enjoy your music uninterrupted while Nexa waits for commands!

---

## ❓ FAQ

### Why does Nexa need an NVIDIA GPU?
Nexa runs local AI models for understanding your voice and generating responses. GPU acceleration is required for real-time performance.

### Is my voice data sent to the cloud?
**No.** All voice recognition and AI processing happens locally on your PC. Your conversations never leave your computer.

### Can I use Nexa without internet?
**Yes!** Nexa is designed to work offline. Weather and web search features require internet, but all core functionality works offline.

### Why is the installer so large?
The installer includes AI models, voice synthesis engines, and GPU libraries (CUDA, cuDNN) to ensure everything works out-of-the-box without additional downloads.

### Nexa isn't hearing me properly
1. Check your microphone is set as default in Windows Settings
2. Ensure background noise is minimal
3. Speak clearly at a normal pace
4. Try "Enable wake word" for noisy environments

### How do I report bugs or give feedback?
Fill out our **Feedback Form** (link in release notes) or create an issue on GitHub.

---

## 🤝 Feedback & Support

Nexa is currently in **Beta**. We welcome your feedback!

- 📝 [Submit Feedback Form](https://forms.gle/YOUR_FORM_ID_HERE)
- 🐛 [Report Bugs on GitHub](https://github.com/OK-ALI/Nexa-AI/issues)
- 📚 [Release Notes](RELEASE_NOTES.md) — See what's new in this version
- 📖 [Command Guide](COMMAND_GUIDE.md) — Full list of voice commands

> ⚠️ **Replace the feedback form link above with your actual Google Form URL**

---

## 📜 License

This project is licensed under the **MIT License** — see the [LICENSE](LICENSE) file for details.

---

<div align="center">

**Made with ❤️ for the Windows community**

*Nexa AI Assistant — Your Voice, Your Control*

</div>
