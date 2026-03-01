"""
Content Box Formatter - JavaScript Bridge for Web-based Content Editor (Phase 25)
Provides the same method signatures as the original QTextEdit-based formatter,
but delegates all formatting operations to the HTML5 editor via runJavaScript().

This bridge allows voice commands (via function_registry.py) to control the
web-based editor without any changes to the command registration layer.
"""

import logging
from typing import Optional, Callable

from Themes.theme_manager import ThemeManager

logger = logging.getLogger(__name__)


class ContentBoxFormatter:
    """
    Formatting bridge for the web-based Content Editor.
    Each method calls a JS function in the editor.html via the run_js callback.
    """

    def __init__(self, run_js: Callable, theme_manager: ThemeManager):
        """
        Initialize formatter bridge.

        Args:
            run_js: Callable that executes JavaScript in the editor WebView.
                    Signature: run_js(script: str, callback=None)
            theme_manager: ThemeManager for theme-aware styling
        """
        self._run_js = run_js
        self.theme_manager = theme_manager

        # Track current state for increase/decrease operations
        self.current_font = "Segoe UI"
        self.current_size = 12

        logger.info("ContentBoxFormatter initialized (JS bridge mode)")

    # ═══════════════════════════════════════════
    # Toolbar (handled by HTML editor natively)
    # ═══════════════════════════════════════════

    def create_formatting_toolbar(self):
        """
        No-op: The formatting toolbar is now rendered inside the HTML editor.
        Returns None since the toolbar is embedded in the web page.
        """
        return None

    def sync_toolbar_state(self):
        """No-op: Toolbar state sync is handled natively by the JS editor."""
        pass

    def apply_theme(self):
        """No-op: Theme is applied via setTheme() JS call from ContentBoxWindow."""
        pass

    # ═══════════════════════════════════════════
    # Font Controls
    # ═══════════════════════════════════════════

    def set_font_family(self, font_name: str) -> str:
        """Set font family for selection or cursor."""
        self.current_font = font_name
        self._run_js(f"execSetFont('{font_name}')")
        logger.info(f"Font changed to {font_name}")
        return f"Font changed to {font_name}"

    def set_font_size(self, size: int) -> str:
        """Set font size (8-24pt)."""
        if size < 8 or size > 24:
            return "Font size must be between 8 and 24 points"
        self.current_size = size
        self._run_js(f"execSetFontSizePt({size})")
        logger.info(f"Font size set to {size}pt")
        return f"Font size set to {size} points"

    def increase_font_size(self) -> str:
        """Increase font size by 2pt."""
        new_size = min(24, self.current_size + 2)
        return self.set_font_size(new_size)

    def decrease_font_size(self) -> str:
        """Decrease font size by 2pt."""
        new_size = max(8, self.current_size - 2)
        return self.set_font_size(new_size)

    # ═══════════════════════════════════════════
    # Text Styling
    # ═══════════════════════════════════════════

    def toggle_bold(self) -> str:
        """Toggle bold formatting."""
        self._run_js("execToggleBold()")
        logger.info("Bold toggled")
        return "Bold toggled"

    def toggle_italic(self) -> str:
        """Toggle italic formatting."""
        self._run_js("execToggleItalic()")
        logger.info("Italic toggled")
        return "Italic toggled"

    def toggle_underline(self) -> str:
        """Toggle underline formatting."""
        self._run_js("execToggleUnderline()")
        logger.info("Underline toggled")
        return "Underline toggled"

    # ═══════════════════════════════════════════
    # Alignment
    # ═══════════════════════════════════════════

    def set_alignment(self, alignment: str) -> str:
        """Set text alignment (left, center, right, justify)."""
        valid = {'left', 'center', 'right', 'justify'}
        if alignment not in valid:
            return f"Invalid alignment: {alignment}. Use left, center, right, or justify."
        self._run_js(f"execSetAlign('{alignment}')")
        logger.info(f"Text aligned to {alignment}")
        return f"Text aligned to {alignment}"

    # ═══════════════════════════════════════════
    # Lists
    # ═══════════════════════════════════════════

    def create_bullet_list(self) -> str:
        """Create or toggle bullet list."""
        self._run_js("execBulletList()")
        logger.info("Bullet list toggled")
        return "Bullet list created"

    def create_numbered_list(self) -> str:
        """Create or toggle numbered list."""
        self._run_js("execNumberedList()")
        logger.info("Numbered list toggled")
        return "Numbered list created"

    # ═══════════════════════════════════════════
    # Indentation
    # ═══════════════════════════════════════════

    def increase_indent(self) -> str:
        """Increase paragraph indent."""
        self._run_js("execIndent()")
        logger.info("Indent increased")
        return "Indent increased"

    def decrease_indent(self) -> str:
        """Decrease paragraph indent."""
        self._run_js("execOutdent()")
        logger.info("Indent decreased")
        return "Indent decreased"

    # ═══════════════════════════════════════════
    # Undo / Redo
    # ═══════════════════════════════════════════

    def undo(self) -> str:
        """Undo last change."""
        self._run_js("execUndo()")
        logger.info("Undo performed")
        return "Undone"

    def redo(self) -> str:
        """Redo last undone change."""
        self._run_js("execRedo()")
        logger.info("Redo performed")
        return "Redone"

    # ═══════════════════════════════════════════
    # Utility
    # ═══════════════════════════════════════════

    def clear_formatting(self) -> str:
        """Remove all formatting from selection."""
        self._run_js("execClearFormatting()")
        logger.info("Formatting cleared")
        return "Formatting removed"

    def set_text_color(self, color: Optional[str] = None) -> str:
        """Set text color. If no color provided, opens color picker."""
        if color:
            self._run_js(f"document.execCommand('foreColor', false, '{color}')")
            logger.info(f"Text color set to {color}")
            return f"Text color changed to {color}"
        else:
            self._run_js("openColorPicker()")
            return "Color picker opened"
