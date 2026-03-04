# NEXA AI — Comprehensive Test Suite

> **Purpose:** Evaluate every feature, function, reasoning capability, follow-up, memory, and integration of NEXA AI before adding new roadmap features.
>
> **How to Use:** Work through each level sequentially. Mark each test ✅ PASS, ❌ FAIL, or ⚠️ PARTIAL. Record any notes in the "Result" column.
>
> **Levels:**
> - **Level 1 — Simple:** Single commands, no parameters or obvious parameters, instant results
> - **Level 2 — Medium:** Commands with specific parameters, multi-word inputs, validation
> - **Level 3 — High:** Multi-turn conversations, follow-ups, context awareness, workflows
> - **Level 4 — Complex:** Compound commands, conditional logic, cross-system integration, edge cases, stress tests

---

## Table of Contents

1. [Level 1 — Simple Tests](#level-1--simple-tests)
2. [Level 2 — Medium Tests](#level-2--medium-tests)
3. [Level 3 — High Tests](#level-3--high-tests)
4. [Level 4 — Complex Tests](#level-4--complex-tests)
5. [Regression & Edge Case Tests](#regression--edge-case-tests)
6. [Scoring Summary](#scoring-summary)

---

# Level 1 — Simple Tests

> Single commands with no or obvious parameters. Should respond instantly or within 2 seconds.

---

## 1.1 — Quick Response Cache (LLM Bypass)

These commands are handled by regex and should bypass the LLM entirely for instant response.

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 1 | "What time is it?" | Returns current time instantly | |
| 2 | "Current time" | Returns current time instantly | |
| 3 | "Tell me the time" | Returns current time instantly | |
| 4 | "Battery level" | Returns battery percentage | |
| 5 | "Battery status" | Returns battery % + charging state | |
| 6 | "How's my battery?" | Returns battery status | |
| 7 | "Current volume" | Returns volume percentage | |
| 8 | "Volume level" | Returns volume percentage | |
| 9 | "What's the volume?" | Returns volume percentage | |
| 10 | "Current brightness" | Returns brightness percentage | |
| 11 | "Brightness level" | Returns brightness percentage | |
| 12 | "What's the brightness?" | Returns brightness percentage | |
| 13 | "WiFi status" | Returns WiFi connection state | |
| 14 | "Internet connection" | Returns WiFi/internet status | |

---

## 1.2 — Time & Date

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 15 | "What's today's date?" | Returns current date | |
| 16 | "What day is it?" | Returns day of week + date | |

---

## 1.3 — System Information

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 17 | "System info" | Returns OS, CPU, RAM, disk info | |
| 18 | "What are my PC specs?" | Returns detailed hardware specs | |
| 19 | "GPU usage" | Returns GPU utilization percentage | |

---

## 1.4 — Volume Control (Basic)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 20 | "Mute" | Mutes system volume | |
| 21 | "Unmute" | Unmutes system volume | |
| 22 | "Volume up" | Increases volume (default increment) | |
| 23 | "Volume down" | Decreases volume (default increment) | |

---

## 1.5 — Brightness Control (Basic)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 24 | "Increase brightness" | Brightness goes up by default step | |
| 25 | "Decrease brightness" | Brightness goes down by default step | |

---

## 1.6 — Music Control (Basic)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 26 | "Pause music" | Pauses currently playing song | |
| 27 | "Resume music" | Resumes paused song | |
| 28 | "Stop music" | Stops playback completely | |
| 29 | "Next song" | Advances to next track | |
| 30 | "Previous song" | Goes to previous track | |
| 31 | "What song is playing?" | Returns current track name + artist | |
| 32 | "Play random music" | Starts playing a random song from library | |

---

## 1.7 — Screenshots

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 33 | "Take a screenshot" | Captures and saves screenshot | |
| 34 | "Screenshot to clipboard" | Captures screenshot to clipboard | |
| 35 | "Open screenshots folder" | Opens the screenshots directory | |

---

## 1.8 — Window Management (Basic)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 36 | "What's the active window?" | Returns current foreground window title | |
| 37 | "Minimize" | Minimizes current window | |
| 38 | "Maximize" | Maximizes current window | |

---

## 1.9 — Theme & UI

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 39 | "Switch theme" | Toggles between dark/light theme | |
| 40 | "Set dark theme" | Switches to dark theme | |
| 41 | "Set light theme" | Switches to light theme | |

---

## 1.10 — Lock & Security

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 42 | "Lock Nexa" | Locks the Nexa interface | |
| 43 | "Lock the screen" | Locks Windows (Win+L) | |

---

## 1.11 — System Power (Basic)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 44 | "Put the computer to sleep" | System enters sleep mode | |
| 45 | "Hibernate" | System hibernates | |

---

## 1.12 — Conversation

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 46 | "Clear conversation history" | Resets conversation context | |
| 47 | "List all your functions" | Returns list of available commands | |
| 48 | "Exit Nexa" | Gracefully shuts down NEXA | |

---

## 1.13 — TTS Engine

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 49 | "What TTS engine are you using?" | Returns current engine name (kokoro/coqui) | |

---

## 1.14 — Clipboard Operations

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 50 | "Select all" | Sends Ctrl+A to active window | |
| 51 | "Copy that" | Sends Ctrl+C | |
| 52 | "Paste" | Sends Ctrl+V | |
| 53 | "Cut" | Sends Ctrl+X | |
| 54 | "Delete selected" | Deletes selected text | |

---

## 1.15 — Smart Memory (Basic)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 55 | "What do you know about me?" | Returns stored knowledge or "I don't have info" | |
| 56 | "Memory stats" | Returns total memories, categories, storage size | |
| 57 | "Show memory panel" | Opens the Memory Panel UI | |

---

## 1.16 — Emotional Intelligence (Basic)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 58 | "What's my mood?" | Returns current detected mood + trend | |
| 59 | "What are my goals?" | Returns list of active goals or "no goals" | |

---

## 1.17 — Proactive Engagement (Basic)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 60 | *(Wait for proactive suggestion)* | NEXA offers suggestion after idle period | |
| 61 | "Sure" / "Yes" (after suggestion) | Accepts and executes proactive suggestion | |
| 62 | "No thanks" (after suggestion) | Declines suggestion gracefully | |

---

# Level 2 — Medium Tests

> Commands with specific parameters, natural language variations, and validation.

---

## 2.1 — Volume Control (Parametric)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 63 | "Set volume to 50" | Volume set to exactly 50% | |
| 64 | "Set volume to 75 percent" | Volume set to 75% | |
| 65 | "Turn the volume up by 20" | Volume increases by 20 from current | |
| 66 | "Decrease volume by 30" | Volume decreases by 30 | |
| 67 | "Set volume to 0" | Volume set to 0% (effective mute) | |
| 68 | "Set volume to 100" | Volume set to 100% | |

---

## 2.2 — Brightness Control (Parametric)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 69 | "Set brightness to 40" | Brightness set to 40% | |
| 70 | "Increase brightness by 25" | Brightness increases by 25 | |
| 71 | "Set brightness to 0" | Minimum brightness | |
| 72 | "Set brightness to 100" | Maximum brightness | |

---

## 2.3 — Application Management

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 73 | "Open Chrome" | Launches Google Chrome | |
| 74 | "Open Notepad" | Launches Notepad | |
| 75 | "Open File Explorer" | Launches Windows Explorer | |
| 76 | "Close Chrome" | Closes Google Chrome | |
| 77 | "Close the active window" | Closes foreground window | |
| 78 | "What apps are running?" | Lists currently running applications | |
| 79 | "What apps are installed?" | Lists installed applications | |
| 80 | "Search installed apps for 'code'" | Filters installed apps by query | |
| 81 | "Is Chrome running?" | Returns yes/no + details | |
| 82 | "Refresh installed apps" | Re-scans app cache | |

---

## 2.4 — Window Management (Parametric)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 83 | "Minimize Chrome" | Minimizes Chrome window specifically | |
| 84 | "Maximize Notepad" | Maximizes Notepad window | |
| 85 | "Restore Chrome" | Restores Chrome to normal size | |
| 86 | "Make it bigger" | Maximizes active window (natural language) | |
| 87 | "Make it smaller" | Minimizes active window (natural language) | |
| 88 | "Make it full screen" | Maximizes active window (natural language) | |
| 89 | "Shrink it" | Minimizes active window (natural language) | |

---

## 2.5 — WiFi Management

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 90 | "List WiFi networks" | Shows available networks | |
| 91 | "Connect to MyNetwork" | Connects to specified network | |
| 92 | "Disconnect WiFi" | Disconnects from current network | |
| 93 | "Show saved WiFi profiles" | Lists saved network profiles | |

---

## 2.6 — Weather

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 94 | "What's the weather?" | Returns weather for default location | |
| 95 | "Weather in London" | Returns weather for London | |
| 96 | "5-day forecast for New York" | Returns 5-day forecast | |
| 97 | "What's the forecast for tomorrow?" | Returns short-term forecast | |

---

## 2.7 — Web Search & Scraping

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 98 | "Search the web for quantum computing" | Opens browser search OR returns results | |
| 99 | "Smart search for Python decorators" | Returns scraped content from web | |
| 100 | "Scrape this URL: https://example.com" | Returns page content | |

---

## 2.8 — YouTube (Basic Playback)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 101 | "Play Bohemian Rhapsody on YouTube" | Plays video in NVP or browser | |
| 102 | "Search YouTube for cooking tutorials" | Returns numbered list of results | |
| 103 | "Get info about Never Gonna Give You Up" | Returns title, views, duration, channel | |
| 104 | "Get trending videos" | Returns trending videos list | |
| 105 | "Get trending videos in Japan" | Returns JP trending videos | |

---

## 2.9 — YouTube Downloads

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 106 | "Download that YouTube video" | Downloads video (after a play/search) | |
| 107 | "Download YouTube audio of Despacito" | Downloads audio only (MP3/M4A) | |
| 108 | "Download status" | Returns download progress % and ETA | |

---

## 2.10 — Music (Specific Songs)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 109 | "Play Blinding Lights" | Finds and plays specific song | |
| 110 | "Play something by The Weeknd" | Plays song by artist match | |
| 111 | "List my music" | Lists songs in library | |
| 112 | "List my music library" | Full library listing | |
| 113 | "Music library stats" | Returns total songs, artists, size | |
| 114 | "Suggest some music" | Returns suggestions based on library | |
| 115 | "Enable shuffle" | Turns shuffle mode on | |
| 116 | "Disable shuffle" | Turns shuffle mode off | |
| 117 | "Set repeat to one" | Sets repeat mode to repeat-one | |
| 118 | "Set repeat to all" | Sets repeat mode to repeat-all | |
| 119 | "What's the playback mode?" | Returns shuffle + repeat status | |
| 120 | "Play all my music" | Plays entire library | |
| 121 | "Play all music shuffled" | Plays entire library in shuffle | |

---

## 2.11 — Local Video

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 122 | "Play a local video 'movie name'" | Searches and plays local video file | |

---

## 2.12 — Gaming

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 123 | "Launch GTA V" | Launches game via Steam/Epic/standalone | |
| 124 | "List my games" | Lists installed games with platforms | |
| 125 | "List my Steam games" | Lists only Steam games | |

---

## 2.13 — Folder Navigation

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 126 | "Open the Downloads folder" | Opens Downloads in Explorer | |
| 127 | "Find the Documents folder" | Finds and opens Documents | |
| 128 | "Open folder Music" | Opens Music folder | |

---

## 2.14 — Smart Memory (Store & Recall)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 129 | "Remember that my favorite color is blue" | Stores fact in memory | |
| 130 | "Remember my birthday is January 15th" | Stores birthday info | |
| 131 | "Remember I prefer dark mode" | Stores preference | |
| 132 | "What do you know about my favorite color?" | Recalls "blue" | |
| 133 | "When is my birthday?" | Recalls birthday with formatting | |
| 134 | "What are my preferences?" | Recalls stored preferences | |
| 135 | "Forget about my favorite color" | Removes color memory | |
| 136 | "What do you know about my favorite color?" | Should say "nothing" after forget | |

---

## 2.15 — Phase 16: Power Plans

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 137 | "What power plan am I using?" | Returns current active plan | |
| 138 | "List power plans" | Shows all available plans | |
| 139 | "Set power plan to high performance" | Changes power plan | |
| 140 | "Set power plan to balanced" | Changes power plan | |

---

## 2.16 — Phase 16: Battery Saver

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 141 | "Enable battery saver" | Sets threshold to 100% via powercfg (always on) | |
| 142 | "Disable battery saver" | Resets threshold to 20% via powercfg | |

---

## 2.17 — Phase 16: Bluetooth

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 143 | "Bluetooth status" | Returns on/off + connected devices | |
| 144 | "Enable Bluetooth" | Turns Bluetooth on | |
| 145 | "Disable Bluetooth" | Turns Bluetooth off | |
| 146 | "List Bluetooth devices" | Lists paired/available devices | |
| 147 | "Open Bluetooth settings" | Opens ms-settings:bluetooth | |
| 147a | "Connect to Galaxy Buds" | Connects to device by name (Enable-PnpDevice) | |
| 147b | "Connect my headphones" | Finds & connects matching BT device | |
| 147c | "Disconnect Galaxy Buds" | Disconnects BT device by name (Disable-PnpDevice) | |
| 147d | "Connect to NonExistentDevice" | Reports device not found, suggests available devices | |

---

## 2.18 — Phase 16: Quick Settings

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 148 | "Enable night light" | Turns night light on via registry | |
| 149 | "Disable night light" | Turns night light off via registry | |
| 150 | "Toggle night light" | Checks registry state, toggles opposite | |
| 151 | "Toggle airplane mode" | Actually toggles via registry RadioManagement key | |
| 152 | "Open accessibility settings" | Opens accessibility page | |
| 153 | "Extend display" | Runs DisplaySwitch.exe /extend | |
| 153a | "Duplicate screen" | Runs DisplaySwitch.exe /clone | |
| 153b | "PC screen only" | Runs DisplaySwitch.exe /internal | |
| 153c | "Second screen only" | Runs DisplaySwitch.exe /external | |
| 154 | "Open cast settings" | Opens cast/mirror settings | |
| 155 | "Open nearby share" | Opens nearby share settings | |
| 156 | "Check for Windows updates" | Uses COM API to list pending updates with names/sizes | |
| 157 | "Focus assist" | Cycles focus assist: off → priority → alarms → off | |
| 157a | "Set focus assist to alarms only" | Sets focus assist to alarms mode | |
| 157b | "Turn off do not disturb" | Sets focus assist to off | |

---

## 2.19 — Phase 16: Scheduled Power & Sign Out

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 158 | "Shutdown in 30 minutes" | Schedules shutdown via `shutdown /s /t 1800` | |
| 159 | "Restart in 10 minutes" | Schedules restart | |
| 160 | "Cancel shutdown" | Cancels scheduled shutdown/restart | |
| 161 | "Shutdown" | 10s minimum safety delay, says "Say cancel to abort" | |
| 161a | "Shutdown" then "Cancel shutdown" | Shutdown scheduled, then cancelled within 10s | |
| 162 | "Restart" | 10s minimum safety delay, says "Say cancel to abort" | |
| 162a | "Sign out" | Signs out current user via shutdown /l | |
| 162b | "Log off" | Signs out (same as sign_out) | |

---

## 2.20 — Emotional Intelligence (Parametric)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 163 | "Journal: Today was a productive day" | Stores journal entry | |
| 164 | "Track goal: Learn Python" | Creates new goal | |
| 165 | "Track goal: Exercise daily, with description staying healthy" | Creates goal with description | |
| 166 | "Update goal Learn Python: making progress" | Adds progress note | |
| 167 | "Update goal Learn Python: completed" | Marks goal as completed | |

---

## 2.21 — TTS Engine Switching

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 168 | "Switch to Kokoro TTS" | Switches to Kokoro engine | |
| 169 | "Switch to Coqui TTS" | Switches to Coqui XTTS engine | |

---

## 2.22 — Offline Mode

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 170 | "Go offline" | Switches to offline mode | |
| 171 | "Go online" | Switches to online mode | |
| 172 | *(While offline)* "Search YouTube for cats" | Should be blocked with helpful message | |
| 173 | *(While offline)* "What's the weather?" | Should be blocked with helpful message | |
| 174 | *(While offline)* "What time is it?" | Should still work (local function) | |
| 175 | *(While offline)* "Play music" | Should still work (local function) | |

---

# Level 3 — High Tests

> Multi-turn conversations, follow-up handling, context awareness, and workflows.

---

## 3.1 — Intent Follow-Up: Music

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 176 | "Play music" | NEXA asks: "Which song would you like me to play?" | |
| 177 | → "Blinding Lights" | Plays the specified song (follow-up resolved) | |
| 178 | "Play music" → *(wait 3 minutes)* → "Blinding Lights" | Intent expired (120s TTL), treats as new command | |
| 179 | "Play music" → "Never mind" | Cancels pending intent gracefully | |
| 180 | "Play music" → "Cancel" | Cancels pending intent | |
| 181 | "Play music" → "Forget it" | Cancels pending intent | |

---

## 3.2 — Intent Follow-Up: Applications

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 182 | "Open an application" | NEXA asks: "Which application should I open?" | |
| 183 | → "Chrome" | Opens Chrome (follow-up resolved) | |
| 184 | "Open" *(single word, no target)* | NEXA asks: "What would you like me to open?" (ambiguity detection) | |
| 185 | → "Notepad" | Opens Notepad | |

---

## 3.3 — Intent Follow-Up: Games

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 186 | "Launch a game" | NEXA asks: "Which game would you like to launch?" | |
| 187 | → "GTA V" | Launches GTA V | |

---

## 3.4 — Intent Follow-Up: Volume & Brightness

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 188 | "Set the volume" | NEXA asks: "What level should I set it to?" | |
| 189 | → "50" | Sets volume to 50% | |
| 190 | "Set brightness" *(no level)* | NEXA asks: "What brightness level would you like?" | |
| 191 | → "80" | Sets brightness to 80% | |

---

## 3.5 — Intent Follow-Up: YouTube Search Results

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 192 | "Search YouTube for lo-fi music" | Returns numbered list (e.g., 5 results) | |
| 193 | → "Play the third one" | Plays result #3 (ordinal extraction) | |
| 194 | → "Play the first one" | Plays result #1 | |
| 195 | → "Play the last one" | Plays the last result | |
| 196 | → "Play number 2" | Plays result #2 (numeric extraction) | |
| 197 | "Search YouTube for cats" → "How many results?" | Returns count of results (counting question) | |
| 198 | "Search YouTube for cats" → "What are they?" | Lists the results again (listing question) | |

---

## 3.6 — Intent Follow-Up: File Sharing

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 199 | "Share a file" | NEXA asks: "Which file would you like to share?" | |
| 200 | → "the last screenshot" | Shares the most recent screenshot (smart path) | |
| 201 | "Share to WhatsApp" | NEXA asks for file, then shares via WhatsApp | |

---

## 3.7 — Pronoun Resolution

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 202 | "Open Chrome" → "Minimize it" | Minimizes Chrome (pronoun resolved to Chrome) | |
| 203 | "Open Notepad" → "Close it" | Closes Notepad (pronoun resolved) | |
| 204 | "Open Chrome" → "Open Notepad" → "Close it" | Closes Notepad (most recent target) | |
| 205 | "Maximize that" *(no prior context)* | Maximizes active window (fallback to active window) | |

---

## 3.8 — Implicit Reference Resolution

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 206 | "Open Chrome" → "Minimize the app" | Minimizes Chrome ("the app" → last app) | |
| 207 | "Open Chrome" → "Close the application" | Closes Chrome | |
| 208 | "Open Chrome" → "Close the window" | Closes Chrome's window | |
| 209 | "Launch GTA V" → "Close the game" | Closes GTA V | |

---

## 3.9 — Content Mode Workflow

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 210 | "Open content mode" | Content box window appears | |
| 211 | *(Type text in content box)* → "Make it formal" | Text refined to formal tone | |
| 212 | "Make it shorter" | Text shortened | |
| 213 | "Fix the grammar" | Grammar corrected | |
| 214 | "Improve this" | Text enhanced | |
| 215 | "Summarize this" | Text summarized | |
| 216 | "Make it casual" | Casual tone applied | |
| 217 | "Paraphrase this" | Text reworded | |
| 218 | "Expand on this" | Text expanded with detail | |
| 219 | "Simplify this" | Text simplified | |
| 220 | "Make it academic" | Academic tone applied | |
| 221 | "Extract key terms" | Key terms extracted from text | |
| 222 | "Create flashcards" | Flashcards generated | |
| 223 | "Generate study questions" | Study questions generated | |
| 224 | "Check difficulty level" | Difficulty assessment returned | |
| 225 | "Create an outline" | Outline created from text | |
| 226 | "Add headings" | Headings added to text | |

---

## 3.10 — Content Mode: Function Isolation

| # | Voice Command (in Content Mode) | Expected Behavior | Result |
|---|---|---|---|
| 227 | "Play music" | BLOCKED — "I can only help with text editing..." | |
| 228 | "Open Chrome" | BLOCKED — same message | |
| 229 | "What time is it?" | BLOCKED — same message | |
| 230 | "Exit content mode" | Returns to normal operation | |
| 231 | "What time is it?" | NOW works normally | |

---

## 3.11 — Content Mode: PDF Creation

| # | Voice Command (in Content Mode) | Expected Behavior | Result |
|---|---|---|---|
| 232 | "Create a PDF" | Creates basic PDF from content box text | |
| 233 | "Create an academic PDF" | Creates academic-formatted PDF | |
| 234 | "Create a business PDF" | Creates business-formatted PDF | |
| 235 | "Create a PDF called 'My Report'" | Creates PDF with custom filename | |

---

## 3.12 — Content Mode: Formatting Commands

| # | Voice Command (in Content Mode) | Expected Behavior | Result |
|---|---|---|---|
| 236 | "Bold" / "Make it bold" | Applies bold formatting | |
| 237 | "Italic" | Applies italic formatting | |
| 238 | "Underline" | Applies underline | |
| 239 | "Align center" | Centers text | |
| 240 | "Align left" | Left-aligns text | |
| 241 | "Align right" | Right-aligns text | |
| 242 | "Set font to Arial" | Changes font | |
| 243 | "Set font size to 16" | Changes font size | |
| 244 | "Increase font size" | Bumps font size up | |
| 245 | "Decrease font size" | Bumps font size down | |
| 246 | "Create a bullet list" | Converts to bulleted list | |
| 247 | "Create a numbered list" | Converts to numbered list | |
| 248 | "Increase indent" | Indents text | |
| 249 | "Decrease indent" | Removes indent | |
| 250 | "Clear formatting" | Removes all formatting | |

---

## 3.13 — File Management (Phase 21)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 251 | "Create a file called test.txt on the desktop" | Creates file at specified location | |
| 252 | "Move test.txt to Documents" | Moves file | |
| 253 | "Copy test.txt to Downloads" | Copies file | |
| 254 | "Rename test.txt to demo.txt" | Renames file | |
| 255 | "Delete demo.txt" | Deletes file (with confirmation?) | |
| 256 | "Search for files named 'report'" | Searches and returns matching files | |
| 257 | "Show recent files" | Lists recently modified files | |
| 258 | "Find duplicate files in Downloads" | Scans for duplicates | |
| 259 | "Organize my Downloads folder" | Auto-sorts files by type | |
| 260 | "Clean up Downloads" | Removes old/temp files | |
| 261 | "Bulk rename files in Documents" | Applies naming pattern | |
| 262 | "Compress the Documents folder" | Creates ZIP archive | |
| 263 | "Extract archive report.zip" | Extracts archive | |
| 264 | "Get info about test.txt" | Returns size, date, type, path | |
| 265 | "List contents of Desktop" | Lists files in folder | |

---

## 3.14 — File Sharing (Phase 15)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 266 | "Share test.txt" | Opens share dialog or copies path | |
| 267 | "Share to WhatsApp" *(uses last file)* | Opens WhatsApp with last file (smart path) | |
| 268 | "Share to phone" | Shares via Phone Link (smart path) | |
| 269 | "Share via Phone Link" | Specific Phone Link sharing | |
| 270 | "Upload to Drive" | Uploads last file to Google Drive | |
| 271 | "Copy file to clipboard" | Copies file to clipboard (smart path) | |

---

## 3.15 — YouTube Advanced

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 272 | "Get the transcript of 'Python tutorial'" | Returns video transcript (auto-captions) | |
| 273 | "Get videos from MKBHD channel" | Lists recent uploads | |
| 274 | "Play YouTube playlist [URL]" | Queues and plays playlist | |
| 275 | "YouTube queue" | Shows current queue | |
| 276 | "Clear YouTube queue" | Clears the queue | |
| 277 | "Download YouTube video in 1080p" | Downloads at specific quality | |

---

## 3.16 — Music: Follow-Up Pattern

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 278 | "Play music" | NEXA asks: "What would you like to play?" | |
| 279 | → "Something by Adele" | Searches and plays Adele song | |
| 280 | "Suggest music based on what's playing" | Returns contextual suggestions | |
| 281 | "List music by The Weeknd" | Filters library by artist | |

---

## 3.17 — Smart Memory: Knowledge Awareness

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 282 | "Remember my name is Ali" | Stores fact | |
| 283 | "What's my name?" | Recalls "Ali" | |
| 284 | "Remember I'm a software engineer" | Stores fact | |
| 285 | "Remember my birthday is March 5th" | Stores birthday | |
| 286 | "When is my birthday?" | Returns formatted: "Your birthday is on March 5th" | |
| 287 | "Forget my birthday" | Removes birthday memory | |
| 288 | "When is my birthday?" | Says doesn't know (after forget) | |
| 289 | "Remember I like coffee over tea" | Stores preference | |
| 290 | "What do you know about my preferences?" | Returns coffee preference | |
| 291 | "Clear old memories" | Removes old/stale memories | |
| 292 | "Clear all memories" | Wipes all stored memories | |

---

## 3.18 — Smart Memory: Deduplication

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 293 | "Remember my favorite color is blue" | Stores fact | |
| 294 | "Remember my favorite colour is blue" | Should NOT create duplicate (0.85 similarity) | |
| 295 | "Remember my favorite color is red" | Should UPDATE existing fact (same topic, new value) | |
| 296 | "What's my favorite color?" | Should return "red" (latest value) | |

---

## 3.19 — Emotional Intelligence: Mood Detection

| # | Voice Input (Natural Speech) | Expected Mood Detection | Result |
|---|---|---|---|
| 297 | "I'm feeling great today! Everything is awesome!" | HAPPY (keywords: great, awesome) | |
| 298 | "I can't wait for the weekend! So excited!!!" | EXCITED (keywords + !!! punctuation) | |
| 299 | "Just relaxing, taking it easy" | CALM | |
| 300 | "I'm so tired, long day..." | TIRED (keywords + ... punctuation) | |
| 301 | "Feeling down today, I miss my friends" | SAD | |
| 302 | "I'm so stressed, too much work, deadlines everywhere" | STRESSED | |
| 303 | "Ugh, this doesn't work! So annoying!!" | FRUSTRATED (keywords + ?? punctuation) | |
| 304 | "I'm furious! This is infuriating!" | ANGRY | |
| 305 | "OK" / "Fine" / *(neutral statement)* | NEUTRAL | |
| 306 | "THIS IS AMAZING" *(all caps)* | EXCITED (all-caps amplification × 1.3) | |

---

## 3.20 — Emotional Intelligence: Journaling & Goals

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 307 | "Journal: Had a breakthrough at work today" | Stores journal entry with emotion context | |
| 308 | "Journal: Feeling a bit overwhelmed" | Stores with SAD/STRESSED emotion | |
| 309 | "Track goal: Read 20 books this year" | Creates active goal | |
| 310 | "Update goal Read 20 books: finished book 5" | Adds progress note | |
| 311 | "Get my goals" | Lists all active goals with status | |
| 312 | "Update goal Read 20 books: completed" | Marks goal as completed | |
| 313 | "Get my goals" | Shows completed goal milestone | |

---

# Level 4 — Complex Tests

> Compound commands, conditional logic, cross-system integration, edge cases, and stress tests.

---

## 4.1 — Compound Commands (Multi-Step)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 314 | "Open Chrome and set volume to 50" | Opens Chrome, THEN sets volume to 50% | |
| 315 | "Play music then decrease brightness by 20" | Plays music, THEN dims screen | |
| 316 | "Close Notepad, open Chrome, and set volume to 30" | Executes all 3 in sequence | |
| 317 | "Take a screenshot and open the screenshots folder" | Screenshot taken, folder opened | |
| 318 | "Mute volume then minimize Chrome" | Mutes, then minimizes | |
| 319 | "Set brightness to 100 after that play some music" | Brightness first, then music | |

---

## 4.2 — Conditional Commands

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 320 | "If battery is below 20, enable battery saver" | Checks battery → conditional action | |
| 321 | "If volume is above 80, decrease it by 30" | Checks volume → conditional decrease | |
| 322 | "If brightness is low, set it to 70" | Checks brightness (<30%) → sets 70 | |
| 323 | "If Chrome is running, close it" | Checks app state → closes if running | |
| 324 | "If Chrome is not running, open it" | Checks app state → opens if not running | |
| 325 | "If WiFi is disconnected, connect to MyNetwork" | Checks WiFi → connects | |
| 326 | "When battery is below 15, put computer to sleep" | Evaluates condition → sleep if true | |
| 327 | "Unless WiFi is connected, search for networks" | Inverted condition logic | |
| 328 | "Set volume to 50 if brightness is above 70" | Post-position conditional format | |

---

## 4.3 — Conditional: Question Exclusion (Should NOT Trigger Conditional)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 329 | "When is my birthday?" | Treated as QUESTION, not conditional | |
| 330 | "When was the last update?" | Treated as question | |
| 331 | "When will you support Bluetooth pairing?" | Treated as question | |
| 332 | "What if I close Chrome?" | Treated as question (starts with "what") | |
| 333 | "How do I set brightness?" | Treated as question (starts with "how") | |

---

## 4.4 — Dynamic Preprocessor: Advanced Splitting

| # | Voice Command | Expected Splitting | Result |
|---|---|---|---|
| 334 | "Hi Nexa, how are you?" | NOT split (no action verbs on both sides) | |
| 335 | "Open Chrome and play music" | Split: ["open Chrome", "play music"] | |
| 336 | "Tell me the time then open Notepad" | Split: ["tell me the time", "open Notepad"] | |
| 337 | "Search and destroy" | NOT split ("destroy" is not an action verb) | |
| 338 | "Turn up the volume, decrease brightness" | Split: ["turn up the volume", "decrease brightness"] | |

---

## 4.5 — Cross-System Integration

| # | Voice Command Sequence | Expected Behavior | Result |
|---|---|---|---|
| 339 | "Play music" → "Set volume to 30" → "What song is playing?" | Music plays → volume adjusted → track info returned (3 separate interactions) | |
| 340 | "Open Chrome" → "Search YouTube for music" → "Play the first one" | App opened → YouTube search → ordinal follow-up resolves | |
| 341 | "Remember I'm working on NEXA project" → *(later)* "What am I working on?" | Memory stores → recall works | |
| 342 | "Take a screenshot" → "Share it to WhatsApp" | Screenshot taken → share uses smart path (last screenshot) | |
| 343 | "Create a PDF in content mode" → "Share it" | PDF created → share uses smart path (last PDF) | |

---

## 4.6 — Natural Language Variations

Test that the LLM correctly maps varied natural language to the right function.

| # | Voice Command | Expected Function Call | Result |
|---|---|---|---|
| 344 | "Crank up the volume" | `increase_volume` | |
| 345 | "Turn it down a bit" | `decrease_volume` | |
| 346 | "Shut down the computer" | `system_shutdown` | |
| 347 | "Reboot" | `system_restart` | |
| 348 | "What's on my screen?" | `read_screen_content` (or disabled message) | |
| 349 | "Kill Chrome" | `close_application("chrome")` | |
| 350 | "Fire up Firefox" | `open_application("firefox")` | |
| 351 | "Dim the screen" | `decrease_brightness` | |
| 352 | "Brighten it up" | `increase_brightness` | |
| 353 | "What programs are open?" | `get_running_applications` | |
| 354 | "Grab a screenshot" | `take_screenshot` | |
| 355 | "What's blasting right now?" *(music playing)* | `whats_playing` | |
| 356 | "Hook me up to WiFi" | `list_wifi_networks` or `connect_wifi` | |
| 357 | "I need to find a file called report" | `search_files("report")` | |

---

## 4.7 — AI Reasoning & Conversation Quality

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 358 | "How are you?" | Natural conversational response (no function call) | |
| 359 | "Who are you?" | Identifies as NEXA AI assistant | |
| 360 | "What can you do?" | Lists capabilities naturally | |
| 361 | "Tell me a joke" | Returns a joke (LLM-generated or proactive) | |
| 362 | "Explain quantum computing in simple terms" | Returns explanation (conversation, no function call) | |
| 363 | "What's the meaning of life?" | Returns philosophical response | |
| 364 | "Thank you" | Returns grateful/warm response | |
| 365 | "You're awesome" | Returns appreciative response | |
| 366 | "I love you" | Returns appropriate response | |

---

## 4.8 — Error Handling & Recovery

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 367 | "Open NonExistentApp12345" | Returns "app not found" message | |
| 368 | "Close an app that isn't running" | Returns "not running" message | |
| 369 | "Set volume to 999" | Clamps to 100% or returns error | |
| 370 | "Set brightness to -50" | Clamps to 0% or returns error | |
| 371 | "Play a song that doesn't exist" | Returns "not found" with suggestions | |
| 372 | "Download YouTube while already downloading" | Returns "download already in progress" | |
| 373 | "Share a file that doesn't exist" | Returns appropriate error | |
| 374 | "Connect to WiFi network that doesn't exist" | Returns network not found message | |
| 375 | *(Empty/silence/noise)* | Should not trigger any command | |
| 376 | "asdfjkl gibberish command" | LLM handles gracefully, asks for clarification | |
| 377 | *(Very long input — 500+ words)* | Handles without crash, possibly truncates | |

---

## 4.9 — Speaker Verification

| # | Test | Expected Behavior | Result |
|---|---|---|---|
| 378 | Start enrollment process | Prompts for 5-7 voice samples with specific phrases | |
| 379 | Provide sample 1: Normal speaking voice | Audio validated (>2s, RMS>0.015) → accepted | |
| 380 | Provide sample 2: Loud voice | Audio validated → accepted | |
| 381 | Provide sample 3: Soft voice | Audio validated → accepted | |
| 382 | Provide sample 4: Fast speaking | Audio validated → accepted | |
| 383 | Provide sample 5: Slow speaking | Audio validated → accepted | |
| 384 | Verification: Enrolled person speaks | Cosine similarity ≥0.85 → verified | |
| 385 | Verification: Different person speaks | Cosine similarity <0.85 → rejected | |
| 386 | Verification: Very short audio (<1s) | Fails quality check → falls through (allowed) | |

---

## 4.10 — Proactive Engagement: Triggers

| # | Scenario | Expected Suggestion | Result |
|---|---|---|---|
| 387 | Battery drops to 15% | BATTERY_WARNING suggestion | |
| 388 | Session active for >90 minutes | BREAK_REMINDER suggestion | |
| 389 | Idle for 45s-2min (evening) | PLAY_MUSIC suggestion | |
| 390 | Idle for 1-15min (evening) | PLAY_YOUTUBE suggestion | |
| 391 | Idle for 2-20min (weekend evening) | WATCH_MOVIE suggestion | |
| 392 | 8-9 AM first interaction | GREETING suggestion | |
| 393 | 5-6 PM daily | ROUTINE_PROMPT suggestion | |
| 394 | Morning/afternoon 1-10min idle | WEATHER_UPDATE suggestion | |
| 395 | Accept suggestion → same type comes again | 70% weight penalty (less likely to repeat) | |
| 396 | 10 PM - 8 AM (quiet hours) | No proactive suggestions | |
| 397 | More than 3 suggestions in one hour | Capped — no more suggestions | |

---

## 4.11 — Mood Tracking: Advanced

| # | Test Scenario | Expected Behavior | Result |
|---|---|---|---|
| 398 | Say 5 happy things in a row | Mood trend: "improving" or "stable (positive)" | |
| 399 | Switch from happy to stressed language | Mood shift detected (valence delta ≥0.4), callback triggered | |
| 400 | Check mood smoothing (EMA 0.7) | New mood weighted 70%, history 30% | |
| 401 | Mood below 0.3 confidence threshold | Should not update mood (too ambiguous) | |
| 402 | Emoji mood: Send "😡" alone | Detects ANGRY mood | |
| 403 | ALL CAPS: "EVERYTHING IS GOING WRONG" | Amplified frustration/anger by 1.3x | |
| 404 | Mixed signals: "I'm happy but stressed" | Weighted average of both, strongest wins | |

---

## 4.12 — Memory Panel Integration

| # | Voice Command / Action | Expected Behavior | Result |
|---|---|---|---|
| 405 | "Show memory panel" | Memory Panel UI opens | |
| 406 | Click "Skills" filter button | Shows only skill memories | |
| 407 | Click "Emotional" filter button | Shows only emotional memories (pink/magenta) | |
| 408 | Click "All" filter | Shows all memories | |
| 409 | "Remember my cat's name is Luna" → Open Memory Panel | New memory appears in panel | |
| 410 | "Forget about my cat" → Check Memory Panel | Memory removed from panel | |
| 411 | *(Trigger proactive memory.updated event)* | Panel auto-refreshes with new data | |

---

## 4.13 — Smart Memory: Edge Cases

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 412 | "Remember [very long fact — 500 characters]" | Stores and recalls correctly | |
| 413 | "What do you know about [topic never mentioned]?" | Returns "I don't have any information about..." | |
| 414 | "Remember my dog is named Max" → "Remember my dog is named Buddy" | Updates existing memory (dedup at 0.85 similarity) | |
| 415 | "Forget about [topic that doesn't exist]" | Graceful "nothing to forget" response | |
| 416 | "Remember my wife's birthday is June 20th" → "When is my wife's birthday?" | Recalls with birthday formatting | |
| 417 | "Remember I have a meeting at 3pm" → "What do I have today?" | Recalls meeting info | |

---

## 4.14 — Compound + Conditional Hybrid

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 418 | "If battery is below 30, enable battery saver and decrease brightness" | Evaluates condition → executes both actions | |
| 419 | "Open Chrome and then if volume is above 50 decrease by 20" | Opens Chrome first, then evaluates conditional | |
| 420 | "If WiFi is connected, search YouTube for music and play the first result" | Conditional → compound execution | |

---

## 4.15 — System Power: Edge Cases

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 421 | "Shutdown" → "Cancel" *(immediately)* | Shutdown initiated then cancelled | |
| 422 | "Schedule shutdown in 1 minute" → "Cancel shutdown" | Scheduled → cancelled before trigger | |
| 423 | "Restart in 0 seconds" | Immediate restart (should have safety delay?) | |
| 424 | "Schedule shutdown in 999 minutes" | Accepts large values or caps | |

---

## 4.16 — YouTube: Edge Cases

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 425 | "Play YouTube [paste URL directly]" | Detects URL and plays directly | |
| 426 | "Download in 4K" *(without ffmpeg)* | Falls back to pre-merged stream | |
| 427 | "Get transcript" *(video has no captions)* | Returns appropriate error message | |
| 428 | "Search YouTube for 'very specific rare query'" | Returns results or "no results found" | |

---

## 4.17 — Music: Edge Cases

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 429 | "Play music" *(empty library)* | Returns "no music files found in Music folder" | |
| 430 | "Next song" *(nothing playing)* | Returns "no music is playing" or similar | |
| 431 | "Pause" *(already paused)* | Handles gracefully, returns "already paused" | |
| 432 | "Resume" *(nothing was paused)* | Handles gracefully | |
| 433 | *(While music plays)* Speak to NEXA | Volume ducks (0.08), then restores after response | |
| 434 | *(Rapid commands)* "Next next next" *(button mashing)* | Handles without crash, skips tracks | |

---

## 4.18 — Volume Ducking During Music

| # | Scenario | Expected Behavior | Result |
|---|---|---|---|
| 435 | Music playing at normal (0.85) → VAD detects speech | Pre-duck to 0.15 | |
| 436 | Speech confirmed (recording) | Full duck to 0.08 | |
| 437 | Response finished | Back to listening (0.70) or normal (0.85) | |
| 438 | Wake word mode: after response | Returns to normal (0.85) | |
| 439 | Direct mode: after response | Returns to listening (0.70) | |

---

## 4.19 — Natural Response Variation

Test that NEXA doesn't always give identical responses.

| # | Voice Command (repeat 3x) | Expected Behavior | Result |
|---|---|---|---|
| 440 | "Mute" (×3) | Different response each time (from 4 variants) | |
| 441 | "Volume up" (×3) | Different response each time | |
| 442 | "Take a screenshot" (×3) | Different response each time | |
| 443 | "Open Chrome" (×3) | Different response each time (from 4 variants) | |

---

## 4.20 — Offline Mode: Comprehensive

| # | Voice Command (while offline) | Expected Behavior | Result |
|---|---|---|---|
| 444 | "Go offline" *(already offline)* | Returns "already in offline mode" | |
| 445 | "Play YouTube" | Blocked with: "Say 'go online' to enable..." | |
| 446 | "Smart search for Python" | Blocked | |
| 447 | "Scrape URL" | Blocked | |
| 448 | "Weather in London" | Blocked | |
| 449 | "5-day forecast" | Blocked | |
| 450 | "Get video transcript" | Blocked | |
| 451 | "Get trending videos" | Blocked | |
| 452 | "Set volume to 50" | WORKS — local function | |
| 453 | "Open Chrome" | WORKS — local function | |
| 454 | "Play music" | WORKS — local function | |
| 455 | "Remember my name is Ali" | WORKS — local function | |
| 456 | "Take a screenshot" | WORKS — local function | |
| 457 | "Go online" | Switches back to online mode | |
| 458 | "Play YouTube cats" | NOW WORKS (online restored) | |

---

## 4.21 — Kernel Governance: Priority Manager

Tests for the `PriorityManager` — priority levels, preemption rules, and rejection logic.

| # | Test Scenario | Expected Behavior | Result |
|---|---|---|---|
| 459 | Submit USER_COMMAND (P90) while IDLE_SUGGESTION (P20) active | USER_COMMAND can preempt — `can_preempt` returns True | |
| 460 | Submit IDLE_SUGGESTION (P20) while USER_COMMAND (P90) active | Cannot preempt — `can_preempt` returns False | |
| 461 | Submit two USER_COMMAND tasks (equal priority) | FIFO order — first submitted runs first, no preemption | |
| 462 | Submit EMERGENCY (P110) while system is locked | NOT rejected — EMERGENCY always passes through locked state | |
| 463 | Submit USER_COMMAND (P90) while system is locked | REJECTED — locked blocks everything below VOICE_INPUT (P100) | |
| 464 | Submit VOICE_INPUT (P100) while system is locked | NOT rejected — VOICE_INPUT passes through locked state | |
| 465 | Submit IDLE_SUGGESTION (P20) while another task active | REJECTED — background-class suppressed by active work | |
| 466 | Submit IDLE_SUGGESTION (P20) while media playing | REJECTED — background-class suppressed by media active | |
| 467 | Submit DOWNLOAD (P30) while task active | REJECTED — DOWNLOAD is background-class (≤40) | |
| 468 | Submit MEDIA_PLAYBACK (P60) while task active | NOT rejected — P60 is above background-class threshold | |

---

## 4.22 — Kernel Governance: Task Queue

Tests for the `TaskQueue` — task lifecycle, priority ordering, and state transitions.

| # | Test Scenario | Expected Behavior | Result |
|---|---|---|---|
| 469 | Submit task → verify status | Task has status "pending" and unique task_id | |
| 470 | Submit 3 tasks at P90, P60, P20 → call `next_task()` | Returns P90 task first (highest priority) | |
| 471 | Submit 2 tasks at same priority → call `next_task()` twice | Returns in FIFO order (earlier creation first) | |
| 472 | Activate a task → check `has_active_tasks()` | Returns True, `get_active_count()` = 1 | |
| 473 | Complete an active task → check `has_active_tasks()` | Returns False, task status = "completed" | |
| 474 | Cancel a pending task → call `next_task()` | Skips cancelled task, returns next valid pending | |
| 475 | Cancel an active task | Task removed from active set, status = "cancelled" | |
| 476 | `peek_active()` with multiple active tasks | Returns highest-priority active task | |
| 477 | `clear()` all queues | Pending, active, completed all empty | |

---

## 4.23 — Kernel Governance: Event Bus

Tests for the `EventBus` — pub/sub communication between modules.

| # | Test Scenario | Expected Behavior | Result |
|---|---|---|---|
| 478 | Subscribe handler → publish event | Handler called with correct kwargs | |
| 479 | Subscribe 3 handlers to same event → publish | All 3 handlers called in subscription order | |
| 480 | Unsubscribe a handler → publish | Unsubscribed handler NOT called, others still called | |
| 481 | Handler throws exception during publish | Exception logged, other handlers still execute (no propagation) | |
| 482 | Publish event with no subscribers | No error — silent no-op | |
| 483 | `clear()` → publish previously subscribed event | No handlers called | |

---

## 4.24 — Kernel Governance: Resource Manager (GPU)

Tests for the `ResourceManager` — VRAM allocation gating and threshold enforcement.

| # | Test Scenario | Expected Behavior | Result |
|---|---|---|---|
| 484 | `can_allocate(1000)` on fresh manager (8192MB total, 7372MB threshold) | Returns True — well within threshold | |
| 485 | Allocate 7000MB → `can_allocate(500)` | Returns False — would exceed 7372MB threshold | |
| 486 | Allocate 3000MB for task_A → release task_A → check available | Available VRAM restored to full after release | |
| 487 | `allocate(task_id, 0)` — zero VRAM request | Returns True — zero-VRAM always succeeds | |
| 488 | Allocate for task → complete task → verify release | VRAM released, `get_allocations()` empty for that task | |

---

## 4.25 — Kernel Governance: Integration (NexaKernel)

Tests for the `NexaKernel` orchestrator — end-to-end task flow and state management.

| # | Test Scenario | Expected Behavior | Result |
|---|---|---|---|
| 489 | `submit_task(USER_COMMAND)` on idle kernel | Returns task_id (not None), "task.submitted" event published | |
| 490 | `submit_task(IDLE_SUGGESTION)` while kernel locked | Returns None (rejected), "task.rejected" event published | |
| 491 | `activate_task` with GPU requirement → `complete_task` | GPU allocated on activate, released on complete | |
| 492 | `cancel_task` on active GPU task | GPU VRAM released, "gpu.released" event published | |
| 493 | `set_locked(True)` → verify `is_locked` property | Property returns True, "state.locked" event published | |
| 494 | `set_media_active(True)` → verify `is_media_active` | Property returns True, "media.started" event published | |
| 495 | `can_run_idle()` while locked | Returns False | |
| 496 | `can_run_idle()` while media active | Returns False | |
| 497 | `can_run_idle()` while task active | Returns False | |
| 498 | `can_run_idle()` on idle, unlocked, no-media kernel | Returns True | |
| 499 | `register_capability("tts", handler, ...)` → `get_capability("tts")` | Returns registered handler dict with correct defaults | |
| 500 | `shutdown()` | All queues cleared, all allocations released, event bus cleared | |

---

# Regression & Edge Case Tests

> Tests for known issues, boundary conditions, and system stability.

---

## R.1 — Input Handling Edge Cases

| # | Input | Expected Behavior | Result |
|---|---|---|---|
| 501 | *(Complete silence for 30 seconds)* | No false triggers, stays idle | |
| 502 | *(Background noise — TV, fan)* | No false triggers or gibberish commands | |
| 503 | *(Whispered command)* "What time is it?" | Still recognized (Faster-Whisper sensitivity) | |
| 504 | *(Shouted command)* "PLAY MUSIC" | Recognized without issues | |
| 505 | *(Accented English)* "Open Chrome please" | Recognized correctly | |
| 506 | *(Very fast speech)* "open chrome set volume 50 play music" | Recognized, possibly split into compound | |

---

## R.2 — Concurrent Operations

| # | Test | Expected Behavior | Result |
|---|---|---|---|
| 507 | Play music → immediately give new command | Volume ducks, command processed, music continues | |
| 508 | Start YouTube download → check download status repeatedly | Status updates correctly, no crash | |
| 509 | Open multiple apps in rapid succession | All open without conflict | |
| 510 | Take screenshot while in content mode | Blocked (content mode isolation) | |

---

## R.3 — State Persistence

| # | Test | Expected Behavior | Result |
|---|---|---|---|
| 511 | Store memory → restart NEXA → recall memory | Memory persists across restarts | |
| 512 | Set dark theme → restart → check theme | Theme setting persists | |
| 513 | Track goal → restart → get goals | Goals persist | |
| 514 | Journal entry → restart → check emotional memory | Journal persists | |
| 515 | Music shuffle ON → restart → check playback mode | Mode persists (or resets — document behavior) | |

---

## R.4 — UI Responsiveness

| # | Test | Expected Behavior | Result |
|---|---|---|---|
| 516 | Voice orb animation during listening | Orb animates when mic active | |
| 517 | Voice orb animation during thinking | Orb shows thinking state | |
| 518 | Voice orb animation during speaking | Orb shows speaking state | |
| 519 | Desktop companion (pet) idle animation | Shows idle state (8 states total) | |
| 520 | Desktop companion during listening | Shows listening animation state | |
| 521 | Desktop companion during thinking | Shows thinking animation state | |
| 522 | Desktop companion during speaking | Shows speaking animation state | |
| 523 | System tray — right click menu | All menu items functional | |
| 524 | Memory Panel — filter buttons all work | Skills, Emotional, All filters functional | |

---

## R.5 — Error Recovery

| # | Test | Expected Behavior | Result |
|---|---|---|---|
| 525 | Kill Ollama process → give command | Detects LLM error, switches to error mode gracefully | |
| 526 | Disconnect internet → "Search YouTube" | Detects offline, returns helpful message | |
| 527 | Unplug headphones during TTS playback | TTS handles gracefully (no crash) | |
| 528 | Fill disk to 99% → "Take a screenshot" | Returns storage error message | |
| 529 | Rapidly alternate between online/offline mode | Stable state transitions, no crash | |

---

## R.6 — Screen Reader & Notifications (Currently Disabled)

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 530 | "Read the screen" | Returns disabled/not available message (Vision removed Phase 24) | |
| 531 | "Describe my screen" | Returns disabled/not available message (Vision removed Phase 24) | |
| 532 | "Read notifications" | Returns "Notification reading is currently unavailable" (Vision dependency removed) | |

---

## R.7 — Keyboard Shortcuts (via Executor)

Note: `MouseController` exists internally but is NOT registered as voice commands. These test the keyboard-shortcut-based clipboard operations.

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 533 | "Select all" | Sends Ctrl+A via `select_all_text` | |
| 534 | "Copy that" | Sends Ctrl+C via `copy_selected_text` | |
| 535 | "Paste" | Sends Ctrl+V via `paste_clipboard` | |

---

## R.8 — Special Characters & Encoding

| # | Voice Command | Expected Behavior | Result |
|---|---|---|---|
| 536 | "Remember my name is José" | Stores with accent correctly | |
| 537 | "Remember 日本語テスト" | Handles Unicode gracefully | |
| 538 | "Search for C++ tutorial" | Handles special characters in search | |
| 539 | "Open the file 'report (final).docx'" | Handles parentheses in filenames | |

---

## R.9 — LLM JSON Parsing

| # | Test Scenario | Expected Behavior | Result |
|---|---|---|---|
| 540 | LLM returns valid function_call JSON | Correctly parsed and executed | |
| 541 | LLM returns conversation-only JSON | Correct — no function call, just TTS response | |
| 542 | LLM returns malformed JSON | Error handler catches, recovers gracefully | |

---

# Scoring Summary

## Level 1 — Simple (Tests 1-62)

| Category | Total | Pass | Fail | Partial |
|---|---|---|---|---|
| Quick Response Cache | 14 | | | |
| Time & Date | 2 | | | |
| System Info | 3 | | | |
| Volume Basic | 4 | | | |
| Brightness Basic | 2 | | | |
| Music Basic | 7 | | | |
| Screenshots | 3 | | | |
| Window Basic | 3 | | | |
| Theme & UI | 3 | | | |
| Lock & Security | 2 | | | |
| System Power Basic | 2 | | | |
| Conversation | 3 | | | |
| TTS Engine | 1 | | | |
| Clipboard | 5 | | | |
| Smart Memory Basic | 3 | | | |
| Emotional Basic | 2 | | | |
| Proactive Basic | 3 | | | |
| **TOTAL Level 1** | **62** | | | |

## Level 2 — Medium (Tests 63-175)

| Category | Total | Pass | Fail | Partial |
|---|---|---|---|---|
| Volume Parametric | 6 | | | |
| Brightness Parametric | 4 | | | |
| App Management | 10 | | | |
| Window Parametric | 7 | | | |
| WiFi Management | 4 | | | |
| Weather | 4 | | | |
| Web Search & Scraping | 3 | | | |
| YouTube Basic | 5 | | | |
| YouTube Downloads | 3 | | | |
| Music Specific | 13 | | | |
| Local Video | 1 | | | |
| Gaming | 3 | | | |
| Folder Navigation | 3 | | | |
| Smart Memory Store/Recall | 8 | | | |
| Power Plans | 4 | | | |
| Battery Saver | 2 | | | |
| Bluetooth | 5 | | | |
| Quick Settings | 10 | | | |
| Scheduled Power | 5 | | | |
| Emotional Parametric | 5 | | | |
| TTS Switching | 2 | | | |
| Offline Mode | 6 | | | |
| **TOTAL Level 2** | **113** | | | |

## Level 3 — High (Tests 176-313)

| Category | Total | Pass | Fail | Partial |
|---|---|---|---|---|
| Follow-Up: Music | 6 | | | |
| Follow-Up: Applications | 4 | | | |
| Follow-Up: Games | 2 | | | |
| Follow-Up: Volume/Brightness | 4 | | | |
| Follow-Up: YouTube Results | 7 | | | |
| Follow-Up: File Sharing | 3 | | | |
| Pronoun Resolution | 4 | | | |
| Implicit References | 4 | | | |
| Content Mode Workflow | 17 | | | |
| Content Mode Isolation | 5 | | | |
| Content Mode PDF | 4 | | | |
| Content Mode Formatting | 15 | | | |
| File Management | 15 | | | |
| File Sharing | 6 | | | |
| YouTube Advanced | 6 | | | |
| Music Follow-Up | 4 | | | |
| Memory Knowledge | 11 | | | |
| Memory Deduplication | 4 | | | |
| Mood Detection | 10 | | | |
| Journaling & Goals | 7 | | | |
| **TOTAL Level 3** | **138** | | | |

## Level 4 — Complex (Tests 314-500)

| Category | Total | Pass | Fail | Partial |
|---|---|---|---|---|
| Compound Commands | 6 | | | |
| Conditional Commands | 9 | | | |
| Conditional Exclusion | 5 | | | |
| Preprocessor Splitting | 5 | | | |
| Cross-System Integration | 5 | | | |
| Natural Language Variations | 14 | | | |
| AI Reasoning & Conversation | 9 | | | |
| Error Handling | 11 | | | |
| Speaker Verification | 9 | | | |
| Proactive Triggers | 11 | | | |
| Mood Advanced | 7 | | | |
| Memory Panel | 7 | | | |
| Memory Edge Cases | 6 | | | |
| Compound + Conditional | 3 | | | |
| System Power Edge Cases | 4 | | | |
| YouTube Edge Cases | 4 | | | |
| Music Edge Cases | 6 | | | |
| Volume Ducking | 5 | | | |
| Response Variation | 4 | | | |
| Offline Comprehensive | 15 | | | |
| Kernel Gov: Priority Manager | 10 | | | |
| Kernel Gov: Task Queue | 9 | | | |
| Kernel Gov: Event Bus | 6 | | | |
| Kernel Gov: Resource Manager (GPU) | 5 | | | |
| Kernel Gov: Integration (NexaKernel) | 12 | | | |
| **TOTAL Level 4** | **187** | | | |

## Regression & Edge Cases (Tests 501-542)

| Category | Total | Pass | Fail | Partial |
|---|---|---|---|---|
| Input Handling | 6 | | | |
| Concurrent Operations | 4 | | | |
| State Persistence | 5 | | | |
| UI Responsiveness | 9 | | | |
| Error Recovery | 5 | | | |
| Screen Reader (Disabled) | 3 | | | |
| Keyboard Shortcuts | 3 | | | |
| Special Characters | 4 | | | |
| LLM JSON Parsing | 3 | | | |
| **TOTAL Regression** | **42** | | | |

---

## Grand Total

| Level | Tests | Pass | Fail | Partial | Score |
|---|---|---|---|---|---|
| Level 1 — Simple | 62 | | | | /62 |
| Level 2 — Medium | 113 | | | | /113 |
| Level 3 — High | 138 | | | | /138 |
| Level 4 — Complex | 187 | | | | /187 |
| Regression & Edge | 42 | | | | /42 |
| **GRAND TOTAL** | **542** | | | | **/542** |

---

> **Last Updated:** <!-- Update this date when tests are run -->
>
> **Tested By:** <!-- Your name -->
>
> **NEXA Version:** Phase 30 (Emotional Intelligence)
>
> **Notes:** <!-- Any overall observations -->
