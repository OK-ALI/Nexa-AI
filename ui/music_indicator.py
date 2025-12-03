"""
Music Indicator Widget - Shows current music playback state
Features:
- Animated music visualizer bars
- Song name display
- Theme-aware styling
- Show/hide animations
"""

import logging
import random
from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QPainter, QColor
from Themes.theme_manager import get_theme_manager

logger = logging.getLogger(__name__)


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


class MusicIndicatorWidget(QWidget):
    """
    Complete music indicator widget.
    Shows music icon, visualizer bars, and current song name.
    """
    
    # Signals
    clicked = Signal()  # Emitted when widget is clicked
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self.theme_manager.theme_changed.connect(self._apply_theme)
        
        self._setup_ui()
        self._apply_theme()
        self.hide()  # Hidden by default
        
        logger.info("✅ MusicIndicatorWidget initialized")
    
    def _setup_ui(self):
        """Setup the music indicator UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(6)
        
        # Music icon
        self.icon = QLabel("🎵")
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
    
    def _apply_theme(self):
        """Apply current theme styling"""
        tm = self.theme_manager
        
        # Container background
        self.setStyleSheet(f"""
            QWidget {{
                background: {tm.get_color('music_indicator', 'background')};
                border-radius: 6px;
            }}
        """)
        
        # Icon style
        self.icon.setStyleSheet(f"""
            font-size: 14px;
            background: transparent;
            color: {tm.get_color('music_indicator', 'icon')};
        """)
        
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
            song_name: Name of the currently playing song
        """
        self.song_label.setText(f"♪ {song_name}")
        self.visualizer.start_animation()
        self.show()
        logger.info(f"🎵 Music indicator: {song_name}")
    
    def set_stopped(self):
        """Stop animation and hide"""
        self.song_label.setText("Not Playing")
        self.visualizer.stop_animation()
        self.hide()
        logger.info("⏹ Music indicator hidden")
    
    def update_song(self, song_name: str):
        """
        Update song name without restarting animation
        
        Args:
            song_name: Name of the new song
        """
        self.song_label.setText(f"♪ {song_name}")
        logger.info(f"🎵 Music indicator updated: {song_name}")
    
    def mousePressEvent(self, event):
        """Handle mouse click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
            logger.info("🖱 Music indicator clicked")
        super().mousePressEvent(event)
