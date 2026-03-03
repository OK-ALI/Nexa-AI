"""
NEXA Vision Player (NVP)
========================

Embedded video player for NEXA AI using QWebEngineView + HTML5 video.
Plays YouTube videos downloaded via yt-dlp directly inside NEXA,
instead of opening in the browser.

Features:
- NEXA-themed UI (dark/light, glassmorphic controls)
- Download panel with quality/size selection
- Keyboard shortcuts (space, F, M, arrows)
- Auto-play on load
- Frame-less window with custom title bar
- Thread-safe: download runs in background thread

Author: Nexa AI Team
Phase: 18+ — NEXA Vision Player
"""

import logging
import os
import sys
import json
import threading
import tempfile
from pathlib import Path
from typing import Optional, Dict, Any

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSizePolicy, QApplication,
    QStackedWidget, QSlider, QPushButton, QLabel, QFileDialog, QGraphicsOpacityEffect
)
from PySide6.QtCore import Qt, QUrl, QTimer, Slot, Signal, QObject, QSize
from PySide6.QtGui import QColor, QFont, QCursor, QIcon, QPixmap

try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    MULTIMEDIA_AVAILABLE = True
except ImportError:
    MULTIMEDIA_AVAILABLE = False

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings, QWebEngineProfile
    from PySide6.QtWebChannel import QWebChannel
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False

from Themes.theme_manager import get_theme_manager

logger = logging.getLogger(__name__)


def _get_project_root() -> str:
    """Get project root directory."""
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _get_nvp_html_path() -> str:
    """Get path to NVP HTML assets."""
    return os.path.join(_get_project_root(), "assets", "nvp", "index.html")


