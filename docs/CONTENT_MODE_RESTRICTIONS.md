# Content Mode Command Restrictions

## Overview
Content Mode now enforces strict command isolation to prevent accidental interruptions while editing text. When Content Mode is active, only content-related functions are allowed.

## Implementation Details

### Location
- **File**: `core/brain.py`
- **Method**: `validate_function_call()` (line ~3299)
- **Helper**: `_is_content_mode_active()` (line ~256)

### Allowed Functions
When Content Mode is active, only these functions can be executed:

1. **`refine_text`** - All 16 refinement modes (grammar, professional, casual, etc.)
2. **`create_pdf`** - All 3 PDF formats (basic, academic, business)
3. **`enter_content_mode`** - Enter Content Mode (idempotent)
4. **`exit_content_mode`** - Exit Content Mode and return to normal operation

### Blocked Functions
All other functions are blocked with a helpful message:
- Music commands (`play_music`, `next_song`, `pause_music`, etc.)
- Application management (`open_application`, `close_application`, etc.)
- System commands (`set_volume`, `take_screenshot`, `get_current_time`, etc.)
- Game management (`launch_game`, `list_games`, etc.)
- Window operations (`minimize_window`, `maximize_window`, etc.)
- All other non-content functions

## User Experience

### Blocking Message
When a blocked command is attempted, Nexa responds:
> "I can only help with text editing while in Content Mode. Please say 'exit content mode' to use other features like music, apps, or system commands."

### Example Scenarios

#### ✅ Allowed in Content Mode
```
User: "Nexa, refine this text in professional mode"
→ Executes refine_text() successfully

User: "Create a PDF in academic format"
→ Executes create_pdf() successfully

User: "Exit content mode"
→ Closes Content Mode window, returns to normal operation
```

#### 🚫 Blocked in Content Mode
```
User: "Play next song"
→ Blocked with message: "I can only help with text editing while in Content Mode..."

User: "Open Chrome"
→ Blocked with message: "I can only help with text editing while in Content Mode..."

User: "What time is it?"
→ Blocked with message: "I can only help with text editing while in Content Mode..."
```

## Technical Implementation

### Detection Method
```python
def _is_content_mode_active(self) -> bool:
    """Check if Content Mode window is currently open and visible."""
    return (hasattr(self.executor, 'content_window') 
            and self.executor.content_window is not None
            and self.executor.content_window.isVisible())
```

### Validation Logic
```python
# VALIDATION 0: Content Mode restriction (executed first)
if self._is_content_mode_active():
    CONTENT_MODE_ALLOWED_FUNCTIONS = {
        'refine_text',
        'create_pdf',
        'enter_content_mode',
        'exit_content_mode'
    }
    
    if func_name not in CONTENT_MODE_ALLOWED_FUNCTIONS:
        logger.info(f"🚫 Content Mode active - blocking '{func_name}'")
        return (False, "I can only help with text editing while in Content Mode. "
                       "Please say 'exit content mode' to use other features...")
```

## Benefits

### 1. **Improved Focus**
- No accidental music playback while editing
- No app launches interrupting workflow
- No system commands disrupting content work

### 2. **Clear User Intent**
- Content Mode is exclusively for text refinement
- Users must explicitly exit to use other features
- Reduces confusion about what commands work where

### 3. **Better UX**
- Helpful message guides users to exit Content Mode
- Clear separation between content work and other tasks
- Prevents frustration from unexpected behavior

## Edge Cases Handled

1. **Window visibility check**: Uses `isVisible()` to ensure Content Mode is actually displayed
2. **Idempotent enter/exit**: Can call `enter_content_mode` while already in Content Mode
3. **Exit always allowed**: `exit_content_mode` is always permitted to prevent lock-in
4. **Null safety**: Checks for `hasattr` and `is not None` before accessing window

## Testing Checklist

- [ ] Enter Content Mode
- [ ] Try `refine_text` with all 16 modes → Should work
- [ ] Try `create_pdf` with all 3 formats → Should work
- [ ] Try `play_music` → Should be blocked
- [ ] Try `open_application` → Should be blocked
- [ ] Try `set_volume` → Should be blocked
- [ ] Try `exit_content_mode` → Should close window
- [ ] After exit, try `play_music` → Should work normally
- [ ] Enter Content Mode again → Should work
- [ ] Try blocked command → Should show helpful message

## Future Enhancements

Potential improvements for future versions:

1. **Whitelist expansion**: Add more content-related functions (e.g., `spell_check`, `word_count`)
2. **Configurable lists**: Allow users to customize allowed functions
3. **Mode indicators**: Visual cue in UI showing Content Mode restrictions active
4. **Quick toggle**: Keyboard shortcut to temporarily disable restrictions
5. **Analytics**: Track which blocked commands users attempt most often

## Related Files

- `core/brain.py` - Main validation logic
- `core/executor.py` - Content Mode window management
- `ui/nexa_content_window.py` - Content Mode UI
- `docs/CONTENT_MODE_FEATURES.md` - Original Content Mode documentation

## Version History

- **v1.0** (2025-01-09): Initial implementation of Content Mode restrictions
  - Added `_is_content_mode_active()` helper method
  - Modified `validate_function_call()` with VALIDATION 0
  - Defined 4 allowed functions (refine_text, create_pdf, enter/exit)
  - Implemented helpful blocking message for better UX
