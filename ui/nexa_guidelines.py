"""
NEXA Guidelines Panel
=====================

Glassmorphic overlay showing NEXA's capabilities, voice commands,
and usage tips for first-time users.

Theme-synced with the main NEXA window.
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGraphicsOpacityEffect, QSizePolicy
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal, QTimer
from PySide6.QtGui import QFont, QColor

from Themes.theme_manager import get_theme_manager

logger = logging.getLogger(__name__)


# ── Content sections for the guidelines ──────────────────────────────

GUIDELINES_SECTIONS = [
    {
        "icon": "🎙️",
        "title": "Voice Commands",
        "items": [
            "Just speak naturally — NEXA understands conversational commands",
            "Say \"Hey NEXA\" followed by your command",
            "Examples: \"What time is it?\", \"Open Chrome\", \"Play some music\"",
            "NEXA can handle follow-up questions using context",
            "Speak clearly for best recognition accuracy",
        ],
    },
    {
        "icon": "🖥️",
        "title": "System Control",
        "items": [
            "Open & close any application by name",
            "Adjust system volume — \"Set volume to 50%\", \"Mute\"",
            "Control screen brightness — \"Brightness up\", \"Set brightness to 80%\"",
            "Window management — minimize, maximize, close windows",
            "Take screenshots — \"Take a screenshot\"",
            "Check system info — battery, CPU, RAM, GPU usage",
            "Get your PC specs — \"What are my PC specs?\"",
        ],
    },
    {
        "icon": "🎵",
        "title": "Music & Media",
        "items": [
            "Play music from your library — \"Play some music\"",
            "Control playback — play, pause, skip, previous, stop",
            "Shuffle & repeat modes available",
            "Search your music library by song, artist, or album",
            "Play YouTube videos — \"Play [song] on YouTube\"",
            "Watch local movies — NEXA scans your movie folder",
            "NEXA Vision Player (NVP) for immersive video playback",
        ],
    },
    {
        "icon": "🌐",
        "title": "Online Features",
        "items": [
            "Web search — \"Search for [topic]\"",
            "Weather info — \"What's the weather?\" (auto-detects location)",
            "Weather forecast — \"What's the forecast for the next 3 days?\"",
            "YouTube search — \"Search YouTube for [topic]\"",
            "Download YouTube videos — multiple quality options (360p–4K)",
            "Download audio (MP3) from YouTube videos",
        ],
    },
    {
        "icon": "🎮",
        "title": "Gaming",
        "items": [
            "Discover installed games from Steam, Epic Games, GOG",
            "Launch games by name — \"Launch [game name]\"",
            "List all installed games — \"What games do I have?\"",
        ],
    },
    {
        "icon": "🧠",
        "title": "Memory & Learning",
        "items": [
            "NEXA remembers things you tell it — \"Remember that I like coffee\"",
            "Recall information — \"What do you know about me?\"",
            "Learns from conversations to personalize responses",
            "Forget things — \"Forget about [topic]\"",
            "Smart Memory tracks your preferences over time",
        ],
    },
    {
        "icon": "📝",
        "title": "Content & Text",
        "items": [
            "Content Mode — focused writing environment",
            "Generate and save PDFs — \"Create a PDF about [topic]\"",
            "Refine & improve text — \"Refine this text: [your text]\"",
            "Copy & paste integration with your clipboard",
        ],
    },
    {
        "icon": "🔌",
        "title": "Connectivity",
        "items": [
            "Check WiFi status — \"Am I connected to WiFi?\"",
            "Network information & diagnostics",
        ],
    },
    {
        "icon": "⚙️",
        "title": "Settings & Customization",
        "items": [
            "Toggle themes — Dark / Light mode with smooth transition",
            "Switch TTS voice engine — Kokoro or Coqui",
            "Companion Mode — animated pet assistant on your desktop",
            "Drag & rearrange sidebar buttons to your preference",
            "Online / Offline mode toggle",
        ],
    },
    {
        "icon": "💡",
        "title": "Pro Tips",
        "items": [
            "NEXA works best with short, clear commands",
            "You can chain requests: \"Open Chrome and search for Python docs\"",
            "Use \"Content Mode\" for writing longer text pieces",
            "Check the Memory Panel to see what NEXA remembers",
            "Press F1 any time to open/close this guide",
            "Theme changes sync across all NEXA windows including NVP",
        ],
    },
]


class NexaGuidelinesPanel(QWidget):
    """
    Glassmorphic guidelines overlay for NEXA.
    Shows capabilities, voice commands, and usage tips.
    Theme-aware — syncs with the main NEXA window.
    """

    closed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()

        # Window setup
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setMinimumSize(520, 520)
        self.resize(560, 640)
        self.setWindowTitle("NEXA — Guidelines")

        self._drag_pos = None
        self._build_ui()
        self._apply_theme()

        # Connect theme signal
        try:
            self.theme_manager.theme_changed.connect(self._apply_theme)
        except Exception:
            pass

    # ── UI Construction ──────────────────────────────────────────────

    def _build_ui(self):
        """Build the glassmorphic panel layout."""
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Outer container with glass background
        self._glass = QFrame(self)
        self._glass.setObjectName("guidelinesGlass")
        glass_layout = QVBoxLayout(self._glass)
        glass_layout.setContentsMargins(0, 0, 0, 0)
        glass_layout.setSpacing(0)

        # ── Header ──
        header = QWidget()
        header.setFixedHeight(52)
        header.setObjectName("guidelinesHeader")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(20, 0, 12, 0)
        h_layout.setSpacing(8)

        # Title
        self._header_icon = QLabel("📖")
        self._header_icon.setStyleSheet("font-size: 20px; background: transparent; border: none;")
        h_layout.addWidget(self._header_icon)

        self._header_title = QLabel("NEXA Guidelines")
        self._header_title.setStyleSheet(
            "font-size: 16px; font-weight: bold; background: transparent; border: none;"
        )
        h_layout.addWidget(self._header_title)

        h_layout.addStretch()

        # Subtitle
        self._header_sub = QLabel("Everything NEXA can do for you")
        self._header_sub.setStyleSheet(
            "font-size: 11px; font-style: italic; background: transparent; border: none;"
        )
        h_layout.addWidget(self._header_sub)

        h_layout.addStretch()

        # Close button
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(30, 30)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setObjectName("guidelinesClose")
        close_btn.clicked.connect(self._close_panel)
        h_layout.addWidget(close_btn)

        glass_layout.addWidget(header)

        # ── Scroll area ──
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setObjectName("guidelinesScroll")

        scroll_content = QWidget()
        self._sections_layout = QVBoxLayout(scroll_content)
        self._sections_layout.setContentsMargins(20, 14, 20, 20)
        self._sections_layout.setSpacing(16)

        # Build all sections
        self._section_widgets = []
        for section in GUIDELINES_SECTIONS:
            section_widget = self._build_section(section)
            self._sections_layout.addWidget(section_widget)
            self._section_widgets.append(section_widget)

        self._sections_layout.addStretch()
        scroll.setWidget(scroll_content)
        glass_layout.addWidget(scroll, 1)

        root.addWidget(self._glass)

    def _build_section(self, section: dict) -> QWidget:
        """Build a single collapsible section."""
        container = QFrame()
        container.setObjectName("guidelinesSection")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 10, 14, 12)
        layout.setSpacing(6)

        # Section header
        header = QLabel(f"{section['icon']}  {section['title']}")
        header.setObjectName("guidelinesSectionTitle")
        header.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        layout.addWidget(header)

        # Items
        for item in section["items"]:
            item_lbl = QLabel(f"  •  {item}")
            item_lbl.setObjectName("guidelinesItem")
            item_lbl.setWordWrap(True)
            item_lbl.setFont(QFont("Segoe UI", 10))
            layout.addWidget(item_lbl)

        return container

    # ── Theme Application ────────────────────────────────────────────

    @staticmethod
    def _is_dark():
        return get_theme_manager().get_theme_name() == "dark"

    def _apply_theme(self):
        """Apply full theme to all widgets."""
        dark = self._is_dark()

        if dark:
            glass_bg = "rgba(10, 14, 24, 0.92)"
            glass_border = "rgba(0, 212, 255, 0.15)"
            header_bg = "rgba(8, 12, 20, 0.95)"
            header_border = "rgba(0, 212, 255, 0.12)"
            title_color = "#00d4ff"
            sub_color = "rgba(0, 212, 255, 0.5)"
            section_bg = "rgba(20, 30, 50, 0.6)"
            section_border = "rgba(0, 212, 255, 0.08)"
            section_title = "#00d4ff"
            item_color = "#c8d6e5"
            close_color = "#888"
            close_hover = "#e81123"
            scrollbar_bg = "rgba(255,255,255,0.04)"
            scrollbar_handle = "rgba(0, 212, 255, 0.25)"
        else:
            glass_bg = "rgba(235, 245, 252, 0.92)"
            glass_border = "rgba(0, 100, 180, 0.18)"
            header_bg = "rgba(228, 240, 248, 0.95)"
            header_border = "rgba(0, 100, 180, 0.15)"
            title_color = "#0077bb"
            sub_color = "rgba(0, 100, 180, 0.5)"
            section_bg = "rgba(255, 255, 255, 0.55)"
            section_border = "rgba(0, 100, 180, 0.10)"
            section_title = "#005a8c"
            item_color = "#333"
            close_color = "#666"
            close_hover = "#e81123"
            scrollbar_bg = "rgba(0,0,0,0.03)"
            scrollbar_handle = "rgba(0, 100, 180, 0.20)"

        self._glass.setStyleSheet(f"""
            QFrame#guidelinesGlass {{
                background: {glass_bg};
                border: 1px solid {glass_border};
                border-radius: 14px;
            }}
        """)

        # Header
        self.findChild(QWidget, "guidelinesHeader").setStyleSheet(f"""
            QWidget#guidelinesHeader {{
                background: {header_bg};
                border-bottom: 1px solid {header_border};
                border-top-left-radius: 14px;
                border-top-right-radius: 14px;
            }}
        """)

        self._header_title.setStyleSheet(
            f"font-size: 16px; font-weight: bold; color: {title_color}; "
            f"background: transparent; border: none;"
        )
        self._header_sub.setStyleSheet(
            f"font-size: 11px; font-style: italic; color: {sub_color}; "
            f"background: transparent; border: none;"
        )
        self._header_icon.setStyleSheet(
            "font-size: 20px; background: transparent; border: none;"
        )

        # Close button
        close_btn = self.findChild(QPushButton, "guidelinesClose")
        if close_btn:
            close_btn.setStyleSheet(f"""
                QPushButton#guidelinesClose {{
                    background: transparent;
                    color: {close_color};
                    border: none;
                    border-radius: 6px;
                    font-size: 16px;
                    font-weight: bold;
                }}
                QPushButton#guidelinesClose:hover {{
                    background: {close_hover};
                    color: white;
                }}
            """)

        # Scroll area
        scroll = self.findChild(QScrollArea, "guidelinesScroll")
        if scroll:
            scroll.setStyleSheet(f"""
                QScrollArea#guidelinesScroll {{
                    background: transparent;
                    border: none;
                }}
                QScrollArea#guidelinesScroll > QWidget > QWidget {{
                    background: transparent;
                }}
                QScrollBar:vertical {{
                    background: {scrollbar_bg};
                    width: 7px;
                    margin: 4px 1px;
                    border-radius: 3px;
                }}
                QScrollBar::handle:vertical {{
                    background: {scrollbar_handle};
                    min-height: 30px;
                    border-radius: 3px;
                }}
                QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                    height: 0px;
                }}
            """)

        # Sections
        for section_w in self._section_widgets:
            section_w.setStyleSheet(f"""
                QFrame#guidelinesSection {{
                    background: {section_bg};
                    border: 1px solid {section_border};
                    border-radius: 10px;
                }}
                QLabel#guidelinesSectionTitle {{
                    color: {section_title};
                    background: transparent;
                    border: none;
                }}
                QLabel#guidelinesItem {{
                    color: {item_color};
                    background: transparent;
                    border: none;
                    padding-left: 4px;
                }}
            """)

        logger.debug(f"🎨 Guidelines theme applied: {'dark' if dark else 'light'}")

    # ── Show / Close with animation ──────────────────────────────────

    def show_animated(self):
        """Show with fade-in animation."""
        self.show()
        self.raise_()
        self.activateWindow()

        # Center on parent or screen
        if self.parent():
            parent_geo = self.parent().geometry()
            self.move(
                parent_geo.x() + (parent_geo.width() - self.width()) // 2,
                parent_geo.y() + (parent_geo.height() - self.height()) // 2,
            )
        else:
            from PySide6.QtWidgets import QApplication
            screen = QApplication.primaryScreen().geometry()
            self.move(
                (screen.width() - self.width()) // 2,
                (screen.height() - self.height()) // 2,
            )

        # Fade in
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(0.0)
        self.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(250)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        def _cleanup():
            self.setGraphicsEffect(None)

        anim.finished.connect(_cleanup)
        self._fade_anim = anim
        anim.start()

    def _close_panel(self):
        """Close with fade-out animation."""
        effect = QGraphicsOpacityEffect(self)
        effect.setOpacity(1.0)
        self.setGraphicsEffect(effect)

        anim = QPropertyAnimation(effect, b"opacity")
        anim.setDuration(180)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)

        def _on_done():
            self.hide()
            self.setGraphicsEffect(None)
            self.closed.emit()

        anim.finished.connect(_on_done)
        self._fade_anim = anim
        anim.start()

    # ── Mouse drag for frameless window ──────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos and event.buttons() & Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    def keyPressEvent(self, event):
        """Close on Escape or F1."""
        if event.key() in (Qt.Key.Key_Escape, Qt.Key.Key_F1):
            self._close_panel()
        else:
            super().keyPressEvent(event)


# ── Singleton factory ────────────────────────────────────────────────

_guidelines_instance = None


def get_or_create_guidelines(parent=None):
    """Get or create the Guidelines panel singleton."""
    global _guidelines_instance

    if _guidelines_instance is not None:
        try:
            _guidelines_instance.isVisible()
        except RuntimeError:
            _guidelines_instance = None

    if _guidelines_instance is None:
        _guidelines_instance = NexaGuidelinesPanel(parent)

    return _guidelines_instance
