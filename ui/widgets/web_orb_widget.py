"""
Web Orb Widget - Phase 17 Particle Orb
A QWebEngineView-based orb visualization using HTML5 Canvas + Particles.
Provides the same API as NexaOrbWidget for drop-in replacement.

Features:
- Particle system with 220 particles orbiting the core
- Audio-reactive (voice amplitude drives particle behavior)
- State-aware: idle, listening, thinking, responding, error
- Smooth color transitions matching theme colors
- Energy ring waves, connection lines, waveform ring
- 60fps requestAnimationFrame loop
- Thread-safe: uses Qt signals to marshal calls to the GUI thread
"""

import logging
import os
import sys

from PySide6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PySide6.QtCore import Qt, QUrl, QTimer, Slot, Signal, QMetaObject, Q_ARG
from PySide6.QtGui import QColor

try:
    from PySide6.QtWebEngineWidgets import QWebEngineView
    from PySide6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False

from Themes.theme_manager import get_theme_manager

logger = logging.getLogger(__name__)


def _get_web_orb_path() -> str:
    """Get the path to the web orb assets (handles frozen/dev)."""
    if getattr(sys, 'frozen', False):
        # Running as bundled executable
        base = sys._MEIPASS
    else:
        # Running in development
        base = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    return os.path.join(base, "assets", "web_orb", "index.html")


class WebOrbWidget(QWidget):
    """
    Particle orb visualization using QWebEngineView.
    
    Drop-in replacement for NexaOrbWidget.
    Same public API:
        - set_state(state: str) 
        - set_audio_amplitude(amplitude: float)
    
    Thread-safe: set_state() and set_audio_amplitude() can be called
    from any thread. JS execution is marshaled to the GUI thread via
    Qt signals with QueuedConnection.
    """

    # Signal for thread-safe state updates from worker threads
    _state_signal = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        # Theme manager
        self.theme_manager = get_theme_manager()

        # State tracking
        self._current_state = "IDLE"
        self._current_amplitude = 0.0
        self._page_ready = False
        self._pending_state = None
        self._pending_theme = None

        # Connect internal signal (queued so it always runs on GUI thread)
        self._state_signal.connect(self._handle_state_change, Qt.ConnectionType.QueuedConnection)

        # Layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create the web view
        self._web_view = QWebEngineView(self)
        self._web_view.setStyleSheet("background: transparent;")

        # Configure web engine settings
        page = self._web_view.page()
        settings = page.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, False)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ShowScrollBars, False)

        # Transparent background
        page.setBackgroundColor(QColor(0, 0, 0, 0))

        layout.addWidget(self._web_view)

        # Load the orb page
        orb_path = _get_web_orb_path()
        if os.path.exists(orb_path):
            self._web_view.setUrl(QUrl.fromLocalFile(orb_path))
            logger.info(f"✅ WebOrbWidget loading: {orb_path}")
        else:
            logger.error(f"❌ Web orb assets not found: {orb_path}")
            return

        # Wait for page load then apply initial state
        self._web_view.loadFinished.connect(self._on_page_loaded)

        # Connect theme changes
        try:
            self.theme_manager.theme_changed.connect(
                self._on_theme_changed,
                Qt.ConnectionType.QueuedConnection
            )
        except Exception as e:
            logger.warning(f"Could not connect theme signal: {e}")

        # Audio update throttle timer (send audio at ~30fps to JS, not every frame)
        self._audio_timer = QTimer(self)
        self._audio_timer.timeout.connect(self._send_audio_level)
        self._audio_timer.start(33)  # ~30fps

        logger.info("✅ WebOrbWidget initialized")

    @Slot(bool)
    def _on_page_loaded(self, ok: bool):
        """Called when the web page finishes loading."""
        if not ok:
            logger.error("❌ Web orb page failed to load")
            return

        logger.info("✅ Web orb page loaded successfully")

        # Small delay to let JS initialize
        QTimer.singleShot(200, self._apply_initial_state)

    def _apply_initial_state(self):
        """Apply any pending state/theme after page load."""
        self._page_ready = True

        # Apply theme
        theme_name = self.theme_manager.get_theme_name()
        self._run_js(f"updateTheme('{theme_name}')")

        # Apply theme colors
        self._send_theme_colors()

        # Apply pending state
        state = self._pending_state or self._current_state
        js_state = self._map_state(state)
        self._run_js(f"updateOrbState('{js_state}')")
        self._pending_state = None

        logger.info(f"✅ Initial state applied: {js_state}, theme: {theme_name}")

    def set_state(self, state: str):
        """
        Update the visual state. Thread-safe — can be called from any thread.
        
        Args:
            state: One of IDLE, LISTENING, THINKING, RESPONDING, CONTENT, ERROR
        """
        self._current_state = state.upper()
        # Emit signal to marshal to GUI thread
        self._state_signal.emit(self._current_state)

    @Slot(str)
    def _handle_state_change(self, state: str):
        """Handle state change on the GUI thread."""
        if self._page_ready:
            js_state = self._map_state(state)
            self._run_js(f"updateOrbState('{js_state}')")
        else:
            self._pending_state = state

    def set_audio_amplitude(self, amplitude: float):
        """
        Update audio amplitude for voice reactivity. Thread-safe.
        
        Args:
            amplitude: Float 0.0 to 1.0
        """
        self._current_amplitude = max(0.0, min(1.0, amplitude))

    def _send_audio_level(self):
        """Send the current audio level to JS (throttled to ~30fps, runs on GUI thread)."""
        if self._page_ready:
            self._run_js(f"updateAudioLevel({self._current_amplitude:.4f})")

    @Slot()
    def _on_theme_changed(self):
        """Handle theme changes from the theme manager."""
        if not self._page_ready:
            return

        theme_name = self.theme_manager.get_theme_name()
        self._run_js(f"updateTheme('{theme_name}')")
        self._send_theme_colors()
        logger.info(f"🎨 Web orb theme updated: {theme_name}")

    def _send_theme_colors(self):
        """Send the current theme's orb colors to JS."""
        try:
            theme = self.theme_manager.get_current_theme()
            orb_colors = theme.get("orb", {})

            # Build color map for JS
            import json
            color_map = {}
            for state_key in ["idle", "listening", "thinking", "responding", "error"]:
                color = orb_colors.get(state_key, "")
                if color:
                    color_map[state_key] = color

            if color_map:
                colors_json = json.dumps(color_map)
                self._run_js(f"setThemeColors('{colors_json}')")
        except Exception as e:
            logger.warning(f"Could not send theme colors: {e}")

    def _map_state(self, state: str) -> str:
        """Map NexaState display names to JS orb state names."""
        mapping = {
            "IDLE": "idle",
            "LISTENING": "listening",
            "THINKING": "thinking",
            "RESPONDING": "responding",
            "CONTENT": "idle",
            "ERROR": "error",
        }
        return mapping.get(state.upper(), "idle")

    def _run_js(self, script: str):
        """Execute JavaScript in the web view."""
        try:
            self._web_view.page().runJavaScript(script)
        except Exception as e:
            logger.debug(f"JS exec error: {e}")

    def cleanup(self):
        """Clean up resources."""
        try:
            self._audio_timer.stop()
            self._web_view.setUrl(QUrl("about:blank"))
        except Exception:
            pass

    def closeEvent(self, event):
        """Handle widget close."""
        self.cleanup()
        super().closeEvent(event)
