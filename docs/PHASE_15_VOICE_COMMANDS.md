# Phase 15 - Voice Commands for File Sharing

## Overview
Phase 15 adds 6 file sharing functions accessible via natural voice commands. The AI (Gemma 3) understands intent and automatically routes to the correct function.

---

## Voice Command Examples

### 1. **General Share Dialog** (`share_file`)
Opens Windows Share dialog with all options.

**Voice Commands:**
- "Share this file on WhatsApp"
- "Share the PDF"
- "Send this file"
- "Share document.pdf"

**What it does:**
- Opens Windows native share UI
- Shows all available targets: WhatsApp, Nearby Share, Phone Link, Email, etc.
- User picks the target (1 click)

---

### 2. **WhatsApp Sharing** (`share_to_whatsapp`)
Specifically for WhatsApp sharing.

**Voice Commands:**
- "Share on WhatsApp"
- "Send to WhatsApp"
- "WhatsApp this PDF"
- "Share my document on WhatsApp"

**What it does:**
- Opens share dialog (WhatsApp highlighted if installed)
- User selects contact
- File sent immediately

---

### 3. **Phone Transfer (Nearby Share)** (`share_to_phone`)
Wireless PC-to-phone transfer via Bluetooth/WiFi.

**Voice Commands:**
- "Share to my phone"
- "Send to phone"
- "Transfer to mobile"
- "Share via Nearby Share"

**What it does:**
- Opens share dialog with Nearby Share option
- Detects nearby devices (within Bluetooth range)
- No internet needed
- Works within same room

**Requirements:**
- Windows 11 (or Windows 10 with Nearby Share enabled)
- Bluetooth + WiFi enabled on both devices
- Devices in proximity

---

### 4. **Phone Link Sharing** (`share_via_phone_link`)
Share to pre-paired phone via Phone Link app.

**Voice Commands:**
- "Send via Phone Link"
- "Share through Phone Link"
- "Send to my paired phone"

**What it does:**
- Opens share dialog
- Shows paired phone as target (if Phone Link configured)
- Sends to specific pre-paired device

**Requirements:**
- Phone Link app installed on Windows
- Phone paired with PC (via "Link to Windows" on Android)
- Internet connection on both devices

---

### 5. **Google Drive Upload** (`upload_to_drive`)
Upload file to Google Drive (auto-syncs to cloud).

**Voice Commands:**
- "Upload to Google Drive"
- "Save to Drive"
- "Upload this to cloud"
- "Put in Google Drive"

**What it does:**
- Copies file to `G:\My Drive\Nexa Shared\` folder
- Google Drive desktop app auto-syncs to cloud
- Creates "Nexa Shared" folder if needed
- Handles duplicate filenames (adds timestamp)

**Requirements:**
- Google Drive desktop app installed
- Drive folder synced

**Automatic Detection:**
SharingService auto-detects Google Drive at:
- `C:\Users\<username>\Google Drive`
- `C:\Users\<username>\GoogleDrive`
- `G:\My Drive`
- `G:\`

---

### 6. **Clipboard File Copy** (`copy_file_to_clipboard`)
Copy file (not path) to clipboard for manual pasting.

**Voice Commands:**
- "Copy file to clipboard"
- "Copy this file"
- "Put file on clipboard"

**What it does:**
- Copies actual file object to Windows clipboard
- User can paste (Ctrl+V) in:
  - File Explorer
  - Email (Gmail, Outlook)
  - Chat apps (Discord, Slack, Teams)
  - Any app accepting file paste

---

## Context-Aware Usage

### Content Mode Integration
When user is in Content Mode with a PDF generated:

**User:** "I just created a PDF, share it on WhatsApp"
- Nexa knows the most recent PDF path
- Opens WhatsApp share dialog automatically
- File pre-attached

---

## Technical Details

### Function Registry
All 6 functions registered in `FunctionRegistry`:
- `share_file`
- `share_to_whatsapp`
- `share_to_phone`
- `share_via_phone_link`
- `upload_to_drive`
- `copy_file_to_clipboard`

### AI Understanding
Gemma 3 (via `brain.py`) interprets:
- **Intent**: What user wants to do
- **Target**: Where to share (WhatsApp, phone, Drive)
- **File**: Which file to share (path extraction from context)

### Error Handling
All functions gracefully handle:
- File not found
- Missing Google Drive
- Share dialog failures
- Permission errors
- Timeout errors

---

## Example Workflows

### Workflow 1: Create & Share PDF
```
User: "Enter content mode"
User: [pastes text]
User: "Create PDF"
Nexa: "PDF created: essay_20250122.pdf"
User: "Share it on WhatsApp"
Nexa: *opens WhatsApp share dialog*
```

### Workflow 2: Upload Document to Drive
```
User: "Upload project.docx to Google Drive"
Nexa: "File uploaded to Google Drive: Nexa Shared/project.docx"
      "File will sync automatically"
```

### Workflow 3: Send Screenshot to Phone
```
User: "Take screenshot"
Nexa: "Screenshot saved"
User: "Send to my phone"
Nexa: *opens Nearby Share dialog*
```

---

## Implementation Status
✅ All 6 functions implemented  
✅ Integrated with CommandExecutor  
✅ Registered in FunctionRegistry  
✅ Google Drive auto-detection working  
✅ Error handling complete  
✅ Ready for production use

---

## Next Steps (Future Enhancements)
- **Phase 18**: Email integration (connects to sharing_service.py)
- **Content Mode Extensions**: Word/Markdown/HTML/PowerPoint exports
- **Smart Defaults**: Remember user's preferred share target
- **Bulk Sharing**: Share multiple files at once

---

# Phase 19 - Smart Memory Voice Commands

## Overview
Phase 19 adds Smart Memory with semantic search, knowledge storage, and memory management via voice.

---

## Voice Command Examples

### 1. **Remember Something** (`remember_this`)
Store a fact or preference that Nexa will remember.

**Voice Commands:**
- "Remember that I prefer dark theme"
- "Remember my birthday is January 15th"
- "Note that I use VS Code for coding"
- "Remember I live in Islamabad"

**What it does:**
- Stores fact in LanceDB with semantic embedding
- Can be recalled later by topic
- Higher priority for user-stated facts

---

### 2. **Forget Something** (`forget_about`)
Delete memories about a specific topic.

**Voice Commands:**
- "Forget about my old address"
- "Delete memories about my ex"
- "Forget what I said about Python"
- "Clear memories about gaming"

**What it does:**
- Searches memories semantically
- Deletes matching entries (up to 10)
- Confirms how many were deleted

---

### 3. **Recall Knowledge** (`what_do_you_know`)
Ask Nexa what it knows about a topic.

**Voice Commands:**
- "What do you know about my preferences?"
- "Do you remember my schedule?"
- "What did I say about work?"
- "Tell me what you know about games"

**What it does:**
- Semantic search across all memories
- Returns knowledge facts + conversation snippets
- Shows top 5 most relevant

---

### 4. **Memory Statistics** (`get_memory_stats`)
Check how many memories are stored.

**Voice Commands:**
- "Show memory stats"
- "How many memories do you have?"
- "Memory status"
- "Check memory count"

**What it does:**
- Shows conversation count
- Shows knowledge facts count
- Shows tracked skills count

---

## Implementation Status
✅ 4 voice commands implemented  
✅ Integrated with FunctionRegistry  
✅ Uses LanceDB for vector storage  
✅ Semantic search working  
✅ Ready for production use

