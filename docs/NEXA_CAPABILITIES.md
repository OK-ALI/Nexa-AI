# 🤖 Nexa AI - Complete Capabilities Reference

**Total Voice Commands:** 180+  
**Last Updated:** March 3, 2026  
**Status:** Phase 30 Complete (22/31 Phases)  
**Next Priority:** 💜 Phase 31 - Personality & Fun

---

## 📊 Quick Stats

| Category | Functions | Status |
|----------|-----------|--------|
| Core AI & Conversation | 3 | ✅ Phase 1 |
| Voice Interface | N/A (built-in) | ✅ Phase 2 |
| System Info & Battery | 5 | ✅ Phase 3 |
| Volume Control | 6 | ✅ Phase 3 |
| Brightness Control | 4 | ✅ Phase 3 |
| Application Management | 6 | ✅ Phase 3 |
| Window Management | 5 | ✅ Phase 4 |
| Screenshots | 3 | ✅ Phase 5 |
| Speaker Verification | N/A (built-in) | ✅ Phase 6 |
| GPU Monitoring | 1 | ✅ Phase 7 |
| WiFi Management | 5 | ✅ Phase 8 |
| Clipboard & Text | 5 | ✅ Phase 9 |
| Keyboard Shortcuts | N/A (built-in) | ✅ Phase 10 |
| File & Folders | 3 | ✅ Phase 11 |
| Music Control | 17 | ✅ Phase 12 |
| Weather | 2 | ✅ Phase 13 |
| Content Mode & PDF | 17 | ✅ Phase 14 |
| File Sharing | 6 | ⏸️ Phase 15 (Paused) |
| System Control | 26 | ✅ Phase 16 |
| Smart Memory | 20 | ✅ Phase 20 |
| File Management | 15 | ✅ Phase 21 |
| YouTube + Web | 12 | ✅ Phase 18 |
| Companion: Thinking | 3 | ✅ Phase 28 |
| Companion: Proactive | 6 | ✅ Phase 29 |
| Companion: Emotional Intelligence | 5 | ✅ Phase 30 |
| Login & Security | 1 | ✅ Bonus |
| Phase 29 Extended | 4 | ✅ Mar 2026 |

---

## 🎤 All Voice Commands by Category

### ⏰ Time & Date
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `get_current_time` | "What time is it?", "Current time" | None |
| `get_current_date` | "What's today's date?", "Today's date" | None |

---

### 🔋 Battery
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `get_battery_status` | "Battery status", "How's my battery?" | None |
| `get_battery_percentage` | "Battery level", "Battery percent" | None |

---

### 🎮 GPU Monitoring
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `get_gpu_usage` | "GPU usage", "VRAM status" | None |

---

### 🌤️ Weather
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `get_weather` | "What's the weather?", "Weather in Tokyo" | `location` (optional) |
| `get_forecast` | "Weather forecast", "Next 3 days forecast" | `location`, `days` (1-5) |

---

### 🔍 Web Search
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `search_web` | "Search for...", "Google..." | `query` (required) |

---

### 📡 WiFi Management
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `get_wifi_status` | "WiFi status", "Am I connected?" | None |
| `disconnect_wifi` | "Disconnect WiFi", "Go offline" | None |
| `connect_wifi` | "Connect to NetworkName" | `network_name` |
| `list_wifi_networks` | "List WiFi networks", "Available networks" | None |
| `get_saved_wifi_profiles` | "Saved WiFi", "WiFi profiles" | None |

---

### 📱 Application Management
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `open_application` | "Open Chrome", "Launch Notepad" | `app_name` |
| `close_application` | "Close Chrome", "Quit Spotify" | `app_name` |
| `close_active_window` | "Close this", "Close window" | None |
| `get_running_applications` | "Running apps", "What's open?" | None |
| `get_installed_applications` | "List installed apps", "My applications" | `search_query`, `limit` |
| `is_application_running` | "Is Chrome running?" | `app_name` |
| `refresh_installed_apps` | "Refresh apps", "Rescan apps" | None |

---

