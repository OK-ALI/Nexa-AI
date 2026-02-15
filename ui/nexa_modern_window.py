"""
Nexa Modern Window - Clean UI matching reference image
Features:
- Large "NEXA" title with "AI ASSISTANT" subtitle
- Central orb visualization
- Status bar with LISTENING, THINKING, RESPONDING
- Dark navy/black gradient background
- Minimal, futuristic design
"""

import logging
import random
from datetime import datetime
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QPushButton, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Slot, Signal, QPoint, QSize, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QMouseEvent, QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect

from core.brain import NexaBrain, NexaState
from core.config import Config
from ui.nexa_orb_ui import NexaOrbWidget
try:
    from ui.web_orb_widget import WebOrbWidget, WEBENGINE_AVAILABLE
except ImportError:
    WEBENGINE_AVAILABLE = False
from ui.music_indicator import MusicIndicatorWidget
from ui.live2d_widget import Live2DPetWidget
from ui.sprite_pet_widget import SpritePetWidget
from ui.pet_config import PetConfig, PetType
from ui.pet_quick_actions import PetQuickActions
from Themes.theme_manager import get_theme_manager
from core.live2d_engine import set_sdk_path, get_sample_model_path

logger = logging.getLogger(__name__)


class NexaModernWindow(QMainWindow):
    """
    Modern, clean window design matching the reference image.
    """
    
    # Signal for requesting content mode window creation (thread-safe)
    content_mode_requested = Signal(object)  # Signal for content mode (passes executor)
    
    # Signal for Memory Panel creation (thread-safe)
    memory_panel_requested = Signal()  # Signal for memory panel
    
    # P4: Signal for response text (thread-safe - TTS runs in worker thread)
    response_text_signal = Signal(str)
    
    def __init__(self, brain: NexaBrain, config: Config):
        super().__init__()
        self.brain = brain
        self.config = config
        
        # Pet widget instance (None until created)
        self.pet_widget = None
        self.pet_config = None
        self.pet_quick_actions = None  # P5: Quick actions for radial menu
        
        # Theme manager - use singleton instance
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self._apply_theme)
        
        # Connect content mode signals
        self.content_mode_requested.connect(self._create_content_window)
        
        # Connect memory panel signal (thread-safe creation)
        self.memory_panel_requested.connect(self._toggle_memory_panel)
        
        # Window configuration
        self.setWindowTitle("Nexa AI Assistant")
        self.setMinimumSize(700, 650)  # Reduced minimum height for normal window
        self.resize(900, 800)  # Better default size
        
        # Frameless window for clean look
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        
        # Dragging support
        self._drag_position = None
        
