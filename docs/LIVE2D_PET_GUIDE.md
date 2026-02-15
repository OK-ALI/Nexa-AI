# 🎭 Nexa Pet System - Technical Guide

**Created:** December 18, 2025  
**Last Updated:** December 18, 2025  
**Status:** ✅ Implemented (Phase P3 Complete)  
**Version:** 2.0  
**Default Mode:** Sprite Animation (Custom Nexa Character)  
**Alternative Mode:** Live2D (Hiyori Model)

---

## 📖 Overview

Nexa's desktop pet supports **two rendering modes**:

### 🎨 Sprite Mode (Default - Recommended)
Uses **your custom Nexa character PNG images** with programmatic animations:
- ✅ **Lightweight** - No OpenGL dependencies
- ✅ **Custom Character** - YOUR Nexa AI assistant design
- ✅ **Smooth Animations** - Floating, breathing, bounce effects
- ✅ **8 States** - idle, listening, thinking, speaking, sleeping, error, happy, content_mode

### 🎬 Live2D Mode (Alternative)
Uses **Live2D Cubism** technology with Hiyori model:
- 🎬 60fps Hardware-Accelerated Rendering
- 🌊 Physics Simulation (hair/clothing)
- 👁️ Auto-Blink & Breathing
- 😊 7 Custom Nexa expressions

---

## 🎨 Sprite Pet System (Default)

### Features
| Feature | Description |
|---------|-------------|
| 🌊 **Floating Animation** | Gentle up-down bobbing (8px sine wave) |
| 💨 **Breathing Animation** | Subtle scale pulse (±1.5% size variation) |
| 🏀 **Bounce Effect** | Spring bounce on state changes |
| 🎭 **Crossfade Transitions** | Smooth ~200ms transitions between states |
| 🖱️ **Draggable** | Click and drag anywhere on screen |
| 📍 **Position Memory** | Remembers position between sessions |
| 📐 **3 Sizes** | Small (350×500), Medium (500×700), Large (650×900) |

### Custom Nexa Character Images

Located in `assets/pet/`:

| Image | State | Description |
|-------|-------|-------------|
| `idle.png` | Idle/Waiting | Calm, relaxed, ready to help |
| `listening.png` | Listening | Attentive, hand near ear |
| `thinking.png` | Processing | Hand on chin, looking up |
| `speaking.png` | TTS Playing | Open mouth, gesturing |
| `sleeping.png` | Inactive | Eyes closed, peaceful |
| `error.png` | Error | Worried, apologetic |
| `veryhappy.png` | Success | Celebrating, sparkles |
| `content_mode.png` | Study Mode | Glasses, book, focused |

### Character Design
- **Style:** Cute anime-style female AI assistant
- **Hair:** Beautiful blonde ponytail with side bangs
- **Eyes:** Bright blue
- **Outfit:** Dark purple futuristic hoodie with glowing cyan "N" logo
- **Proportions:** Chibi-style (large head, small body)

### Files

| File | Purpose | Lines |
|------|---------|-------|
| `ui/sprite_pet_widget.py` | Sprite animation widget | ~530 |
| `ui/pet_config.py` | Pet preferences & size settings | ~265 |
| `assets/pet/*.png` | 8 character state images | - |

---

## 🔄 State-to-Image Mapping

```python
STATE_IMAGES = {
    'idle': 'idle.png',
    'listening': 'listening.png',
    'thinking': 'thinking.png',
    'speaking': 'speaking.png',
    'executing': 'thinking.png',
    'content_mode': 'content_mode.png',
    'error': 'error.png',
    'happy': 'veryhappy.png',
    'sleeping': 'sleeping.png',
    'recognizing': 'listening.png',
}
```

---

## 🔧 Architecture

```
┌────────────────────────────────────────────────────────────────┐
│                        NexaBrain                               │
│                                                                │
│  state_changed(NexaState) ──────────────────────┐              │
└─────────────────────────────────────────────────┼──────────────┘
                                                  │
                                                  ▼
┌────────────────────────────────────────────────────────────────┐
│                    NexaModernWindow                            │
│                                                                │
│  _update_pet_state(state) → pet_widget.set_state(state.value) │
│                                                                │
│  Pet Type Selection (from config):                            │
│    SPRITE → SpritePetWidget (default)                         │
│    LIVE2D → Live2DPetWidget (alternative)                     │
└─────────────────────────────────────────────────┼──────────────┘
                                                  │
                    ┌─────────────────────────────┴─────────────────────────────┐
                    │                                                           │
                    ▼                                                           ▼
┌───────────────────────────────────────┐     ┌───────────────────────────────────────┐
│         SpritePetWidget               │     │         Live2DPetWidget               │
│         (DEFAULT)                     │     │         (ALTERNATIVE)                 │
│                                       │     │                                       │
│  • QWidget with custom paintEvent     │     │  • QOpenGLWidget + 60fps timer        │
│  • QTimer(16ms) for animations        │     │  • Live2D physics & rendering         │
│  • PNG image crossfade                │     │  • Expression system                  │
│  • Float/breathe/bounce effects       │     │  • Motion playback                    │
└───────────────────────────────────────┘     └───────────────────────────────────────┘
```

