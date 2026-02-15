"""
Nexa Content Box Window - Web-based Content Editing (Phase 25)
Modernized editor using QWebEngineView + contentEditable for rich text editing.
Replaces the old QTextEdit-based editor with a fully themed web-based editor.

Features:
- Modern HTML5 toolbar with auto-syncing formatting state
- Full offline support (no CDN dependencies)
- Theme-aware (dark/light) via JS bridge
- Thread-safe text updates via Qt signals
- Same public API as the original for backward compatibility
"""

import json
import logging
import os
import sys
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, Slot, QPropertyAnimation, QEasingCurve, QSize, QUrl

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    from PySide6.QtGui import QFont, QColor
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    from PySide6.QtGui import QFont, QColor

from Themes.theme_manager import ThemeManager

logger = logging.getLogger(__name__)


def _get_editor_html_path() -> str:
    """Get absolute path to the content editor HTML asset."""
    if getattr(sys, 'frozen', False):
        base = sys._MEIPASS
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, "assets", "content_editor", "editor.html")


class EditorPage(QWebEnginePage):
    """
    Custom QWebEnginePage that intercepts console messages from the
    editor's JavaScript for Python-JS communication.
    """

    # Signal emitted when JS sends a NEXA message
    nexa_message = Signal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)

    def javaScriptConsoleMessage(self, level, message, line, source):
        """Intercept console.log('NEXA:...') messages from the editor JS."""
        if message.startswith('NEXA:'):
            try:
                data = json.loads(message[5:])
                self.nexa_message.emit(data)
            except (json.JSONDecodeError, Exception) as e:
                logger.debug(f"Editor JS parse error: {e}")
        elif level == QWebEnginePage.JavaScriptConsoleMessageLevel.ErrorMessageLevel:
            logger.debug(f"Editor JS error: {message}")


