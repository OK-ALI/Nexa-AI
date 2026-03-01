"""
Music Indicator Widget - Shows current music playback state
Features:
- Animated music visualizer bars
- Song name display
- Theme-aware styling with glassmorphism
- Show/hide animations
- Modern popup music player with full controls
- PNG icon support for all controls
"""

import logging
import random
from pathlib import Path
from typing import Dict, Optional
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, 
    QFrame, QSlider, QGraphicsDropShadowEffect, QGraphicsBlurEffect
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve, QPoint, Property, QSize
from PySide6.QtGui import QPainter, QColor, QLinearGradient, QPainterPath, QIcon, QPixmap
from Themes.theme_manager import get_theme_manager

logger = logging.getLogger(__name__)


class MusicIconManager:
    """
    Manages all NEXA icons with caching and theme support.
    Loads PNG icons from music_player_required_icons and other_icons folders.
    """
    
    # Path to icons directories
    ICONS_DIR = Path(__file__).parent.parent / "music_player_required_icons"
    OTHER_ICONS_DIR = Path(__file__).parent.parent / "other_icons"
    
    # Icon file mappings - music player icons
    ICON_FILES = {
        'play': 'play_button.png',
        'pause': 'pause-button.png',
        'stop': 'stop.png',
        'previous': 'back.png',
        'next': 'next.png',
        'shuffle': 'shuffle.png',
        'random': 'random.png',
        'repeat_off': 'repeat_off.png',
        'repeat_one': 'repeat-once.png',
        'repeat_all': 'repeat_all.png',
        'volume': 'volume.png',
        'mute': 'mute.png',
        'music_dark': 'music_dark_mode_icon.png',
        'music_light': 'music_light_mode_icon.png',
        'wave_dark': 'sound_wave_dark_mode.png',
        'wave_light': 'sound_wave_light_mode.png',
        'library': 'music_library.png',
        'playlist': 'playlist.png',
        'album_art': 'album_art.png',
        'equalizer': 'equalizer.png',
    }
    
    # Other icons mappings (from other_icons folder)
    OTHER_ICON_FILES = {
        # Theme icons
        'theme_dark': 'dark_theme.png',
        'theme_light': 'light_theme.png',
        # Mic icons
        'mic_on': 'mic_on.png',
        'mic_off': 'mic_off.png',
        # Panel icons
        'memory': 'neural_network_memory.png',
        'assistant': 'secretary_assistant.png',
        'settings': 'settings.png',
        'switch_off': 'switch_off.png',
        # Radial menu icons
        'capture': 'capture.png',           # Screenshot
        'share': 'share.png',               # Share/Copy
        'mode': 'mode_toggle.png',          # Online/Offline mode
        'sleep': 'sleep_zzz.png',           # Sleep mode
        'wake': 'wake.gif',                 # Wake up (animated)
        'content': 'content.png',           # Content mode
        'exit': 'exit_sign.png',            # Exit app
        'shutdown': 'switch_off.png',       # Shutdown/power off
        'assistant_anim': 'virtual_assistant.gif',  # Animated assistant
        # Memory panel icons
        'conversation': 'conversation.png', # Chat/conversation type
        'lightning': 'lightning.png',       # Skills/power
        'thought': 'thought.png',           # Thought bubble
        'favourite': 'favourite.png',       # Star/favorite
        'close': 'close.png',               # Close/X button
        'trash': 'trash-bin.png',           # Delete/clear
        'clock': 'clock.png',               # Timestamp
        'warning': 'warning.png',           # Warning/alert
        'search': 'search.png',             # Search
        'sparkle': 'sparkle.png',           # Decorative sparkle
        'check': 'check.png',               # Success/ready
        'copy': 'copy.png',                 # Copy to clipboard
        'paste': 'paste.png',               # Paste from clipboard
        'download': 'download.png',         # Download (YouTube downloads)
        # Button action icons (aliases/reuses)
        'edit': 'settings.png',             # Edit (reuse settings)
        'export': 'share.png',              # Export (reuse share)
        'pin': 'favourite.png',             # Pin (reuse favourite)
        'guide': 'user-guide.png',          # Guidelines/help
    }
    
    # Singleton instance
    _instance: Optional['MusicIconManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._icon_cache: Dict[str, QIcon] = {}
        self._pixmap_cache: Dict[str, QPixmap] = {}
        logger.info(f"🎵 MusicIconManager initialized. Icons dir: {self.ICONS_DIR}")
    
    def get_icon(self, name: str, size: int = 24) -> QIcon:
        """
        Get a QIcon for the specified icon name.
        
        Args:
            name: Icon name from ICON_FILES keys
            size: Icon size (used for cache key)
            
        Returns:
            QIcon object (empty if icon not found)
        """
        cache_key = f"{name}_{size}"
        
        if cache_key not in self._icon_cache:
            pixmap = self.get_pixmap(name, size)
            self._icon_cache[cache_key] = QIcon(pixmap)
        
        return self._icon_cache[cache_key]
    
    def get_pixmap(self, name: str, size: int = 24) -> QPixmap:
        """
        Get a QPixmap for the specified icon name with high-DPI support.
        
        Args:
            name: Icon name from ICON_FILES keys
            size: Desired logical size (will scale for high-DPI displays)
            
        Returns:
            QPixmap object (empty if icon not found)
        """
        # Get device pixel ratio for high-DPI support
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        device_ratio = app.devicePixelRatio() if app else 1.0
        
        # Scale size for high-DPI (render at 2x or 3x for crisp icons)
        render_size = int(size * device_ratio)
        cache_key = f"{name}_{render_size}"
        
        if cache_key not in self._pixmap_cache:
            # Check music icons first, then other icons
            filename = self.ICON_FILES.get(name)
            icon_path = None
            
            if filename:
                icon_path = self.ICONS_DIR / filename
            else:
                # Check other icons
                filename = self.OTHER_ICON_FILES.get(name)
                if filename:
                    icon_path = self.OTHER_ICONS_DIR / filename
            
            if not filename or not icon_path:
                logger.warning(f"⚠️ Unknown icon name: {name}")
                return QPixmap()
            
            if not icon_path.exists():
                logger.warning(f"⚠️ Icon file not found: {icon_path}")
                return QPixmap()
            
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                # Scale to render size (larger for high-DPI) with best quality
                pixmap = pixmap.scaled(
                    render_size, render_size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                # Set device pixel ratio so Qt knows this is a high-DPI image
                pixmap.setDevicePixelRatio(device_ratio)
                self._pixmap_cache[cache_key] = pixmap
                logger.debug(f"📷 Loaded icon: {name} ({size}px @ {device_ratio}x)")
            else:
                logger.warning(f"⚠️ Failed to load icon: {icon_path}")
                return QPixmap()
        
        return self._pixmap_cache[cache_key]
    
    def get_music_icon(self, is_dark_theme: bool) -> QIcon:
        """Get theme-appropriate music note icon."""
        return self.get_icon('music_dark' if is_dark_theme else 'music_light', 20)
    
    def get_music_pixmap(self, is_dark_theme: bool, size: int = 20) -> QPixmap:
        """Get theme-appropriate music note pixmap."""
        return self.get_pixmap('music_dark' if is_dark_theme else 'music_light', size)
    
    def get_theme_icon(self, is_dark_theme: bool, size: int = 22) -> QIcon:
        """Get theme toggle icon (sun for dark mode, moon for light mode)."""
        return self.get_icon('theme_light' if is_dark_theme else 'theme_dark', size)
    
    def get_assistant_icon(self, size: int = 22) -> QIcon:
        """Get assistant/pet icon."""
        return self.get_icon('assistant', size)
    
    def get_memory_icon(self, size: int = 22) -> QIcon:
        """Get memory panel icon."""
        return self.get_icon('memory', size)
    
    def get_mic_icon(self, is_on: bool, size: int = 22) -> QIcon:
        """Get microphone icon based on state."""
        return self.get_icon('mic_on' if is_on else 'mic_off', size)
    
    def get_settings_icon(self, size: int = 22) -> QIcon:
        """Get settings icon."""
        return self.get_icon('settings', size)
    
    def clear_cache(self):
        """Clear all cached icons and pixmaps."""
        self._icon_cache.clear()
        self._pixmap_cache.clear()
        logger.info("🗑️ Icon cache cleared")


# Global icon manager instance
def get_icon_manager() -> MusicIconManager:
    """Get the global MusicIconManager instance."""
    return MusicIconManager()


class MusicVisualizerWidget(QWidget):
    """Mini music visualizer with animated bars"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.bars = [0.2, 0.4, 0.6, 0.8, 0.6, 0.4, 0.2, 0.3]  # 8 bars
        self.bar_width = 3
        self.bar_spacing = 2
        self.max_height = 16
        self.animating = False
        
        # Theme manager
        self.theme_manager = get_theme_manager()
        
        # Animation timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_bars)
        
        # Set fixed size
        total_width = (self.bar_width + self.bar_spacing) * len(self.bars)
        self.setFixedSize(total_width, self.max_height)
    
    def start_animation(self):
        """Start the bar animation"""
        self.animating = True
        self.timer.start(100)  # Update every 100ms
    
    def stop_animation(self):
        """Stop the bar animation"""
        self.animating = False
        self.timer.stop()
        self.bars = [0.2] * len(self.bars)
        self.update()
    
    def update_bars(self):
        """Update bar heights with smooth random changes"""
        if self.animating:
            for i in range(len(self.bars)):
                # Random walk - smooth changes
                change = random.uniform(-0.15, 0.15)
                self.bars[i] = max(0.1, min(1.0, self.bars[i] + change))
            self.update()
    
    def paintEvent(self, event):
        """Draw the animated bars"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get theme color
        color_hex = self.theme_manager.get_color('music_indicator', 'visualizer')
        color = QColor(color_hex) if self.animating else QColor("#666666")
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)
        
        x = 0
        for height_ratio in self.bars:
            height = int(self.max_height * height_ratio)
            y = self.max_height - height
            
            # Draw rounded rectangle bar
            painter.drawRoundedRect(x, y, self.bar_width, height, 1, 1)
            x += self.bar_width + self.bar_spacing


class MusicPlayerPopup(QFrame):
    """
    Modern glassmorphism popup music player with full controls.
    Features beautiful gradients, blur effects, and theme-aware styling.
    """
    
    # Control signals (connect to music manager)
    play_pause_clicked = Signal()
    stop_clicked = Signal()
    random_clicked = Signal()
    next_clicked = Signal()
    previous_clicked = Signal()
    shuffle_clicked = Signal()
    repeat_clicked = Signal()
    volume_changed = Signal(int)
    close_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self._apply_theme)
        
        self._is_playing = False
        self._shuffle_enabled = False
        self._repeat_mode = 'off'  # 'off', 'one', 'all'
        self._is_dark_theme = True
        
        self._setup_ui()
        self._apply_theme()
        self.hide()
        
        # Window flags for popup behavior
        self.setWindowFlags(Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        logger.info("✅ MusicPlayerPopup initialized with modern design")
    
    def _setup_ui(self):
        """Setup compact modern popup UI with PNG icons"""
        self.setFixedSize(280, 220)
        
        # Get icon manager
        self.icon_manager = get_icon_manager()
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 10, 12, 10)
        main_layout.setSpacing(6)
        
        # Compact header with library icon and song info
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        
        # Library icon (shows when no song playing)
        self.library_icon = QLabel()
        self.library_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.library_icon.setPixmap(self.icon_manager.get_pixmap('library', 40))
        self.library_icon.setFixedHeight(44)
        header_layout.addWidget(self.library_icon)
        
        # Song info layout
        song_layout = QVBoxLayout()
        song_layout.setSpacing(2)
        
        self.song_title = QLabel("No song playing")
        self.song_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.song_title.setWordWrap(True)
        self.song_title.setMaximumHeight(36)
        song_layout.addWidget(self.song_title)
        
        self.artist_label = QLabel("—")
        self.artist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        song_layout.addWidget(self.artist_label)
        
        header_layout.addLayout(song_layout)
        main_layout.addLayout(header_layout)
        
        # Compact visualizer
        viz_container = QWidget()
        viz_layout = QHBoxLayout(viz_container)
        viz_layout.setContentsMargins(0, 2, 0, 2)
        viz_layout.addStretch()
        self.popup_visualizer = MusicVisualizerWidget()
        self.popup_visualizer.max_height = 14
        self.popup_visualizer.setFixedSize(70, 14)
        viz_layout.addWidget(self.popup_visualizer)
        viz_layout.addStretch()
        main_layout.addWidget(viz_container)
        
        # Main control buttons row
        controls_layout = QHBoxLayout()
        controls_layout.setSpacing(6)
        controls_layout.addStretch()
        
        # Shuffle button - with PNG icon
        self.shuffle_btn = QPushButton()
        self.shuffle_btn.setIcon(self.icon_manager.get_icon('shuffle', 24))
        self.shuffle_btn.setIconSize(QSize(24, 24))
        self.shuffle_btn.setFixedSize(30, 30)
        self.shuffle_btn.setObjectName("smallBtn")
        self.shuffle_btn.clicked.connect(self._on_shuffle)
        self.shuffle_btn.setToolTip("Shuffle")
        self.shuffle_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_layout.addWidget(self.shuffle_btn)
        
        # Previous button - with PNG icon
        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(self.icon_manager.get_icon('previous', 26))
        self.prev_btn.setIconSize(QSize(26, 26))
        self.prev_btn.setFixedSize(34, 34)
        self.prev_btn.setObjectName("controlBtn")
        self.prev_btn.clicked.connect(lambda: self.previous_clicked.emit())
        self.prev_btn.setToolTip("Previous")
        self.prev_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_layout.addWidget(self.prev_btn)
        
        # Play/Pause button - prominent with PNG icon
        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.icon_manager.get_icon('play', 36))
        self.play_btn.setIconSize(QSize(36, 36))
        self.play_btn.setFixedSize(46, 46)
        self.play_btn.setObjectName("playBtn")
        self.play_btn.clicked.connect(self._on_play_pause)
        self.play_btn.setToolTip("Play/Pause")
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_layout.addWidget(self.play_btn)
        
        # Stop button - with PNG icon
        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(self.icon_manager.get_icon('stop', 26))
        self.stop_btn.setIconSize(QSize(26, 26))
        self.stop_btn.setFixedSize(34, 34)
        self.stop_btn.setObjectName("stopBtn")
        self.stop_btn.clicked.connect(lambda: self.stop_clicked.emit())
        self.stop_btn.setToolTip("Stop")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_layout.addWidget(self.stop_btn)
        
        # Next button - with PNG icon
        self.next_btn = QPushButton()
        self.next_btn.setIcon(self.icon_manager.get_icon('next', 26))
        self.next_btn.setIconSize(QSize(26, 26))
        self.next_btn.setFixedSize(34, 34)
        self.next_btn.setObjectName("controlBtn")
        self.next_btn.clicked.connect(lambda: self.next_clicked.emit())
        self.next_btn.setToolTip("Next")
        self.next_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_layout.addWidget(self.next_btn)
        
        # Repeat button - with PNG icon
        self.repeat_btn = QPushButton()
        self.repeat_btn.setIcon(self.icon_manager.get_icon('repeat_off', 24))
        self.repeat_btn.setIconSize(QSize(24, 24))
        self.repeat_btn.setFixedSize(30, 30)
        self.repeat_btn.setObjectName("smallBtn")
        self.repeat_btn.clicked.connect(self._on_repeat)
        self.repeat_btn.setToolTip("Repeat")
        self.repeat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        controls_layout.addWidget(self.repeat_btn)
        
        controls_layout.addStretch()
        main_layout.addLayout(controls_layout)
        
        # Secondary row: Random button + Volume
        secondary_layout = QHBoxLayout()
        secondary_layout.setSpacing(8)
        
        # Random button - with PNG icon
        self.random_btn = QPushButton()
        self.random_btn.setIcon(self.icon_manager.get_icon('random', 20))
        self.random_btn.setIconSize(QSize(20, 20))
        self.random_btn.setFixedSize(28, 28)
        self.random_btn.setObjectName("randomBtn")
        self.random_btn.clicked.connect(lambda: self.random_clicked.emit())
        self.random_btn.setToolTip("Play Random Song")
        self.random_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        secondary_layout.addWidget(self.random_btn)
        
        # Volume icon - using QLabel with pixmap
        self.volume_icon = QLabel()
        self.volume_icon.setPixmap(self.icon_manager.get_pixmap('volume', 16))
        self.volume_icon.setFixedSize(18, 18)
        self._is_muted = False
        secondary_layout.addWidget(self.volume_icon)
        
        # Volume slider
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(50)
        self.volume_slider.setFixedHeight(12)
        self.volume_slider.valueChanged.connect(self._on_volume_changed)
        self.volume_slider.setToolTip("Volume")
        self.volume_slider.setCursor(Qt.CursorShape.PointingHandCursor)
        secondary_layout.addWidget(self.volume_slider)
        
        # Volume percentage
        self.volume_label = QLabel("50%")
        self.volume_label.setFixedWidth(28)
        secondary_layout.addWidget(self.volume_label)
        
        main_layout.addLayout(secondary_layout)
        
        # Subtle shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
    
    def _on_volume_changed(self, value: int):
        """Handle volume slider change and update icon"""
        self.volume_label.setText(f"{value}%")
        self.volume_changed.emit(value)
        
        # Update volume icon based on mute state
        new_muted = value == 0
        if new_muted != self._is_muted:
            self._is_muted = new_muted
            icon_name = 'mute' if new_muted else 'volume'
            self.volume_icon.setPixmap(self.icon_manager.get_pixmap(icon_name, 16))
    
    def _apply_theme(self):
        """Apply compact modern theme styling"""
        tm = self.theme_manager
        current_theme = tm.get_theme_name()
        self._is_dark_theme = current_theme == 'dark'
        
        accent = tm.get_color('music_indicator', 'visualizer')
        text_primary = tm.get_color('text', 'primary')
        text_secondary = tm.get_color('text', 'secondary')
        
        if self._is_dark_theme:
            bg_main = "rgba(12, 16, 28, 0.96)"
            border_color = "rgba(0, 212, 255, 0.25)"
            btn_bg = "rgba(255, 255, 255, 0.08)"
            btn_hover = "rgba(0, 212, 255, 0.25)"
            slider_groove = "rgba(255, 255, 255, 0.12)"
            stop_color = "#FF5555"
        else:
            bg_main = "rgba(255, 255, 255, 0.96)"
            border_color = "rgba(0, 136, 204, 0.3)"
            btn_bg = "rgba(0, 136, 204, 0.08)"
            btn_hover = "rgba(0, 136, 204, 0.2)"
            slider_groove = "rgba(0, 0, 0, 0.08)"
            stop_color = "#DD3333"
        
        self.setStyleSheet(f"""
            MusicPlayerPopup {{
                background: {bg_main};
                border-radius: 12px;
                border: 1px solid {border_color};
            }}
            QLabel {{
                color: {text_primary};
                background: transparent;
                font-family: 'Segoe UI', sans-serif;
            }}
            QPushButton#smallBtn {{
                background: {btn_bg};
                border: none;
                border-radius: 13px;
                color: {text_secondary};
                font-size: 11px;
                font-weight: 600;
            }}
            QPushButton#smallBtn:hover {{
                background: {btn_hover};
                color: {accent};
            }}
            QPushButton#controlBtn {{
                background: {btn_bg};
                border: none;
                border-radius: 15px;
                color: {text_secondary};
                font-size: 10px;
                font-weight: bold;
                letter-spacing: -2px;
            }}
            QPushButton#controlBtn:hover {{
                background: {btn_hover};
                color: {accent};
            }}
            QPushButton#playBtn {{
                background: {accent};
                border: none;
                border-radius: 19px;
                color: {'#0A0F19' if self._is_dark_theme else '#FFFFFF'};
                font-size: 14px;
            }}
            QPushButton#playBtn:hover {{
                background: {accent}DD;
            }}
            QPushButton#playBtn:pressed {{
                background: {accent}AA;
            }}
            QPushButton#stopBtn {{
                background: {btn_bg};
                border: none;
                border-radius: 15px;
                color: {stop_color};
                font-size: 10px;
            }}
            QPushButton#stopBtn:hover {{
                background: rgba(255, 85, 85, 0.2);
                color: {stop_color};
            }}
            QPushButton#randomBtn {{
                background: {btn_bg};
                border: none;
                border-radius: 10px;
                color: {text_secondary};
                font-size: 11px;
            }}
            QPushButton#randomBtn:hover {{
                background: {btn_hover};
                color: {accent};
            }}
            QSlider::groove:horizontal {{
                background: {slider_groove};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {accent};
                width: 10px;
                height: 10px;
                margin: -3px 0;
                border-radius: 5px;
            }}
            QSlider::sub-page:horizontal {{
                background: {accent};
                border-radius: 2px;
            }}
        """)
        
        # Song title - compact
        self.song_title.setStyleSheet(f"""
            font-size: 12px; 
            font-weight: 600; 
            color: {text_primary};
        """)
        
        # Artist label - subtle
        self.artist_label.setStyleSheet(f"""
            font-size: 10px; 
            color: {text_secondary};
        """)
        
        # Volume label & icon
        self.volume_label.setStyleSheet(f"font-size: 9px; color: {text_secondary};")
        self.volume_icon.setStyleSheet(f"font-size: 11px; color: {text_secondary};")
    
    def set_song_info(self, title: str, artist: str = ""):
        """Update the song info display"""
        self.song_title.setText(title if title else "No song playing")
        self.artist_label.setText(artist if artist else "—")
        
        # Update visualizer state
        if title:
            self.popup_visualizer.start_animation()
        else:
            self.popup_visualizer.stop_animation()
    
    def set_playing(self, is_playing: bool):
        """Update play/pause button state with PNG icons"""
        self._is_playing = is_playing
        icon_name = 'pause' if is_playing else 'play'
        self.play_btn.setIcon(self.icon_manager.get_icon(icon_name, 36))
        
        if is_playing:
            self.popup_visualizer.start_animation()
        else:
            self.popup_visualizer.stop_animation()
    
    def set_shuffle(self, enabled: bool):
        """Update shuffle button state"""
        self._shuffle_enabled = enabled
        accent = self.theme_manager.get_color('music_indicator', 'visualizer')
        if enabled:
            self.shuffle_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {accent};
                    color: {'#0A0F19' if self._is_dark_theme else '#FFFFFF'};
                    border: none;
                    border-radius: 14px;
                    font-size: 12px;
                }}
            """)
        else:
            self._apply_theme()
    
    def set_repeat_mode(self, mode: str):
        """Update repeat button state with PNG icons ('off', 'one', 'all')"""
        self._repeat_mode = mode
        icon_names = {'off': 'repeat_off', 'one': 'repeat_one', 'all': 'repeat_all'}
        self.repeat_btn.setIcon(self.icon_manager.get_icon(icon_names.get(mode, 'repeat_off'), 24))
        accent = self.theme_manager.get_color('music_indicator', 'visualizer')
        if mode != 'off':
            self.repeat_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {accent};
                    border: none;
                    border-radius: 14px;
                }}
            """)
        else:
            self._apply_theme()
    
    def set_volume(self, level: int):
        """Update volume slider without triggering signal"""
        self.volume_slider.blockSignals(True)
        self.volume_slider.setValue(level)
        self.volume_slider.blockSignals(False)
        self.volume_label.setText(f"{level}%")
    
    def _on_play_pause(self):
        """Handle play/pause click"""
        self.play_pause_clicked.emit()
    
    def _on_shuffle(self):
        """Handle shuffle click"""
        self.shuffle_clicked.emit()
    
    def _on_repeat(self):
        """Handle repeat click"""
        self.repeat_clicked.emit()
    
    def show_at(self, pos: QPoint):
        """Show popup to the RIGHT of the button (for vertical sidebar)"""
        # Position popup to the right of the button with some offset
        adjusted_pos = QPoint(pos.x() + 10, pos.y() - self.height() // 2)
        self.move(adjusted_pos)
        self.show()
        logger.info("🎵 Music player popup shown to the right of button")
    
    def hideEvent(self, event):
        """Handle hide event"""
        self.close_requested.emit()
        super().hideEvent(event)


class MusicIndicatorWidget(QWidget):
    """
    Complete music indicator widget.
    Shows music icon, visualizer bars, and current song name.
    Clicking opens a popup music player with full controls.
    """
    
    # Signals
    clicked = Signal()  # Emitted when widget is clicked
    
    # Control signals (forwarded from popup)
    play_pause_requested = Signal()
    stop_requested = Signal()
    random_requested = Signal()
    next_requested = Signal()
    previous_requested = Signal()
    shuffle_requested = Signal()
    repeat_requested = Signal()
    volume_requested = Signal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self._apply_theme)
        
        self._current_song = ""
        self._current_artist = ""
        self._is_playing = False
        
        self._setup_ui()
        self._setup_popup()
        self._apply_theme()
        self.hide()  # Hidden by default
        
        logger.info("✅ MusicIndicatorWidget initialized with popup player")
    
    def _setup_ui(self):
        """Setup the music indicator UI with PNG icons"""
        self.icon_manager = get_icon_manager()
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        
        # Music icon - using PNG
        self.icon = QLabel()
        self.icon.setFixedSize(20, 20)
        self.icon.setStyleSheet("background: transparent;")
        layout.addWidget(self.icon)
        
        # Visualizer bars
        self.visualizer = MusicVisualizerWidget()
        layout.addWidget(self.visualizer)
        
        # Song name label
        self.song_label = QLabel("Not Playing")
        self.song_label.setStyleSheet("background: transparent;")
        layout.addWidget(self.song_label)
        
        self.setFixedHeight(30)
        
        # Make clickable
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _setup_popup(self):
        """Setup the popup music player"""
        self.popup = MusicPlayerPopup()
        
        # Forward popup signals
        self.popup.play_pause_clicked.connect(self.play_pause_requested.emit)
        self.popup.stop_clicked.connect(self.stop_requested.emit)
        self.popup.random_clicked.connect(self.random_requested.emit)
        self.popup.next_clicked.connect(self.next_requested.emit)
        self.popup.previous_clicked.connect(self.previous_requested.emit)
        self.popup.shuffle_clicked.connect(self.shuffle_requested.emit)
        self.popup.repeat_clicked.connect(self.repeat_requested.emit)
        self.popup.volume_changed.connect(self.volume_requested.emit)
    
    def _apply_theme(self):
        """Apply current theme styling with theme-aware PNG icon"""
        tm = self.theme_manager
        is_dark = tm.get_theme_name() == 'dark'
        
        # Container background
        self.setStyleSheet(f"""
            QWidget {{
                background: {tm.get_color('music_indicator', 'background')};
                border-radius: 6px;
            }}
        """)
        
        # Update music icon for current theme
        self.icon.setPixmap(self.icon_manager.get_music_pixmap(is_dark, 18))
        self.icon.setStyleSheet("background: transparent;")
        
        # Song label style
        self.song_label.setStyleSheet(f"""
            color: {tm.get_color('music_indicator', 'text')};
            font-size: 11px;
            background: transparent;
        """)
    
    def set_playing(self, song_name: str):
        """
        Start playing animation with song name
        
        Args:
            song_name: Name of the currently playing song (format: "Title by Artist")
        """
        # Parse song name and artist
        if " by " in song_name:
            parts = song_name.split(" by ", 1)
            self._current_song = parts[0].strip()
            self._current_artist = parts[1].strip() if len(parts) > 1 else ""
        else:
            self._current_song = song_name
            self._current_artist = ""
        
        self._is_playing = True
        self.song_label.setText(f"♪ {song_name}")
        self.visualizer.start_animation()
        self.show()
        
        # Update popup
        self.popup.set_song_info(self._current_song, self._current_artist)
        self.popup.set_playing(True)
        
        logger.info(f"🎵 Music indicator: {song_name}")
    
    def set_stopped(self):
        """Stop animation and hide"""
        self._is_playing = False
        self._current_song = ""
        self._current_artist = ""
        
        self.song_label.setText("Not Playing")
        self.visualizer.stop_animation()
        self.hide()
        
        # Update popup
        self.popup.set_song_info("", "")
        self.popup.set_playing(False)
        self.popup.hide()
        
        logger.info("⏹ Music indicator hidden")
    
    def update_song(self, song_name: str):
        """
        Update song name without restarting animation
        
        Args:
            song_name: Name of the new song (format: "Title by Artist")
        """
        # Parse song name and artist
        if " by " in song_name:
            parts = song_name.split(" by ", 1)
            self._current_song = parts[0].strip()
            self._current_artist = parts[1].strip() if len(parts) > 1 else ""
        else:
            self._current_song = song_name
            self._current_artist = ""
        
        self.song_label.setText(f"♪ {song_name}")
        
        # Update popup if visible
        self.popup.set_song_info(self._current_song, self._current_artist)
        
        logger.info(f"🎵 Music indicator updated: {song_name}")
    
    def set_shuffle_state(self, enabled: bool):
        """Update shuffle state on popup"""
        self.popup.set_shuffle(enabled)
    
    def set_repeat_state(self, mode: str):
        """Update repeat mode on popup ('off', 'one', 'all')"""
        self.popup.set_repeat_mode(mode)
    
    def set_volume_level(self, level: int):
        """Update volume level on popup slider"""
        self.popup.set_volume(level)
    
    def set_paused(self, paused: bool):
        """Update play/pause state"""
        self._is_playing = not paused
        self.popup.set_playing(not paused)
        
        if paused:
            self.visualizer.stop_animation()
        else:
            self.visualizer.start_animation()
    
    def mousePressEvent(self, event):
        """Handle mouse click - toggle popup"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            self._toggle_popup()
        super().mousePressEvent(event)
    
    def _toggle_popup(self):
        """Toggle the popup music player"""
        if self.popup.isVisible():
            self.popup.hide()
        else:
            # Show popup above the indicator
            global_pos = self.mapToGlobal(QPoint(self.width() // 2, 0))
            self.popup.show_at(global_pos)
            
            # Update popup with current state
            self.popup.set_song_info(self._current_song, self._current_artist)
            self.popup.set_playing(self._is_playing)