---

## ⚙️ Configuration

### Pet Preferences File
Location: `config/pet_preferences.json`

```json
{
    "enabled": true,
    "pet_type": "sprite",
    "size": "medium",
    "position_x": 1420,
    "position_y": 330,
    "snap_to_edges": true,
    "snap_distance": 20,
    "always_on_top": true,
    "show_in_taskbar": false
}
```

### Pet Type Options
| Value | Description |
|-------|-------------|
| `"sprite"` | Animated PNG sprites (default, your custom Nexa character) |
| `"live2d"` | Live2D Hiyori model with custom expressions |

### Size Options
| Size | Dimensions |
|------|------------|
| `"small"` | 350×500 px |
| `"medium"` | 500×700 px |
| `"large"` | 650×900 px |

---

## 📝 Usage

### Toggle Pet
Click the 🐾 button in Nexa's main window, or right-click system tray.

### Change Size
Right-click the pet → Size → Small/Medium/Large

### Test Expressions
Right-click the pet → Test Expression → Select state

### Move Pet
Left-click and drag anywhere on screen.

### Double-Click
Shows happy expression for 2 seconds!

---
from core.live2d_engine import Live2DModel, PetExpression

model = Live2DModel("path/to/model.model3.json")
model.load()

# Set expression
model.set_expression("F05")  # Happy

# Start motion
model.start_random_motion("TapBody", priority=2)

# Direct parameter control
model.set_parameter("ParamMouthOpenY", 0.5)  # Open mouth

# Look at position
model.set_look_at(0.5, 0.0)  # Look right
```

---

## � Live2D Mode (Alternative)

If you prefer the Live2D Hiyori model, change `pet_type` in config:

```json
{ "pet_type": "live2d" }
```

### Live2D Dependencies

```bash
pip install live2d-py PyOpenGL PyOpenGL_accelerate
```

### Live2D Files

| File | Purpose |
|------|---------|
| `core/live2d_engine.py` | Live2D model wrapper (447 lines) |
| `ui/live2d_widget.py` | OpenGL widget (350 lines) |

### Custom Nexa Expressions (Hiyori)

7 custom expressions in `Hiyori/expressions/nexa_*.exp3.json`:

| Expression | State | Visual |
|------------|-------|--------|
| `nexa_idle` | Idle | Calm smile, relaxed |
| `nexa_listening` | Listening | Wide eyes, raised brows |
| `nexa_thinking` | Thinking | Eyes up-left, contemplative |
| `nexa_speaking` | Speaking | Open mouth, animated |
| `nexa_happy` | Happy | Closed-eye smile, blush |
| `nexa_sleeping` | Sleeping | Eyes closed, peaceful |
| `nexa_error` | Error | Worried frown |

---

## 🎯 Future Improvements

### P4: Speech Bubble
- Animated text bubble above pet
- Typewriter effect for responses
- Auto-dismiss with fade

### P5: Enhanced Animations
- More expression variations
- Particle effects (hearts, sparkles)
- Lip-sync during TTS

### P6: Advanced Interactions
- Click reactions (head pat, poke)
- Drag reactions (surprise, wiggle)
- Mouse tracking (eyes follow cursor)

---

## 🐛 Troubleshooting

### Pet Not Showing
1. Check logs for errors
2. Verify images exist in `assets/pet/`
3. Try right-click → Test Expression

### Sprite Images Not Loading
1. Verify PNG files are valid
2. Check file names match STATE_IMAGES mapping
3. Ensure transparent backgrounds

### Live2D Not Working
1. Check OpenGL support (GPU drivers)
2. Reinstall: `pip install --force-reinstall live2d-py`
3. Verify model path exists

### Performance Issues
1. Reduce window size (right-click → Size → Small)
2. Switch to Sprite mode (lighter than Live2D)

---

## 📚 Resources

- **Sprite Pet:** No external dependencies, PySide6 only
- **live2d-py GitHub:** https://github.com/Arkueid/live2d-py
- **Live2D SDK:** https://www.live2d.com/sdk/download/native/

---

## 📄 Quick Summary

| Feature | Sprite Mode (Default) | Live2D Mode |
|---------|----------------------|-------------|
| **Status** | ✅ Default | Alternative |
| **Character** | Custom Nexa images | Hiyori model |
| **Dependencies** | PySide6 only | live2d-py, OpenGL |
| **GPU Required** | No | Yes |
| **States** | 8 images | 7 expressions |
| **Animation** | Float/breathe/bounce | Physics-based |
| **Customization** | Replace PNGs | Edit expressions |

**Switch modes:** Edit `config/pet_preferences.json` → `"pet_type": "sprite"` or `"live2d"`

---

## 📄 License

- **Sprite Mode:** No license required - uses your custom PNG images
- **Live2D Mode:** Live2D Cubism SDK requires a license for commercial use. Sample models (Haru, Hiyori, Mark) are for testing only.

---

*Last Updated: Phase 3 - Sprite Pet System is now the default, with Live2D available as an alternative.*