### 🔊 Volume Control
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `set_volume` | "Set volume to 50" | `level` (0-100) |
| `get_current_volume` | "Current volume", "Volume level" | None |
| `increase_volume` | "Volume up", "Louder" | `amount` (default 10) |
| `decrease_volume` | "Volume down", "Quieter" | `amount` (default 10) |
| `mute_volume` | "Mute", "Mute volume" | None |
| `unmute_volume` | "Unmute", "Unmute volume" | None |

---

### 💡 Brightness Control
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `set_brightness` | "Set brightness to 50" | `level` (0-100) |
| `get_current_brightness` | "Current brightness" | None |
| `increase_brightness` | "Brighter", "Brightness up" | `amount` (default 10) |
| `decrease_brightness` | "Dimmer", "Brightness down" | `amount` (default 10) |

---

### 👁️ Screen Vision (OCR)
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `read_screen_content` | "Read screen", "What's on screen?" | None |
| `describe_screen` | "Describe screen", "What am I looking at?" | None |

---

### 🪟 Window Management
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `minimize_window` | "Minimize Chrome", "Minimize this" | `app_name` |
| `maximize_window` | "Maximize window" | `app_name` |
| `restore_window` | "Restore window" | `app_name` |
| `get_active_window` | "Active window", "What window?" | None |

---

### 📸 Screenshots
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `take_screenshot` | "Take screenshot", "Screenshot" | `custom_name` (optional) |
| `take_screenshot_clipboard` | "Screenshot to clipboard" | `custom_name` (optional) |
| `open_screenshots_folder` | "Open screenshots folder" | None |

---

### 🎮 Games
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `launch_game` | "Launch Minecraft", "Play GTA" | `game_name` |
| `list_games` | "List games", "My games" | `platform` (optional) |

---

### 📁 Files & Folders
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `open_folder` | "Open downloads", "Open documents" | `folder_name` |
| `find_folder` | "Find folder games" | `folder_name` |

---

### 🎵 Music Control (17 functions)
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `play_music` | "Play music", "Play song_name" | `song_name` (optional) |
| `play_random_music` | "Random music", "Shuffle play" | None |
| `list_music` | "List songs", "My music" | `limit` (optional) |
| `pause_music` | "Pause", "Pause music" | None |
| `resume_music` | "Resume", "Continue playing" | None |
| `stop_music` | "Stop music" | None |
| `next_song` | "Next song", "Skip" | None |
| `previous_song` | "Previous song", "Go back" | None |
| `whats_playing` | "What's playing?", "Current song" | None |
| `music_library_stats` | "Music stats", "Library stats" | None |
| `suggest_music` | "Suggest songs" | `count`, `based_on_current` |
| `enable_shuffle` | "Enable shuffle", "Shuffle on" | None |
| `disable_shuffle` | "Disable shuffle", "Shuffle off" | None |
| `set_repeat_mode` | "Repeat one", "Repeat all", "Repeat off" | `mode` |
| `get_playback_mode` | "Playback mode" | None |
| `play_all_library` | "Play all music" | `shuffle` (optional) |

---

### 🎨 Theme Control
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `switch_theme` | "Switch theme", "Toggle theme" | None |
| `set_dark_theme` | "Dark mode", "Dark theme" | None |
| `set_light_theme` | "Light mode", "Light theme" | None |

---

### 📋 Clipboard & Text
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `select_all_text` | "Select all" | None |
| `copy_selected_text` | "Copy that", "Copy" | None |
| `paste_clipboard` | "Paste", "Paste it" | None |
| `cut_selected_text` | "Cut that" | None |
| `delete_selected_text` | "Delete selection" | None |

---

### 📝 Content Mode & PDF (17 functions)
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `enter_content_mode` | "Content mode", "Open content box" | None |
| `exit_content_mode` | "Exit content mode", "Close content" | None |
| `mark_content_ready` | "I'm ready", "Content ready" | None |
| `refine_text` | "Make it formal", "Summarize", "Improve" | `mode` (many options) |
| `create_pdf` | "Create PDF", "Export PDF" | `pdf_format`, `filename` |
| `format_bold` | "Bold", "Make it bold" | None |
| `format_italic` | "Italic" | None |
| `format_underline` | "Underline" | None |
| `format_align` | "Center align", "Justify" | `alignment` |
| `set_font` | "Use Arial font" | `font_name` |
| `set_font_size` | "Font size 14" | `size` |
| `increase_font_size` | "Bigger font" | None |
| `decrease_font_size` | "Smaller font" | None |
| `create_bullet_list` | "Make bullet list" | None |
| `create_numbered_list` | "Make numbered list" | None |
| `increase_indent` | "Indent more" | None |
| `decrease_indent` | "Indent less" | None |
| `clear_formatting` | "Clear formatting" | None |