def _nvp_icon(name: str, size: int = 24) -> QIcon:
    """
    Load an icon from project icon folders.
    
    Searches: music_player_required_icons/ then other_icons/
    Returns empty QIcon if not found.
    """
    root = _get_project_root()
    for folder in ("music_player_required_icons", "other_icons"):
        path = os.path.join(root, folder, name)
        if os.path.isfile(path):
            pixmap = QPixmap(path)
            if not pixmap.isNull():
                # Scale with smooth transform for crisp rendering
                scaled = pixmap.scaled(
                    size, size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                return QIcon(scaled)
    logger.warning(f"⚠️ NVP icon not found: {name}")
    return QIcon()


class NVPBridge(QObject):
    """
    Python<->JS bridge for NVP.
    Exposed to JavaScript as 'nvpBridge' via QWebChannel.
    """
    
    # Signals for thread-safe window operations
    minimize_signal = Signal()
    maximize_signal = Signal()
    close_signal = Signal()
    download_signal = Signal(str, bool)  # quality, audio_only
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    @Slot()
    def minimizeRequested(self):
        self.minimize_signal.emit()
    
    @Slot()
    def maximizeRequested(self):
        self.maximize_signal.emit()
    
    @Slot()
    def closeRequested(self):
        self.close_signal.emit()
    
    @Slot(str, bool)
    def downloadRequested(self, quality: str, audio_only: bool):
        self.download_signal.emit(quality, audio_only)


class NexaVisionPlayer(QMainWindow):
    """
    NEXA Vision Player — Embedded NEXA-themed video player.
    
    Two modes (same window):
    - YouTube: QWebEngineView + iframe embed (online only)
    - Local: QMediaPlayer + QVideoWidget (online + offline)
    """
    
    # Signals
    _download_progress_signal = Signal(float, str, str)
    _download_complete_signal = Signal(str)
    _download_error_signal = Signal(str)
    
    # Video file extensions for movie scanning
    VIDEO_EXTENSIONS = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.webm', '.m4v', '.ts', '.mpg', '.mpeg'}
    DEFAULT_MOVIE_PATH = r"D:\Movie"
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        if not WEBENGINE_AVAILABLE:
            logger.error("❌ QWebEngineView not available — NVP disabled")
            return
        
        self.theme_manager = get_theme_manager()
        self._video_info = {}
        self._video_file_path = None
        self._youtube_service = None
        self._http_server = None
        self._http_port = 0
        self._current_mode = 'youtube'  # 'youtube' or 'local'
        
        # Window setup — frameless with custom title bar
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setMinimumSize(720, 480)
        self.resize(960, 600)
        self.setWindowTitle("NVP — NEXA Vision Player")
        
        # Center on screen
        screen = QApplication.primaryScreen().geometry()
        self.move(
            (screen.width() - self.width()) // 2,
            (screen.height() - self.height()) // 2,
        )
        
        # Central widget
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # === Native Qt Title Bar (always visible in BOTH modes) ===
        self._title_bar = self._build_native_title_bar()
        layout.addWidget(self._title_bar)
        
        # === Stacked Widget: YouTube (0) | Local (1) ===
        self._stack = QStackedWidget(central)
        
        # --- Page 0: YouTube (QWebEngineView) ---
        self._web_view = QWebEngineView()
        self._web_view.setStyleSheet("background: #0A0F19;")
        # Apply initial theme to native widgets after build
        # (deferred to after all widgets are created)
        page = self._web_view.page()
        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.PlaybackRequiresUserGesture, False)
        
        # QWebChannel bridge
        self._bridge = NVPBridge(self)
        self._channel = QWebChannel(page)
        self._channel.registerObject("nvpBridge", self._bridge)
        page.setWebChannel(self._channel)
        self._bridge.minimize_signal.connect(self.showMinimized)
        self._bridge.maximize_signal.connect(self._toggle_maximize)
        self._bridge.close_signal.connect(self.close)
        self._bridge.download_signal.connect(self._on_download_requested)
        
        self._download_progress_signal.connect(self._update_download_progress)
        self._download_complete_signal.connect(self._on_download_complete)
        self._download_error_signal.connect(self._on_download_error)
        
        self._stack.addWidget(self._web_view)  # index 0
        
        # --- Page 1: Local Player (QMediaPlayer + QVideoWidget) ---
        self._local_container = QWidget()
        local_layout = QVBoxLayout(self._local_container)
        local_layout.setContentsMargins(0, 0, 0, 0)
        local_layout.setSpacing(0)
        
        if MULTIMEDIA_AVAILABLE:
            self._video_widget = QVideoWidget()
            self._video_widget.setStyleSheet("background: #0A0F19;")
            
            self._media_player = QMediaPlayer()
            self._audio_output = QAudioOutput()
            self._audio_output.setVolume(0.75)
            self._media_player.setAudioOutput(self._audio_output)
            self._media_player.setVideoOutput(self._video_widget)
            
            local_layout.addWidget(self._video_widget, 1)
            
            # Local controls overlay
            self._local_controls = self._build_local_controls()
            local_layout.addWidget(self._local_controls)
            
            # Connect QMediaPlayer signals
            self._media_player.positionChanged.connect(self._on_position_changed)
            self._media_player.durationChanged.connect(self._on_duration_changed)
            self._media_player.playbackStateChanged.connect(self._on_playback_state_changed)
        else:
            fallback = QLabel("Local video playback requires PySide6-Multimedia")
            fallback.setAlignment(Qt.AlignmentFlag.AlignCenter)
            fallback.setStyleSheet("color: #ff6b6b; background: #0A0F19; font-size: 14px;")
            local_layout.addWidget(fallback)
        
        self._stack.addWidget(self._local_container)  # index 1
        
        layout.addWidget(self._stack)
        
        # Load YouTube mode HTML
        html_dir = os.path.dirname(_get_nvp_html_path())
        if os.path.isdir(html_dir):
            self._start_http_server(html_dir)
            nvp_url = f"http://localhost:{self._http_port}/index.html"
            self._web_view.setUrl(QUrl(nvp_url))
            logger.info(f"✅ NVP loading: {nvp_url}")
        else:
            logger.error(f"❌ NVP assets directory not found: {html_dir}")
        
        self._web_view.loadFinished.connect(self._on_page_loaded)
        self._page_ready = False
        self._pending_video = None
        
        # Mouse drag for frameless window
        self._drag_pos = None
        
        # Connect theme
        try:
            self.theme_manager.theme_changed.connect(self._on_theme_changed)
        except Exception:
            pass
        
        # Auto-hide controls timer for local mode
        self._controls_hide_timer = QTimer(self)
        self._controls_hide_timer.setInterval(3000)
        self._controls_hide_timer.setSingleShot(True)
        self._controls_hide_timer.timeout.connect(self._hide_local_controls)
        
        # Apply initial theme
        self._apply_nvp_theme()
        
        # Core AI Kernel reference (set via set_kernel())
        self._kernel = None
        
        logger.info("✅ NEXA Vision Player initialized")
    
    def _start_http_server(self, directory: str):
        """Start a local HTTP server to serve NVP assets."""
        import http.server
        import socketserver
        import functools
        
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=directory)
        
        # Find a free port
        self._http_server = socketserver.TCPServer(("127.0.0.1", 0), handler)
        self._http_port = self._http_server.server_address[1]
        
        # Silence HTTP logs
        handler_class = self._http_server.RequestHandlerClass
        handler_class.log_message = lambda *args: None
        
        # Run in daemon thread
        server_thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
        server_thread.start()
        logger.info(f"✅ NVP HTTP server started on port {self._http_port}")
    
    # ================================================================
    # NATIVE TITLE BAR (visible in both YouTube + Local modes)
    # ================================================================
    
    def _build_native_title_bar(self) -> QWidget:
        """Build a persistent Qt title bar always visible above the video."""
        bar = QWidget()
        bar.setFixedHeight(38)
        bar.setStyleSheet("""
            QWidget {
                background: rgba(8, 12, 22, 0.97);
                border-bottom: 1px solid rgba(0, 212, 255, 0.12);
            }
            QLabel {
                color: #ccc;
                background: transparent;
                border: none;
            }
            QPushButton {
                background: transparent; border: none; color: #999;
                font-size: 14px; padding: 4px 10px; border-radius: 4px;
                min-width: 28px; min-height: 24px;
            }
            QPushButton:hover { background: rgba(255,255,255,0.08); color: #eee; }
        """)
        
        h = QHBoxLayout(bar)
        h.setContentsMargins(10, 0, 4, 0)
        h.setSpacing(2)
        
        # NVP brand text — gradient cyan→purple (matching initializing loading circle)
        self._brand_lbl = QLabel()
        self._brand_lbl.setText(
            '<span style="font-size:13px; font-weight:700; font-family:Segoe UI,sans-serif;">'
            '<span style="color:#00D4FF;">N</span>'
            '<span style="color:#6B3FCC;">V</span>'
            '<span style="color:#9333EA;">P</span>'
            '</span>'
        )
        self._brand_lbl.setStyleSheet(
            "font-size: 13px; font-weight: bold; "
            "background: transparent; border: none; padding-right: 6px;"
        )
        self._brand_lbl.setFixedWidth(36)
        h.addWidget(self._brand_lbl)
        
        # Title text (draggable area) — no separator, just the video title
        self._native_title = QLabel("NEXA Vision Player")
        self._native_title.setStyleSheet(
            "font-size: 12px; color: #aaa; font-family: 'Segoe UI', sans-serif;"
        )
        self._native_title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        h.addWidget(self._native_title, 1)
        
        # --- Aspect Ratio button (local mode only, hidden initially) ---
        self._aspect_modes = ['16:9', '4:3', 'Fill', 'Fit']
        self._aspect_idx = 0
        self._aspect_btn = QPushButton("⊞ 16:9")
        self._aspect_btn.setToolTip("Change aspect ratio")
        self._aspect_btn.setStyleSheet("""
            QPushButton {
                color: #00d4ff; font-size: 11px; padding: 3px 8px;
                border: 1px solid rgba(0,212,255,0.2); border-radius: 4px;
            }
            QPushButton:hover { background: rgba(0,212,255,0.12); }
        """)
        self._aspect_btn.clicked.connect(self._cycle_aspect_ratio)
        self._aspect_btn.hide()  # shown only in local mode
        h.addWidget(self._aspect_btn)
        
        # --- Download button ---
        self._tb_dl_btn = QPushButton()
        self._tb_dl_btn.setIcon(_nvp_icon("download.png", 20))
        self._tb_dl_btn.setIconSize(QSize(20, 20))
        self._tb_dl_btn.setToolTip("Download")
        self._tb_dl_btn.clicked.connect(self._toggle_download_panel)
        h.addWidget(self._tb_dl_btn)
        
        # Separator
        h.addSpacing(4)
        
        # --- Window controls (text-based for standard look) ---
        min_btn = QPushButton("─")
        min_btn.setToolTip("Minimize")
        min_btn.clicked.connect(self.showMinimized)
        h.addWidget(min_btn)
        
        max_btn = QPushButton("□")
        max_btn.setToolTip("Maximize")
        max_btn.clicked.connect(self._toggle_maximize)
        h.addWidget(max_btn)
        
        close_btn = QPushButton()
        close_btn.setIcon(_nvp_icon("close.png", 16))
        close_btn.setIconSize(QSize(16, 16))
        close_btn.setToolTip("Close")
        close_btn.setStyleSheet("""
            QPushButton:hover { background: #e81123; }
        """)
        close_btn.clicked.connect(self.close)
        h.addWidget(close_btn)
        
        return bar
    
    def _toggle_download_panel(self):
        """Toggle the download panel via JavaScript (YouTube mode) or ignore in local mode."""
        if self._current_mode == 'youtube' and self._page_ready:
            self._web_view.page().runJavaScript("toggleDownload()")
    
    def _update_title_text(self, title: str):
        """Update the native title bar text (no separator, just the title)."""
        display = title if len(title) < 60 else title[:57] + "..."
        self._native_title.setText(display)
        self.setWindowTitle(f"NVP {title}")
    
    def _cycle_aspect_ratio(self):
        """Cycle through aspect ratio modes for local video."""
        if not MULTIMEDIA_AVAILABLE or self._current_mode != 'local':
            return
        
        self._aspect_idx = (self._aspect_idx + 1) % len(self._aspect_modes)
        mode = self._aspect_modes[self._aspect_idx]
        self._aspect_btn.setText(f"⊞ {mode}")
        
        vw = self._video_widget
        if mode == '16:9':
            vw.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        elif mode == '4:3':
            vw.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatio)
        elif mode == 'Fill':
            vw.setAspectRatioMode(Qt.AspectRatioMode.KeepAspectRatioByExpanding)
        elif mode == 'Fit':
            vw.setAspectRatioMode(Qt.AspectRatioMode.IgnoreAspectRatio)
        
        logger.info(f"⊞ Aspect ratio: {mode}")
    
    # ================================================================
    # LOCAL VIDEO PLAYER — QMediaPlayer controls
    # ================================================================
    
    def _build_local_controls(self) -> QWidget:
        """Build glassmorphic controls bar for local video playback."""
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet("""
            QWidget { background: rgba(10, 15, 25, 0.92); border-top: 1px solid rgba(0, 212, 255, 0.15); }
            QPushButton {
                background: transparent; border: none; color: #e0e0e0;
                font-size: 18px; padding: 6px 12px; border-radius: 6px;
            }
            QPushButton:hover { background: rgba(0, 212, 255, 0.15); color: #00d4ff; }
            QLabel { color: #888; font-size: 12px; font-family: Consolas, monospace; }
            QSlider::groove:horizontal {
                height: 4px; background: rgba(255,255,255,0.08); border-radius: 2px;
            }
            QSlider::handle:horizontal {
                width: 14px; height: 14px; margin: -5px 0;
                background: #00d4ff; border-radius: 7px;
            }
            QSlider::sub-page:horizontal { background: #00d4ff; border-radius: 2px; }
        """)
        
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 0, 12, 0)
        h.setSpacing(10)
        
        # Cache icons for play/pause toggle
        self._play_icon = _nvp_icon("play_button.png", 24)
        self._pause_icon = _nvp_icon("pause-button.png", 24)
        self._vol_icon = _nvp_icon("volume.png", 22)
        self._mute_icon = _nvp_icon("mute.png", 22)
        self._fs_icon = _nvp_icon("capture.png", 22)
        
        # Play/pause
        self._local_play_btn = QPushButton()
        self._local_play_btn.setIcon(self._play_icon)
        self._local_play_btn.setIconSize(QSize(24, 24))
        self._local_play_btn.setFixedSize(40, 40)
        self._local_play_btn.clicked.connect(self._toggle_local_playback)
        h.addWidget(self._local_play_btn)
        
        # Current time
        self._local_time_label = QLabel("0:00")
        h.addWidget(self._local_time_label)
        
        # Seek slider
        self._local_seek = QSlider(Qt.Orientation.Horizontal)
        self._local_seek.setRange(0, 0)
        self._local_seek.sliderMoved.connect(self._on_seek_moved)
        self._local_seek.sliderPressed.connect(lambda: self._media_player.pause() if hasattr(self, '_media_player') else None)
        self._local_seek.sliderReleased.connect(self._on_seek_released)
        h.addWidget(self._local_seek, 1)
        
        # Duration
        self._local_duration_label = QLabel("0:00")
        h.addWidget(self._local_duration_label)
        
        # Volume icon + slider
        vol_btn = QPushButton()
        vol_btn.setIcon(self._vol_icon)
        vol_btn.setIconSize(QSize(22, 22))
        vol_btn.setFixedSize(36, 36)
        vol_btn.clicked.connect(self._toggle_local_mute)
        h.addWidget(vol_btn)
        self._local_vol_btn = vol_btn
        
        self._local_volume = QSlider(Qt.Orientation.Horizontal)
        self._local_volume.setRange(0, 100)
        self._local_volume.setValue(75)
        self._local_volume.setFixedWidth(80)
        self._local_volume.valueChanged.connect(self._on_volume_changed)
        h.addWidget(self._local_volume)
        
        # Fullscreen
        fs_btn = QPushButton()
        fs_btn.setIcon(self._fs_icon)
        fs_btn.setIconSize(QSize(22, 22))
        fs_btn.setFixedSize(36, 36)
        fs_btn.clicked.connect(self._toggle_maximize)
        h.addWidget(fs_btn)
        
        return bar
    
    def play_local_file(self, file_path: str, title: str = ""):
        """Play a local video file using QMediaPlayer."""
        if not MULTIMEDIA_AVAILABLE:
            logger.error("❌ PySide6-Multimedia not available for local playback")
            return
        
        self._current_mode = 'local'
        self._stack.setCurrentIndex(1)  # switch to local player
        self._video_file_path = file_path
        
        if not title:
            title = Path(file_path).stem.replace('.', ' ').replace('_', ' ')
        
        # Native title bar — show title, aspect ratio, hide download
        self._update_title_text(title)
        self._aspect_btn.show()
        self._tb_dl_btn.hide()  # no download for local files
        
        self._video_info = {
            'title': title,
            'file_path': file_path,
        }
        
        # Load and play
        self._media_player.setSource(QUrl.fromLocalFile(file_path))
        self._media_player.play()
        self._local_controls.show()
        
        self.show()
        self.raise_()
        self.activateWindow()
        
        logger.info(f"▶ NVP local: {title} ({file_path})")
    
        # Notify kernel: media is now active
        if self._kernel:
            self._kernel.set_media_active(True)
    
    def _toggle_local_playback(self):
        if not MULTIMEDIA_AVAILABLE:
            return
        if self._media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._media_player.pause()
        else:
            self._media_player.play()
    
    def _toggle_local_mute(self):
        if not MULTIMEDIA_AVAILABLE:
            return
        muted = self._audio_output.isMuted()
        self._audio_output.setMuted(not muted)
        self._local_vol_btn.setIcon(self._mute_icon if not muted else self._vol_icon)
    
    @Slot(int)
    def _on_position_changed(self, pos_ms):
        if not self._local_seek.isSliderDown():
            self._local_seek.setValue(pos_ms)
        self._local_time_label.setText(self._format_ms(pos_ms))
    
    @Slot(int)
    def _on_duration_changed(self, dur_ms):
        self._local_seek.setRange(0, dur_ms)
        self._local_duration_label.setText(self._format_ms(dur_ms))
    
    @Slot(QMediaPlayer.PlaybackState)
    def _on_playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._local_play_btn.setIcon(self._pause_icon)
        else:
            self._local_play_btn.setIcon(self._play_icon)
    
    def _on_seek_moved(self, pos):
        self._media_player.setPosition(pos)
    
    def _on_seek_released(self):
        self._media_player.setPosition(self._local_seek.value())
        self._media_player.play()
    
    def _on_volume_changed(self, value):
        if MULTIMEDIA_AVAILABLE:
            self._audio_output.setVolume(value / 100.0)
    
    def _hide_local_controls(self):
        if self._current_mode == 'local' and hasattr(self, '_local_controls'):
            self._local_controls.hide()
    
    def _show_local_controls(self):
        if self._current_mode == 'local' and hasattr(self, '_local_controls'):
            self._local_controls.show()
            self._controls_hide_timer.start()
    
    @staticmethod
    def _format_ms(ms: int) -> str:
        """Format milliseconds to H:MM:SS or M:SS."""
        total_secs = ms // 1000
        h = total_secs // 3600
        m = (total_secs % 3600) // 60
        s = total_secs % 60
        if h > 0:
            return f"{h}:{m:02d}:{s:02d}"
        return f"{m}:{s:02d}"
    
    def mouseMoveEvent(self, event):
        """Show controls on mouse move, auto-hide after 3s."""
        if self._current_mode == 'local':
            self._show_local_controls()
        if self._drag_pos and event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
    
    # ================================================================
    # MOVIE LIBRARY SCANNER
    # ================================================================
    
    @classmethod
    def scan_movie_library(cls, base_path: str = None) -> list:
        """
        Scan movie folder for video files.
        
        Walks D:\Movie (or custom path) -> subfolders -> finds video files.
        Returns list of {title, path, size_mb}.
        """
        base = base_path or cls.DEFAULT_MOVIE_PATH
        movies = []
        
        if not os.path.isdir(base):
            logger.warning(f"Movie library path not found: {base}")
            return movies
        
        for root, dirs, files in os.walk(base):
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in cls.VIDEO_EXTENSIONS:
                    full_path = os.path.join(root, f)
                    try:
                        size_mb = os.path.getsize(full_path) / (1024 * 1024)
                        # Use parent folder name as title if file is in subfolder
                        rel = os.path.relpath(root, base)
                        title = rel if rel != '.' else os.path.splitext(f)[0]
                        movies.append({
                            'title': title.replace('.', ' ').replace('_', ' '),
                            'path': full_path,
                            'filename': f,
                            'size_mb': round(size_mb, 1),
                        })
                    except Exception:
                        pass
        
        logger.info(f"🎬 Found {len(movies)} movies in {base}")
        return movies
    
    @classmethod
    def find_movie(cls, query: str, base_path: str = None) -> Optional[str]:
        """
        Find a movie by fuzzy name match.
        Returns file path or None.
        """
        movies = cls.scan_movie_library(base_path)
        if not movies:
            return None
        
        query_lower = query.lower().strip()
        
        # Exact title match
        for m in movies:
            if query_lower == m['title'].lower():
                return m['path']
        
        # Substring match
        for m in movies:
            if query_lower in m['title'].lower() or query_lower in m['filename'].lower():
                return m['path']
        
        # Word match — any word from query in title
        query_words = query_lower.split()
        best_match = None
        best_score = 0
        for m in movies:
            title_lower = m['title'].lower() + ' ' + m['filename'].lower()
            score = sum(1 for w in query_words if w in title_lower)
            if score > best_score:
                best_score = score
                best_match = m['path']
        
        return best_match
    
    @Slot(bool)
    def _on_page_loaded(self, ok: bool):
        if not ok:
            logger.error("❌ NVP page failed to load")
            return
        
        # Ignore about:blank loads (fired after closeEvent navigates away)
        current_url = self._web_view.url().toString()
        if 'about:blank' in current_url:
            logger.debug("NVP: Ignoring about:blank load — not marking page ready")
            return
        
        self._page_ready = True
        
        # Inject QWebChannel bridge
        # Load qwebchannel.js from Qt resources and set up the bridge
        self._run_js("""
            var script = document.createElement('script');
            script.src = 'qrc:///qtwebchannel/qwebchannel.js';
            script.onload = function() {
                new QWebChannel(qt.webChannelTransport, function(channel) {
                    window.nvpBridge = channel.objects.nvpBridge;
                });
            };
            document.head.appendChild(script);
        """)
        
        # Apply theme — give JS enough time to define setTheme()
        theme = self.theme_manager.get_theme_name()
        QTimer.singleShot(600, lambda: self._run_js(
            f"if (typeof setTheme === 'function') setTheme('{theme}')"
        ))
        
        # Play pending video
        if self._pending_video:
            QTimer.singleShot(800, self._play_pending)
        
        # Re-send cached download formats now that JS is ready
        if hasattr(self, '_last_download_formats') and self._last_download_formats:
            QTimer.singleShot(900, lambda: self.set_download_formats(self._last_download_formats))
        
        logger.info("✅ NVP page loaded")
    
    def _play_pending(self):
        if self._pending_video:
            info = self._pending_video
            self._pending_video = None
            self.play_video_file(
                info['file_path'],
                info.get('title', ''),
                info.get('channel', ''),
                info.get('duration', ''),
            )
            # Re-send download formats if available (they were lost on page reload)
            if hasattr(self, '_last_download_formats') and self._last_download_formats:
                QTimer.singleShot(600, lambda: self.set_download_formats(self._last_download_formats))
    
    def play_video_file(self, file_path: str, title: str = "", channel: str = "", duration: str = ""):
        """
        Load and play a video (YouTube mode).
        
        If _video_info has a 'id' field, embeds YouTube directly (no download needed).
        Otherwise plays from a local file via HTML5 video.
        """
        self._current_mode = 'youtube'
        self._stack.setCurrentIndex(0)  # QWebEngineView
        self._video_file_path = file_path
        
        # Native title bar — show title + download, hide aspect ratio
        self._update_title_text(title or 'YouTube')
        self._aspect_btn.hide()
        self._tb_dl_btn.show()
        
        # Use update() to preserve url/id set by _launch_nvp
        self._video_info.update({
            'title': title,
            'channel': channel,
            'duration': duration,
            'file_path': file_path,
        })
        
        if not self._page_ready:
            self._pending_video = self._video_info.copy()
            # Reload the NVP HTML page if it was unloaded (e.g. after close)
            if self._http_port:
                nvp_url = f"http://localhost:{self._http_port}/index.html"
                self._web_view.setUrl(QUrl(nvp_url))
                logger.info(f"🔄 NVP page reloading: {nvp_url}")
            return
        
        # Hide the HTML title bar (native Qt bar replaces it)
        self._run_js("document.querySelector('.title-bar').style.display='none'")
        
        # Escape strings for JS
        safe_title = title.replace("'", "\\'").replace('"', '\\"')
        safe_channel = channel.replace("'", "\\'").replace('"', '\\"')
        
        video_id = self._video_info.get('id', '')
        
        if video_id:
            # YouTube embed mode — no download, instant playback
            self._run_js(f"loadYouTube('{video_id}', '{safe_title}')")
            logger.info(f"▶ NVP embed: {title} (youtube:{video_id})")
        elif file_path:
            # Local file mode
            file_url = QUrl.fromLocalFile(file_path).toString()
            self._run_js(f"loadVideo('{file_url}', '{safe_title}', '{safe_channel}', '{duration}')")
            logger.info(f"▶ NVP file: {title} ({file_path})")
        else:
            logger.error("❌ NVP: No video_id or file_path provided")
        
        # Notify kernel: media is now active
        if self._kernel:
            self._kernel.set_media_active(True)
    
    def set_loading_progress(self, percent: float, text: str = ""):
        """Update loading progress (called during download)."""
        safe_text = text.replace("'", "\\'")
        self._run_js(f"setLoadingProgress({percent}, '{safe_text}')")
    
    def set_download_formats(self, formats: list):
        """
        Set available download formats for the download panel.
        
        Args:
            formats: List of dicts with keys: quality, label, format, size, audio_only
        """
        # Cache formats for re-use after page reload
        self._last_download_formats = formats
        if not self._page_ready:
            # Page not loaded yet — formats will be sent from _on_page_loaded
            return
        formats_json = json.dumps(formats).replace("'", "\\'")
        self._run_js(f"setDownloadFormats('{formats_json}')")
    
    def set_youtube_service(self, yt_service):
        """Attach YouTube service for download functionality."""
        self._youtube_service = yt_service
    
    def set_kernel(self, kernel):
        """
        Set Core AI Kernel reference for media state notifications.
        
        The kernel uses media state to block idle suggestions
        during video playback.
        
        Args:
            kernel: NexaKernel instance
        """
        self._kernel = kernel
        logger.info("🔷 Core AI Kernel connected to NVP")
    
    @Slot(str, bool)
    def _on_download_requested(self, quality: str, audio_only: bool):
        """Handle download request from NVP JS download panel."""
        if not self._youtube_service or not self._video_info:
            return
        
        video_url = self._video_info.get('url', '')
        video_id = self._video_info.get('id', '')
        
        if not video_url and video_id:
            video_url = f"https://www.youtube.com/watch?v={video_id}"
        
        if not video_url:
            self._run_js("downloadError('No video URL available')")
            return
        
        # Chain callbacks: forward youtube_service events to BOTH
        # the NVP JS panel AND the main-window DownloadProgressWidget.
        orig_progress = self._youtube_service.on_download_progress
        orig_complete = self._youtube_service.on_download_complete
        orig_error = self._youtube_service.on_download_error
        
        def _restore_callbacks():
            self._youtube_service.on_download_progress = orig_progress
            self._youtube_service.on_download_complete = orig_complete
            self._youtube_service.on_download_error = orig_error
        
        def chained_progress(percent, speed, eta, title):
            self._download_progress_signal.emit(percent, speed or '', eta or '')
            if orig_progress:
                try:
                    orig_progress(percent, speed, eta, title)
                except Exception:
                    pass
        
        def chained_complete(title, filepath):
            self._download_complete_signal.emit(title)
            _restore_callbacks()
            if orig_complete:
                try:
                    orig_complete(title, filepath)
                except Exception:
                    pass
        
        def chained_error(title, error_msg):
            self._download_error_signal.emit(error_msg)
            _restore_callbacks()
            if orig_error:
                try:
                    orig_error(title, error_msg)
                except Exception:
                    pass
        
        self._youtube_service.on_download_progress = chained_progress
        self._youtube_service.on_download_complete = chained_complete
        self._youtube_service.on_download_error = chained_error
        
        # download_youtube() does a blocking info-fetch then spawns its own
        # worker thread, so we run it in a thread to avoid freezing the UI.
        # NOTE: do NOT emit _download_complete_signal here — download_youtube()
        # only returns a "starting download" status string, not a completion.
        def download_thread():
            try:
                self._youtube_service.download_youtube(
                    video_url,
                    audio_only=audio_only,
                    quality=quality,
                )
                # Actual completion is reported via on_download_complete callback.
            except Exception as e:
                self._download_error_signal.emit(str(e))
                _restore_callbacks()
        
        thread = threading.Thread(target=download_thread, daemon=True)
        thread.start()
    
    @Slot(float, str, str)
    def _update_download_progress(self, percent, speed, eta):
        safe_speed = json.dumps(speed)
        safe_eta = json.dumps(eta)
        self._run_js(f"updateDownloadProgress({percent}, {safe_speed}, {safe_eta})")
    
    @Slot(str)
    def _on_download_complete(self, result):
        safe_result = json.dumps(result)
        self._run_js(f"downloadComplete({safe_result})")
    
    @Slot(str)
    def _on_download_error(self, error):
        safe_error = json.dumps(error)
        self._run_js(f"downloadError({safe_error})")
    
    @Slot()
    def _on_theme_changed(self):
        # Forward theme to YouTube JS player
        if self._page_ready:
            theme = self.theme_manager.get_theme_name()
            self._run_js(f"setTheme('{theme}')")
        # Restyle native Qt widgets
        self._apply_nvp_theme()
    
    def _apply_nvp_theme(self):
        """Apply current theme to all native NVP widgets (title bar, controls, brand)."""
        is_dark = self.theme_manager.get_theme_name() == 'dark'
        
        # --- Title bar ---
        if is_dark:
            tb_bg = 'rgba(8, 12, 22, 0.97)'
            tb_border = 'rgba(0, 212, 255, 0.12)'
            tb_label = '#ccc'
            tb_btn = '#999'
            tb_btn_hover_bg = 'rgba(255,255,255,0.08)'
            tb_btn_hover_text = '#eee'
        else:
            tb_bg = 'rgba(230, 240, 248, 0.97)'
            tb_border = 'rgba(0, 100, 180, 0.18)'
            tb_label = '#444'
            tb_btn = '#666'
            tb_btn_hover_bg = 'rgba(0,100,180,0.08)'
            tb_btn_hover_text = '#222'
        
        self._title_bar.setStyleSheet(f"""
            QWidget {{
                background: {tb_bg};
                border-bottom: 1px solid {tb_border};
            }}
            QLabel {{
                color: {tb_label};
                background: transparent;
                border: none;
            }}
            QPushButton {{
                background: transparent; border: none; color: {tb_btn};
                font-size: 14px; padding: 4px 10px; border-radius: 4px;
                min-width: 28px; min-height: 24px;
            }}
            QPushButton:hover {{ background: {tb_btn_hover_bg}; color: {tb_btn_hover_text}; }}
        """)
        
        # --- Brand label (gradient applied via HTML, just keep background transparent) ---
        self._brand_lbl.setStyleSheet(
            "font-size: 13px; font-weight: bold; "
            "background: transparent; border: none; padding-right: 6px;"
        )
        # Update per-letter gradient colors for dark/light theme
        if is_dark:
            self._brand_lbl.setText(
                '<span style="font-size:13px; font-weight:700; font-family:Segoe UI,sans-serif;">'
                '<span style="color:#00D4FF;">N</span>'
                '<span style="color:#6B3FCC;">V</span>'
                '<span style="color:#9333EA;">P</span>'
                '</span>'
            )
        else:
            self._brand_lbl.setText(
                '<span style="font-size:13px; font-weight:700; font-family:Segoe UI,sans-serif;">'
                '<span style="color:#0077bb;">N</span>'
                '<span style="color:#5533aa;">V</span>'
                '<span style="color:#7722cc;">P</span>'
                '</span>'
            )
        
        # --- Title text (no background) ---
        title_color = '#aaa' if is_dark else '#555'
        self._native_title.setStyleSheet(
            f"font-size: 12px; color: {title_color}; font-family: 'Segoe UI', sans-serif; "
            f"background: transparent; border: none;"
        )
        
        # --- Aspect ratio button ---
        if hasattr(self, '_aspect_btn'):
            if is_dark:
                self._aspect_btn.setStyleSheet("""
                    QPushButton {
                        color: #00d4ff; font-size: 11px; padding: 3px 8px;
                        border: 1px solid rgba(0,212,255,0.2); border-radius: 4px;
                    }
                    QPushButton:hover { background: rgba(0,212,255,0.12); }
                """)
            else:
                self._aspect_btn.setStyleSheet("""
                    QPushButton {
                        color: #0077bb; font-size: 11px; padding: 3px 8px;
                        border: 1px solid rgba(0,100,180,0.25); border-radius: 4px;
                    }
                    QPushButton:hover { background: rgba(0,100,180,0.10); }
                """)
        
        # --- Local controls bar ---
        if hasattr(self, '_local_controls'):
            if is_dark:
                ctrl_bg = 'rgba(10, 15, 25, 0.92)'
                ctrl_border = 'rgba(0, 212, 255, 0.15)'
                ctrl_btn = '#e0e0e0'
                ctrl_hover = 'rgba(0, 212, 255, 0.15)'
                ctrl_accent = '#00d4ff'
                ctrl_label = '#888'
                groove_bg = 'rgba(255,255,255,0.08)'
            else:
                ctrl_bg = 'rgba(230, 240, 248, 0.92)'
                ctrl_border = 'rgba(0, 100, 180, 0.18)'
                ctrl_btn = '#333'
                ctrl_hover = 'rgba(0, 100, 180, 0.12)'
                ctrl_accent = '#0077bb'
                ctrl_label = '#666'
                groove_bg = 'rgba(0,0,0,0.06)'
            
            self._local_controls.setStyleSheet(f"""
                QWidget {{ background: {ctrl_bg}; border-top: 1px solid {ctrl_border}; }}
                QPushButton {{
                    background: transparent; border: none; color: {ctrl_btn};
                    font-size: 18px; padding: 6px 12px; border-radius: 6px;
                }}
                QPushButton:hover {{ background: {ctrl_hover}; color: {ctrl_accent}; }}
                QLabel {{ color: {ctrl_label}; font-size: 12px; font-family: Consolas, monospace; }}
                QSlider::groove:horizontal {{
                    height: 4px; background: {groove_bg}; border-radius: 2px;
                }}
                QSlider::handle:horizontal {{
                    width: 14px; height: 14px; margin: -5px 0;
                    background: {ctrl_accent}; border-radius: 7px;
                }}
                QSlider::sub-page:horizontal {{ background: {ctrl_accent}; border-radius: 2px; }}
            """)
        
        # --- WebView background ---
        web_bg = '#0A0F19' if is_dark else '#E8F4F8'
        self._web_view.setStyleSheet(f"background: {web_bg};")
        
        logger.debug(f"🎨 NVP theme applied: {'dark' if is_dark else 'light'}")
    
    @Slot()
    def _toggle_maximize(self):
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
    
    def _run_js(self, script: str):
        try:
            self._web_view.page().runJavaScript(script)
        except Exception as e:
            logger.debug(f"NVP JS error: {e}")
    
    # === Frameless window drag ===
    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseReleaseEvent(self, event):
        self._drag_pos = None
    
    def closeEvent(self, event):
        """Hide NVP on close instead of destroying — keeps singleton alive."""
        try:
            # Stop local media player to free resources
            if MULTIMEDIA_AVAILABLE and hasattr(self, '_media_player'):
                self._media_player.stop()
            
            # Don't shut down the HTTP server — we'll reuse it
            
            # Navigate to blank to stop any active media (YouTube iframe, video)
            self._web_view.setUrl(QUrl("about:blank"))
            # Mark page as not ready — will be reloaded on next play
            self._page_ready = False
        except Exception:
            pass
        
        # CRITICAL: Hide instead of destroy to prevent crash on reopen
        event.ignore()
        self.hide()
        
        # Notify kernel: media is no longer active
        if self._kernel:
            self._kernel.set_media_active(False)


# === Factory function for thread-safe creation ===

_nvp_instance: Optional[NexaVisionPlayer] = None


def get_or_create_nvp(parent=None) -> Optional[NexaVisionPlayer]:
    """
    Get or create the NVP singleton.
    MUST be called from the GUI thread.
    """
    global _nvp_instance
    
    if not WEBENGINE_AVAILABLE:
        logger.error("❌ QWebEngineView not available — NVP disabled")
        return None
    
    # Check if existing instance is still alive (C++ object not destroyed)
    if _nvp_instance is not None:
        try:
            # Access a property to verify the C++ object is alive
            _nvp_instance.isVisible()
        except RuntimeError:
            # C++ object was destroyed — clear stale reference
            logger.warning("⚠️ NVP instance was destroyed, creating new one")
            _nvp_instance = None
    
    if _nvp_instance is None:
        _nvp_instance = NexaVisionPlayer(parent)
    
    return _nvp_instance
