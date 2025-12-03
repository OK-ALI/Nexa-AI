# 🤖 Nexa AI - Your Personal AI Desktop Assistant

<div align="center">

![Version](https://img.shields.io/badge/version-1.1-blue)
![Status](https://img.shields.io/badge/status-production%20ready-green)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

**Hybrid AI Desktop Assistant for Windows**

[Features](#features) • [Installation](#installation) • [Documentation](#documentation) • [Quick Start](#quick-start)

</div>

---

## 🌟 What is Nexa?

Nexa is an advanced **AI desktop assistant** that uses **Llama 3.1 8B** to give you complete control over your Windows computer using natural voice commands.

### Key Highlights

- 🎙️ **Voice-First Interface** - Natural conversations, no wake words
- 🌐 **Single Model Architecture** - Llama 3.1 8B (Online & Offline)
- 🔒 **Privacy-First** - Fully functional offline mode
- ⚡ **Fast & Responsive** - 5-15 second responses
- 🎯 **50+ Commands** - Full system control
- 🎤 **Speaker Verification** - Voice recognition (SpeechBrain)
- 🎨 **Beautiful UI** - Animated voice orb with 60-bar waveform

---

## ✨ Features

### System Control

- 📱 Open/close applications (80+ detected)
- 🔊 Volume control (set/increase/decrease/mute)
- 💡 Brightness control
- 🪟 Window management (minimize/maximize/restore)
- 📸 Screenshots (file or clipboard)
- 🎮 Game launching (Steam/Epic/Xbox)
- 📂 Folder operations
- 📋 Clipboard operations
- 📡 WiFi management
- 🔋 Battery information

### AI Capabilities

- 💬 Natural conversations
- 🧠 Context awareness
- 🔄 Follow-up questions
- 👁️ Screen reading (online mode)
- 🖼️ Screen description (online mode)
- 🎤 Speaker verification (optional)

---

## 🚀 Quick Start

### 1. Install Prerequisites

```powershell
# Python 3.11+
python --version

# NVIDIA CUDA (for GPU acceleration)
nvidia-smi

# Ollama (for offline mode)
ollama pull llama3.1:8b-instruct-q4_K_M
```

### 2. Clone & Setup

```powershell
git clone https://github.com/yourusername/Nexa-MyAI.git
cd Nexa-MyAI

# Create virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure

Edit `.env` file:

```properties
# No API keys required for Llama 3.1
SPEAKER_VERIFICATION_ENABLED=true
SPEAKER_VERIFICATION_THRESHOLD=0.65
SPEAKER_ENROLLMENT_SAMPLES=7
```

### 4. Launch

```powershell
python main.py
```

---

## 📚 Documentation

### **📖 [COMPLETE DOCUMENTATION](NEXA_COMPLETE_DOCUMENTATION.md)**

This single comprehensive document contains **EVERYTHING:**

- ✅ Full feature list (50+ commands)
- ✅ Installation & setup guide
- ✅ Testing phases & checklists
- ✅ Bug fixes & solutions
- ✅ Speaker verification guide
- ✅ Development roadmap
- ✅ Performance benchmarks
- ✅ Troubleshooting guide
- ✅ FAQs & quick reference

**👉 START HERE:** [NEXA_COMPLETE_DOCUMENTATION.md](NEXA_COMPLETE_DOCUMENTATION.md)

---

## 🎯 Quick Examples

### Voice Commands

```
"What time is it?"              → Shows current time
"Open Notepad"                  → Opens Notepad
"Set volume to 50"              → Sets volume to 50%
"List my games"                 → Shows installed games
"Take a screenshot"             → Captures screen
"What's my battery level?"      → Shows battery %
"Read my screen"                → OCR (online mode only)
"Enroll my voice"               → Voice recognition setup
```

### Follow-up Commands

```
"List running apps"
  → "Close Chrome"              → Context-aware

"What time is it?"
  → "Thanks"                    → Natural conversation
```

---

## 🔧 Technology Stack

### AI Models

- **Model:** Llama 3.1 8B (Local via Ollama)
- **Speech:** Faster-Whisper Large-v3-turbo
- **TTS:** Piper (Amy voice)
- **Speaker Verification:** SpeechBrain ECAPA-TDNN

### Core

- **Language:** Python 3.11+
- **UI:** PyQt6
- **GPU:** CUDA (NVIDIA)
- **Server:** Ollama (local AI)

---

## 📊 Performance

| Mode | Response Time | Accuracy | Privacy |
|------|---------------|----------|---------|
| **Online** | 2-5 seconds | 95%+ | Internet enabled features |
| **Offline** | 2-5 seconds | 95%+ | 100% local ✅ |

---

## 🐛 Known Issues

### All Critical Bugs: ✅ FIXED

| Issue | Status | Date Fixed |
|-------|--------|------------|
| Time/Battery Hallucination | ✅ Fixed | Oct 13, 2025 |
| Zero Apps Detected | ✅ Fixed | Oct 13, 2025 |
| Battery Format | ✅ Fixed | Oct 13, 2025 |
| Slow Offline Response | ✅ Fixed | Oct 16, 2025 |
| Brightness TypeError | ✅ Fixed | Oct 22, 2025 |
| Enrollment Cutoff | ✅ Fixed | Oct 22, 2025 |
| Enrollment Not Required | ✅ Fixed | Oct 22, 2025 |

**Current Status:** Production Ready ✅

---

## 🗺️ Roadmap

### Completed (60%)

- ✅ Core AI System (Hybrid online/offline)
- ✅ Voice Interface (Speech + TTS)
- ✅ 50+ System Functions
- ✅ Beautiful UI
- ✅ Speaker Verification
- ✅ Performance Optimizations

### In Progress

- ⏳ Advanced Personalization
- ⏳ Enhanced Automation
- ⏳ Offline Vision (OCR)

### Planned

- 📋 Multi-device support
- 📋 Mobile companion app
- 📋 Plugin system
- 📋 Multi-language support

---

## 🆘 Troubleshooting

### Common Issues

**No response?**

- Check microphone working
- Verify "Listening..." indicator shows

**Too slow?**

- Close background apps
- Check GPU usage
- Verify Ollama running

**Vision not working offline?**

- Expected behavior (requires online mode)
- Switch to online mode for vision features (coming soon)

**More help:** See [Troubleshooting Guide](NEXA_COMPLETE_DOCUMENTATION.md#10-troubleshooting-guide)

---

## 📞 Support

- **Documentation:** [NEXA_COMPLETE_DOCUMENTATION.md](NEXA_COMPLETE_DOCUMENTATION.md)
- **GitHub Issues:** [Report a bug](https://github.com/yourusername/Nexa-MyAI/issues)
- **Email:** [Your email]

---

## 🎓 System Requirements

### Minimum

- Windows 10/11 (64-bit)
- 8 GB RAM
- NVIDIA GPU (4+ GB VRAM)
- 10 GB free storage

### Recommended

- Windows 11
- 16 GB RAM
- NVIDIA RTX 3060+ (6+ GB VRAM)
- 20 GB SSD storage

### Current Dev Setup

- GPU: NVIDIA RTX 3070 (8 GB)
- RAM: 16 GB
- Performance: Excellent ✅

---

## 🌟 What Makes Nexa Special?

1. **Single Model Power** - Llama 3.1 8B for everything
2. **Privacy-First** - 100% offline capable
3. **Natural Conversations** - No rigid commands
4. **Context Aware** - Remembers conversation
5. **Beautiful Interface** - Animated voice orb
6. **GPU Accelerated** - Fast processing
7. **Speaker Verification** - Voice recognition
8. **Open Source** - Full control

---

## 📜 License

[Your chosen license - e.g., MIT]

---

## 👤 Author

**Ali Adil Waseem**

- Project Creator & Lead Developer
- [GitHub Profile]
- [Contact Info]

---

## 🙏 Credits

### Technologies Used

- Llama 3.1 8B by Meta (Local AI)
- Faster-Whisper by Systran (Speech Recognition)
- Piper TTS by Rhasspy (Text-to-Speech)
- SpeechBrain (Speaker Verification)
- Silero VAD (Voice Detection)
- PyQt6 (User Interface)
- Ollama (Local AI Serving)

---

## 🚀 Get Started

1. **Read the documentation:** [NEXA_COMPLETE_DOCUMENTATION.md](NEXA_COMPLETE_DOCUMENTATION.md)
2. **Follow installation steps** (5 minutes)
3. **Launch Nexa** (`python main.py`)
4. **Say "Hello Nexa"** 🎙️
5. **Enjoy your AI assistant!** ✨

---

<div align="center">

**Nexa AI - Your Personal AI, Running on YOUR Computer, Serving YOU**

⭐ Star this repo if you find it helpful!

</div>