**Refine Modes:** `formal`, `shorter`, `grammar_only`, `improve`, `summarize`, `casual`, `paraphrase`, `expand`, `simplify`, `academic`, `outline`, `add_headings`, `extract_terms`, `flashcards`, `study_questions`, `difficulty_check`

---

### 📤 File Sharing (Phase 15 - Paused)
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `share_file` | "Share file", "Share it" | `file_path` (auto-detect) |
| `share_to_whatsapp` | "Share on WhatsApp" | `file_path` |
| `share_to_phone` | "Share to phone", "Send to phone" | `file_path` |
| `share_via_phone_link` | "Send via phone link" | `file_path` |
| `upload_to_drive` | "Upload to drive" | `file_path`, `folder` |
| `copy_file_to_clipboard` | "Copy file" | `file_path` |

**Status:** ⏸️ Paused - Clipboard & Google Drive working, platform automation research ongoing.

---

### ⚡ System Control (Phase 16 - 26 functions)

#### Power Control
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `lock_screen` | "Lock screen", "Lock computer" | None |
| `system_sleep` | "Sleep", "Put to sleep" | None |
| `system_hibernate` | "Hibernate" | None |
| `system_restart` | "Restart computer", "Reboot" | `delay_seconds` |
| `system_shutdown` | "Shutdown computer", "Power off" | `delay_seconds` |
| `schedule_shutdown` | "Shutdown in 30 minutes" | `minutes` |
| `schedule_restart` | "Restart in 5 minutes" | `minutes` |
| `cancel_shutdown` | "Cancel shutdown" | None |

#### Power Plans
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `get_power_plan` | "What power plan?", "Power mode" | None |
| `list_power_plans` | "List power plans" | None |
| `set_power_plan` | "High performance mode", "Power saver" | `plan` |

#### Battery Saver
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `enable_battery_saver` | "Enable battery saver" | None |
| `disable_battery_saver` | "Disable battery saver" | None |

#### Bluetooth
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `get_bluetooth_status` | "Bluetooth status" | None |
| `list_bluetooth_devices` | "List Bluetooth devices" | None |
| `open_bluetooth_settings` | "Bluetooth settings", "Pair bluetooth" | None |
| `enable_bluetooth` | "Turn on bluetooth" | None |
| `disable_bluetooth` | "Turn off bluetooth" | None |

#### Night Light
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `enable_night_light` | "Enable night light", "Blue light on" | None |
| `disable_night_light` | "Disable night light" | None |
| `toggle_night_light` | "Night light settings" | None |

#### Quick Settings
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `toggle_airplane_mode` | "Airplane mode", "Flight mode" | None |
| `open_accessibility_settings` | "Accessibility", "Ease of access" | None |
| `open_display_project` | "Second screen", "Extend display" | None |
| `open_cast_settings` | "Cast settings", "Connect to TV" | None |
| `open_nearby_share` | "Nearby share" | None |
| `check_windows_update` | "Check for updates" | None |
| `open_focus_assist` | "Focus assist", "Do not disturb" | None |

---

### 🐾 Desktop Companion (P1-P7 Complete)
| Feature | Description |
|---------|-------------|
| **Sprite Mode** | Custom Nexa character with 8 states, floating/breathing animations |
| **Live2D Mode** | Professional 2D animation with physics, expressions, motions |
| **States** | Idle, Listening, Thinking, Speaking, Sleeping, Happy, Error, Content Mode |
| **Integration** | Syncs with NexaBrain state, draggable, transparent window |

---

### 🎬 YouTube & Web (Phase 18)
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `play_youtube` | "Play Bohemian Rhapsody on YouTube" | `query` |
| `search_youtube` | "Search YouTube for tutorials" | `query`, `max_results` |
| `download_youtube` | "Download this video" | `url`, `quality` |
| `get_youtube_trending` | "What's trending on YouTube?" | None |
| `search_web` | "Search for...", "Google..." | `query` |

