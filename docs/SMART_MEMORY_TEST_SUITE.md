# Smart Memory Voice Command Test Suite

Complete manual testing checklist for Nexa's Smart Memory features.

**Last Updated:** January 1, 2026  
**Status:** Ready for Testing  
**Recent Fixes (Jan 1, 2026):**
- ✅ Knowledge table migration (category column)
- ✅ Follow-up list resolution (games/songs/apps now persist correctly)
- ✅ Memory Panel toggle buttons (added logging)
- ✅ Memory Panel size increased (550x700)
- ✅ Music list follow-ups ("play the third one" after "list songs")
- ✅ Dynamic ordinal support for all list types

---

## 🧠 Part 1: Remember Facts

Test the **remember_this** command that stores knowledge in LanceDB.

| # | Voice Command | Expected Result |
|---|---------------|-----------------|
| 1 | "Remember that I prefer dark theme" | ✅ Stored fact about theme preference |
| 2 | "Note that my favorite browser is Chrome" | ✅ Stored fact about browser |
| 3 | "Remember that I like jazz music" | ✅ Stored fact about music |
| 4 | "Remember I work from 9 to 5" | ✅ Stored fact about schedule |
| 5 | "Note that my birthday is December 15" | ✅ Stored fact about birthday |

---

## 📚 Part 2: Recall Knowledge

Test the **what_do_you_know** command that searches memories semantically.

| # | Voice Command | Expected Result |
|---|---------------|-----------------|
| 1 | "What do you know about my preferences?" | Shows theme, music preferences |
| 2 | "Do you remember my favorite browser?" | Returns Chrome |
| 3 | "What do you know about music?" | Returns jazz preference |
| 4 | "Do you remember my schedule?" | Returns work hours |
| 5 | "What do you know about themes?" | Returns dark theme preference |

---

## 🗑️ Part 3: Forget Memories

Test the **forget_about** command that deletes matching memories.

| # | Voice Command | Expected Result |
|---|---------------|-----------------|
| 1 | "Forget about jazz music" | Deletes music preference |
| 2 | "Delete memories about browsers" | Deletes browser preference |
| 3 | "Forget my work schedule" | Deletes schedule info |

**Verify deletion:**
- Say "What do you know about music?" → Should NOT find jazz anymore

---

## 📊 Part 4: Memory Statistics

Test the **get_memory_stats** command.

| # | Voice Command | Expected Result |
|---|---------------|-----------------|
| 1 | "Memory stats" | Shows conversation, knowledge, skills counts |
| 2 | "How many memories do you have?" | Shows counts |
| 3 | "Show memory statistics" | Shows counts |

---

## 🖼️ Part 5: Memory Panel GUI

Test the **show_memory_panel** command that opens the GUI.

| # | Voice Command | Expected Result |
|---|---------------|-----------------|
| 1 | "Show my memories" | Opens Memory Panel window |
| 2 | "Open memory panel" | Opens Memory Panel window |
| 3 | "Manage my memories" | Opens Memory Panel window |

**In the GUI, test:**
- [ ] Search bar filters memories
- [ ] Tabs switch between Conversations/Knowledge/Skills
- [ ] Star icon marks memory as important
- [ ] Trash icon deletes memory (with confirmation)
- [ ] Export button saves to JSON
- [ ] Clear Old button removes old memories

---

## 🔄 Part 6: Follow-up Conversations (Intent State)

Test dynamic follow-ups that ask for missing information.

### Test 6.1: Normal Follow-up

1. Say: **"Play a song"**
   - Expected: Nexa asks "Which song would you like me to play?"
2. Reply: **"Bohemian Rhapsody"**
   - Expected: Attempts to play the song

### Test 6.2: Cancel Follow-up

1. Say: **"Set a reminder"**
   - Expected: Nexa asks for reminder details
2. Reply: **"Never mind"** or **"Cancel"** or **"Forget it"**
   - Expected: Nexa cancels and returns to normal

### Test 6.3: Override with New Command

1. Say: **"Play music from..."**
   - Expected: Nexa waits for more info
2. Reply: **"What time is it?"**
   - Expected: Nexa abandons music request and tells the time

### Test 6.4: Timeout

1. Say: **"Send an email to..."**
   - Expected: Nexa waits for recipient
2. Wait 2+ minutes without responding
   - Expected: Follow-up expires, Nexa returns to normal

---

## 🔗 Part 7: Contextual Memory (This/That References)

Test reference resolution from previous actions.

### Test 7.1: Close Reference

1. Say: **"Open Chrome"**
   - Expected: Opens Chrome
2. Say: **"Close it"**
   - Expected: Closes Chrome (resolved "it" = Chrome)

### Test 7.2: Volume Reference

1. Say: **"Set volume to 80"**
   - Expected: Volume set to 80%
2. Say: **"Lower that"**
   - Expected: Decreases volume (resolved "that" = volume)

---

## 🔢 Part 7.5: Ordinal Follow-ups (Dynamic Lists)

Test that "the first/second/third one" works for ALL list types.

### Test 7.5.1: Games List

1. Say: **"List my games"**
   - Expected: Lists installed games
2. Say: **"How many?"**
   - Expected: Tells count (follow-up works)
3. Say: **"Open the third one"**
   - Expected: Opens the 3rd game from the list (NOT running apps!)

### Test 7.5.2: Music List

