"""
Nexa Content Box Window - Content editing and PDF generation interface
Voice-controlled window for text refinement and document creation in Content Mode.
"""

import logging
from typing import Optional, Callable
from pathlib import Path

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTextEdit,
    QPushButton, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, Slot, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QTextCursor

from Themes.theme_manager import ThemeManager
from ui.content_box_formatter import ContentBoxFormatter  # Phase 14

logger = logging.getLogger(__name__)


class ContentBoxWindow(QMainWindow):
    """
    Content editing window for Content Mode.
    Voice-controlled interface with theme sync.
    """
    
    # Signals
    closed = Signal()  # Emitted when window is closed
    refine_requested = Signal(str, str)  # (mode, text) - Request text refinement
    pdf_requested = Signal(str, str, str)  # (format, filename, text) - Request PDF generation
    update_text_signal = Signal(str)  # Signal to update text from worker thread (thread-safe)
    update_status_signal = Signal(str, int, bool)  # Signal to update status (message, timeout, is_error)
    content_ready = Signal(str)  # NEW: Signal when user confirms content is ready (for voice detection)
    
    def __init__(self, parent=None, theme_manager: Optional[ThemeManager] = None):
        super().__init__(parent)
        
        # Theme manager
        self.theme_manager = theme_manager or ThemeManager()
        self.theme_manager.theme_changed.connect(self._apply_theme)
        
        # Window properties
        self.setWindowTitle("Nexa • Content Mode")
        self.setGeometry(150, 150, 900, 700)
        self.setMinimumSize(700, 500)
        
        # Frameless window for modern look - INDEPENDENT, not constrained to parent
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | 
            Qt.WindowType.Window  # Make it a top-level independent window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Dragging support
        self._drag_position = None
        
        # Track if content has been modified
        self.is_modified = False
        
        # Content validation limits
        self.MIN_WORDS = 50  # Minimum words (1 small paragraph)
        self.MAX_WORDS = 500  # Maximum words allowed
        self.content_status = "empty"  # States: empty, not_ready, ready, exceeds_limit
        self._previous_status = "empty"  # Track previous status to detect transitions
        self._skip_validation = False  # Flag to skip validation for Nexa's output
        
        # Connect internal signals for thread-safe updates
        self.update_text_signal.connect(self._update_text_slot)
        self.update_status_signal.connect(self._update_status_slot)
        
        # Initialize UI
        self._init_ui()
        self._apply_theme()
        
        # Add keyboard shortcuts (Phase 14 - Issue #4)
        self._setup_shortcuts()
        
        logger.info("✨ Content Box Window initialized (900x700, voice-controlled)")
    
    def _setup_shortcuts(self):
        """Setup keyboard shortcuts for formatting."""
        from PySide6.QtGui import QShortcut, QKeySequence
        
        # Bold - Ctrl+B
        bold_shortcut = QShortcut(QKeySequence("Ctrl+B"), self)
        bold_shortcut.activated.connect(self.formatter.toggle_bold)
        
        # Italic - Ctrl+I
        italic_shortcut = QShortcut(QKeySequence("Ctrl+I"), self)
        italic_shortcut.activated.connect(self.formatter.toggle_italic)
        
        # Underline - Ctrl+U
        underline_shortcut = QShortcut(QKeySequence("Ctrl+U"), self)
        underline_shortcut.activated.connect(self.formatter.toggle_underline)
        
        # Undo - Ctrl+Z (already works by default, but explicit)
        undo_shortcut = QShortcut(QKeySequence("Ctrl+Z"), self)
        undo_shortcut.activated.connect(self.formatter.undo)
        
        # Redo - Ctrl+Y
        redo_shortcut = QShortcut(QKeySequence("Ctrl+Y"), self)
        redo_shortcut.activated.connect(self.formatter.redo)
        
        logger.info("✅ Keyboard shortcuts registered (Ctrl+B/I/U/Z/Y)")
    
    def _init_ui(self):
        """Initialize UI components."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.central_widget = central_widget  # Store for theme updates
        
        # Container widget for shadow effect
        self.container = QWidget(central_widget)
        container_layout = QVBoxLayout(self.container)
        container_layout.setSpacing(0)
        container_layout.setContentsMargins(0, 0, 0, 0)
        
        # Main layout for central widget (with margins for shadow)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(15, 15, 15, 15)  # Space for shadow
        main_layout.addWidget(self.container)
        
        # Inner layout for container content
        inner_layout = QVBoxLayout()
        inner_layout.setSpacing(0)
        inner_layout.setContentsMargins(20, 0, 20, 20)
        container_layout.addLayout(inner_layout)
        
        # Top bar with controls
        top_bar = self._create_top_bar()
        inner_layout.addWidget(top_bar)
        
        # Title section
        title_section = self._create_title_section()
        inner_layout.addWidget(title_section)
        
        inner_layout.addSpacing(15)
        
        # Toolbar with utility buttons (Copy, Clear)
        toolbar = self._create_toolbar()
        inner_layout.addLayout(toolbar)
        
        inner_layout.addSpacing(5)
        
        # Text editor (main content area)
        self.text_editor = QTextEdit()
        self.text_editor.setPlaceholderText(
            "Start typing or paste your content here...\n\n"
            "🎤 Voice Commands:\n\n"
            "  • Refine: 'Make it formal' | 'Make it shorter' | 'Fix grammar'\n"
            "           'Improve this' | 'Summarize' | 'Make it casual'\n\n"
            "  • Format: 'Make it bold' | 'Align center' | 'Bullet list'\n"
            "            'Bigger font' | 'Underline this'\n\n"
            "  • Create PDF: 'Create PDF' | 'Create PDF with bullets'\n"
            "                'Create formatted PDF'\n\n"
            "  • Exit: 'Exit content mode' | 'Close editor'"
        )
        self.text_editor.setFont(QFont("Segoe UI", 12))
        self.text_editor.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        self.text_editor.textChanged.connect(self._on_text_changed)
        
        # Initialize formatter (Phase 14) - AFTER text_editor is created
        self.formatter = ContentBoxFormatter(self.text_editor, self.theme_manager)
        
        # Formatting toolbar (Phase 14)
        formatting_toolbar = self.formatter.create_formatting_toolbar()
        inner_layout.addWidget(formatting_toolbar)
        
        inner_layout.addSpacing(5)
        
        # Add text editor to layout
        inner_layout.addWidget(self.text_editor, 1)
        
        # Status bar
        status_bar = self._create_status_bar()
        inner_layout.addWidget(status_bar)
    
    def _create_top_bar(self) -> QWidget:
        """Create top bar with window controls."""
        top_bar = QWidget()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet("background: transparent;")
        
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(0, 10, 0, 10)
        
        # Left spacer
        layout.addStretch()
        
        # Minimize button
        self.min_btn = QPushButton("—")
        self.min_btn.setFixedSize(35, 35)
        self.min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(self.min_btn)
        
        # Close button
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(35, 35)
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)
        
        return top_bar
    
    def _create_title_section(self) -> QWidget:
        """Create title section with mode indicator."""
        section = QWidget()
        section.setFixedHeight(80)
        section.setStyleSheet("background: transparent;")
        
        layout = QVBoxLayout(section)
        layout.setSpacing(5)
        layout.setContentsMargins(20, 5, 20, 5)
        
        # Title
        self.title_label = QLabel("CONTENT MODE")
        self.title_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        # Subtitle with AI quote
        self.subtitle_label = QLabel("✨ AI-Powered Content Creation")
        self.subtitle_label.setFont(QFont("Segoe UI", 11))
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle_label)
        
        return section
    
    def _create_status_bar(self) -> QWidget:
        """Create status bar with word count and content status indicator."""
        status_bar = QWidget()
        status_bar.setFixedHeight(45)
        
        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(25, 8, 25, 8)
        
        # Word count
        self.word_count_label = QLabel("Words: 0 | Characters: 0")
        self.word_count_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.word_count_label)
        
        layout.addStretch()
        
        # Content status indicator (colored with emoji)
        self.status_indicator = QLabel("⚪ No Content")
        self.status_indicator.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.status_indicator)
        
        return status_bar
    
    def _create_toolbar(self) -> QHBoxLayout:
        """Create toolbar with utility buttons (Copy, Clear, Ready)."""
        layout = QHBoxLayout()
        layout.setSpacing(10)
        
        # Copy All button
        self.copy_btn = QPushButton("📋 Copy All")
        self.copy_btn.setFixedSize(120, 36)
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_all)
        layout.addWidget(self.copy_btn)
        
        # Clear button
        self.clear_btn = QPushButton("🗑️ Clear")
        self.clear_btn.setFixedSize(100, 36)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear_text)
        layout.addWidget(self.clear_btn)
        
        layout.addStretch()
        
        return layout
    
    def _copy_all(self):
        """Copy all text to clipboard."""
        text = self.text_editor.toPlainText()
        if text:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)
            self.set_status("✓ Text copied to clipboard", 2000)
            logger.info("📋 Text copied to clipboard")
    
    def _clear_text(self):
        """Clear all text."""
        self._skip_validation = False  # Reset validation flag
        self.text_editor.clear()
        logger.info("🗑️ Text cleared")
    
    def _on_text_changed(self):
        """Handle text changes - update statistics and content status indicator."""
        text = self.text_editor.toPlainText()
        
        # Update word and character count
        words = len([w for w in text.split() if w.strip()])
        chars = len(text)
        self.word_count_label.setText(f"Words: {words} | Characters: {chars}")
        
        # Update content status indicator based on word count (skip if Nexa's output)
        if not self._skip_validation:
            self._update_content_status(words)
        else:
            # Reset flag after handling Nexa's output
            self._skip_validation = False
        
        # Mark as modified
        self.is_modified = len(text) > 0
    
    def _update_content_status(self, word_count: int):
        """
        Update content status indicator based on word count.
        Only emit content_ready signal when transitioning FROM not_ready TO ready.
        
        States:
        - ⚪ No Content (0 words)
        - 🔴 Not Ready (1-49 words - below minimum)
        - 🟢 Content Ready (50-500 words - ready for processing)
        - 🟡 Exceeds Limit (501+ words - too long)
        """
        # Determine new status
        if word_count == 0:
            new_status = "empty"
            self.status_indicator.setText("⚪ No Content")
            status_color = "#808080"  # Gray
        elif word_count < self.MIN_WORDS:
            new_status = "not_ready"
            self.status_indicator.setText(f"🔴 Not Ready ({word_count}/{self.MIN_WORDS})")
            status_color = "#FF5555"  # Red
        elif word_count <= self.MAX_WORDS:
            new_status = "ready"
            self.status_indicator.setText("✓ Ready")
            status_color = "#50C878"  # Green
        else:
            new_status = "exceeds_limit"
            self.status_indicator.setText(f"🟡 Exceeds Limit ({word_count}/{self.MAX_WORDS})")
            status_color = "#FFA500"  # Orange/Yellow
        
        # Apply color styling
        self.status_indicator.setStyleSheet(f"color: {status_color}; background: transparent; font-weight: bold;")
        
        # Only emit signal when transitioning TO ready from a non-ready state
        # This prevents emitting every time user types while content is already ready
        if new_status == "ready" and self._previous_status != "ready":
            self.content_ready.emit(text := self.text_editor.toPlainText())
            logger.debug(f"✓ Content status: READY ({word_count} words) - Signal emitted")
        elif new_status == "exceeds_limit":
            logger.debug(f"⚠ Content status: EXCEEDS LIMIT ({word_count} words)")
        
        # Update status tracking
        self.content_status = new_status
        self._previous_status = new_status
    
    def _apply_theme(self):
        """Apply theme from ThemeManager - matching Nexa main UI with shadow."""
        tm = self.theme_manager
        
        # Get theme colors
        bg_start = tm.get_color('background', 'gradient_start')
        bg_end = tm.get_color('background', 'gradient_end')
        text_primary = tm.get_color('text', 'primary')
        text_secondary = tm.get_color('text', 'secondary')
        accent = text_secondary  # Use cyan color from text.secondary (no accent key in themes)
        
        is_dark = tm.get_theme_name().lower() == "dark"  # Fixed: case-insensitive check
        
        # Central widget - transparent for shadow effect
        self.central_widget.setStyleSheet("background: transparent;")
        
        # Container with shadow and gradient background
        self.container.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {bg_start},
                    stop:1 {bg_end}
                );
                border-radius: 12px;
            }}
        """)
        
        # Apply drop shadow effect with more transparent/subtle appearance
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        from PySide6.QtGui import QColor
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)  # More blur for softer shadow
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        # More transparent shadow
        shadow.setColor(QColor(0, 0, 0, 60 if is_dark else 40))
        self.container.setGraphicsEffect(shadow)
        
        # Title labels - matching Nexa main UI exactly
        self.title_label.setStyleSheet(f"""
            color: {tm.get_color('title', 'main')};
            background: transparent;
            letter-spacing: 2px;
        """)
        
        self.subtitle_label.setStyleSheet(f"""
            color: {tm.get_color('title', 'subtitle')};
            background: transparent;
        """)
        
        # Window control buttons - matching Nexa style
        btn_base = "rgba(50, 70, 100, 100)" if is_dark else "rgba(200, 210, 220, 120)"
        btn_hover = "rgba(70, 90, 120, 140)" if is_dark else "rgba(160, 170, 180, 160)"
        
        self.min_btn.setStyleSheet(f"""
            QPushButton {{
                background: {btn_base};
                color: {text_secondary};
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {btn_hover};
            }}
        """)
        
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(180, 50, 60, 100);
                color: #FF6B6B;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: rgba(200, 60, 70, 140);
            }}
        """)
        
        # Toolbar buttons - matching Nexa style
        toolbar_btn_style = f"""
            QPushButton {{
                background: {btn_base};
                color: {text_primary};
                border: none;
                border-radius: 6px;
                font-size: 11px;
                font-weight: 600;
                padding: 8px 12px;
            }}
            QPushButton:hover {{
                background: {btn_hover};
            }}
            QPushButton:pressed {{
                background: {accent};
            }}
        """
        self.copy_btn.setStyleSheet(toolbar_btn_style)
        self.clear_btn.setStyleSheet(toolbar_btn_style)
        
        # Text editor - HIGH CONTRAST for better visibility
        if is_dark:
            # Dark mode: Dark cyan/teal background with white text
            editor_bg = "rgba(5, 35, 45, 0.95)"  # Darker cyan/teal
            editor_text = "#FFFFFF"
            placeholder_color = "rgba(0, 200, 220, 0.5)"  # Brighter cyan placeholder
            # Selection: Cyan with good opacity
            selection_bg = "rgba(0, 212, 255, 0.35)"  # 35% opacity cyan
            selection_text = "#FFFFFF"  # White text on selection
        else:
            # Light mode: White background with dark text
            editor_bg = "rgba(255, 255, 255, 0.95)"
            editor_text = "#1a1a1a"
            placeholder_color = "rgba(100, 110, 130, 0.5)"
            # Selection: Darker blue with high opacity for visibility
            selection_bg = "rgba(0, 90, 153, 0.25)"  # 25% opacity dark blue
            selection_text = "#1A1A1A"  # Keep dark text for readability
        
        self.text_editor.setStyleSheet(f"""
            QTextEdit {{
                background: {editor_bg};
                color: {editor_text};
                border: none;
                border-radius: 8px;
                padding: 20px;
                font-family: "Segoe UI";
                font-size: 12pt;
                selection-background-color: {selection_bg};
                selection-color: {selection_text};
            }}
            QTextEdit::placeholder {{
                color: {placeholder_color};
            }}
        """)
        
        # Status labels
        self.word_count_label.setStyleSheet(f"""
            color: {text_secondary};
            background: transparent;
        """)
        
        self.status_indicator.setStyleSheet(f"""
            color: {accent};
            background: transparent;
            font-weight: bold;
        """)
        
        # Apply theme to formatter (Phase 14)
        if hasattr(self, 'formatter'):
            self.formatter.apply_theme()
        
        logger.info(f"🎨 Content window theme applied: {tm.get_theme_name()}")
    
    # --- Mouse drag support ---
    def mousePressEvent(self, event):
        """Handle mouse press for window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for window dragging."""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            self.move(event.globalPosition().toPoint() - self._drag_position)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None
    
    # --- Public Methods ---
    
    def set_text(self, text: str, skip_validation: bool = False):
        """
        Set text content (thread-safe).
        Emits signal to update text in main thread.
        
        Args:
            text: Text content to set
            skip_validation: If True, skip word count validation (for Nexa's refined output)
        """
        self._skip_validation = skip_validation
        self.update_text_signal.emit(text)
    
    @Slot(str)
    def _update_text_slot(self, text: str):
        """Slot to actually update text in main thread."""
        self.text_editor.setPlainText(text)
        logger.debug(f"📝 Text set ({len(text)} chars)")
    
    def get_text(self) -> str:
        """Get current text content."""
        return self.text_editor.toPlainText()
    
    def get_html(self) -> str:
        """Get current content as HTML (preserves formatting)."""
        return self.text_editor.toHtml()
    
    def is_content_ready(self) -> bool:
        """
        Check if content is ready for processing.
        
        Returns:
            bool: True if content meets minimum requirements and doesn't exceed maximum
        """
        return self.content_status == "ready"
    
    def get_content_status(self) -> str:
        """
        Get current content status.
        
        Returns:
            str: Current status - 'empty', 'not_ready', 'ready', or 'exceeds_limit'
        """
        return self.content_status
    
    def get_word_count(self) -> int:
        """Get current word count."""
        text = self.text_editor.toPlainText()
        return len([w for w in text.split() if w.strip()])
    
    def set_status(self, message: str, duration: int = 0, error: bool = False):
        """
        Set status message (thread-safe).
        
        Args:
            message: Status message to display
            duration: Duration in milliseconds (0 = permanent)
            error: Whether this is an error message
        """
        self.update_status_signal.emit(message, duration, error)
    
    @Slot(str, int, bool)
    def _update_status_slot(self, message: str, duration: int, error: bool):
        """Slot to actually update status in main thread."""
        # Only show error messages or processing updates
        # Don't override the automatic content status indicator with "Ready" messages
        if error or ("refined" in message.lower() or "created" in message.lower()):
            color = "#FF5555" if error else "#9333EA"
            self.status_indicator.setText(message)
            self.status_indicator.setStyleSheet(f"color: {color}; font-weight: bold; background: transparent;")
            
            if duration > 0:
                # After showing the message, recalculate content status
                QTimer.singleShot(duration, lambda: self._update_content_status(self.get_word_count()))
    
    def _reset_status(self):
        """Reset status to default."""
        # Don't reset to "Ready" - let the automatic indicator handle it
        # This method is kept for backward compatibility with set_status calls
        pass
    
    def showEvent(self, event):
        """Handle window show event with fade-in animation."""
        super().showEvent(event)
        
        # Start with transparent
        self.setWindowOpacity(0.0)
        
        # Create fade-in animation
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)  # 200ms fade-in
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.start()
        
        logger.debug("✨ Content Box fade-in animation started")
    
    def closeEvent(self, event):
        """Handle window close event."""
        logger.info("🚪 Content Box Window closing")
        self.closed.emit()
        event.accept()