---

### 🧠 Smart Memory (Phase 20)
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `learn_fact` | "Remember that I like dark theme" | `fact` |
| `recall_memories` | "What do you know about me?" | `query` |
| `forget_memory` | "Forget about my password" | `query` |
| `show_memory_panel` | "Show my memories" | None |

---

### 📂 File Management (Phase 21)
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `create_file` | "Create a file called notes.txt" | `file_name`, `content` |
| `move_file` | "Move report.pdf to Documents" | `source`, `destination` |
| `copy_file` | "Copy photo.jpg to backup" | `source`, `destination` |
| `delete_file` | "Delete old_file.txt" | `file_path` |
| `rename_file` | "Rename doc.txt to notes.txt" | `file_path`, `new_name` |
| `find_files` | "Find all PDF files" | `pattern`, `location` |
| `organize_downloads` | "Organize my downloads" | None |
| `compress_folder` | "Zip the project folder" | `folder_path` |

---

### 🔐 Login & Security (Bonus)
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `lock_nexa` | "Lock Nexa", "Lock yourself" | None |

---

### 💜 Emotional Intelligence (Phase 30)
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `journal_thought` | "Journal a thought", "Remember this feeling" | `thought` |
| `track_goal` | "Track a goal", "I want to learn guitar" | `goal_name`, `description` |
| `update_goal` | "Update my goal", "I made progress on..." | `goal_name`, `status`, `progress_note` |
| `get_my_goals` | "Show my goals", "What are my goals?" | None |
| `get_my_mood` | "What's my mood?", "How am I feeling?" | None |

---

### 💭 Companion Mode (Phases 28-29)
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `accept_proactive_suggestion` | "Sure", "Yes, do it" | None |
| `decline_proactive_suggestion` | "No thanks", "Not now" | None |

---

### 🚪 Nexa Control
| Function | Voice Commands | Parameters |
|----------|----------------|------------|
| `exit_nexa` | "Exit Nexa", "Goodbye Nexa", "Quit Nexa" | None |
| `clear_conversation_history` | "Clear history", "Forget conversation" | None |

---

## 🔮 Coming Soon (Planned Phases)

### 💜 Companion Mode

| Phase | Feature | Description | Status |
|-------|---------|-------------|--------|
| **28** | Thinking State Feedback | "Working on it...", "Let me check..." - Immediate audio feedback | ✅ COMPLETED |
| **29** | Proactive Engagement | Idle suggestions, break reminders, time-based greetings | ✅ COMPLETED |
| **30** | Emotional Intelligence | Mood detection, emotional memory, check-ins, journaling, goal tracking | ✅ COMPLETED |
| **31** | Personality & Fun | Opinions, jokes, mini-games, compliments, nicknames | 📋 PLANNED |

### Standard Phases

| Phase | Feature | Status |
|-------|---------|--------|
| 17 | Modern Particle Orb UI | ✅ Completed |
| 18 | YouTube + Web Intelligence | ✅ Completed |
| 19 | Email Integration | 📋 Planned |
| 20 | Smart Memory (LanceDB) | ✅ Completed |
| 21 | File Management | ✅ Completed |
| 22 | Screen Reading (PaddleOCR) | 📋 Planned |
| 23 | Smart Notifications | 📋 Planned |
| 24 | Productivity Suite | 📋 Planned |
| 25 | Voice Profile Enhancement | 📋 Planned |
| 26 | Advanced AI Features | 📋 Planned |

---

## 📌 Notes

1. **Single Model Architecture**: Llama 3.1 8B for both online and offline via Ollama
2. **No Wake Word**: Responds to all speech (configurable in `listener.py`)
3. **Speaker Verification**: Enrolled users only (Phase 6)
4. **Smart File Detection**: Many commands auto-detect last created file
5. **Content Mode**: Full document editing with PDF export
6. **Phase 15 (Sharing)**: Clipboard method works universally, platform automation paused
7. **Emotional Intelligence**: Mood tracking, goal management, event check-ins (Phase 30)
8. **180+ Functions**: Registered in `capabilities/function_registry.py`