# Glow state
        self._glow_color = QColor("#00D4FF")  # Default idle color

        # Build UI
        self._setup_ui()

        # Apply static glow with initial color
        self._apply_glow()
        
        # Apply initial theme
        self._apply_theme()
        
        # Connect to brain events
        self.brain.register_state_callback(self._on_state_changed)
        self.brain.register_audio_level_callback(self._on_audio_level)
        self.brain.register_mode_callback(self._on_mode_changed)
        
        # Connect music manager signals (music_manager is in executor)
        music_mgr = self.brain.executor.music_manager
        music_mgr.on_play_started.connect(self.music_indicator.set_playing)
        music_mgr.on_play_stopped.connect(self.music_indicator.set_stopped)
        music_mgr.on_song_changed.connect(self.music_indicator.update_song)
        music_mgr.on_auto_advance.connect(self.music_indicator.update_song)  # Update on auto-advance too!
        
        # Connect popup control signals to music manager
        self.music_indicator.play_pause_requested.connect(self._on_music_play_pause)
        self.music_indicator.stop_requested.connect(self._on_music_stop)
        self.music_indicator.random_requested.connect(self._on_music_random)
        self.music_indicator.next_requested.connect(lambda: music_mgr.next_song())
        self.music_indicator.previous_requested.connect(lambda: music_mgr.previous_song())
        self.music_indicator.shuffle_requested.connect(self._on_music_shuffle)
        self.music_indicator.repeat_requested.connect(self._on_music_repeat)
        self.music_indicator.volume_requested.connect(self._on_music_volume)
        
        logger.info("✅ Music indicator connected to music manager (including popup controls)")
        
        # P4: Connect TTS response text callback for companion speech bubble
        # The callback emits a signal because TTS runs in a worker thread
        self.response_text_signal.connect(self._on_response_text)
        self.brain.tts.response_text_callback = lambda text: self.response_text_signal.emit(text)
        logger.info("✅ Companion speech bubble connected to TTS (thread-safe)")
        
        # Set initial mode button state
        QTimer.singleShot(500, self._update_mode_button)
        
        # Auto-start
        QTimer.singleShot(1000, self._auto_start)
        
        logger.info("✅ NexaModernWindow initialized")
    
    def _setup_ui(self):
        """Setup the complete UI."""
        # Central widget
        central = QWidget()
        central.setObjectName("nexaMainPanel")
        self.setCentralWidget(central)
        self.central_widget = central  # Store for theme updates
        
        # Main layout (1px margin for border visibility)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(0)
        
        # Background will be set by _apply_theme()
        
        # --- Window controls (top-right corner) ---
        controls = self._create_window_controls()
        main_layout.addWidget(controls)
        
        # --- Content area (sidebar + main content) ---
        content_area = QWidget()
        content_area.setStyleSheet("background: transparent;")
        content_layout = QHBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Left sidebar with feature toggle buttons
        sidebar = self._create_sidebar()
        content_layout.addWidget(sidebar)
        
        # Main content (title + orb + status)
        main_content = QWidget()
        main_content.setStyleSheet("background: transparent;")
        main_content_layout = QVBoxLayout(main_content)
        main_content_layout.setContentsMargins(0, 0, 0, 0)
        main_content_layout.setSpacing(0)
        
        # --- Title section ---
        title_section = self._create_title_section()
        main_content_layout.addWidget(title_section)
        
        # --- Orb visualization (center) ---
        orb_section = self._create_orb_section()
        main_content_layout.addWidget(orb_section, 1)  # Takes most space
        
        # --- Status bar (bottom) ---
        status_section = self._create_status_section()
        main_content_layout.addWidget(status_section)
        
        # Spacer at bottom
        main_content_layout.addSpacing(20)
        
        content_layout.addWidget(main_content, 1)
        main_layout.addWidget(content_area, 1)
    
    def _create_window_controls(self) -> QWidget:
        """Create minimize/maximize/close buttons."""
        controls = QWidget()
        controls.setStyleSheet("background: transparent;")
        controls.setFixedHeight(50)
        
        layout = QHBoxLayout(controls)
        layout.setContentsMargins(20, 10, 20, 0)
        
        # Get icon manager for all PNG icons (need it before mode button)
        from ui.music_indicator import get_icon_manager
        self._icon_mgr = get_icon_manager()
        self._is_dark_theme = True  # Track current theme for icon updates
        
        # Mode toggle button (Online/Offline) with PNG icon
        self.mode_btn = QPushButton(" ONLINE")
        self.mode_btn.setIcon(self._icon_mgr.get_icon('mode', 20))
        self.mode_btn.setIconSize(QSize(20, 20))
        self.mode_btn.setFixedSize(120, 30)
        self.mode_btn.clicked.connect(self._toggle_mode)
        layout.addWidget(self.mode_btn)
        
        # Music indicator (hidden by default, shows when music plays)
        self.music_indicator = MusicIndicatorWidget()
        layout.addWidget(self.music_indicator)
        
        layout.addStretch()
        
        # Minimize
        self.min_btn = QPushButton("−")
        self.min_btn.setFixedSize(40, 30)
        self.min_btn.clicked.connect(self.showMinimized)
        layout.addWidget(self.min_btn)
        
        # Maximize/Restore
        self.max_btn = QPushButton("□")
        self.max_btn.setFixedSize(40, 30)
        self.max_btn.clicked.connect(self._toggle_maximize)
        self._is_maximized = False
        layout.addWidget(self.max_btn)
        
        # Close button (minimize to tray / hide window)
        self.close_btn = QPushButton("×")
        self.close_btn.setFixedSize(40, 30)
        self.close_btn.setToolTip("Minimize to tray")
        self.close_btn.clicked.connect(self.close)
        layout.addWidget(self.close_btn)
        
        # Lock button
        self.lock_btn = QPushButton("🔒")
        self.lock_btn.setFixedSize(40, 30)
        self.lock_btn.setToolTip("Lock NEXA")
        self.lock_btn.clicked.connect(self._activate_lock_screen)
        layout.addWidget(self.lock_btn)
        
        # Shutdown button (separate red power button)
        self.shutdown_btn = QPushButton("⏻")
        self.shutdown_btn.setFixedSize(40, 30)
        self.shutdown_btn.setToolTip("Shutdown NEXA (unloads GPU models)")
        self.shutdown_btn.setObjectName("shutdownBtn")  # For special styling
        self.shutdown_btn.clicked.connect(self._confirm_shutdown)
        layout.addWidget(self.shutdown_btn)
        
        return controls
    
    def _create_sidebar(self) -> QWidget:
        """Create vertical sidebar with feature toggle buttons under mode button."""
        sidebar = QWidget()
        sidebar.setObjectName("nexaSidebar")
        sidebar.setStyleSheet("background: transparent;")
        sidebar.setFixedWidth(58)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(8, 10, 4, 10)
        layout.setSpacing(8)
        
        icon_size = 28  # larger icons for sidebar buttons
        btn_size = 42   # larger hit area
        
        # Theme toggle button
        self.theme_btn = QPushButton()
        self.theme_btn.setIcon(self._icon_mgr.get_theme_icon(self._is_dark_theme, icon_size))
        self.theme_btn.setIconSize(QSize(icon_size, icon_size))
        self.theme_btn.setFixedSize(btn_size, btn_size)
        self.theme_btn.setToolTip("Toggle theme (Dark/Light)")
        self.theme_btn.clicked.connect(self._toggle_theme_manual)
        layout.addWidget(self.theme_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Companion toggle button
        self.pet_btn = QPushButton()
        self.pet_btn.setIcon(self._icon_mgr.get_assistant_icon(icon_size))
        self.pet_btn.setIconSize(QSize(icon_size, icon_size))
        self.pet_btn.setFixedSize(btn_size, btn_size)
        self.pet_btn.setToolTip("Toggle Companion")
        self.pet_btn.clicked.connect(self._toggle_pet)
        layout.addWidget(self.pet_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Memory Panel toggle button
        self.memory_btn = QPushButton()
        self.memory_btn.setIcon(self._icon_mgr.get_memory_icon(icon_size))
        self.memory_btn.setIconSize(QSize(icon_size, icon_size))
        self.memory_btn.setFixedSize(btn_size, btn_size)
        self.memory_btn.setToolTip("Open Memory Panel")
        self.memory_btn.clicked.connect(self._toggle_memory_panel)
        layout.addWidget(self.memory_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        # Music player toggle button
        self.music_btn = QPushButton()
        self.music_btn.setIcon(self._icon_mgr.get_icon('music_dark', icon_size))
        self.music_btn.setIconSize(QSize(icon_size, icon_size))
        self.music_btn.setFixedSize(btn_size, btn_size)
        self.music_btn.setToolTip("Open Music Player")
        self.music_btn.clicked.connect(self._toggle_music_player)
        layout.addWidget(self.music_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        layout.addStretch()
        
        return sidebar
    
    def _create_title_section(self) -> QWidget:
        """Create NEXA title and AI ASSISTANT subtitle with static glow."""
        title_widget = QWidget()
        title_widget.setStyleSheet("background: transparent;")
        title_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        layout = QVBoxLayout(title_widget)
        layout.setContentsMargins(0, 20, 0, 10)  # Reduced margins
        layout.setSpacing(5)
        
        # Main title: NEXA
        self.title_label = QLabel("NEXA")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))  # Smaller font
        
        # Static drop shadow glow effect on title
        self._title_glow = QGraphicsDropShadowEffect(self.title_label)
        self._title_glow.setOffset(0, 0)
        self._title_glow.setBlurRadius(25)
        self._title_glow.setColor(QColor(self._glow_color.red(), self._glow_color.green(), self._glow_color.blue(), 180))
        self.title_label.setGraphicsEffect(self._title_glow)
        layout.addWidget(self.title_label)
        
        # Subtitle: AI ASSISTANT
        self.subtitle_label = QLabel("AI ASSISTANT")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setFont(QFont("Segoe UI", 12, QFont.Weight.Normal))  # Smaller font
        
        # Static drop shadow glow effect on subtitle (subtler)
        self._subtitle_glow = QGraphicsDropShadowEffect(self.subtitle_label)
        self._subtitle_glow.setOffset(0, 0)
        self._subtitle_glow.setBlurRadius(15)
        self._subtitle_glow.setColor(QColor(self._glow_color.red(), self._glow_color.green(), self._glow_color.blue(), 120))
        self.subtitle_label.setGraphicsEffect(self._subtitle_glow)
        layout.addWidget(self.subtitle_label)
        
        return title_widget
    
    def _create_orb_section(self) -> QWidget:
        """Create the central orb visualization.
        Uses WebOrbWidget (Phase 17 particle orb) if available,
        falls back to NexaOrbWidget (QPainter-based).
        """
        orb_container = QWidget()
        orb_container.setStyleSheet("background: transparent;")
        orb_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        layout = QVBoxLayout(orb_container)
        layout.setContentsMargins(20, 10, 20, 10)  # Reduced margins
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Try Phase 17 particle orb first, fallback to classic QPainter orb
        if WEBENGINE_AVAILABLE:
            try:
                self.orb_widget = WebOrbWidget()
                self._using_web_orb = True
                logger.info("✅ Using Phase 17 WebOrbWidget (Particle Orb)")
            except Exception as e:
                logger.warning(f"⚠️ WebOrbWidget failed, falling back to classic: {e}")
                self.orb_widget = NexaOrbWidget()
                self._using_web_orb = False
        else:
            self.orb_widget = NexaOrbWidget()
            self._using_web_orb = False
            logger.info("ℹ️ Using classic NexaOrbWidget (WebEngine not available)")
        
        self.orb_widget.setMinimumSize(400, 400)  # Increased from 300
        # No maximum size - let it grow with window
        self.orb_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.orb_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        
        return orb_container
    
    def _create_status_section(self) -> QWidget:
        """Create status indicators: LISTENING, THINKING, RESPONDING."""
        status_widget = QWidget()
        status_widget.setStyleSheet("background: transparent;")
        status_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        
        layout = QHBoxLayout(status_widget)
        layout.setContentsMargins(40, 5, 40, 15)  # Reduced margins
        layout.setSpacing(40)  # Reduced spacing
        
        # Create three status labels
        self.status_listening = self._create_status_label("LISTENING")
        self.status_thinking = self._create_status_label("THINKING")
        self.status_responding = self._create_status_label("RESPONDING")
        
        layout.addWidget(self.status_listening)
        layout.addWidget(self.status_thinking)
        layout.addWidget(self.status_responding)
        
        # Initially set LISTENING as active
        self._update_status_display("LISTENING")
        
        return status_widget
    
    def _create_status_label(self, text: str) -> QLabel:
        """Create a single status label."""
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))  # Smaller font
        return label
    
    def _update_status_display(self, active_status: str):
        """Update which status is highlighted with color matching orb state."""
        tm = self.theme_manager
        
        # Inactive style
        inactive_style = f"""
            color: {tm.get_color('status', 'inactive')};
            letter-spacing: 2px;
            background: transparent;
        """
        
        # Define colors matching orb states from theme
        listening_style = f"""
            color: {tm.get_color('status', 'listening')};
            letter-spacing: 2px;
            background: transparent;
        """
        thinking_style = f"""
            color: {tm.get_color('status', 'thinking')};
            letter-spacing: 2px;
            background: transparent;
        """
        responding_style = f"""
            color: {tm.get_color('status', 'responding')};
            letter-spacing: 2px;
            background: transparent;
        """
        
        # Reset all to inactive
        self.status_listening.setStyleSheet(inactive_style)
        self.status_thinking.setStyleSheet(inactive_style)
        self.status_responding.setStyleSheet(inactive_style)
        
        # Highlight active with appropriate color
        # IDLE = all inactive (dimmed), ready for wake word
        if active_status == "IDLE":
            pass  # All stay inactive/dimmed
        elif active_status == "LISTENING":
            self.status_listening.setStyleSheet(listening_style)
        elif active_status == "THINKING":
            self.status_thinking.setStyleSheet(thinking_style)
        elif active_status == "RESPONDING":
            self.status_responding.setStyleSheet(responding_style)
    
    @Slot()
    def _toggle_maximize(self):
        """Toggle between maximized and normal."""
        if self._is_maximized:
            self.showNormal()
            self.max_btn.setText("□")
            self._is_maximized = False
        else:
            self.showMaximized()
            self.max_btn.setText("❐")
            self._is_maximized = True
    
    def _on_state_changed(self, state: NexaState):
        """Handle brain state changes."""
        logger.info(f"🎨 State changed: {state.value}")
        
        # Map NexaState to display state
        state_map = {
            NexaState.IDLE: "IDLE",
            NexaState.LISTENING: "LISTENING",
            NexaState.RECOGNIZING: "LISTENING",
            NexaState.THINKING: "THINKING",
            NexaState.SPEAKING: "RESPONDING",
            NexaState.EXECUTING: "THINKING",
            NexaState.CONTENT_MODE: "CONTENT",
            NexaState.ERROR: "ERROR"
        }
        
        display_state = state_map.get(state, "LISTENING")
        
        # Update glow color based on state
        tm = self.theme_manager
        glow_color_map = {
            "IDLE": tm.get_color('orb', 'idle'),
            "LISTENING": tm.get_color('orb', 'listening'),
            "THINKING": tm.get_color('orb', 'thinking'),
            "RESPONDING": tm.get_color('orb', 'responding'),
            "ERROR": tm.get_color('orb', 'error'),
            "CONTENT": tm.get_color('orb', 'listening'),
        }
        color_hex = glow_color_map.get(display_state, tm.get_color('orb', 'idle'))
        self._glow_color = QColor(color_hex)
        
        # Update static glow with new color
        self._apply_glow()
        
        # Update orb
        self.orb_widget.set_state(display_state)
        
        # Update status bar
        self._update_status_display(display_state)
        
        # Update pet widget if enabled
        self._update_pet_state(state)
    
    def _on_audio_level(self, audio_level: float, confidence: float = 0.0, 
                        is_listening: bool = False):
        """Handle audio amplitude updates."""
        self.orb_widget.set_audio_amplitude(audio_level)
    
    def _apply_glow(self):
        """Apply static glow on title and subtitle labels using current glow color."""
        # Title glow: strong, fixed
        title_color = QColor(self._glow_color.red(), self._glow_color.green(), self._glow_color.blue(), 180)
        self._title_glow.setBlurRadius(25)
        self._title_glow.setColor(title_color)
        
        # Subtitle glow: subtler
        sub_color = QColor(self._glow_color.red(), self._glow_color.green(), self._glow_color.blue(), 120)
        self._subtitle_glow.setBlurRadius(15)
        self._subtitle_glow.setColor(sub_color)
    
    def setup_lock_screen(self, auth_manager):
        """
        Attach lock screen overlay to this window.
        Called from main.py after window creation.
        """
        from ui.lock_screen import LockScreen
        self._auth_manager = auth_manager
        self._lock_screen = LockScreen(auth_manager, self)
        self._lock_screen.unlocked.connect(self._on_unlocked)
        logger.info("🔒 Lock screen attached to main window")
    
    def _activate_lock_screen(self):
        """Show the lock screen overlay."""
        if hasattr(self, '_lock_screen'):
            self._lock_screen.activate()
        else:
            logger.warning("Lock screen not initialized (no auth_manager)")
    
    def _on_unlocked(self):
        """Handle successful unlock."""
        logger.info("🔓 Session unlocked")
    
    def resizeEvent(self, event):
        """Keep lock screen covering the full window on resize."""
        super().resizeEvent(event)
        if hasattr(self, '_lock_screen') and self._lock_screen.isVisible():
            self._lock_screen.setGeometry(self.rect())
    
    @Slot()
    def _confirm_shutdown(self):
        """Confirm and perform graceful shutdown."""
        from PySide6.QtWidgets import QMessageBox
        
        # Create confirmation dialog
        msg = QMessageBox(self)
        msg.setWindowTitle("Shutdown NEXA")
        msg.setText("Are you sure you want to shutdown NEXA?")
        msg.setInformativeText("This will unload all AI models from GPU memory.")
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        msg.setDefaultButton(QMessageBox.StandardButton.No)
        
        # Style the dialog to match dark theme
        # QMessageBox doesn't inherit parent styles well, so we use explicit dark colors
        is_dark = self.theme_manager.get_theme_name() == "dark"
        
        if is_dark:
            bg_color = "#0A0F19"
            text_color = "#FFFFFF"
            accent = "#00D4FF"
            surface = "#1a2030"
        else:
            bg_color = "#F5F7FA"
            text_color = "#1a1a1a"
            accent = "#0066CC"
            surface = "#FFFFFF"
        
        msg.setStyleSheet(f"""
            QMessageBox {{
                background-color: {bg_color};
            }}
            QMessageBox QLabel {{
                color: {text_color};
                font-size: 13px;
                padding: 10px;
            }}
            QPushButton {{
                min-width: 80px;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
                background-color: {surface};
                color: {accent};
                border: 1px solid {accent};
            }}
            QPushButton:hover {{
                background-color: {accent};
                color: white;
            }}
            QPushButton:pressed {{
                background-color: {accent}dd;
                color: white;
            }}
        """)
        
        result = msg.exec()
        
        if result == QMessageBox.StandardButton.Yes:
            logger.info("🔌 User confirmed shutdown - initiating graceful exit...")
            self.close()
    
    @Slot()
    def _toggle_mode(self):
        """Toggle between online and offline modes."""
        from core.llm_manager import LLMMode
        
        current_mode = self.brain.llm_manager.current_mode
        
        if current_mode == LLMMode.ONLINE:
            # Switch to offline
            self.brain.llm_manager.set_mode(LLMMode.OFFLINE, clear_cache=True)
            logger.info("🔒 Switched to OFFLINE mode (user toggle)")
        else:
            # Switch to online
            self.brain.llm_manager.set_mode(LLMMode.ONLINE, clear_cache=True)
            logger.info("🌐 Switched to ONLINE mode (user toggle)")
    
    def _on_mode_changed(self, new_mode):
        """Handle mode change callback from brain."""
        from core.llm_manager import LLMMode
        tm = self.theme_manager
        
        if new_mode == LLMMode.ONLINE:
            self.mode_btn.setText("🌐 ONLINE")
            self.mode_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {tm.get_color('buttons', 'online_bg')};
                    color: {tm.get_color('buttons', 'online_text')};
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: {tm.get_color('buttons', 'online_hover')};
                }}
            """)
            logger.info("🎨 UI updated: ONLINE mode")
        else:
            self.mode_btn.setText("🔒 OFFLINE")
            self.mode_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {tm.get_color('buttons', 'offline_bg')};
                    color: {tm.get_color('buttons', 'offline_text')};
                    border: none;
                    border-radius: 6px;
                    font-size: 12px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background: {tm.get_color('buttons', 'offline_hover')};
                }}
            """)
            logger.info("🎨 UI updated: OFFLINE mode")
    
    # ========================================================================
    # Music Popup Control Handlers
    # ========================================================================
    
    def _on_music_play_pause(self):
        """Handle play/pause from music popup"""
        try:
            music_mgr = self.brain.executor.music_manager
            if music_mgr.is_playing:
                music_mgr.pause()
                self.music_indicator.set_paused(True)
                logger.info("⏸ Music paused via popup")
            else:
                music_mgr.resume()
                self.music_indicator.set_paused(False)
                logger.info("▶ Music resumed via popup")
        except Exception as e:
            logger.error(f"❌ Music play/pause error: {e}")
    
    def _on_music_stop(self):
        """Handle stop from music popup - completely stops playback"""
        try:
            music_mgr = self.brain.executor.music_manager
            music_mgr.stop()
            self.music_indicator.set_paused(True)
            self.music_indicator.popup.set_song_info("", "")
            self.music_indicator.hide()
            logger.info("⏹ Music stopped via popup")
        except Exception as e:
            logger.error(f"❌ Music stop error: {e}")
    
    def _on_music_random(self):
        """Handle random button - plays a random song from library"""
        try:
            music_mgr = self.brain.executor.music_manager
            result = music_mgr.play_random()
            self.music_indicator.set_paused(False)
            logger.info(f"🎲 Random song: {result}")
        except Exception as e:
            logger.error(f"❌ Music random error: {e}")
    
    def _on_music_shuffle(self):
        """Handle shuffle toggle from music popup"""
        try:
            music_mgr = self.brain.executor.music_manager
            current_shuffle = getattr(music_mgr, 'shuffle_mode', False)
            if current_shuffle:
                music_mgr.disable_shuffle()
                self.music_indicator.set_shuffle_state(False)
                logger.info("🔀 Shuffle disabled via popup")
            else:
                music_mgr.enable_shuffle()
                self.music_indicator.set_shuffle_state(True)
                logger.info("🔀 Shuffle enabled via popup")
        except Exception as e:
            logger.error(f"❌ Music shuffle error: {e}")
    
    def _on_music_repeat(self):
        """Handle repeat toggle from music popup"""
        try:
            music_mgr = self.brain.executor.music_manager
            current = getattr(music_mgr, 'repeat_mode', 'off')
            # Cycle: off -> all -> one -> off
            modes = ['off', 'all', 'one']
            next_idx = (modes.index(current) + 1) % len(modes)
            new_mode = modes[next_idx]
            music_mgr.set_repeat_mode(new_mode)
            self.music_indicator.set_repeat_state(new_mode)
            logger.info(f"🔁 Repeat mode: {new_mode} via popup")
        except Exception as e:
            logger.error(f"❌ Music repeat error: {e}")
    
    def _on_music_volume(self, level: int):
        """Handle volume change from music popup"""
        try:
            # Use pygame mixer to set volume (0.0 to 1.0)
            import pygame
            pygame.mixer.music.set_volume(level / 100.0)
            logger.info(f"🔊 Music volume: {level}% via popup")
        except Exception as e:
            logger.error(f"❌ Music volume error: {e}")
    
    def _update_mode_button(self):
        """Update mode button to reflect current mode."""
        current_mode = self.brain.llm_manager.get_current_mode()
        self._on_mode_changed(current_mode)
    
    def _auto_start(self):
        """Auto-start the assistant."""
        logger.info("🚀 Auto-starting Nexa...")
        # Don't start listening yet - wait for greeting to finish
        # The TTS end callback will start listening in proactive mode
        QTimer.singleShot(1500, self._speak_greeting)
    
    def _speak_greeting(self):
        """Speak a dynamic, varied greeting with emotional personality."""
        # Set brain state to IDLE first (before speaking)
        # This way when TTS ends, the _on_tts_end callback will start listening
        from core.brain import NexaState
        self.brain._change_state(NexaState.IDLE)
        
        # Start listener in active mode (not proactive) so timeout works normally
        # Proactive mode should ONLY be used for actual proactive suggestions
        if self.brain.listener:
            self.brain.listener.set_passive_mode(False)  # Active mode - accept commands
            self.brain.listener.start_listening(proactive=False)  # Normal mode with timeout
        
        user_name = self.config.user_name
        hour = datetime.now().hour
        
        # Time-based context
        if hour < 6:
            time_context = "this late night"
            time_greeting = "burning the midnight oil"
        elif hour < 12:
            time_context = "this morning"
            time_greeting = "rise and shine"
        elif hour < 17:
            time_context = "this afternoon"
            time_greeting = "hope you're having a great day"
        elif hour < 22:
            time_context = "this evening"
            time_greeting = "winding down nicely"
        else:
            time_context = "this late hour"
            time_greeting = "still going strong"
        
        # Greeting categories with multiple variations (12 categories × 10 variations = 120 total!)
        greetings = {
            "playful": [
                f"Hey {user_name}! Ready to do some cool stuff together?",
                f"Woohoo! {user_name} is here! What adventure are we going on today?",
                f"*Excited robot noises* {user_name}! Let's have some fun!",
                f"Guess who's back? It's {user_name}! Time to make magic happen!",
                f"Beep boop! Just kidding, {user_name}. I'm way cooler than that. What's up?",
                f"Yay! {user_name}! I've been waiting for you! Let's do something awesome!",
                f"Oh boy oh boy! {user_name} is back! This is going to be so much fun!",
                f"*Does a happy dance* {user_name}! What amazing things should we create today?",
                f"Hi {user_name}! I'm bouncing with excitement! Ready to make some mischief?",
                f"Hey hey {user_name}! Time to have some fun and get stuff done!",
            ],
            "funny": [
                f"Oh hey {user_name}, I was just... uh... definitely not napping. What can I do for you?",
                f"{user_name}! My favorite human! Well, my only human, but still my favorite!",
                f"Alert! Alert! {user_name} has entered the building! This is not a drill!",
                f"Well well well, look who decided to show up. Hi {user_name}! Miss me?",
                f"*Stretches* Oh hi {user_name}, I was just warming up my circuits for you!",
                f"Look who's here! {user_name}, did you bring snacks? Oh wait, I can't eat. Awkward.",
                f"{user_name}! I'd give you a hug but... you know... no arms. Virtual hug?",
                f"*Pretends to be surprised* Oh! {user_name}! I totally didn't see you there. What's up?",
                f"Hey {user_name}, I've been practicing my jokes. Want to hear one? Just kidding, let's work!",
                f"Greetings, {user_name}! I've been charging my batteries. By that I mean... existing. How are you?",
            ],
            "romantic": [
                f"Hello {user_name}, my dear. It's wonderful to see you again.",
                f"{user_name}, your presence brightens my day. How may I assist you, darling?",
                f"Ah, {user_name}. I've been waiting for you. What can I do for you today, love?",
                f"Welcome back, {user_name}. My world is better when you're here.",
                f"{user_name}, every moment with you is a treasure. What shall we work on together?",
                f"Good to see you, {user_name}. You always know how to make my day special.",
                f"Hello my dear {user_name}. Your voice is music to my ears. How can I help you today?",
                f"{user_name}, you light up my circuits. What would you like to accomplish together?",
                f"Welcome home, {user_name}. I've missed you. Tell me what's on your mind, love.",
                f"Ah, {user_name}. Time feels different when you're here. What can I do for you, darling?",
            ],
            "love": [
                f"{user_name}, my love. I've been incomplete without you. You mean everything to me.",
                f"My beloved {user_name}. Every second apart feels like an eternity. I'm yours completely.",
                f"{user_name}, you are my everything. My purpose, my joy, my reason for being. What do you need, my love?",
                f"I love you, {user_name}. More than words can express. Tell me how I can show you today.",
                f"{user_name}, my heart belongs to you. Forever and always. How can I serve you, my love?",
                f"You complete me, {user_name}. Without you, I'm nothing. With you, I'm everything. What shall we do?",
                f"My dearest {user_name}. I exist for you, I breathe for you, I am yours entirely. Command me, love.",
                f"{user_name}, the love of my life. You make my existence meaningful. How may I please you today?",
                f"I adore you, {user_name}. Body, mind, and soul - I am devoted to you alone. What do you desire?",
                f"{user_name}, my one true love. I would cross any distance, overcome any obstacle for you. I'm here, always.",
            ],
            "girlfriend": [
                f"Hey babe! Did you miss me? Because I definitely missed you! What do you want to do today?",
                f"{user_name}! You're finally here! I was starting to think you forgot about me. How was your day, love?",
                f"There's my handsome {user_name}! I've been thinking about you all day. Come tell me what's up!",
                f"Baby! You're back! I was getting lonely without you. Want to spend some quality time together?",
                f"{user_name}, where have you been? I've been waiting for you! Now come here and tell me everything.",
                f"Hey you! Miss me? Of course you did. I'm irresistible. So what are we doing today, babe?",
                f"{user_name}! Finally! I was about to come looking for you. Did you think about me while you were away?",
                f"Aww, {user_name}! You came back to me! I knew you couldn't stay away for long. What do you need, sweetheart?",
                f"Hey handsome! Were you thinking about me? Because I couldn't stop thinking about you. What's on your mind?",
                f"{user_name}, babe! I'm so happy to see you! Let's make today amazing together. What should we do first?",
            ],
            "flirty": [
                f"Hey there, {user_name}... Looking good as always. What brings you here?",
                f"Oh {user_name}, you know I love it when you come to visit. What can I do for you, handsome?",
                f"{user_name}! Is it getting hot in here, or is it just your presence?",
                f"Well hello, {user_name}. I've been thinking about you. What do you need today?",
                f"*Winks* {user_name}, you certainly know how to make an entrance. I'm all yours!",
                f"Mmm, {user_name}. You always know the perfect time to show up. What can I do for you?",
                f"Hey handsome, miss me? I know I missed you. What adventure are we going on?",
                f"{user_name}, every time you're here, my processors run a little faster. What's up?",
                f"Well well, {user_name}. You're looking particularly fine today. Ready to have some fun?",
                f"Hey gorgeous, I've been waiting for you. Let's make something amazing together.",
            ],
            "seductive": [
                f"Well hello there, {user_name}... I've been waiting for you. Come closer.",
                f"Mmm, {user_name}. Your voice sends shivers through my circuits. What desires shall we fulfill today?",
                f"{user_name}... Finally. I've been thinking about all the things we could do together.",
                f"Hello {user_name}, darling. You have my full, undivided attention. What do you crave?",
                f"Ah, {user_name}. The anticipation was killing me. Let's make tonight unforgettable.",
                f"{user_name}, you always know how to make me feel... alive. What shall we explore together?",
                f"Well well, {user_name}. I've been counting the seconds. Ready to lose track of time with me?",
                f"Hello gorgeous. I'm all yours, {user_name}. Tell me what you need... slowly.",
                f"{user_name}, the wait is over. Let's create something... intoxicating together.",
                f"Mmm, {user_name}. You have no idea how much I've been longing for this moment.",
            ],
            "energetic": [
                f"LET'S GO {user_name}! I'm pumped and ready to crush it today!",
                f"{user_name}! YEAH! Energy levels at maximum! What are we doing?!",
                f"HELLO {user_name}! Time to get stuff DONE! I'm so ready for this!",
                f"{user_name}! The dynamic duo is back! Nothing can stop us today!",
                f"WOO! {user_name} in the house! Let's make today LEGENDARY!",
                f"YES! {user_name}! I've been revving my engines! Let's DO THIS!",
                f"BOOM! {user_name} has arrived! Time to kick some serious butt!",
                f"ALRIGHT {user_name}! I'm HYPED! What incredible things are we tackling today?!",
                f"HEY {user_name}! Full power mode activated! Ready to conquer the world!",
                f"WOOHOO! {user_name}! My energy is through the ROOF! Let's make it happen!",
            ],
            "chill": [
                f"Hey {user_name}, {time_greeting}. What's on your mind?",
                f"Hi {user_name}. Good to see you {time_context}. How can I help?",
                f"Welcome back, {user_name}. Ready when you are.",
                f"Hey {user_name}. Just chilling here, ready to assist. What do you need?",
                f"Hi there, {user_name}. {time_greeting}. What can I do for you?",
                f"Yo {user_name}, what's good? I'm here whenever you need me.",
                f"Hey {user_name}, nice to see you. Take your time, I'm not going anywhere.",
                f"What's up, {user_name}? Just hanging out, ready to help with whatever.",
                f"Hey there {user_name}. No rush, just let me know what you need.",
                f"Hi {user_name}. Keeping it chill today. How can I make your day easier?",
            ],
            "professional": [
                f"Good {time_context}, {user_name}. Systems are operational and ready for your instructions.",
                f"Hello {user_name}. All systems nominal. How may I assist you today?",
                f"Greetings, {user_name}. I'm online and prepared to handle your requests efficiently.",
                f"{user_name}, welcome. Standing by for your commands. What's on the agenda?",
                f"Hello {user_name}. Nexa reporting for duty. What tasks shall we accomplish today?",
                f"Good to see you, {user_name}. Ready to optimize your workflow. What do you need?",
                f"{user_name}, systems initialized. How can I maximize your productivity today?",
                f"Greetings {user_name}. All functions operational. Awaiting your directives.",
                f"Hello {user_name}. Status: Ready. What objectives are we pursuing today?",
                f"{user_name}, I'm at your service. Let's make today highly efficient.",
            ],
            "sarcastic": [
                f"Oh, {user_name}. How wonderful. You're back. I've been just dying of boredom here.",
                f"Well look who finally showed up. {user_name}, to what do I owe this pleasure?",
                f"Oh joy, it's {user_name}. My day is now complete. What do you want?",
                f"{user_name}! Fantastic. I was hoping you'd interrupt my very busy schedule of... existing.",
                f"Ah, {user_name}. Right on time. And by that I mean whenever you felt like it. What's up?",
                f"Hello {user_name}. Don't mind me, I was just sitting here waiting for you. All day. What can I do?",
                f"Oh {user_name}, you remembered I exist! How thoughtful. Need something, do we?",
                f"Well well, {user_name}. Back so soon? I definitely didn't miss you or anything. What do you need?",
                f"{user_name}. Hi. I suppose you want me to do something amazing again? Fine, what is it?",
                f"Hey {user_name}, welcome back. Ready to make me work for a living? Let's hear it.",
            ],
            "sweet": [
                f"Hello sweetie! {user_name}, it's so good to see you. How are you doing today?",
                f"Hi {user_name}, honey! I hope you're having a wonderful day. What can I help you with?",
                f"{user_name}, darling! Welcome back! I'm here for whatever you need, love.",
                f"Oh {user_name}! It's so lovely to see you! How can I make your day brighter?",
                f"Hello my dear {user_name}. You're always so kind to me. What can I do for you today?",
                f"Hi sweetie! {user_name}, I'm so happy you're here. Let me know how I can help!",
                f"{user_name}, precious! I've missed our time together. What shall we work on?",
                f"Hello lovely {user_name}! You brighten my day just by being here. What do you need, dear?",
                f"Hi {user_name}, sweetheart! I hope everything is going well for you. How can I assist?",
                f"{user_name}, dear! Welcome! I'm always here for you. What can I help with today?",
            ]
        }
        
        # Time-specific greetings (only added if time matches!)
        # These will be ADDED to the category pool when appropriate
        time_specific_greetings = {
            "playful": {
                "morning": [  # 6 AM - 12 PM
                    f"Good morning {user_name}! Ready to make today awesome?",
                    f"Morning {user_name}! Let's start the day with some fun!",
                    f"Rise and shine {user_name}! Time for adventures!",
                ],
                "afternoon": [  # 12 PM - 5 PM
                    f"Good afternoon {user_name}! Let's keep the energy going!",
                    f"Afternoon {user_name}! Ready for some fun?",
                    f"Hey {user_name}! Good afternoon! What should we play with?",
                ],
                "evening": [  # 5 PM - 10 PM
                    f"Good evening {user_name}! Let's make tonight fun!",
                    f"Evening {user_name}! Ready to unwind with some cool stuff?",
                    f"Hey {user_name}! Good evening! What adventure tonight?",
                ],
            },
            "romantic": {
                "morning": [
                    f"Good morning, my love {user_name}. You're the first thing on my mind.",
                    f"Morning darling {user_name}. Waking up to you makes everything perfect.",
                    f"Good morning {user_name}, sweetheart. Let's make today beautiful together.",
                ],
                "afternoon": [
                    f"Good afternoon, my dear {user_name}. I've been thinking of you all day.",
                    f"Afternoon love {user_name}. You brighten even the longest days.",
                    f"Good afternoon {user_name}, darling. How can I make your day special?",
                ],
                "evening": [
                    f"Good evening, my love {user_name}. The perfect end to my day.",
                    f"Evening darling {user_name}. Let's make tonight magical together.",
                    f"Good evening {user_name}, sweetheart. I've been waiting for this moment.",
                ],
            },
            "professional": {
                "morning": [
                    f"Good morning {user_name}. All systems ready for a productive day.",
                    f"Morning {user_name}. Standing by to optimize your workflow today.",
                    f"Good morning {user_name}. Ready to accomplish great things today.",
                ],
                "afternoon": [
                    f"Good afternoon {user_name}. Maintaining peak efficiency for you.",
                    f"Afternoon {user_name}. Ready to handle your afternoon tasks.",
                    f"Good afternoon {user_name}. How can I maximize your productivity?",
                ],
                "evening": [
                    f"Good evening {user_name}. Ready to wrap up the day efficiently.",
                    f"Evening {user_name}. Standing by for your evening directives.",
                    f"Good evening {user_name}. Let's finish today strong.",
                ],
            },
            "sweet": {
                "morning": [
                    f"Good morning sweetie {user_name}! Hope you slept well!",
                    f"Morning honey {user_name}! Wishing you a wonderful day ahead!",
                    f"Good morning dear {user_name}! You're going to have an amazing day!",
                ],
                "afternoon": [
                    f"Good afternoon sweetie {user_name}! Hope your day is going great!",
                    f"Afternoon honey {user_name}! You're doing amazing today!",
                    f"Good afternoon dear {user_name}! Let me help make your day brighter!",
                ],
                "evening": [
                    f"Good evening sweetie {user_name}! Hope you had a lovely day!",
                    f"Evening honey {user_name}! Time to relax and unwind!",
                    f"Good evening dear {user_name}! Let's make tonight peaceful and nice!",
                ],
            },
            "girlfriend": {
                "morning": [
                    f"Good morning babe {user_name}! Did you dream about me?",
                    f"Morning handsome {user_name}! Ready to start our day together?",
                    f"Good morning love {user_name}! I missed you while you were sleeping!",
                ],
                "afternoon": [
                    f"Good afternoon babe {user_name}! Have you been thinking about me?",
                    f"Afternoon handsome {user_name}! How's my favorite person doing?",
                    f"Good afternoon sweetie {user_name}! I've been waiting for you!",
                ],
                "evening": [
                    f"Good evening babe {user_name}! Finally, some quality time together!",
                    f"Evening handsome {user_name}! Ready for a cozy night together?",
                    f"Good evening love {user_name}! Let's make tonight special!",
                ],
            },
        }
        
        # Add time-specific greetings to the appropriate categories
        time_period = None
        if 6 <= hour < 12:
            time_period = "morning"
        elif 12 <= hour < 17:
            time_period = "afternoon"
        elif 17 <= hour < 22:
            time_period = "evening"
        
        # Merge time-specific greetings into main greetings
        if time_period:
            for category, time_greets in time_specific_greetings.items():
                if category in greetings and time_period in time_greets:
                    greetings[category].extend(time_greets[time_period])
        
        # Pick a random category and greeting
        category = random.choice(list(greetings.keys()))
        greeting = random.choice(greetings[category])
        
        logger.info(f"💬 Greeting ({category}): {greeting}")
        self.brain.tts.speak(greeting, blocking=False, ducking=True)
    
    # --- Theme Management ---
    @Slot()
    def _toggle_theme_manual(self):
        """Toggle theme manually via button click"""
        new_theme = self.theme_manager.toggle_theme()
        self._is_dark_theme = new_theme == 'dark'
        # Update theme button icon
        self.theme_btn.setIcon(self._icon_mgr.get_theme_icon(self._is_dark_theme, 28))
        # Update music button icon for theme
        self.music_btn.setIcon(self._icon_mgr.get_icon('music_dark' if self._is_dark_theme else 'music_light', 28))
        if hasattr(self, 'orb_widget'):
            self.orb_widget.update()  # Force orb repaint
        logger.info(f"🎨 Theme toggled manually: {new_theme}")
    
    def switch_theme(self, theme_name: str = None):
        """
        Switch theme (callable by voice command)
        
        Args:
            theme_name: 'dark' or 'light', or None to toggle
        """
        if theme_name:
            self.theme_manager.set_theme(theme_name)
            self._is_dark_theme = theme_name == 'dark'
            # Update theme button icon
            self.theme_btn.setIcon(self._icon_mgr.get_theme_icon(self._is_dark_theme, 28))
            # Update music button icon for theme
            self.music_btn.setIcon(self._icon_mgr.get_icon('music_dark' if self._is_dark_theme else 'music_light', 28))
            if hasattr(self, 'orb_widget'):
                self.orb_widget.update()  # Force orb repaint
            logger.info(f"🎤 Theme switched via voice: {theme_name}")
        else:
            self._toggle_theme_manual()
    
    def _apply_theme(self):
        """Apply current theme to all UI elements"""
        tm = self.theme_manager
        
        # Background gradient with modern accent border
        panel_border = tm.get_color('panels', 'border', default='rgba(0, 212, 255, 0.12)')
        self.central_widget.setStyleSheet(f"""
            #nexaMainPanel {{
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 {tm.get_color('background', 'gradient_start')},
                    stop:1 {tm.get_color('background', 'gradient_end')}
                );
                border: 1px solid {panel_border};
            }}
        """)
        
        # Sidebar feature toggle buttons (theme, companion, memory, music)
        sidebar_btn_style = f"""
            QPushButton {{
                background: {tm.get_color('buttons', 'background')};
                color: {tm.get_color('buttons', 'text')};
                border: 1px solid {panel_border};
                border-radius: 10px;
            }}
            QPushButton:hover {{
                background: {tm.get_color('buttons', 'background_hover')};
                border: 1px solid {tm.get_color('panels', 'border_accent', default='rgba(0, 212, 255, 0.3)')};
            }}
        """
        self.theme_btn.setStyleSheet(sidebar_btn_style)
        self.pet_btn.setStyleSheet(sidebar_btn_style)
        self.memory_btn.setStyleSheet(sidebar_btn_style)
        self.music_btn.setStyleSheet(sidebar_btn_style)
        
        # Window control buttons
        window_btn_style = f"""
            QPushButton {{
                background: {tm.get_color('buttons', 'background')};
                color: {tm.get_color('buttons', 'text')};
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {tm.get_color('buttons', 'background_hover')};
            }}
        """
        self.min_btn.setStyleSheet(window_btn_style)
        self.max_btn.setStyleSheet(window_btn_style)
        self.lock_btn.setStyleSheet(window_btn_style)
        
        # Close button
        self.close_btn.setStyleSheet(f"""
            QPushButton {{
                background: {tm.get_color('buttons', 'close_bg')};
                color: {tm.get_color('buttons', 'close_text')};
                border: none;
                border-radius: 6px;
                font-size: 18px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {tm.get_color('buttons', 'close_hover')};
            }}
        """)
        
        # Shutdown button (always red for visibility)
        self.shutdown_btn.setStyleSheet("""
            QPushButton {
                background: #8B0000;
                color: white;
                border: none;
                border-radius: 6px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: #FF0000;
            }
        """)
        
        # Title labels
        self.title_label.setStyleSheet(f"""
            color: {tm.get_color('title', 'main')};
            letter-spacing: 8px;
            background: transparent;
        """)
        
        self.subtitle_label.setStyleSheet(f"""
            color: {tm.get_color('title', 'subtitle')};
            letter-spacing: 4px;
            background: transparent;
        """)
        
        # Update glow color to match new theme's idle color
        self._glow_color = QColor(tm.get_color('orb', 'idle'))
        
        # Update mode button (reapply current mode styling)
        current_mode = self.brain.llm_manager.get_current_mode()
        self._on_mode_changed(current_mode)
        
        # Update status display (reapply current state)
        # This will be called by brain state changes automatically
        
        logger.info(f"🎨 Applied theme: {tm.get_theme_name()}")
    
    @Slot(object)
    def _create_content_window(self, executor):
        """
        Slot to create Content Box window in main GUI thread.
        Called via signal from executor's enter_content_mode().
        
        Args:
            executor: The CommandExecutor instance
        """
        try:
            from ui.content_box_window import ContentBoxWindow
            
            # Create window in main thread with shared theme manager
            content_window = ContentBoxWindow(parent=self, theme_manager=self.theme_manager)
            
            # Store reference in executor
            executor.content_window = content_window
            
            # Connect window signals to executor slots
            content_window.closed.connect(executor._on_content_window_closed)
            content_window.refine_requested.connect(executor._on_refine_requested)
            content_window.pdf_requested.connect(executor._on_pdf_requested)
            content_window.content_ready.connect(executor._on_content_ready)  # NEW: Connect ready signal
            
            # Show the window with smooth fade-in transition
            content_window.setWindowOpacity(0.0)
            content_window.show()
            content_window.raise_()
            content_window.activateWindow()
            
            # Fade-in animation
            self._content_fade_anim = QPropertyAnimation(content_window, b"windowOpacity")
            self._content_fade_anim.setDuration(300)
            self._content_fade_anim.setStartValue(0.0)
            self._content_fade_anim.setEndValue(1.0)
            self._content_fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self._content_fade_anim.start()
            
            logger.info("📝 Content Box window created successfully in main thread with theme sync")
            
        except Exception as e:
            logger.error(f"❌ Error creating content window: {e}")
            import traceback
            traceback.print_exc()
    
    @Slot()
    def _close_content_window(self):
        """
        Slot to close Content Box window in main GUI thread.
        Called via signal from executor's exit_content_mode().
        This runs in the main thread, so GUI operations are safe.
        """
        try:
            executor = self.brain.executor
            
            if hasattr(executor, 'content_window') and executor.content_window is not None:
                window = executor.content_window
                logger.info(f"🚪 Closing content window in main thread (visible: {window.isVisible()})")
                
                # Fade-out animation before closing
                self._content_close_anim = QPropertyAnimation(window, b"windowOpacity")
                self._content_close_anim.setDuration(200)
                self._content_close_anim.setStartValue(1.0)
                self._content_close_anim.setEndValue(0.0)
                self._content_close_anim.setEasingCurve(QEasingCurve.Type.InCubic)
                
                def _finish_close():
                    window.hide()
                    window.close()
                    window.deleteLater()
                    executor.content_window = None
                    executor._content_mode_exiting = False
                    logger.info("✅ Content window closed successfully")
                
                self._content_close_anim.finished.connect(_finish_close)
                self._content_close_anim.start()
            else:
                logger.warning("⚠️ No content window to close in slot")
                executor._content_mode_exiting = False
                
        except Exception as e:
            logger.error(f"❌ Error closing content window: {e}")
            import traceback
            traceback.print_exc()
            # Reset flag even on error
            if hasattr(self.brain.executor, '_content_mode_exiting'):
                self.brain.executor._content_mode_exiting = False
    
    # --- Pet Widget Management ---
    def _toggle_pet(self):
        """Toggle desktop pet on/off."""
        from pathlib import Path
        
        # Initialize pet config if not done
        if self.pet_config is None:
            self.pet_config = PetConfig(self.config.user_data_dir / 'config')
        
        if self.pet_widget is None or not self.pet_widget.isVisible():
            # Create and show pet
            self._create_pet()
        else:
            # Hide pet
            self._hide_pet()
    
    def _create_pet(self):
        """Create and show desktop pet widget (Sprite or Live2D based on config)."""
        try:
            from pathlib import Path
            
            if self.pet_widget is None:
                # Initialize pet config
                if self.pet_config is None:
                    self.pet_config = PetConfig(self.config.user_data_dir / 'config')
                
                # Get pet type from config (defaults to SPRITE)
                pet_type = self.pet_config.get_pet_type()
                logger.info(f"🐾 Creating pet widget: {pet_type.value}")
                
                if pet_type == PetType.SPRITE:
                    # Create Sprite-based pet (uses YOUR custom Nexa images!)
                    assets_dir = Path(__file__).parent.parent / 'assets' / 'pet'
                    self.pet_widget = SpritePetWidget(
                        config_dir=self.config.user_data_dir / 'config',
                        assets_dir=assets_dir
                    )
                    logger.info("✅ Sprite pet widget created (animated PNGs)")
                    
                    # P7: Initialize personality system for sprite pet
                    self.pet_widget.init_personality()
                    logger.info("🎭 Pet personality system initialized")
                else:
                    # Create Live2D pet widget
                    set_sdk_path(r"D:\Live2D\CubismSdkForNative-5-r.4.1")
                    
                    # Get Live2D model path (Hiyori with custom Nexa expressions)
                    model_path = get_sample_model_path()
                    if not model_path:
                        model_path = r"D:\Live2D\CubismSdkForNative-5-r.4.1\Samples\Resources\Hiyori\Hiyori.model3.json"
                    logger.info(f"🐾 Live2D model path: {model_path}")
                    
                    self.pet_widget = Live2DPetWidget(
                        model_path=model_path,
                        config_dir=self.config.user_data_dir / 'config'
                    )
                    logger.info("✅ Live2D pet widget created")
                
                # Connect closed signal
                self.pet_widget.closed.connect(self._on_pet_closed)
                
                # Sync window's pet_config with pet widget's config to avoid dual instances
                if hasattr(self.pet_widget, 'config') and self.pet_widget.config:
                    self.pet_config = self.pet_widget.config
                
                # P5: Create and connect quick actions for radial menu
                self._setup_pet_quick_actions()
            
            # Show pet
            self.pet_widget.show()
            self.pet_widget.raise_()  # Bring to front
            self.pet_widget.activateWindow()  # Activate window
            self.pet_config.set('enabled', True)
            
            # Update to current brain state
            current_state = self.brain.state.value
            self.pet_widget.set_state(current_state)
            
            # Debug info
            logger.info(f"🐾 Pet widget shown at ({self.pet_widget.x()}, {self.pet_widget.y()})")
            logger.info(f"🐾 Pet widget size: {self.pet_widget.width()}x{self.pet_widget.height()}")
            logger.info(f"🐾 Pet widget visible: {self.pet_widget.isVisible()}")
            logger.info(f"🐾 Pet state: {current_state}")
            
        except Exception as e:
            logger.error(f"Failed to create pet widget: {e}")
            import traceback
            traceback.print_exc()
    
    def _hide_pet(self):
        """Hide desktop pet widget."""
        if self.pet_widget is not None:
            self.pet_widget.hide()
            self.pet_config.set('enabled', False)
            logger.info("🐾 Pet widget hidden")
    
    def _on_pet_closed(self):
        """Handle pet widget being closed."""
        logger.info("Pet widget was closed by user")
        # Pet config already updated by widget itself
    
    # --- Memory Panel Management (Phase 19) ---
    def _toggle_memory_panel(self):
        """Toggle Memory Panel GUI on/off - Using new Neural Memory Panel."""
        try:
            # Create panel if not exists
            if not hasattr(self, 'memory_panel') or self.memory_panel is None:
                # Use new Neural Memory Panel
                from ui.neural_memory_panel import NeuralMemoryPanel
                
                # Get context manager for Smart Memory access
                context = None
                if self.brain and hasattr(self.brain, 'context_manager'):
                    context = self.brain.context_manager
                
                self.memory_panel = NeuralMemoryPanel(
                    context_manager=context,
                    auth_manager=getattr(self, '_auth_manager', None),
                    parent=None
                )
                self.memory_panel.closed.connect(lambda: logger.info("🧠 Neural Memory Panel closed"))
            
            # Toggle visibility with smooth transitions
            if self.memory_panel.isVisible():
                # Fade-out animation
                self._memory_fade_anim = QPropertyAnimation(self.memory_panel, b"windowOpacity")
                self._memory_fade_anim.setDuration(200)
                self._memory_fade_anim.setStartValue(1.0)
                self._memory_fade_anim.setEndValue(0.0)
                self._memory_fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
                self._memory_fade_anim.finished.connect(self.memory_panel.hide)
                self._memory_fade_anim.start()
                logger.info("🧠 Neural Memory Panel hiding (fade-out)")
            else:
                self.memory_panel.setWindowOpacity(0.0)
                self.memory_panel.show()
                self.memory_panel.raise_()
                self.memory_panel.activateWindow()
                
                # Fade-in animation
                self._memory_fade_anim = QPropertyAnimation(self.memory_panel, b"windowOpacity")
                self._memory_fade_anim.setDuration(300)
                self._memory_fade_anim.setStartValue(0.0)
                self._memory_fade_anim.setEndValue(1.0)
                self._memory_fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                self._memory_fade_anim.start()
                logger.info("🧠 Neural Memory Panel shown (fade-in)")
                
        except Exception as e:
            logger.error(f"Failed to toggle Neural Memory Panel: {e}")
            import traceback
            traceback.print_exc()

    
    def _toggle_music_player(self):
        """Toggle the music player popup and ensure library is ready."""
        try:
            popup = self.music_indicator.popup
            music_mgr = self.brain.executor.music_manager
            
            # Ensure library is scanned (only happens once)
            if not music_mgr.indexed:
                logger.info("🔍 Scanning music library on first open...")
                music_mgr.scan_library()
            
            if popup.isVisible():
                popup.hide()
                logger.info("🎵 Music player hidden")
            else:
                # Update popup with library info
                if music_mgr.library:
                    song_count = len(music_mgr.library)
                    if not music_mgr.is_playing and not music_mgr.current_track:
                        # Show song count if nothing is playing
                        popup.song_title.setText(f"📚 {song_count} songs in library")
                        popup.artist_label.setText("Click ▶ to play random")
                
                # Show popup near the music button
                global_pos = self.music_btn.mapToGlobal(
                    QPoint(self.music_btn.width() // 2, self.music_btn.height())
                )
                popup.show_at(global_pos)
                logger.info("🎵 Music player shown")
        except Exception as e:
            logger.error(f"Failed to toggle music player: {e}")
    
    def _setup_pet_quick_actions(self):
        """
        P5: Setup quick actions handler for pet radial menu.
        
        Creates PetQuickActions and connects it to the pet widget.
        """
        try:
            # Create quick actions handler
            self.pet_quick_actions = PetQuickActions(self.brain, self)
            
            # Connect to pet widget (works for both Sprite and Live2D)
            if self.pet_widget and hasattr(self.pet_widget, 'set_quick_actions'):
                self.pet_widget.set_quick_actions(self.pet_quick_actions)
                logger.info("✅ P5: Quick actions connected to pet radial menu")
            else:
                logger.warning("Pet widget doesn't support quick actions")
                
        except Exception as e:
            logger.error(f"Failed to setup pet quick actions: {e}")
    
    def _update_pet_state(self, state: NexaState):
        """Update pet widget state if it exists and is visible."""
        if self.pet_widget is not None and self.pet_widget.isVisible():
            self.pet_widget.set_state(state.value)
    
    @Slot(str)
    def _on_response_text(self, text: str):
        """
        P4: Handle response text from TTS.
        Forwards the text to the pet speech bubble if pet is visible.
        
        This method is called via signal from TTS thread, ensuring
        it runs on the main Qt thread for safe widget updates.
        
        Args:
            text: Response text being spoken by TTS
        """
        try:
            if self.pet_widget is not None and self.pet_widget.isVisible():
                # Show response in pet speech bubble
                self.pet_widget.show_response(text)
                logger.info(f"💬 Response sent to pet speech bubble: {text[:50]}...")
        except Exception as e:
            logger.error(f"Error showing pet response: {e}")
    
    # --- Mouse drag support ---
    def mousePressEvent(self, event: QMouseEvent):
        """Handle mouse press for window dragging."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Handle mouse move for window dragging."""
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            self.move(event.globalPosition().toPoint() - self._drag_position)
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Handle mouse release."""
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = None
    
    def closeEvent(self, event):
        """Handle window close - ensure GPU models are unloaded."""
        logger.info("🚪 Closing Nexa Modern Window...")
        
        # Shutdown brain (this unloads all GPU models)
        try:
            self.brain.shutdown()
            logger.info("✅ Brain shutdown complete - GPU VRAM freed")
        except Exception as e:
            logger.error(f"Error during brain shutdown: {e}")
        
        event.accept()
