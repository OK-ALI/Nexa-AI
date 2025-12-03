"""
Content Box Formatter - Rich Text Formatting for Content Mode
Handles all text formatting operations including fonts, styles, alignment, lists, and colors.
Phase 14 implementation.
"""

import logging
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QComboBox, QColorDialog,
    QToolButton, QButtonGroup
)
from PySide6.QtCore import Qt
from PySide6.QtGui import (
    QTextCursor, QTextCharFormat, QFont, QColor, QTextListFormat,
    QTextBlockFormat
)

from Themes.theme_manager import ThemeManager

logger = logging.getLogger(__name__)


class ContentBoxFormatter:
    """
    Rich text formatting manager for Content Box.
    Provides toolbar UI and formatting methods for voice/button control.
    """
    
    def __init__(self, text_editor, theme_manager: ThemeManager):
        """
        Initialize formatter.
        
        Args:
            text_editor: QTextEdit instance to format
            theme_manager: ThemeManager for theme-aware styling
        """
        self.text_editor = text_editor
        self.theme_manager = theme_manager
        
        # Current formatting state
        self.current_font = "Segoe UI"
        self.current_size = 12
        
        # Toolbar widgets (created in create_formatting_toolbar)
        self.toolbar = None
        self.font_combo = None
        self.size_combo = None
        self.bold_btn = None
        self.italic_btn = None
        self.underline_btn = None
        self.align_left_btn = None
        self.align_center_btn = None
        self.align_right_btn = None
        self.align_justify_btn = None
        
        logger.info("ContentBoxFormatter initialized")
    
    # ========== TOOLBAR CREATION ==========
    
    def create_formatting_toolbar(self) -> QWidget:
        """
        Create formatting toolbar with all controls.
        
        Returns:
            QWidget: Toolbar widget ready to add to layout
        """
        toolbar = QWidget()
        toolbar.setFixedHeight(45)
        layout = QHBoxLayout(toolbar)
        layout.setContentsMargins(0, 5, 0, 5)
        layout.setSpacing(8)
        
        # Font family dropdown
        self.font_combo = QComboBox()
        self.font_combo.setFixedWidth(140)
        self.font_combo.addItems([
            "Segoe UI", "Arial", "Times New Roman", "Courier New",
            "Georgia", "Verdana", "Comic Sans MS", "Trebuchet MS"
        ])
        self.font_combo.setCurrentText(self.current_font)
        self.font_combo.currentTextChanged.connect(self._on_font_changed)
        layout.addWidget(self.font_combo)
        
        # Font size dropdown
        self.size_combo = QComboBox()
        self.size_combo.setFixedWidth(60)
        self.size_combo.addItems([str(i) for i in range(8, 25, 2)])
        self.size_combo.setCurrentText(str(self.current_size))
        self.size_combo.currentTextChanged.connect(self._on_size_changed)
        layout.addWidget(self.size_combo)
        
        # Separator
        layout.addSpacing(5)
        
        # Style buttons (Bold, Italic, Underline)
        self.bold_btn = self._create_style_button("B", "Bold (Ctrl+B)", self._on_bold_clicked)
        self.bold_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.bold_btn)
        
        self.italic_btn = self._create_style_button("I", "Italic (Ctrl+I)", self._on_italic_clicked)
        self.italic_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal))
        self.italic_btn.font().setItalic(True)
        layout.addWidget(self.italic_btn)
        
        self.underline_btn = self._create_style_button("U", "Underline (Ctrl+U)", self._on_underline_clicked)
        self.underline_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Normal))
        layout.addWidget(self.underline_btn)
        
        # Separator
        layout.addSpacing(5)
        
        # Alignment buttons
        align_group = QButtonGroup(toolbar)
        
        self.align_left_btn = self._create_style_button("≡", "Align Left", lambda: self._on_align_clicked('left'))
        self.align_center_btn = self._create_style_button("≡", "Align Center", lambda: self._on_align_clicked('center'))
        self.align_right_btn = self._create_style_button("≡", "Align Right", lambda: self._on_align_clicked('right'))
        self.align_justify_btn = self._create_style_button("≡", "Justify", lambda: self._on_align_clicked('justify'))
        
        for btn in [self.align_left_btn, self.align_center_btn, self.align_right_btn, self.align_justify_btn]:
            align_group.addButton(btn)
            layout.addWidget(btn)
        
        # Separator
        layout.addSpacing(5)
        
        # List buttons
        bullet_btn = self._create_style_button("•", "Bullet List", self._on_bullet_clicked)
        layout.addWidget(bullet_btn)
        
        numbered_btn = self._create_style_button("1.", "Numbered List", self._on_numbered_clicked)
        layout.addWidget(numbered_btn)
        
        # Separator
        layout.addSpacing(5)
        
        # Indent buttons
        indent_in_btn = self._create_style_button("→", "Increase Indent", self._on_indent_increase)
        layout.addWidget(indent_in_btn)
        
        indent_out_btn = self._create_style_button("←", "Decrease Indent", self._on_indent_decrease)
        layout.addWidget(indent_out_btn)
        
        # Separator
        layout.addSpacing(5)
        
        # Color button
        color_btn = self._create_style_button("A", "Text Color", self._on_color_clicked)
        layout.addWidget(color_btn)
        
        # Separator
        layout.addSpacing(5)
        
        # Undo/Redo buttons
        undo_btn = self._create_style_button("↶", "Undo (Ctrl+Z)", self._on_undo_clicked)
        layout.addWidget(undo_btn)
        
        redo_btn = self._create_style_button("↷", "Redo (Ctrl+Y)", self._on_redo_clicked)
        layout.addWidget(redo_btn)
        
        # Stretch to push everything left
        layout.addStretch()
        
        self.toolbar = toolbar
        logger.info("Formatting toolbar created")
        return toolbar
    
    def _create_style_button(self, text: str, tooltip: str, callback) -> QPushButton:
        """Create a formatting button."""
        btn = QPushButton(text)
        btn.setFixedSize(32, 32)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.clicked.connect(callback)
        return btn
    
    # ========== BUTTON CALLBACKS ==========
    
    def _on_font_changed(self, font_name: str):
        """Handle font family change."""
        self.set_font_family(font_name)
    
    def _on_size_changed(self, size_str: str):
        """Handle font size change."""
        try:
            size = int(size_str)
            self.set_font_size(size)
        except ValueError:
            pass
    
    def _on_bold_clicked(self):
        """Handle bold button click."""
        self.toggle_bold()
    
    def _on_italic_clicked(self):
        """Handle italic button click."""
        self.toggle_italic()
    
    def _on_underline_clicked(self):
        """Handle underline button click."""
        self.toggle_underline()
    
    def _on_align_clicked(self, alignment: str):
        """Handle alignment button click."""
        self.set_alignment(alignment)
    
    def _on_bullet_clicked(self):
        """Handle bullet list button click."""
        self.create_bullet_list()
    
    def _on_numbered_clicked(self):
        """Handle numbered list button click."""
        self.create_numbered_list()
    
    def _on_indent_increase(self):
        """Handle indent increase button click."""
        self.increase_indent()
    
    def _on_indent_decrease(self):
        """Handle indent decrease button click."""
        self.decrease_indent()
    
    def _on_color_clicked(self):
        """Handle color button click."""
        self.set_text_color()
    
    def _on_undo_clicked(self):
        """Handle undo button click."""
        self.undo()
    
    def _on_redo_clicked(self):
        """Handle redo button click."""
        self.redo()
    
    # ========== FONT CONTROLS ==========
    
    def set_font_family(self, font_name: str) -> str:
        """
        Set font family for selection or cursor.
        
        Args:
            font_name: Font family name (e.g., "Arial", "Times New Roman")
            
        Returns:
            str: Status message
        """
        cursor = self.text_editor.textCursor()
        
        if cursor.hasSelection():
            # Apply to selection
            fmt = QTextCharFormat()
            fmt.setFontFamily(font_name)
            cursor.mergeCharFormat(fmt)
            self.current_font = font_name
            logger.info(f"Font changed to {font_name} (selection)")
            return f"Font changed to {font_name}"
        else:
            # Apply to cursor (next typing)
            self.current_font = font_name
            self.text_editor.setCurrentFont(QFont(font_name))
            logger.info(f"Font changed to {font_name} (cursor)")
            return f"Font set to {font_name}"
    
    def set_font_size(self, size: int) -> str:
        """
        Set font size (8-24pt).
        
        Args:
            size: Font size in points
            
        Returns:
            str: Status message
        """
        if size < 8 or size > 24:
            return "Font size must be between 8 and 24 points"
        
        cursor = self.text_editor.textCursor()
        
        if cursor.hasSelection():
            # Apply to selection
            fmt = QTextCharFormat()
            fmt.setFontPointSize(size)
            cursor.mergeCharFormat(fmt)
            self.current_size = size
            logger.info(f"Font size changed to {size}pt (selection)")
            return f"Font size set to {size} points"
        else:
            # Apply to cursor (next typing)
            self.current_size = size
            self.text_editor.setFontPointSize(size)
            logger.info(f"Font size changed to {size}pt (cursor)")
            return f"Font size set to {size} points"
    
    def increase_font_size(self) -> str:
        """Increase font size by 2pt."""
        new_size = min(24, self.current_size + 2)
        return self.set_font_size(new_size)
    
    def decrease_font_size(self) -> str:
        """Decrease font size by 2pt."""
        new_size = max(8, self.current_size - 2)
        return self.set_font_size(new_size)
    
    # ========== TEXT STYLING ==========
    
    def toggle_bold(self) -> str:
        """
        Toggle bold formatting.
        
        Returns:
            str: Status message
        """
        cursor = self.text_editor.textCursor()
        fmt = cursor.charFormat()
        
        # Toggle bold
        new_weight = QFont.Weight.Normal if fmt.fontWeight() == QFont.Weight.Bold else QFont.Weight.Bold
        
        if cursor.hasSelection():
            # Apply to selection
            new_fmt = QTextCharFormat()
            new_fmt.setFontWeight(new_weight)
            cursor.mergeCharFormat(new_fmt)
        else:
            # Apply to cursor (next typing)
            self.text_editor.setFontWeight(new_weight)
        
        is_bold = new_weight == QFont.Weight.Bold
        logger.info(f"Bold {'applied' if is_bold else 'removed'}")
        return "Bold applied" if is_bold else "Bold removed"
    
    def toggle_italic(self) -> str:
        """
        Toggle italic formatting.
        
        Returns:
            str: Status message
        """
        cursor = self.text_editor.textCursor()
        fmt = cursor.charFormat()
        
        # Toggle italic
        new_italic = not fmt.fontItalic()
        
        if cursor.hasSelection():
            # Apply to selection
            new_fmt = QTextCharFormat()
            new_fmt.setFontItalic(new_italic)
            cursor.mergeCharFormat(new_fmt)
        else:
            # Apply to cursor (next typing)
            self.text_editor.setFontItalic(new_italic)
        
        logger.info(f"Italic {'applied' if new_italic else 'removed'}")
        return "Italic applied" if new_italic else "Italic removed"
    
    def toggle_underline(self) -> str:
        """
        Toggle underline formatting.
        
        Returns:
            str: Status message
        """
        cursor = self.text_editor.textCursor()
        fmt = cursor.charFormat()
        
        # Toggle underline
        new_underline = not fmt.fontUnderline()
        
        if cursor.hasSelection():
            # Apply to selection
            new_fmt = QTextCharFormat()
            new_fmt.setFontUnderline(new_underline)
            cursor.mergeCharFormat(new_fmt)
        else:
            # Apply to cursor (next typing)
            self.text_editor.setFontUnderline(new_underline)
        
        logger.info(f"Underline {'applied' if new_underline else 'removed'}")
        return "Underline applied" if new_underline else "Underline removed"
    
    # ========== ALIGNMENT ==========
    
    def set_alignment(self, alignment: str) -> str:
        """
        Set text alignment.
        
        Args:
            alignment: 'left', 'center', 'right', or 'justify'
            
        Returns:
            str: Status message
        """
        alignment_map = {
            'left': Qt.AlignmentFlag.AlignLeft,
            'center': Qt.AlignmentFlag.AlignCenter,
            'right': Qt.AlignmentFlag.AlignRight,
            'justify': Qt.AlignmentFlag.AlignJustify
        }
        
        if alignment not in alignment_map:
            return f"Invalid alignment: {alignment}. Use left, center, right, or justify."
        
        self.text_editor.setAlignment(alignment_map[alignment])
        logger.info(f"Text aligned to {alignment}")
        return f"Text aligned to {alignment}"
    
    # ========== COLORS ==========
    
    def set_text_color(self, color: Optional[str] = None) -> str:
        """
        Set text color.
        
        Args:
            color: Color name or hex code (optional, opens picker if None)
            
        Returns:
            str: Status message
        """
        if color is None:
            # Open color picker
            color_dialog = QColorDialog(self.text_editor)
            if color_dialog.exec():
                selected_color = color_dialog.selectedColor()
                self.text_editor.setTextColor(selected_color)
                logger.info(f"Text color changed to {selected_color.name()}")
                return f"Text color changed"
            else:
                return "Color selection cancelled"
        else:
            # Use provided color
            qcolor = QColor(color)
            if qcolor.isValid():
                self.text_editor.setTextColor(qcolor)
                logger.info(f"Text color changed to {color}")
                return f"Text color changed to {color}"
            else:
                return f"Invalid color: {color}"
    
    # ========== LISTS ==========
    
    def create_bullet_list(self) -> str:
        """
        Create bulleted list.
        
        Returns:
            str: Status message
        """
        cursor = self.text_editor.textCursor()
        list_format = QTextListFormat()
        list_format.setStyle(QTextListFormat.Style.ListDisc)
        cursor.createList(list_format)
        logger.info("Bullet list created")
        return "Bullet list created"
    
    def create_numbered_list(self) -> str:
        """
        Create numbered list.
        
        Returns:
            str: Status message
        """
        cursor = self.text_editor.textCursor()
        list_format = QTextListFormat()
        list_format.setStyle(QTextListFormat.Style.ListDecimal)
        cursor.createList(list_format)
        logger.info("Numbered list created")
        return "Numbered list created"
    
    # ========== INDENTATION ==========
    
    def increase_indent(self) -> str:
        """
        Increase paragraph indent.
        
        Returns:
            str: Status message
        """
        cursor = self.text_editor.textCursor()
        block_format = cursor.blockFormat()
        current_indent = block_format.indent()
        block_format.setIndent(current_indent + 1)
        cursor.setBlockFormat(block_format)
        logger.info("Indent increased")
        return "Indent increased"
    
    def decrease_indent(self) -> str:
        """
        Decrease paragraph indent.
        
        Returns:
            str: Status message
        """
        cursor = self.text_editor.textCursor()
        block_format = cursor.blockFormat()
        current_indent = block_format.indent()
        if current_indent > 0:
            block_format.setIndent(current_indent - 1)
            cursor.setBlockFormat(block_format)
            logger.info("Indent decreased")
            return "Indent decreased"
        else:
            return "Already at minimum indent"
    
    # ========== UNDO/REDO ==========
    
    def undo(self) -> str:
        """
        Undo last change.
        
        Returns:
            str: Status message
        """
        if self.text_editor.document().isUndoAvailable():
            self.text_editor.undo()
            logger.info("Undo performed")
            return "Undone"
        else:
            return "Nothing to undo"
    
    def redo(self) -> str:
        """
        Redo last undone change.
        
        Returns:
            str: Status message
        """
        if self.text_editor.document().isRedoAvailable():
            self.text_editor.redo()
            logger.info("Redo performed")
            return "Redone"
        else:
            return "Nothing to redo"
    
    # ========== UTILITY ==========
    
    def clear_formatting(self) -> str:
        """
        Remove all formatting from selection.
        
        Returns:
            str: Status message
        """
        cursor = self.text_editor.textCursor()
        
        if cursor.hasSelection():
            # Get plain text
            text = cursor.selectedText()
            
            # Remove formatting by replacing with plain text
            cursor.removeSelectedText()
            cursor.insertText(text)
            
            logger.info("Formatting cleared from selection")
            return "Formatting removed"
        else:
            return "No text selected"
    
    # ========== THEME INTEGRATION ==========
    
    def apply_theme(self):
        """Apply theme colors to toolbar buttons."""
        if not self.toolbar:
            return
        
        tm = self.theme_manager
        is_dark = tm.get_theme_name().lower() == "dark"
        
        # Button styling
        btn_base = "rgba(50, 70, 100, 100)" if is_dark else "rgba(200, 210, 220, 120)"
        btn_hover = "rgba(70, 90, 120, 140)" if is_dark else "rgba(160, 170, 180, 160)"
        text_color = tm.get_color('text', 'primary')
        
        button_style = f"""
            QPushButton {{
                background: {btn_base};
                color: {text_color};
                border: none;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {btn_hover};
            }}
            QPushButton:pressed {{
                background: rgba(0, 200, 220, 0.3);
            }}
        """
        
        combo_style = f"""
            QComboBox {{
                background: {btn_base};
                color: {text_color};
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 10px;
            }}
            QComboBox:hover {{
                background: {btn_hover};
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 5px solid {text_color};
            }}
        """
        
        # Apply to all buttons
        for widget in self.toolbar.findChildren(QPushButton):
            widget.setStyleSheet(button_style)
        
        # Apply to combos
        if self.font_combo:
            self.font_combo.setStyleSheet(combo_style)
        if self.size_combo:
            self.size_combo.setStyleSheet(combo_style)
        
        logger.info(f"Formatter theme applied: {tm.get_theme_name()}")