class ContentBoxWindow(QMainWindow):
    """
    Content editing window for Content Mode.
    Uses QWebEngineView with a custom HTML5 editor for modern rich-text editing.
    Voice-controlled interface with theme sync.
    """

    # Signals (same as original for full backward compatibility)
    closed = Signal()
    refine_requested = Signal(str, str)
    pdf_requested = Signal(str, str, str)
    update_text_signal = Signal(str)
    update_status_signal = Signal(str, int, bool)
    content_ready = Signal(str)

    def __init__(self, parent=None, theme_manager: Optional[ThemeManager] = None):
        super().__init__(parent)

        # Theme manager
        self.theme_manager = theme_manager or ThemeManager()
        self.theme_manager.theme_changed.connect(self._apply_theme)

        # Window properties
        self.setWindowTitle("Nexa \u2022 Content Mode")
        self.setGeometry(150, 150, 900, 700)
        self.setMinimumSize(700, 500)

        # Frameless independent window
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Window
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Dragging
        self._drag_position = None

        # Content state
        self.is_modified = False
        self.MIN_WORDS = 50
        self.MAX_WORDS = 500
        self.content_status = "empty"
        self._previous_status = "empty"
        self._skip_validation = False

        # Cached text/HTML from JS (for synchronous access)
        self._cached_text = ""
        self._cached_html = ""
        self._cached_words = 0
        self._page_ready = False

        # Thread-safe signal connections
        self.update_text_signal.connect(self._update_text_slot)
        self.update_status_signal.connect(self._update_status_slot)

        # Build UI
        self._init_ui()
        self._apply_theme()

        logger.info("\u2728 Content Box Window initialized (Web-based editor, 900\u00d7700)")

    def _init_ui(self):
        """Initialize UI components with QWebEngineView editor."""
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.central_widget = central_widget

        # Container for shadow effect
        self.container = QWidget(central_widget)
        container_layout = QVBoxLayout(self.container)
        container_layout.setSpacing(0)
        container_layout.setContentsMargins(0, 0, 0, 0)

        # Main layout (with margins for shadow)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.addWidget(self.container)

        # Inner layout
        inner_layout = QVBoxLayout()
        inner_layout.setSpacing(0)
        inner_layout.setContentsMargins(20, 0, 20, 20)
        container_layout.addLayout(inner_layout)

        # Top bar
        top_bar = self._create_top_bar()
        inner_layout.addWidget(top_bar)

        # Title section
        title_section = self._create_title_section()
        inner_layout.addWidget(title_section)

        inner_layout.addSpacing(10)

        # Utility toolbar (Copy, Clear)
        toolbar = self._create_toolbar()
        inner_layout.addLayout(toolbar)

        inner_layout.addSpacing(5)

        # Web-based editor (replaces QTextEdit + formatting toolbar)
        if WEBENGINE_AVAILABLE:
            self._setup_web_editor(inner_layout)
        else:
            self._setup_fallback_editor(inner_layout)

        # Status bar
        status_bar = self._create_status_bar()
        inner_layout.addWidget(status_bar)

        # Create formatter bridge (for voice command compatibility)
        from ui.content_box_formatter import ContentBoxFormatter
        self.formatter = ContentBoxFormatter(self._run_js, self.theme_manager)

    def _setup_web_editor(self, layout):
        """Set up the QWebEngineView-based editor."""
        self._web_view = QWebEngineView(self)
        self._web_view.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )

        # Custom page for JS-Python communication
        self._editor_page = EditorPage(self._web_view)
        self._editor_page.nexa_message.connect(self._on_editor_message)
        self._web_view.setPage(self._editor_page)

        # Configure settings
        settings = self._editor_page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True
        )
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)
        settings.setAttribute(
            QWebEngineSettings.WebAttribute.FocusOnNavigationEnabled, True
        )

        # Transparent background
        self._editor_page.setBackgroundColor(QColor(0, 0, 0, 0))

        # Load editor HTML
        editor_path = _get_editor_html_path()
        if os.path.exists(editor_path):
            self._web_view.setUrl(QUrl.fromLocalFile(editor_path))
            logger.info(f"\U0001f4dd Loading editor: {editor_path}")
        else:
            logger.error(f"\u274c Editor HTML not found: {editor_path}")

        # Wait for page load
        self._web_view.loadFinished.connect(self._on_page_loaded)

        layout.addWidget(self._web_view, 1)

    def _setup_fallback_editor(self, layout):
        """Fallback: plain QTextEdit if WebEngine is unavailable."""
        from PySide6.QtWidgets import QTextEdit
        logger.warning("\u26a0 QWebEngineView unavailable - falling back to QTextEdit")

        self._web_view = None
        self._editor_page = None

        self.text_editor = QTextEdit()
        self.text_editor.setPlaceholderText("Start typing your content here...")
        self.text_editor.setFont(QFont("Segoe UI", 12))
        self.text_editor.textChanged.connect(self._on_fallback_text_changed)
        layout.addWidget(self.text_editor, 1)

    # ── Top bar / title / toolbar / status ──

    def _create_top_bar(self) -> QWidget:
        """Create top bar with window controls."""
        top_bar = QWidget()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet("background: transparent;")

        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(0, 10, 0, 10)
        layout.addStretch()

        self.min_btn = QPushButton("\u2014")
        self.min_btn.setFixedSize(35, 35)
        self.min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(self.min_btn)

        self.close_btn = QPushButton("\u2715")
        self.close_btn.setFixedSize(35, 35)
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)

        return top_bar

    def _create_title_section(self) -> QWidget:
        """Create title section."""
        section = QWidget()
        section.setFixedHeight(80)
        section.setStyleSheet("background: transparent;")

        layout = QVBoxLayout(section)
        layout.setSpacing(5)
        layout.setContentsMargins(20, 5, 20, 5)

        self.title_label = QLabel("CONTENT MODE")
        self.title_label.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        self.subtitle_label = QLabel("AI-Powered Content Creation")
        self.subtitle_label.setFont(QFont("Segoe UI", 11))
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle_label)

        return section

    def _create_toolbar(self) -> QHBoxLayout:
        """Create toolbar with Copy / Clear buttons."""
        from ui.music_indicator import get_icon_manager
        icon_mgr = get_icon_manager()

        layout = QHBoxLayout()
        layout.setSpacing(10)

        self.copy_btn = QPushButton(" Copy All")
        self.copy_btn.setIcon(icon_mgr.get_icon('copy', 18))
        self.copy_btn.setIconSize(QSize(18, 18))
        self.copy_btn.setFixedSize(120, 36)
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_all)
        layout.addWidget(self.copy_btn)

        self.clear_btn = QPushButton(" Clear")
        self.clear_btn.setIcon(icon_mgr.get_icon('trash', 18))
        self.clear_btn.setIconSize(QSize(18, 18))
        self.clear_btn.setFixedSize(100, 36)
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.clicked.connect(self._clear_text)
        layout.addWidget(self.clear_btn)

        layout.addStretch()
        return layout

    def _create_status_bar(self) -> QWidget:
        """Create status bar with word count and content status."""
        status_bar = QWidget()
        status_bar.setFixedHeight(45)

        layout = QHBoxLayout(status_bar)
        layout.setContentsMargins(25, 8, 25, 8)

        self.word_count_label = QLabel("Words: 0 | Characters: 0")
        self.word_count_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.word_count_label)

        layout.addStretch()

        self.status_indicator = QLabel("\u26aa No Content")
        self.status_indicator.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        layout.addWidget(self.status_indicator)

        return status_bar

    # ═══════════════════════════════════════════
    # Web Editor Communication
    # ═══════════════════════════════════════════

    @Slot(bool)
    def _on_page_loaded(self, ok: bool):
        """Called when the editor HTML finishes loading."""
        if not ok:
            logger.error("\u274c Content editor page failed to load")
            return

        self._page_ready = True
        logger.info("\u2705 Content editor page loaded")

        # Apply initial theme after small delay for JS init
        QTimer.singleShot(100, self._sync_theme_to_js)

    def _sync_theme_to_js(self):
        """Send current theme to the JS editor."""
        theme_name = self.theme_manager.get_theme_name()
        self._run_js(f"setTheme('{theme_name}')")

    @Slot(dict)
    def _on_editor_message(self, data: dict):
        """Handle messages from the editor JS (console.log interception)."""
        event = data.get('event')

        if event == 'textChanged':
            words = data.get('words', 0)
            chars = data.get('chars', 0)

            # Update word count display
            self.word_count_label.setText(f"Words: {words} | Characters: {chars}")
            self._cached_words = words
            self.is_modified = words > 0

            # Update content status
            if not self._skip_validation:
                self._update_content_status(words)
            else:
                self._skip_validation = False

            # Refresh cached text/HTML asynchronously
            self._refresh_cache()

    def _refresh_cache(self):
        """Asynchronously update cached text and HTML from JS."""
        if not self._page_ready or not self._web_view:
            return
        self._run_js("getContent()", lambda t: setattr(self, '_cached_text', t or ""))
        self._run_js("getHTML()", lambda h: setattr(self, '_cached_html', h or ""))

    def _update_content_status(self, word_count: int):
        """Update content status indicator."""
        if word_count == 0:
            new_status = "empty"
            self.status_indicator.setText("\u26aa No Content")
            color = "#808080"
        elif word_count < self.MIN_WORDS:
            new_status = "not_ready"
            self.status_indicator.setText(f"\U0001f534 Not Ready ({word_count}/{self.MIN_WORDS})")
            color = "#FF5555"
        elif word_count <= self.MAX_WORDS:
            new_status = "ready"
            self.status_indicator.setText("\u2713 Ready")
            color = "#50C878"
        else:
            new_status = "exceeds_limit"
            self.status_indicator.setText(f"\U0001f7e1 Exceeds Limit ({word_count}/{self.MAX_WORDS})")
            color = "#FFA500"

        self.status_indicator.setStyleSheet(
            f"color: {color}; background: transparent; font-weight: bold;"
        )

        # Emit content_ready only on transition TO ready
        if new_status == "ready" and self._previous_status != "ready":
            self.content_ready.emit(self._cached_text)
            logger.debug(f"\u2713 Content status: READY ({word_count} words)")

        self.content_status = new_status
        self._previous_status = new_status

    def _run_js(self, script: str, callback=None):
        """Execute JavaScript in the web editor."""
        if self._web_view and self._page_ready:
            try:
                if callback:
                    self._web_view.page().runJavaScript(script, callback)
                else:
                    self._web_view.page().runJavaScript(script)
            except Exception as e:
                logger.debug(f"JS exec error: {e}")

    # ═══════════════════════════════════════════
    # Actions
    # ═══════════════════════════════════════════

    def _copy_all(self):
        """Copy all text to clipboard."""
        text = self.get_text()
        if text:
            from PySide6.QtWidgets import QApplication
            QApplication.clipboard().setText(text)
            self.set_status("\u2713 Text copied to clipboard", 2000)
            logger.info("\U0001f4cb Text copied to clipboard")

    def _clear_text(self):
        """Clear all text."""
        self._skip_validation = False
        if self._web_view:
            self._run_js("clearEditor()")
        elif hasattr(self, 'text_editor'):
            self.text_editor.clear()
        self._cached_text = ""
        self._cached_html = ""
        self._cached_words = 0
        logger.info("\U0001f5d1\ufe0f Text cleared")

    # ═══════════════════════════════════════════
    # Theme
    # ═══════════════════════════════════════════

    def _apply_theme(self):
        """Apply theme to Python UI elements and propagate to JS editor."""
        tm = self.theme_manager
        bg_start = tm.get_color('background', 'gradient_start')
        bg_end = tm.get_color('background', 'gradient_end')
        text_primary = tm.get_color('text', 'primary')
        text_secondary = tm.get_color('text', 'secondary')
        accent = text_secondary
        is_dark = tm.get_theme_name().lower() == "dark"

        self.central_widget.setStyleSheet("background: transparent;")

        self.container.setStyleSheet(f"""
            QWidget {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {bg_start}, stop:1 {bg_end}
                );
                border-radius: 12px;
            }}
        """)

        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 60 if is_dark else 40))
        self.container.setGraphicsEffect(shadow)

        self.title_label.setStyleSheet(f"""
            color: {tm.get_color('title', 'main')};
            background: transparent; letter-spacing: 2px;
        """)
        self.subtitle_label.setStyleSheet(f"""
            color: {tm.get_color('title', 'subtitle')};
            background: transparent;
        """)

        btn_base = "rgba(50, 70, 100, 100)" if is_dark else "rgba(200, 210, 220, 120)"
        btn_hover = "rgba(70, 90, 120, 140)" if is_dark else "rgba(160, 170, 180, 160)"

        self.min_btn.setStyleSheet(f"""
            QPushButton {{
                background: {btn_base}; color: {text_secondary};
                border: none; border-radius: 6px;
                font-size: 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background: {btn_hover}; }}
        """)
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background: rgba(180, 50, 60, 100); color: #FF6B6B;
                border: none; border-radius: 6px;
                font-size: 16px; font-weight: bold;
            }}
            QPushButton:hover {{ background: rgba(200, 60, 70, 140); }}
        """)

        toolbar_style = f"""
            QPushButton {{
                background: {btn_base}; color: {text_primary};
                border: none; border-radius: 6px;
                font-size: 11px; font-weight: 600; padding: 8px 12px;
            }}
            QPushButton:hover {{ background: {btn_hover}; }}
            QPushButton:pressed {{ background: {accent}; }}
        """
        self.copy_btn.setStyleSheet(toolbar_style)
        self.clear_btn.setStyleSheet(toolbar_style)

        self.word_count_label.setStyleSheet(
            f"color: {text_secondary}; background: transparent;"
        )
        self.status_indicator.setStyleSheet(
            f"color: {accent}; background: transparent; font-weight: bold;"
        )

        # Propagate theme to JS editor
        if self._page_ready:
            self._sync_theme_to_js()

        logger.info(f"\U0001f3a8 Content window theme applied: {tm.get_theme_name()}")

    # ── Drag support ──

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = (
                event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            )

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            self.move(event.globalPosition().toPoint() - self._drag_position)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None

    # ═══════════════════════════════════════════
    # Public API (backward compatible)
    # ═══════════════════════════════════════════

    def set_text(self, text: str, skip_validation: bool = False):
        """Set text content (thread-safe)."""
        self._skip_validation = skip_validation
        self.update_text_signal.emit(text)

    @Slot(str)
    def _update_text_slot(self, text: str):
        """Slot to update text in main thread."""
        self._cached_text = text
        if self._web_view and self._page_ready:
            escaped = json.dumps(text)
            self._run_js(f"setContent({escaped})")
        elif hasattr(self, 'text_editor'):
            self.text_editor.setPlainText(text)
        logger.debug(f"\U0001f4dd Text set ({len(text)} chars)")

    def get_text(self) -> str:
        """Get current text content (synchronous, uses cache)."""
        return self._cached_text

    def get_html(self) -> str:
        """Get current content as HTML (synchronous, uses cache)."""
        return self._cached_html

    def is_content_ready(self) -> bool:
        """Check if content meets requirements."""
        return self.content_status == "ready"

    def get_content_status(self) -> str:
        """Get current content status."""
        return self.content_status

    def get_word_count(self) -> int:
        """Get current word count."""
        return self._cached_words

    def set_status(self, message: str, duration: int = 0, error: bool = False):
        """Set status message (thread-safe)."""
        self.update_status_signal.emit(message, duration, error)

    @Slot(str, int, bool)
    def _update_status_slot(self, message: str, duration: int, error: bool):
        """Update status in main thread."""
        if error or ("refined" in message.lower() or "created" in message.lower()
                     or "copied" in message.lower() or "\u2713" in message):
            color = "#FF5555" if error else "#9333EA"
            self.status_indicator.setText(message)
            self.status_indicator.setStyleSheet(
                f"color: {color}; font-weight: bold; background: transparent;"
            )
            if duration > 0:
                QTimer.singleShot(
                    duration,
                    lambda: self._update_content_status(self._cached_words)
                )

    # ── Fallback text editor support ──

    def _on_fallback_text_changed(self):
        """Handle text changes in fallback QTextEdit mode."""
        text = self.text_editor.toPlainText()
        words = len([w for w in text.split() if w.strip()])
        self._cached_text = text
        self._cached_html = self.text_editor.toHtml()
        self._cached_words = words
        self.word_count_label.setText(f"Words: {words} | Characters: {len(text)}")
        if not self._skip_validation:
            self._update_content_status(words)
        else:
            self._skip_validation = False
        self.is_modified = len(text) > 0

    # ── Window events ──

    def showEvent(self, event):
        """Fade-in animation on show."""
        super().showEvent(event)
        self.setWindowOpacity(0.0)
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.start()

    def closeEvent(self, event):
        """Handle window close."""
        logger.info("\U0001f6aa Content Box Window closing")
        self.closed.emit()
        event.accept()
