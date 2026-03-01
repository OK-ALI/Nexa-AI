"""
Download Progress Widget
========================

A sleek download progress bar for NEXA's main window.
Shows YouTube download progress with the accent color (#00D4FF).
Appears when a download starts and hides when complete.

Features:
- Animated progress bar matching NEXA's accent color
- Download icon from other_icons/download.png
- Title, percentage, speed, ETA display
- Auto-hide animation on completion
- Theme-aware (dark/light)
"""

import logging
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QProgressBar, QGraphicsOpacityEffect
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, Slot, QPropertyAnimation, 
    QEasingCurve, QSize, Property
)
from PySide6.QtGui import QFont, QColor, QIcon

logger = logging.getLogger(__name__)


class DownloadProgressWidget(QWidget):
    """
    Download progress bar widget for NEXA main window.
    
    Shows download progress with icon, title, percentage, speed, and ETA.
    Matches the accent color of the loading circle (#00D4FF for dark theme).
    Auto-hides after download completion.
    """
    
    # Signals for thread-safe UI updates from download worker thread
    progress_updated = Signal(float, str, str, str)  # percent, speed, eta, title
    download_finished = Signal(str, str)              # title, filepath
    download_failed = Signal(str, str)                # title, error
    show_requested = Signal(str)                      # title — thread-safe show_download
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._is_visible = False
        self._auto_hide_timer = QTimer(self)
        self._auto_hide_timer.setSingleShot(True)
        self._auto_hide_timer.timeout.connect(self._hide_animated)
        
        self._setup_ui()
        self._connect_signals()
        
        # Start hidden
        self.setVisible(False)
        self.setFixedHeight(0)
        
    def _setup_ui(self):
        """Build the progress bar UI."""
        self.setObjectName("downloadProgressWidget")
        self.setStyleSheet("background: transparent;")
        
        # Main layout
        layout = QHBoxLayout(self)
        layout.setContentsMargins(40, 4, 40, 4)
        layout.setSpacing(10)
        
        # Download icon
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(20, 20)
        self._icon_label.setStyleSheet("background: transparent;")
        
        # Load download icon from icon manager
        try:
            from ui.music_indicator import get_icon_manager
            icon_mgr = get_icon_manager()
            pixmap = icon_mgr.get_pixmap('download', 20)
            if not pixmap.isNull():
                self._icon_label.setPixmap(pixmap)
        except Exception as e:
            logger.debug(f"Could not load download icon: {e}")
            self._icon_label.setText("⬇")
        
        layout.addWidget(self._icon_label)
        
        # Info section (title + progress bar)
        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(2)
        
        # Title + stats row
        stats_layout = QHBoxLayout()
        stats_layout.setContentsMargins(0, 0, 0, 0)
        
        self._title_label = QLabel("Downloading...")
        self._title_label.setFont(QFont("Segoe UI", 9))
        self._title_label.setStyleSheet("color: #AABBCC; background: transparent;")
        stats_layout.addWidget(self._title_label)
        
        stats_layout.addStretch()
        
        self._stats_label = QLabel("")
        self._stats_label.setFont(QFont("Segoe UI", 8))
        self._stats_label.setStyleSheet("color: #8899AA; background: transparent;")
        stats_layout.addWidget(self._stats_label)
        
        info_layout.addLayout(stats_layout)
        
        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setFixedHeight(6)
        self._progress_bar.setRange(0, 1000)  # Use 1000 for smooth animation
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(False)
        self._apply_progress_style(is_dark=True)
        
        info_layout.addWidget(self._progress_bar)
        layout.addLayout(info_layout, 1)
        
        # Percentage label
        self._percent_label = QLabel("0%")
        self._percent_label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        self._percent_label.setStyleSheet("color: #00D4FF; background: transparent;")
        self._percent_label.setFixedWidth(45)
        self._percent_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self._percent_label)
    
    def _connect_signals(self):
        """Connect thread-safe signals to UI update slots."""
        self.progress_updated.connect(self._on_progress_updated)
        self.download_finished.connect(self._on_download_finished)
        self.download_failed.connect(self._on_download_failed)
        self.show_requested.connect(self._on_show_requested)
    
    def _apply_progress_style(self, is_dark: bool = True):
        """Apply theme-matching style to progress bar."""
        if is_dark:
            accent = "#00D4FF"
            bg = "rgba(255, 255, 255, 0.08)"
            chunk_bg = f"""
                qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {accent},
                    stop:1 #00A8CC
                )
            """
        else:
            accent = "#0066CC"
            bg = "rgba(0, 0, 0, 0.08)"
            chunk_bg = f"""
                qlineargradient(
                    x1:0, y1:0, x2:1, y2:0,
                    stop:0 {accent},
                    stop:1 #004499
                )
            """
        
        self._progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background: {bg};
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: {chunk_bg};
                border-radius: 3px;
            }}
        """)
    
    # ==================== PUBLIC METHODS ====================
    
    def show_download(self, title: str):
        """
        Show the download progress bar with initial state.
        
        Thread-safe: if called from a background thread, the update
        is dispatched to the GUI thread via show_requested signal.
        
        Args:
            title: Video/audio title being downloaded
        """
        # Always go through the signal to ensure GUI-thread execution
        self.show_requested.emit(title)
    
    @Slot(str)
    def _on_show_requested(self, title: str):
        """Handle show_download on the GUI thread."""
        self._auto_hide_timer.stop()
        
        # Truncate long titles
        display_title = title[:50] + "..." if len(title) > 50 else title
        self._title_label.setText(f"⬇ {display_title}")
        self._stats_label.setText("")
        self._percent_label.setText("0%")
        self._percent_label.setStyleSheet("color: #00D4FF; background: transparent;")
        self._progress_bar.setValue(0)
        
        # Show with animation
        self.setVisible(True)
        self.setFixedHeight(40)
        self._is_visible = True
        
        logger.info(f"📥 Download progress bar shown: '{title}'")
    
    def update_progress(self, percent: float, speed: str = "", eta: str = "", title: str = ""):
        """
        Update download progress (thread-safe via signal).
        
        Call from any thread — uses signal internally.
        
        Args:
            percent: Download progress 0-100
            speed: Download speed string (e.g., "2.5MiB/s")
            eta: Estimated time remaining (e.g., "00:45")
            title: Video title (updates the label if non-empty)
        """
        # Emit signal for thread-safe UI update
        self.progress_updated.emit(percent, speed, eta, title)
    
    def finish_download(self, title: str, filepath: str):
        """Signal download completion (thread-safe)."""
        self.download_finished.emit(title, filepath)
    
    def fail_download(self, title: str, error: str):
        """Signal download failure (thread-safe)."""
        self.download_failed.emit(title, error)
    
    def apply_theme(self, is_dark: bool):
        """Update widget colors for current theme."""
        self._apply_progress_style(is_dark)
        
        if is_dark:
            self._title_label.setStyleSheet("color: #AABBCC; background: transparent;")
            self._stats_label.setStyleSheet("color: #8899AA; background: transparent;")
            self._percent_label.setStyleSheet("color: #00D4FF; background: transparent;")
        else:
            self._title_label.setStyleSheet("color: #555555; background: transparent;")
            self._stats_label.setStyleSheet("color: #888888; background: transparent;")
            self._percent_label.setStyleSheet("color: #0066CC; background: transparent;")
    
    # ==================== SLOTS ====================
    
    @Slot(float, str, str, str)
    def _on_progress_updated(self, percent: float, speed: str, eta: str, title: str):
        """Handle progress update on UI thread."""
        # Update title label if a real video title arrives
        if title:
            display_title = title[:50] + "..." if len(title) > 50 else title
            self._title_label.setText(f"⬇ {display_title}")
        
        # Update progress bar (0-1000 for smooth values)
        self._progress_bar.setValue(int(percent * 10))
        
        # Update percentage
        self._percent_label.setText(f"{percent:.0f}%")
        
        # Update stats
        stats_parts = []
        if speed:
            stats_parts.append(speed)
        if eta and eta != "Unknown":
            stats_parts.append(f"ETA: {eta}")
        self._stats_label.setText(" | ".join(stats_parts))
    
    @Slot(str, str)
    def _on_download_finished(self, title: str, filepath: str):
        """Handle download completion on UI thread."""
        self._title_label.setText(f"✅ Downloaded: {title[:40]}")
        self._percent_label.setText("100%")
        self._progress_bar.setValue(1000)
        self._stats_label.setText("Complete!")
        
        # Auto-hide after 5 seconds
        self._auto_hide_timer.start(5000)
        
        logger.info(f"✅ Download progress bar: complete - '{title}'")
    
    @Slot(str, str)
    def _on_download_failed(self, title: str, error: str):
        """Handle download failure on UI thread."""
        self._title_label.setText(f"❌ Failed: {title[:40]}")
        self._percent_label.setText("Error")
        self._percent_label.setStyleSheet("color: #FF4444; background: transparent;")
        self._stats_label.setText(error[:60])
        
        # Auto-hide after 8 seconds
        self._auto_hide_timer.start(8000)
        
        logger.warning(f"❌ Download progress bar: failed - '{title}': {error}")
    
    def _hide_animated(self):
        """Hide the progress bar."""
        self.setFixedHeight(0)
        self.setVisible(False)
        self._is_visible = False
