# Nexa Voice Command Test Suite

Manual testing checklist for Smart Memory and core features.

---

## 🧠 Smart Memory Commands

### Remember Facts
- [ ] "Remember that I prefer dark theme"
- [ ] "Note that my favorite browser is Chrome"
- [ ] "Remember that I like jazz music"

### Recall Knowledge
- [ ] "What do you know about my preferences?"
- [ ] "Do you remember my favorite browser?"
- [ ] "What do you know about themes?"

### Forget Memories
- [ ] "Forget about jazz music"
- [ ] "Delete memories about browsers"

### Memory Stats
- [ ] "Memory stats"
- [ ] "How many memories do you have?"

### Memory Panel
- [ ] "Show my memories"
- [ ] "Open memory panel"

---

## 🔊 Volume Controls

- [ ] "Set volume to 50"
- [ ] "Mute"
- [ ] "Unmute"
- [ ] "Volume up"
- [ ] "Volume down"

---

## 🖥️ Application Control

- [ ] "Open Chrome"
- [ ] "Open Notepad"
- [ ] "Close Chrome"
- [ ] "Switch to Notepad"

---

## 🌤️ Weather & Time

- [ ] "What's the weather?"
- [ ] "Is it raining?"
- [ ] "What time is it?"
- [ ] "What's today's date?"

---

## 💡 Brightness

- [ ] "Set brightness to 70"
- [ ] "Increase brightness"
- [ ] "Decrease brightness"

---

## 🎵 Music (Spotify)

- [ ] "Play some music"
- [ ] "Pause music"
- [ ] "Next song"
- [ ] "Previous song"

---

## 📝 Content Mode

- [ ] "Enter content mode"
- [ ] "Make it formal"
- [ ] "Make it shorter"
- [ ] "Create PDF"
- [ ] "Exit content mode"

---

## 🔍 Web Search

- [ ] "Search for Python tutorials"
- [ ] "Look up weather in London"

---

## ⚡ System Commands

- [ ] "Battery status"
- [ ] "System info"
- [ ] "WiFi status"

---

## 🔄 Follow-up Tests

Test the Intent State system:

1. Say: "Play a song" → Should ask "Which song?"
2. Reply: "Bohemian Rhapsody" → Should play

Cancel test:
1. Say: "Set a reminder" → Should ask for details
2. Reply: "Never mind" → Should cancel

Override test:
1. Say: "Play music from..." → Waiting for input
2. Say: "What time is it?" → Should override and answer

---

## ✅ Test Results

| Feature | Status | Notes |
|---------|--------|-------|
| Remember facts | | |
| Recall knowledge | | |
| Forget memories | | |
| Memory panel | | |
| Volume control | | |
| App control | | |
| Weather | | |
| Follow-ups | | |
| Cancel/Override | | |
