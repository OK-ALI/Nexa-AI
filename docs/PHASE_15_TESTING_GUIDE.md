# Phase 15 - Manual Testing Guide

## Quick Test (Without Running Full Nexa)

### Option 1: Test SharingService Directly
```powershell
# In PowerShell (from project root)
.venv\Scripts\Activate.ps1
python core/sharing_service.py
```

**What happens:**
- ✅ Opens Windows Share dialog automatically
- ✅ Tests all 6 methods
- ✅ Uploads test file to Google Drive
- ✅ Copies file to clipboard

**Expected Output:**
```
✅ Service initialized
📁 Google Drive: G:\My Drive
1️⃣ Testing Windows Share Dialog... ✅
2️⃣ Testing WhatsApp Share... ✅
3️⃣ Testing Nearby Share... ✅
4️⃣ Testing Phone Link... ✅
5️⃣ Testing Google Drive Upload... ✅
6️⃣ Testing Clipboard Copy... ✅
```

---

### Option 2: Test Integration (Without Voice)
```powershell
.venv\Scripts\Activate.ps1
python test_sharing_integration.py
```

**What this verifies:**
- ✅ Executor loads successfully
- ✅ Sharing service initialized
- ✅ All 6 functions registered
- ✅ No errors or conflicts

---

## Full Voice Testing (With Nexa Running)

### Prerequisites
1. Start Nexa: `python main.py`
2. Wait for: "🎤 Listening..." message
3. Create a test file first (or use existing file)

---

### Test 1: Windows Share Dialog
**Voice Command:**
```
"Share this file: C:\Users\aliwa\Desktop\test.pdf"
```

**Expected Result:**
- Windows Share dialog opens
- File is pre-attached
- Shows all targets: WhatsApp, Nearby Share, Email, etc.

**Alternative Commands:**
- "Share test.pdf"
- "Send this file"
- "Share my document"

---

### Test 2: WhatsApp Sharing
**Voice Command:**
```
"Share on WhatsApp: C:\Users\aliwa\Desktop\test.pdf"
```

**Expected Result:**
- Share dialog opens
- WhatsApp appears as option (if installed)
- Click WhatsApp → Select contact → Send

**Alternative Commands:**
- "Send to WhatsApp"
- "WhatsApp this PDF"

---

### Test 3: Nearby Share (Phone Transfer)
**Voice Command:**
```
"Share to my phone: C:\Users\aliwa\Desktop\test.pdf"
```

**Expected Result:**
- Share dialog opens
- "Nearby Share" option visible
- Phone detected (if Bluetooth/WiFi on)

**Requirements:**
- ✅ Windows 11 or Windows 10 with Nearby Share
- ✅ Bluetooth + WiFi enabled on PC
- ✅ Phone nearby with Bluetooth on

**Alternative Commands:**
- "Send to phone"
- "Transfer to mobile"

---

### Test 4: Google Drive Upload
**Voice Command:**
```
"Upload to Google Drive: C:\Users\aliwa\Desktop\test.pdf"
```

**Expected Result:**
- Nexa responds: "File uploaded to Google Drive: Nexa Shared/test.pdf"
- File appears in `G:\My Drive\Nexa Shared\`
- Google Drive syncs automatically

**Verify:**
```powershell
dir "G:\My Drive\Nexa Shared\"
```

**Alternative Commands:**
- "Save to Drive"
- "Upload to cloud"

---

### Test 5: Clipboard Copy
**Voice Command:**
```
"Copy file to clipboard: C:\Users\aliwa\Desktop\test.pdf"
```

**Expected Result:**
- Nexa responds: "File copied to clipboard"
- Open File Explorer → Press Ctrl+V → File pastes!

**Test Pasting In:**
- File Explorer (Ctrl+V)
- Gmail (Compose → Ctrl+V)
- Discord/Slack (Ctrl+V in chat)

---

## Real-World Usage Scenario

### Scenario: Student Sharing Assignment PDF

**Step 1: Create PDF**
```
You: "Enter content mode"
You: [paste essay text]
You: "Create PDF"
Nexa: "PDF created: essay_20251209.pdf"
```

**Step 2: Share on WhatsApp**
```
You: "Share it on WhatsApp"
Nexa: [Opens share dialog with WhatsApp]
You: [Select contact → Send]
```

---

### Scenario: Send Screenshot to Phone

**Step 1: Take Screenshot**
```
You: "Take screenshot"
Nexa: "Screenshot saved to: C:\Users\aliwa\Pictures\Nexa Screenshots\..."
```

**Step 2: Transfer to Phone**
```
You: "Send to my phone"
Nexa: [Opens Nearby Share]
You: [Select phone → Accept on phone]
```

---

## Quick Verification Checklist

After running Nexa, test these commands:

- [ ] **Share Dialog Works**
  - Say: "Share C:\test.txt"
  - Dialog opens: ✅ / ❌

- [ ] **WhatsApp Option Appears**
  - Say: "Share on WhatsApp: C:\test.txt"
  - WhatsApp visible: ✅ / ❌

- [ ] **Google Drive Upload Works**
  - Say: "Upload to Drive: C:\test.txt"
  - File in G:\My Drive\Nexa Shared\: ✅ / ❌

- [ ] **Clipboard Copy Works**
  - Say: "Copy file to clipboard: C:\test.txt"
  - Can paste in Explorer: ✅ / ❌

---

## Troubleshooting

### Issue: "Google Drive not detected"
**Fix:**
1. Check if Google Drive is installed
2. Verify it's syncing: Look for `G:\My Drive` or `C:\Users\<username>\Google Drive`
3. If not there, SharingService will report: "Google Drive not detected"

### Issue: "Share dialog doesn't open"
**Fix:**
1. Check Windows version (Windows 10/11)
2. Try alternative command: "Open share dialog for C:\test.txt"
3. Check logs: `data/logs/nexa_*.log`

### Issue: "WhatsApp not appearing in share options"
**Fix:**
1. Install WhatsApp from Microsoft Store
2. Restart Nexa
3. WhatsApp should now appear in share dialog

### Issue: "Nearby Share not working"
**Fix:**
1. Windows 11: Settings → System → Nearby sharing → Turn ON
2. Enable Bluetooth + WiFi
3. Phone: Enable Bluetooth
4. Try again within same room

---

## Logs Location

Check logs for detailed debugging:
```
data/logs/nexa_YYYYMMDD_HHMMSS.log
```

Search for:
- `📁 Google Drive found`
- `📤 Opening Windows Share dialog`
- `📱 Sharing to WhatsApp`
- `☁️ Uploading to Google Drive`

---

## Expected Function Count

After Phase 15:
- **Total Functions:** 94 (was 88, added 6)

Verify:
```powershell
python test_sharing_integration.py
```

Should show: `Functions registered: 94`

---

## Next Steps After Testing

Once all tests pass:
1. ✅ Phase 15 is production-ready
2. 📝 Document any issues found
3. 🚀 Start using in daily workflow!

Recommended first use case:
- Create assignment in Content Mode
- Generate PDF
- Share on WhatsApp with classmates