1. Say: **"List my songs"** or **"Show my music"**
   - Expected: Lists songs from music library
2. Say: **"Play the second one"**
   - Expected: Plays the 2nd song from the list

### Test 7.5.3: Running Apps

1. Say: **"What apps are running?"**
   - Expected: Lists running applications
2. Say: **"Close the last one"**
   - Expected: Closes the last app from the list

### Test 7.5.4: WiFi Networks

1. Say: **"List WiFi networks"**
   - Expected: Shows available networks
2. Say: **"Connect to the first one"**
   - Expected: Connects to the 1st network

### Ordinal Support:
- `first`, `1st` → index 0
- `second`, `2nd` → index 1
- `third`, `3rd` → index 2
- `fourth`, `4th` → index 3
- `fifth`, `5th` → index 4
- `last` → index -1
- `previous` → index -2

---

## 🎯 Part 8: Semantic Search Quality

Test that memories are found by meaning, not just keywords.

| # | First Store | Then Search | Should Match? |
|---|-------------|-------------|---------------|
| 1 | "Remember I like coffee" | "What beverages do I enjoy?" | ✅ Yes |
| 2 | "Remember my car is Tesla" | "What vehicle do I drive?" | ✅ Yes |
| 3 | "Remember I work at Google" | "Where am I employed?" | ✅ Yes |
| 4 | "Remember I prefer dark mode" | "What UI theme do I like?" | ✅ Yes |

---

## 📝 Part 9: Conversation Memory

Test that conversations are automatically stored.

1. Have a conversation:
   - "What's the weather today?"
   - "Open calculator"
   - "Set brightness to 70"

2. Say: **"Show my memories"**
   - Expected: See recent conversations in Conversations tab

3. Say: **"What did we talk about earlier?"**
   - Expected: Nexa recalls recent topics

---

## 🤖 Part 10: Automatic Learning (Natural Conversation)

This tests Nexa's ability to **learn from natural conversation** without explicit "remember" commands.

### Test 10.1: Preference Detection

Say these naturally (Nexa should learn WITHOUT you saying "remember"):

| # | What You Say | Nexa Should Learn |
|---|--------------|-------------------|
| 1 | "I really prefer dark themes, they're easier on my eyes" | User prefers dark themes |
| 2 | "Chrome is my go-to browser for everything" | User's favorite browser is Chrome |
| 3 | "I'm a huge jazz fan, especially Miles Davis" | User loves jazz music |
| 4 | "I usually start work around 9 AM" | User starts work at 9 AM |
| 5 | "My birthday is on December 15th" | User's birthday is December 15th |

### Verify Learning Worked:

After saying the above, ask:
- "What do you know about my preferences?" → Should recall dark themes, Chrome
- "Do you remember my birthday?" → Should recall December 15th
- "What music do I like?" → Should recall jazz

### Test 10.2: Contextual Learning

| # | Conversation Flow | Should Learn |
|---|-------------------|--------------|
| 1 | "Open Spotify and play some jazz" | User uses Spotify for music |
| 2 | "Set volume to 30, I like it quiet when working" | User prefers quiet volume for work |
| 3 | "I hate bright screens, can you lower brightness?" | User dislikes bright screens |

---

## ✅ Test Results Tracking

| Feature | Status | Notes |
|---------|--------|-------|
| **Remember facts** | ⬜ | |
| **Recall knowledge** | ⬜ | |
| **Forget memories** | ⬜ | |
| **Memory stats** | ⬜ | |
| **Memory Panel GUI** | ⬜ | |
| **Memory Panel toggle star** | ⬜ | Check logs for "Toggle importance" |
| **Memory Panel size** | ⬜ | Should be 550x700 |
| **Follow-up resolve** | ⬜ | |
| **Follow-up cancel** | ⬜ | |
| **Follow-up override** | ⬜ | |
| **Follow-up timeout** | ⬜ | |
| **Close it reference** | ⬜ | |
| **Lower that reference** | ⬜ | |
| **Games → open third one** | ⬜ | Critical: Should open game, not app |
| **Music → play second one** | ⬜ | |
| **Apps → close last one** | ⬜ | |
| **WiFi → connect first one** | ⬜ | |
| **Semantic coffee→beverages** | ⬜ | |
| **Semantic Tesla→vehicle** | ⬜ | |
| **Conversation storage** | ⬜ | Check "You: [msg] → [response]" format |

**Legend:** ⬜ Not tested | ✅ Passed | ❌ Failed

---

## 🐛 Issues Found

Document any issues here:

| Issue | Voice Command | Expected | Actual |
|-------|---------------|----------|--------|
| | | | |
| | | | |
| | | | |

---

## 📝 Fixes Applied (January 1, 2026)

| Issue | Root Cause | Fix Applied |
|-------|-----------|-------------|
| Knowledge not storing | Missing `category` column in LanceDB table | Added migration in `memory_store.py` |
| "Open third one" → wrong list | `push_action()` overwrote `last_action_data` | Now checks `IntentState._last_list` first |
| Memory Panel crash | PyQt5/PySide6 mismatch | Fixed imports to PySide6 |
| Memory Panel toggle not visible | Silent errors | Added logging to `_on_marked_important()` |
| Memory Panel too small | Fixed 450x600 size | Increased to 550x700 |
| Music ordinals not working | No `list_music` wrapper | Added `list_music()` to executor with follow-up support |
