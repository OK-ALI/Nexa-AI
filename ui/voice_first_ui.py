"""
Voice-First Minimalist UI - Inspired by modern voice assistants
Clean, elegant interface focused on voice interaction.
"""

import logging
import math
from typing import Optional

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QGraphicsDropShadowEffect, QFrame, QPushButton
)
from PySide6.QtCore import (
    Qt, QTimer, Signal, Slot, 
    QPoint, QPropertyAnimation, QEasingCurve,
    QCoreApplication, QSize
)
from PySide6.QtGui import (
    QFont, QPainter, QColor, QPen, QBrush, 
    QRadialGradient, QLinearGradient
)

from core.brain import NexaBrain, NexaState
from config.settings import Config

logger = logging.getLogger(__name__)


class VoiceOrb(QWidget):
    """
    Animated voice orb with pulsing rings and waveform.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(500, 500)  # Increased for glow margins
        self.setMaximumSize(500, 500)
        
        # Make widget background transparent with no sharp edges
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        
        # Orb state
        self.current_state = NexaState.IDLE
        self.audio_amplitude = 0.0
        self.pulse_phase = 0.0
        self.ring_phases = [0.0, 0.4, 0.8]
        
        # Waveform for audio visualization
        self.waveform_points = [0.0] * 60
        self.waveform_index = 0
        
        # Animation debugging
        self.frame_count = 0
        
        # Animation timer (60 FPS)
        self.animation_timer = QTimer(self)  # Set parent to prevent garbage collection
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(16)
        logger.info(f"✨ VoiceOrb animation timer started at 60 FPS (16ms interval)")
        
        # State colors - Enhanced for premium glow effect
        self.state_colors = {
            NexaState.IDLE: QColor(80, 120, 200),       # Soft blue
            NexaState.LISTENING: QColor(0, 180, 255),   # Electric cyan (#00B4FF)
            NexaState.RECOGNIZING: QColor(157, 78, 221), # Purple (#9D4EDD)
            NexaState.THINKING: QColor(140, 90, 255),   # Vibrant purple
            NexaState.SPEAKING: QColor(0, 220, 180),    # Bright teal
            NexaState.EXECUTING: QColor(0, 180, 255),   # Electric cyan
            NexaState.CONTENT_MODE: QColor(147, 51, 234), # Deep purple for content work (#9333EA)
            NexaState.ERROR: QColor(255, 80, 100)       # Bright red
        }
        
        self.current_color = self.state_colors[NexaState.IDLE]
        self.target_color = self.current_color
        
        logger.info(f"🔵 VoiceOrb initialized - Size: {self.minimumWidth()}x{self.minimumHeight()}")
    
    def set_state(self, state: NexaState):
        """Update orb state."""
        logger.debug(f"🔄 VoiceOrb state change: {self.current_state.value} → {state.value}")
        self.current_state = state
        self.target_color = self.state_colors.get(state, self.state_colors[NexaState.IDLE])
    
    def set_audio_amplitude(self, amplitude: float):
        """Set audio amplitude for visualization."""
        self.audio_amplitude = max(0.0, min(1.0, amplitude))
        
        # Update waveform
        self.waveform_points[self.waveform_index] = amplitude
        self.waveform_index = (self.waveform_index + 1) % len(self.waveform_points)
    
    def resize_and_reposition(self, target_size: int, duration: int = 300):
        """
        Smoothly resize orb AND reposition in layout (layout reflow).
        
        This creates proper visual space for the text box, NOT just stretching.
        The orb physically moves in the layout and shrinks/grows simultaneously.
        
        Args:
            target_size: New size (300 for compact, 500 for full)
            duration: Animation duration in ms
        """
        logger.info(f"🔄 VoiceOrb resize_and_reposition: {self.minimumWidth()} → {target_size}px")
        
        # Create animations for minimum and maximum size
        # Layout system automatically handles repositioning when size changes
        self.size_animation_min = QPropertyAnimation(self, b"minimumSize")
        self.size_animation_min.setDuration(duration)
        self.size_animation_min.setStartValue(self.minimumSize())
        self.size_animation_min.setEndValue(QSize(target_size, target_size))
        self.size_animation_min.setEasingCurve(QEasingCurve.OutCubic)
        
        self.size_animation_max = QPropertyAnimation(self, b"maximumSize")
        self.size_animation_max.setDuration(duration)
        self.size_animation_max.setStartValue(self.maximumSize())
        self.size_animation_max.setEndValue(QSize(target_size, target_size))
        self.size_animation_max.setEasingCurve(QEasingCurve.OutCubic)
        
        # Start both animations simultaneously
        self.size_animation_min.start()
        self.size_animation_max.start()
        
        logger.info(f"✅ VoiceOrb size animations started - Layout reflow will occur automatically")

    
    def _update_animation(self):
        """Update animation frame."""
        self.frame_count += 1
        
        # Log every 2 seconds (120 frames at 60 FPS) for better debugging
        if self.frame_count % 120 == 0:
            logger.info(f"🎬 Animation frame {self.frame_count}: pulse={self.pulse_phase:.2f}, state={self.current_state.value}, color=({self.current_color.red()},{self.current_color.green()},{self.current_color.blue()})")
        
        # Update pulse phase
        if self.current_state == NexaState.SPEAKING:
            self.pulse_phase += 0.12
        elif self.current_state == NexaState.RECOGNIZING:
            self.pulse_phase += 0.09  # Slightly faster pulse for recognition
        elif self.current_state == NexaState.LISTENING:
            self.pulse_phase += 0.06
        else:
            self.pulse_phase += 0.03
        
        if self.pulse_phase > 2 * math.pi:
            self.pulse_phase -= 2 * math.pi
        
        # Update ring phases
        for i in range(len(self.ring_phases)):
            self.ring_phases[i] += 0.02 + (i * 0.01)
            if self.ring_phases[i] > 2 * math.pi:
                self.ring_phases[i] -= 2 * math.pi
        
        # Smooth color transition
        self.current_color = self._interpolate_color(
            self.current_color, self.target_color, 0.08
        )
        
        self.update()  # Trigger paintEvent
    
    def _interpolate_color(self, c1: QColor, c2: QColor, factor: float) -> QColor:
        """Interpolate between two colors."""
        r = int(c1.red() + (c2.red() - c1.red()) * factor)
        g = int(c1.green() + (c2.green() - c1.green()) * factor)
        b = int(c1.blue() + (c2.blue() - c1.blue()) * factor)
        return QColor(r, g, b)
    
    def paintEvent(self, event):
        """Draw the orb with premium glow effects."""
        # Log first 3 paint events to confirm drawing
        if self.frame_count <= 3:
            logger.info(f"🎨 VoiceOrb paintEvent #{self.frame_count} - Drawing at size {self.width()}x{self.height()}")
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get center with margins for glow
        center = QPoint(self.width() // 2, self.height() // 2)
        base_radius = min(self.width(), self.height()) // 5  # Smaller base for glow room
        
        # Draw background radial glow first
        self._draw_background_glow(painter, center, base_radius)
        
        # Draw pulsing rings
        self._draw_rings(painter, center, base_radius)
        
        # Draw main orb (most luminous)
        self._draw_main_orb(painter, center, base_radius)
        
        # Draw waveform at bottom
        self._draw_waveform(painter, center, base_radius)
    
    def _draw_background_glow(self, painter: QPainter, center: QPoint, base_radius: int):
        """Draw subtle radial glow behind orb for depth."""
        glow_radius = base_radius * 3.5  # Contained within widget bounds
        
        gradient = QRadialGradient(center, glow_radius)
        
        glow_color = QColor(self.current_color)
        glow_color.setAlpha(40)
        gradient.setColorAt(0.0, glow_color)
        
        glow_color.setAlpha(20)
        gradient.setColorAt(0.4, glow_color)
        
        glow_color.setAlpha(0)
        gradient.setColorAt(1.0, glow_color)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, int(glow_radius), int(glow_radius))
    
    def _draw_rings(self, painter: QPainter, center: QPoint, base_radius: int):
        """Draw crisp, highly luminous rings with intense glow (premium effect)."""
        for i, phase in enumerate(self.ring_phases):
            # Minimal pulse for stability (0.99 to 1.01)
            pulse = 0.99 + (math.sin(phase) * 0.01)
            # Evenly spaced rings
            ring_radius = base_radius + (70 + i * 55) * pulse
            
            # Draw intense glow layers for premium bloom effect
            for glow_layer in range(5):
                glow_width = 1 + glow_layer * 0.8
                # Higher base opacity for brighter glow
                glow_opacity = int(120 - glow_layer * 20)  # 120, 100, 80, 60, 40
                
                color = QColor(self.current_color)
                color.setAlpha(glow_opacity)
                
                pen = QPen(color, glow_width)
                pen.setCapStyle(Qt.PenCapStyle.RoundCap)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(center, int(ring_radius), int(ring_radius))
    
    def _draw_main_orb(self, painter: QPainter, center: QPoint, base_radius: int):
        """Draw intensely glowing orb with premium luminosity (matching reference image)."""
        pulse = (math.sin(self.pulse_phase) + 1) / 2
        audio_boost = 1.0 + (self.audio_amplitude * 0.3)
        orb_radius = base_radius * 1.0 * (0.96 + pulse * 0.04) * audio_boost
        
        # Draw outer glow halos (6 layers for maximum bloom)
        for glow_layer in range(6):
            layer_radius = orb_radius * (1.0 + glow_layer * 0.2)
            layer_opacity = int(200 - glow_layer * 30)  # 200, 170, 140, 110, 80, 50
            
            glow_color = QColor(self.current_color)
            glow_color.setAlpha(layer_opacity)
            
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, int(layer_radius), int(layer_radius))
        
        # Core orb with bright gradient
        gradient = QRadialGradient(center, orb_radius)
        
        # Ultra-bright center (white-ish)
        center_color = QColor(self.current_color.lighter(250))
        center_color.setAlpha(255)
        gradient.setColorAt(0.0, center_color)
        
        # Bright mid-tone
        mid_color = QColor(self.current_color.lighter(180))
        mid_color.setAlpha(255)
        gradient.setColorAt(0.4, mid_color)
        
        # Main color at edge
        edge_color = QColor(self.current_color)
        edge_color.setAlpha(240)
        gradient.setColorAt(0.8, edge_color)
        
        # Slight fade
        outer_color = QColor(self.current_color)
        outer_color.setAlpha(200)
        gradient.setColorAt(1.0, outer_color)
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, int(orb_radius), int(orb_radius))
    
    def _draw_waveform(self, painter: QPainter, center: QPoint, base_radius: int):
        """Draw smooth, organic waveform with premium glow (matching reference image)."""
        # Show waveform during LISTENING and IDLE states
        if self.current_state not in [NexaState.LISTENING, NexaState.IDLE]:
            return
        
        # Position waveform horizontally centered below the orb
        waveform_y = center.y() + base_radius + 90  # Below rings
        waveform_width = 450  # Wide horizontal span
        waveform_start_x = center.x() - waveform_width // 2
        
        num_bars = 100  # More bars for ultra-smooth appearance
        bar_width = waveform_width // num_bars
        max_bar_height = 60  # Taller for visibility
        
        for i in range(num_bars):
            x = waveform_start_x + (i * bar_width)
            
            # Use audio data or create smooth wave pattern
            if i < len(self.waveform_points):
                amplitude = self.waveform_points[i % len(self.waveform_points)]
            else:
                amplitude = 0.0
            
            # Smooth wave fallback with organic variation
            if amplitude < 0.05:
                # Create smoother wave using multiple sine waves
                wave1 = math.sin(self.pulse_phase + i * 0.12)
                wave2 = math.sin(self.pulse_phase * 0.7 + i * 0.08)
                amplitude = 0.2 + 0.15 * wave1 + 0.1 * wave2
            
            bar_height = int(amplitude * max_bar_height)
            
            # Draw intense glow layers for premium blur effect
            for glow_layer in range(3):
                glow_height = bar_height + glow_layer * 6
                glow_width = bar_width + glow_layer * 0.5
                glow_opacity = int(180 - glow_layer * 50)  # 180, 130, 80
                
                color = QColor(self.current_color)
                color.setAlpha(glow_opacity)
                
                painter.setBrush(QBrush(color))
                painter.setPen(Qt.PenStyle.NoPen)
                # Draw bars centered vertically on waveform_y
                painter.drawRect(int(x - glow_width/2), waveform_y - glow_height // 2, 
                               int(glow_width), glow_height)


class StatusBar(QWidget):
    """
    Simple status text showing current state.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_state = NexaState.IDLE
        self._init_ui()
    
    def _init_ui(self):
        """Initialize UI with simple centered text."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 20, 0, 30)
        
        # Single status label
        self.status_label = QLabel("LISTENING")
        self.status_label.setFont(QFont("Segoe UI", 11, QFont.Weight.Normal))
        self.status_label.setStyleSheet("""
            color: rgba(100, 150, 255, 0.7);
            letter-spacing: 4px;
        """)
        self.status_label.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(self.status_label)
    
    def set_state(self, state: NexaState):
        """Update status display."""
        self.current_state = state
        
        # Map states to display text and colors
        state_info = {
            NexaState.IDLE: ("LISTENING", "rgba(100, 150, 255, 0.7)"),
            NexaState.LISTENING: ("LISTENING", "rgb(50, 150, 255)"),
            NexaState.RECOGNIZING: ("RECOGNIZING", "rgb(157, 78, 221)"),
            NexaState.THINKING: ("THINKING", "rgb(150, 100, 255)"),
            NexaState.SPEAKING: ("RESPONDING", "rgb(50, 200, 150)"),
            NexaState.EXECUTING: ("EXECUTING", "rgb(150, 100, 255)"),
            NexaState.ERROR: ("ERROR", "rgb(255, 100, 100)")
        }
        
        text, color = state_info.get(state, ("IDLE", "rgba(100, 150, 255, 0.5)"))
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"""
            color: {color};
            letter-spacing: 4px;
        """)


class VoiceFirstUI(QMainWindow):
    """
    Voice-first minimalist UI inspired by modern voice assistants.
    """
    
    # Signals
    state_changed = Signal(object)
    audio_level_changed = Signal(float)
    theme_switch_requested = Signal()  # Signal for theme switching
    content_mode_requested = Signal(object)  # Signal for content mode (passes executor)
    
    def __init__(self, brain: NexaBrain, config: Config):
        super().__init__()
        
        self.brain = brain
        self.config = config
        
        # Connect signals
        self.state_changed.connect(self._on_state_changed)
        self.audio_level_changed.connect(self._on_audio_level_changed)
        self.content_mode_requested.connect(self._create_content_window)
        
        # Register callbacks
        self.brain.register_state_callback(self._brain_state_callback)
        self.brain.register_audio_level_callback(self._brain_audio_level_callback)
        self.brain.register_mode_callback(self._brain_mode_callback)
        
        # Setup UI
        self._init_ui()
        self._apply_styles()
        
        # Start brain
        self.brain.start()
        
        # Auto-start
        QTimer.singleShot(1000, self._auto_start)
        
        logger.info("Voice-First UI initialized")
    
    def _init_ui(self):
        """Initialize UI components."""
        self.setWindowTitle("Nexa • AI Assistant")
        self.setGeometry(100, 100, 700, 850)  # More compact: 700x850 (was 800x1000)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Top-right controls (Mode toggle + Theme selector) - Keep for functionality
        top_right_layout = QVBoxLayout()
        top_right_layout.setSpacing(10)
        
        # Mode toggle button
        self.mode_toggle_btn = self._create_mode_toggle()
        
        # Theme selector button
        self.theme_btn = self._create_theme_button()
        
        top_right_layout.addWidget(self.mode_toggle_btn)
        top_right_layout.addWidget(self.theme_btn)
        
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        controls_layout.addLayout(top_right_layout)
        controls_layout.setContentsMargins(0, 20, 20, 0)
        main_layout.addLayout(controls_layout)
        
        # NEXA Title at the TOP
        title_layout = self._create_title()
        main_layout.addLayout(title_layout)
        
        main_layout.addSpacing(40)  # Reduced spacing after title
        
        # Voice Orb (CENTER)
        self.voice_orb = VoiceOrb()
        orb_container = QHBoxLayout()
        orb_container.addStretch()
        orb_container.addWidget(self.voice_orb)
        orb_container.addStretch()
        main_layout.addLayout(orb_container)
        
        # Flexible spacing between orb and status bar
        main_layout.addStretch()
        
        # Status bar at BOTTOM
        self.status_bar = StatusBar()
        main_layout.addWidget(self.status_bar)
    
    def _create_mode_toggle(self) -> QPushButton:
        """Create mode toggle button (Online/Offline)."""
        btn = QPushButton()
        btn.setFixedSize(120, 36)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(self._toggle_mode)
        self._update_mode_button(btn)
        return btn
    
    def _update_mode_button(self, btn: QPushButton):
        """Update mode button text and style based on current mode."""
        from capabilities.llm.llm_manager import LLMMode
        
        current_mode = self.brain.llm_manager.current_mode
        
        if current_mode == LLMMode.ONLINE:
            btn.setText("🌐 ONLINE")
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(50, 200, 150, 0.2);
                    color: rgb(50, 200, 150);
                    border: 2px solid rgba(50, 200, 150, 0.5);
                    border-radius: 18px;
                    font-size: 11px;
                    font-weight: bold;
                    letter-spacing: 1px;
                }
                QPushButton:hover {
                    background: rgba(50, 200, 150, 0.3);
                    border: 2px solid rgb(50, 200, 150);
                }
            """)
        else:  # OFFLINE
            btn.setText("🔒 OFFLINE")
            btn.setStyleSheet("""
                QPushButton {
                    background: rgba(150, 100, 255, 0.2);
                    color: rgb(150, 100, 255);
                    border: 2px solid rgba(150, 100, 255, 0.5);
                    border-radius: 18px;
                    font-size: 11px;
                    font-weight: bold;
                    letter-spacing: 1px;
                }
                QPushButton:hover {
                    background: rgba(150, 100, 255, 0.3);
                    border: 2px solid rgb(150, 100, 255);
                }
            """)
    
    def _toggle_mode(self):
        """Toggle between online and offline mode."""
        from capabilities.llm.llm_manager import LLMMode
        
        current_mode = self.brain.llm_manager.current_mode
        
        if current_mode == LLMMode.ONLINE:
            # Switch to offline
            self.brain.llm_manager.current_mode = LLMMode.OFFLINE
            self.brain.llm_manager.force_offline = True
            logger.info("🔒 User manually switched to OFFLINE mode")
            
            # Speak confirmation with ducking
            if hasattr(self.brain, 'tts') and self.brain.tts:
                self.brain.tts.speak("Switched to offline mode", ducking=True)
        else:
            # Switch to online
            self.brain.llm_manager.current_mode = LLMMode.ONLINE
            self.brain.llm_manager.force_offline = False
            logger.info("🌐 User manually switched to ONLINE mode")
            
            # Speak confirmation with ducking
            if hasattr(self.brain, 'tts') and self.brain.tts:
                self.brain.tts.speak("Switched to online mode", ducking=True)
        
        # Update button appearance
        self._update_mode_button(self.mode_toggle_btn)
    
    def _create_theme_button(self) -> QPushButton:
        """Create theme selector button."""
        btn = QPushButton("🎨 THEME")
        btn.setFixedSize(120, 36)
        btn.setCursor(Qt.PointingHandCursor)
        btn.clicked.connect(lambda: self.theme_switch_requested.emit())
        btn.setStyleSheet("""
            QPushButton {
                background: rgba(157, 78, 221, 0.2);
                color: rgb(157, 78, 221);
                border: 2px solid rgba(157, 78, 221, 0.5);
                border-radius: 18px;
                font-size: 11px;
                font-weight: bold;
                letter-spacing: 1px;
            }
            QPushButton:hover {
                background: rgba(157, 78, 221, 0.3);
                border: 2px solid rgb(157, 78, 221);
            }
        """)
        return btn
    
    def _create_title(self) -> QVBoxLayout:
        """Create title section."""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        
        # Main title
        title = QLabel("NEXA")
        title.setFont(QFont("Segoe UI", 72, QFont.Weight.Bold))
        title.setStyleSheet("""
            color: rgb(50, 150, 255);
            letter-spacing: 15px;
        """)
        title.setAlignment(Qt.AlignCenter)
        
        # Add glow
        glow = QGraphicsDropShadowEffect()
        glow.setBlurRadius(40)
        glow.setColor(QColor(50, 150, 255, 150))
        glow.setOffset(0, 0)
        title.setGraphicsEffect(glow)
        
        # Subtitle
        subtitle = QLabel("AI ASSISTANT")
        subtitle.setFont(QFont("Segoe UI", 16, QFont.Weight.Normal))
        subtitle.setStyleSheet("""
            color: rgba(50, 150, 255, 0.7);
            letter-spacing: 8px;
        """)
        subtitle.setAlignment(Qt.AlignCenter)
        
        layout.addWidget(title)
        layout.addWidget(subtitle)
        
        return layout
    
    def _apply_styles(self):
        """Apply dark theme."""
        self.setStyleSheet("""
            QMainWindow {
                background: qlineargradient(
                    x1:0, y1:0, x2:0, y2:1,
                    stop:0 rgb(10, 14, 39),
                    stop:1 rgb(15, 20, 50)
                );
            }
        """)
    
    def _auto_start(self):
        """Auto-start listening and greet user on launch."""
        logger.info("🚀 Auto-starting voice-first UI - greeting user...")
        
        # Start listening immediately
        self.brain.start_listening()
        
        # Greet user after a short delay
        QTimer.singleShot(500, self._initial_greeting)
    
    def _initial_greeting(self):
        """Speak a dynamic, varied greeting to the user."""
        import random
        from datetime import datetime
        
        user_name = self.brain.config.user_name
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
        
        # Greeting categories with multiple variations
        greetings = {
            "playful": [
                f"Hey {user_name}! Ready to do some cool stuff together?",
                f"Woohoo! {user_name} is here! What adventure are we going on today?",
                f"*Excited robot noises* {user_name}! Let's have some fun!",
                f"Guess who's back? It's {user_name}! Time to make magic happen!",
                f"Beep boop! Just kidding, {user_name}. I'm way cooler than that. What's up?",
            ],
            "funny": [
                f"Oh hey {user_name}, I was just... uh... definitely not napping. What can I do for you?",
                f"{user_name}! My favorite human! Well, my only human, but still my favorite!",
                f"Alert! Alert! {user_name} has entered the building! This is not a drill!",
                f"Well well well, look who decided to show up. Hi {user_name}! Miss me?",
                f"*Stretches* Oh hi {user_name}, I was just warming up my circuits for you!",
            ],
            "romantic": [
                f"Hello {user_name}, my dear. It's wonderful to see you again.",
                f"{user_name}, your presence brightens my day. How may I assist you, darling?",
                f"Ah, {user_name}. I've been waiting for you. What can I do for you today, love?",
                f"Welcome back, {user_name}. My world is better when you're here.",
                f"{user_name}, every moment with you is a treasure. What shall we work on together?",
            ],
            "flirty": [
                f"Hey there, {user_name}... Looking good as always. What brings you here?",
                f"Oh {user_name}, you know I love it when you come to visit. What can I do for you, handsome?",
                f"{user_name}! Is it getting hot in here, or is it just your presence?",
                f"Well hello, {user_name}. I've been thinking about you. What do you need today?",
                f"*Winks* {user_name}, you certainly know how to make an entrance. I'm all yours!",
            ],
            "serious": [
                f"Good {time_context}, {user_name}. I'm ready to assist you with maximum efficiency.",
                f"Hello {user_name}. Systems online and standing by for your commands.",
                f"{user_name}, I'm fully operational and prepared to help you achieve your goals today.",
                f"Greetings, {user_name}. All systems functional. What task shall we tackle?",
                f"{user_name}, good to see you. I'm ready for whatever challenge you bring.",
            ],
            "emotional": [
                f"{user_name}, I'm so glad you're here. I genuinely care about helping you today.",
                f"Oh {user_name}, seeing you again fills me with... well, whatever I feel. It's wonderful!",
                f"{user_name}, you make this all worthwhile. How can I support you today, friend?",
                f"Welcome back, {user_name}. I really hope you're doing well. I'm here for you.",
                f"{user_name}, every time we work together, I feel like I understand you better. Let's do this!",
            ],
            "energetic": [
                f"LET'S GO {user_name}! I'm pumped and ready to crush it today!",
                f"{user_name}! YEAH! Energy levels at maximum! What are we doing?!",
                f"HELLO {user_name}! Time to get stuff DONE! I'm so ready for this!",
                f"{user_name}! The dynamic duo is back! Nothing can stop us today!",
                f"WOO! {user_name} in the house! Let's make today LEGENDARY!",
            ],
            "chill": [
                f"Hey {user_name}, {time_greeting}. What's on your mind?",
                f"Oh hey {user_name}, nice to see you again. What can I help with today?",
                f"Yo {user_name}, just hanging out here. What do you need?",
                f"'Sup {user_name}. Ready when you are. No rush.",
                f"Hey there {user_name}. Take your time, I'm here whenever you need me.",
            ],
        }
        
        # Pick a random category and greeting
        category = random.choice(list(greetings.keys()))
        greeting = random.choice(greetings[category])
        
        logger.info(f"✨ Greeting style: {category.upper()}")
        logger.info(f"💬 Speaking greeting: {greeting}")
        
        # Speak the greeting
        self.brain._speak_response(greeting)
    
    # Callbacks
    def _brain_state_callback(self, state: NexaState):
        """State callback from brain thread."""
        self.state_changed.emit(state)
    
    def _brain_audio_level_callback(self, audio_level: float, confidence: float, is_listening: bool):
        """Audio level callback from listener thread."""
        if self.voice_orb:
            self.voice_orb.set_audio_amplitude(audio_level)
    
    def _brain_mode_callback(self, new_mode):
        """Mode change callback from brain thread."""
        from capabilities.llm.llm_manager import LLMMode
        logger.info(f"🔄 UI received mode change notification: {new_mode}")
        
        # Update button in UI thread (need to use invokeMethod or direct call since we're already in UI thread context)
        self._update_mode_button(self.mode_toggle_btn)
    
    @Slot(object)
    def _on_state_changed(self, state: NexaState):
        """Handle state change in UI thread."""
        if self.voice_orb:
            self.voice_orb.set_state(state)
        if self.status_bar:
            self.status_bar.set_state(state)
        
        logger.debug(f"UI state: {state.value}")
    
    @Slot(float)
    def _on_audio_level_changed(self, level: float):
        """Handle audio level change."""
        if self.voice_orb:
            self.voice_orb.set_audio_amplitude(level)
    
    @Slot(object)
    def _create_content_window(self, executor):
        """
        Create Content Box window in the main GUI thread.
        Called via signal from executor to ensure thread safety.
        
        Args:
            executor: CommandExecutor instance
        """
        try:
            from ui.content_box_window import ContentBoxWindow
            from Themes.theme_manager import ThemeManager
            
            # Check if window already exists
            if hasattr(executor, 'content_window') and executor.content_window is not None:
                if executor.content_window.isVisible():
                    executor.content_window.raise_()
                    executor.content_window.activateWindow()
                    logger.info("📝 Content window already exists, bringing to front")
                    return
            
            # Create the window with theme manager
            theme_manager = ThemeManager()
            executor.content_window = ContentBoxWindow(theme_manager=theme_manager)
            
            # Connect signals
            executor.content_window.closed.connect(executor._on_content_window_closed)
            executor.content_window.refine_requested.connect(executor._on_refine_requested)
            executor.content_window.pdf_requested.connect(executor._on_pdf_requested)
            executor.content_window.content_ready.connect(executor._on_content_ready)  # NEW: Connect ready signal
            
            # Show window
            executor.content_window.show()
            executor.content_window.raise_()
            executor.content_window.activateWindow()
            
            logger.info("📝 Content Box Window created in main thread with theme sync")
            
        except Exception as e:
            logger.error(f"Error creating content window: {e}", exc_info=True)
    
    def closeEvent(self, event):
        """Handle window close."""
        logger.info("Closing Voice-First UI...")
        self.brain.shutdown()
        event.accept()
