"""
Enhanced Status Widget - Visual status indicators with icons and progress bars
"""

import logging
from typing import Optional

from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
    QProgressBar, QGraphicsDropShadowEffect
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, Property
from PySide6.QtGui import QFont, QColor

from core.brain import NexaState

logger = logging.getLogger(__name__)


class StatusIndicator(QWidget):
    """
    Enhanced status indicator with icon, label, and progress bar.
    Shows current state with visual feedback.
    """
    
    # State display information
    STATE_INFO = {
        NexaState.IDLE: {
            "icon": "⭕",
            "text": "IDLE",
            "color": "#3A3A3A",
            "show_progress": False
        },
        NexaState.LISTENING: {
            "icon": "🎧",
            "text": "LISTENING",
            "color": "#00D9FF",
            "show_progress": False
        },
        NexaState.THINKING: {
            "icon": "🧠",
            "text": "THINKING",
            "color": "#9D00FF",
            "show_progress": True
        },
        NexaState.SPEAKING: {
            "icon": "💬",
            "text": "SPEAKING",
            "color": "#00FF88",
            "show_progress": True
        },
        NexaState.EXECUTING: {
            "icon": "⚙️",
            "text": "EXECUTING",
            "color": "#9D00FF",
            "show_progress": True
        },
        NexaState.CONTENT_MODE: {
            "icon": "📝",
            "text": "CONTENT MODE",
            "color": "#9333EA",
            "show_progress": False
        },
        NexaState.ERROR: {
            "icon": "⚠️",
            "text": "ERROR",
            "color": "#FF3232",
            "show_progress": False
        }
    }
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_state = NexaState.IDLE
        self._opacity = 1.0
        
        self._init_ui()
        
        # Pulse animation timer for active states
        self.pulse_timer = QTimer()
        self.pulse_timer.timeout.connect(self._pulse_animation)
        self.pulse_value = 0
        
    def _init_ui(self):
        """Initialize UI components."""
        # Main layout
        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Status row (icon + text)
        status_row = QHBoxLayout()
        status_row.setSpacing(10)
        
        # Icon label
        self.icon_label = QLabel("⭕")
        self.icon_label.setFont(QFont("Segoe UI", 16))
        self.icon_label.setAlignment(Qt.AlignCenter)
        status_row.addWidget(self.icon_label)
        
        # Text label
        self.text_label = QLabel("IDLE")
        self.text_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.text_label.setStyleSheet("""
            color: #3A3A3A;
            letter-spacing: 2px;
        """)
        status_row.addWidget(self.text_label)
        status_row.addStretch()
        
        layout.addLayout(status_row)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 3px;
            }
            QProgressBar::chunk {
                background-color: #00D9FF;
                border-radius: 3px;
            }
        """)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # Add glow effect to icon
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(15)
        glow.setColor(QColor(0, 217, 255, 100))
        glow.setOffset(0, 0)
        self.icon_label.setGraphicsEffect(glow)
    
    def set_state(self, state: NexaState):
        """
        Update status indicator to show new state.
        
        Args:
            state: New Nexa state
        """
        if state == self.current_state:
            return
            
        self.current_state = state
        info = self.STATE_INFO.get(state, self.STATE_INFO[NexaState.IDLE])
        
        # Update icon and text
        self.icon_label.setText(info["icon"])
        self.text_label.setText(info["text"])
        
        # Update color
        color = info["color"]
        self.text_label.setStyleSheet(f"""
            color: {color};
            letter-spacing: 2px;
        """)
        
        # Update progress bar style
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: rgba(255, 255, 255, 0.1);
                border: none;
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
        
        # Update glow effect color
        glow = self.icon_label.graphicsEffect()
        if glow:
            glow_color = QColor(color)
            glow_color.setAlpha(150)
            glow.setColor(glow_color)
        
        # Show/hide progress bar
        if info["show_progress"]:
            self.progress_bar.show()
            self.progress_bar.setValue(0)
            self._start_progress_animation()
            
            # Start pulse animation for active states
            if not self.pulse_timer.isActive():
                self.pulse_timer.start(50)  # 20 FPS
        else:
            self.progress_bar.hide()
            self.pulse_timer.stop()
        
        logger.debug(f"Status indicator updated: {info['text']}")
    
    def _start_progress_animation(self):
        """Start indeterminate progress animation."""
        # Create smooth progress animation
        self.progress_animation = QPropertyAnimation(self.progress_bar, b"value")
        self.progress_animation.setDuration(2000)
        self.progress_animation.setStartValue(0)
        self.progress_animation.setEndValue(100)
        self.progress_animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.progress_animation.setLoopCount(-1)  # Infinite loop
        self.progress_animation.start()
    
    def _pulse_animation(self):
        """Create subtle pulse effect for active states."""
        self.pulse_value += 0.1
        
        # Calculate pulse opacity (0.7 to 1.0)
        import math
        pulse = 0.85 + 0.15 * math.sin(self.pulse_value)
        
        # Apply to icon (subtle pulsing)
        opacity_effect = f"opacity: {pulse};"
        current_style = self.text_label.styleSheet()
        if "opacity:" not in current_style:
            self.text_label.setStyleSheet(current_style + opacity_effect)
    
    def get_opacity(self):
        """Get opacity for animation."""
        return self._opacity
    
    def set_opacity(self, value):
        """Set opacity for animation."""
        self._opacity = value
        self.setWindowOpacity(value)
    
    opacity = Property(float, get_opacity, set_opacity)


class ThemeToggleButton(QWidget):
    """
    Theme toggle button for switching between dark and light themes.
    """
    
    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window  # Store reference to main window
        self.is_dark_theme = True  # Start with dark theme
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI components."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Theme toggle button
        self.theme_button = QLabel("🌙")
        self.theme_button.setFont(QFont("Segoe UI", 16))
        self.theme_button.setAlignment(Qt.AlignCenter)
        self.theme_button.setFixedSize(40, 40)
        self.theme_button.setStyleSheet("""
            QLabel {
                background-color: rgba(255, 255, 255, 0.05);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 20px;
                padding: 5px;
            }
            QLabel:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
            }
        """)
        self.theme_button.setCursor(Qt.PointingHandCursor)
        self.theme_button.mousePressEvent = self._toggle_theme
        
        # Add glow effect
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(15)
        glow.setColor(QColor(255, 255, 255, 80))
        glow.setOffset(0, 0)
        self.theme_button.setGraphicsEffect(glow)
        
        layout.addWidget(self.theme_button)
    
    def _toggle_theme(self, event):
        """Toggle between dark and light themes."""
        self.is_dark_theme = not self.is_dark_theme
        
        if self.is_dark_theme:
            self.theme_button.setText("🌙")
            logger.info("Switched to dark theme")
        else:
            self.theme_button.setText("☀️")
            logger.info("Switched to light theme")
        
        # Apply theme via main window reference
        if self.main_window and hasattr(self.main_window, 'apply_theme'):
            self.main_window.apply_theme(self.is_dark_theme)
    
    def set_theme(self, is_dark: bool):
        """Set theme without triggering toggle."""
        self.is_dark_theme = is_dark
        self.theme_button.setText("🌙" if is_dark else "☀️")
