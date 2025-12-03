# Nexa - AI Assistant (Beta Release)

## 📦 Installation Instructions

### Option 1: Standalone (No Installer)
1.  Navigate to the `dist/Nexa_Auto` folder.
2.  Run `Nexa_Auto.exe`.
3.  **First Run**:
    *   The app will automatically check for **Ollama**.
    *   It will download the **Llama 3.1 8b** model (approx 4.7GB) if missing.
    *   It will verify your internet connection for the Weather service.

### Option 2: Create Installer (Recommended)
To create a professional `setup.exe` file:
1.  Install **Inno Setup** (free) from [jrsoftware.org](https://jrsoftware.org/isdl.php).
2.  Open the `setup.iss` file in this folder.
3.  Click **Compile**.
4.  The installer will be created in the `Output` folder.

## 🔑 Key Features in Beta
*   **Voice Control**: "Hey Nexa" (requires Llama 3.1).
*   **Weather**: Auto-configured (bundled key).
*   **Privacy**: All AI processing is **local** via Ollama.

## 🎛️ UI Controls
*   **Mode Toggle**: Click the button at the bottom to switch between **🌐 Online** and **🔒 Offline** modes.
*   **Theme Selector**: Customize Nexa's appearance with different visual themes.
*   **Music Indicator**: Animated visualizer appears when music is playing.

## 🎯 Nexa States (Orb Colors)
*   🔵 **Idle** - Waiting for wake word
*   🔷 **Listening** - Hearing your voice
*   🟣 **Thinking** - Processing your request
*   🩵 **Speaking** - Nexa is responding
*   🔴 **Error** - Something went wrong

## ⚠️ Troubleshooting
*   **"Ollama not found"**: Make sure you have installed Ollama from [ollama.com](https://ollama.com).
*   **Slow First Response**: The AI model takes about 30-60 seconds to load into memory on the very first command.
*   **Permission Errors**: If installed to Program Files, user data is stored in `%LOCALAPPDATA%\Nexa AI\`.
