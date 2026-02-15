"""
Pet Settings Panel - Customization UI for Nexa Pet
A floating futuristic settings panel with sliders and toggles.

Features:
- Size slider (50-200%)
- Opacity slider (20-100%)
- Toggle switches for options
- Nexa theme (cyan/blue on dark navy)
- Glassmorphism with neon glow

Part of P6: Settings Panel & Customization
"""

import logging
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QCheckBox, QFrame, QGraphicsDropShadowEffect,
    QApplication
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QPoint
from PySide6.QtGui import QColor, QFont

logger = logging.getLogger(__name__)


class PetSettingsPanel(QWidget):
    """
    Floating settings panel for pet customization.
    
    Emits signals when settings change for real-time preview.
    """
    
    # Signals for real-time updates
    size_changed = Signal(int)       # percentage 50-200
    opacity_changed = Signal(float)  # 0.2-1.0
    animations_toggled = Signal(bool)
    speech_bubble_toggled = Signal(bool)
    snap_to_edges_toggled = Signal(bool)
    expression_speed_changed = Signal(float)  # 0.5-2.0
    settings_closed = Signal()
    # P7 Personality signals
    personality_toggled = Signal(bool)
    time_aware_toggled = Signal(bool)
    idle_timeout_changed = Signal(int)  # minutes 1-10
    # Glow effect signals
    glow_toggled = Signal(bool)
    glow_intensity_changed = Signal(float)  # 0.0-1.0
    
    def __init__(self, parent=None, config=None):
        """
        Initialize settings panel.
        
        Args:
            parent: Parent widget (pet widget)
            config: PetConfig instance for loading/saving settings
        """
        super().__init__(None)  # Top-level window
        
        self.parent_widget = parent
        self.config = config
        self.fade_animation = None  # For smooth transitions
        
        self._setup_window()
        self._setup_ui()
        self._apply_styling()
        self._load_current_settings()
        
        logger.info("⚙️ Pet settings panel initialized")
    
    def _setup_window(self):
        """Configure window properties."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setFixedWidth(300)
        self.setMinimumHeight(520)
    
    def _setup_ui(self):
        """Setup the panel UI."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(0)
        
        # Container for styling
        self.container = QFrame()
        self.container.setObjectName("settingsContainer")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 12, 16, 16)
        container_layout.setSpacing(6)
        
        # Header with title and close button
        header = QHBoxLayout()
        header.setSpacing(10)
        
        title = QLabel("Companion Settings")
        title.setObjectName("panelTitle")
        title.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("closeButton")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self._close_panel)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.close_btn)
        container_layout.addLayout(header)
        
        # ═══════════════════════════════════════════════════════════════
        # Appearance Section
        # ═══════════════════════════════════════════════════════════════
        container_layout.addWidget(self._create_separator())
        
        appearance_header = QLabel("Appearance")
        appearance_header.setObjectName("sectionHeader")
        container_layout.addWidget(appearance_header)
        
        # Size slider
        self.size_slider = self._create_slider_row(
            "Size", 50, 200, 100, "%", self._on_size_changed
        )
        container_layout.addLayout(self.size_slider['layout'])
        
        # Opacity slider
        self.opacity_slider = self._create_slider_row(
            "Opacity", 20, 100, 100, "%", self._on_opacity_changed
        )
        container_layout.addLayout(self.opacity_slider['layout'])
        
        # ═══════════════════════════════════════════════════════════════
        # Visual Effects Section
        # ═══════════════════════════════════════════════════════════════
        container_layout.addWidget(self._create_separator())
        
        effects_header = QLabel("Effects")
        effects_header.setObjectName("sectionHeader")
        container_layout.addWidget(effects_header)
        
        # Glow toggle
        self.glow_toggle = self._create_toggle_row(
            "Cyan Glow", True, self._on_glow_toggled
        )
        container_layout.addLayout(self.glow_toggle['layout'])
        
        # Glow intensity slider
        self.glow_intensity_slider = self._create_slider_row(
            "Glow Power", 10, 100, 60, "%", self._on_glow_intensity_changed
        )
        container_layout.addLayout(self.glow_intensity_slider['layout'])
        
        # Animations toggle
        self.animations_toggle = self._create_toggle_row(
            "Animations", True, self._on_animations_toggled
        )
        container_layout.addLayout(self.animations_toggle['layout'])
        
        # ═══════════════════════════════════════════════════════════════
        # Behavior Section
        # ═══════════════════════════════════════════════════════════════
        container_layout.addWidget(self._create_separator())
        
        behavior_header = QLabel("Behavior")
        behavior_header.setObjectName("sectionHeader")
        container_layout.addWidget(behavior_header)
        
        # Speech bubble toggle
        self.speech_bubble_toggle = self._create_toggle_row(
            "Speech Bubble", True, self._on_speech_bubble_toggled
        )
        container_layout.addLayout(self.speech_bubble_toggle['layout'])
        
        # Snap to edges toggle
        self.snap_toggle = self._create_toggle_row(
            "Snap to Edges", True, self._on_snap_toggled
        )
        container_layout.addLayout(self.snap_toggle['layout'])
        
        # Expression speed slider
        self.speed_slider = self._create_slider_row(
            "Expression Speed", 50, 200, 100, "%", self._on_speed_changed
        )
        container_layout.addLayout(self.speed_slider['layout'])
        
        # ═══════════════════════════════════════════════════════════════
        # Personality Section
        # ═══════════════════════════════════════════════════════════════
        container_layout.addWidget(self._create_separator())
        
        p7_header = QLabel("Personality")
        p7_header.setObjectName("sectionHeader")
        container_layout.addWidget(p7_header)
        
        # Personality toggle
        self.personality_toggle = self._create_toggle_row(
            "Enable Personality", True, self._on_personality_toggled
        )
        container_layout.addLayout(self.personality_toggle['layout'])
        
        # Time-aware toggle
        self.time_aware_toggle = self._create_toggle_row(
            "Time-Aware Mode", True, self._on_time_aware_toggled
        )
        container_layout.addLayout(self.time_aware_toggle['layout'])
        
        # Idle timeout slider
        self.idle_timeout_slider = self._create_slider_row(
            "Sleep After", 1, 10, 5, " min", self._on_idle_timeout_changed
        )
        container_layout.addLayout(self.idle_timeout_slider['layout'])
        
        # End spacer
        container_layout.addSpacing(10)
        
        main_layout.addWidget(self.container)
        
        # Add glow effect to container
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(40)
        shadow.setColor(QColor(0, 180, 255, 120))
        shadow.setOffset(0, 5)
        self.container.setGraphicsEffect(shadow)
    
    def _create_separator(self) -> QFrame:
        """Create a horizontal separator line."""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setObjectName("separator")
        return line
    
    def _create_slider_row(self, label: str, min_val: int, max_val: int, 
                           default: int, suffix: str, callback: Callable) -> dict:
        """Create a labeled slider row with proper alignment."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(8)
        
        # Label - fixed width for alignment
        lbl = QLabel(label)
        lbl.setObjectName("settingLabel")
        lbl.setFixedWidth(110)
        
        # Slider - expands to fill
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setObjectName("settingSlider")
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default)
        slider.setFixedHeight(20)
        
        # Value label - fixed width, right aligned
        value_lbl = QLabel(f"{default}{suffix}")
        value_lbl.setObjectName("valueLabel")
        value_lbl.setFixedWidth(50)
        value_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Connect slider
        def on_change(val):
            value_lbl.setText(f"{val}{suffix}")
            callback(val)
        
        slider.valueChanged.connect(on_change)
        
        layout.addWidget(lbl)
        layout.addWidget(slider, 1)
        layout.addWidget(value_lbl)
        
        return {
            'layout': layout,
            'slider': slider,
            'value_label': value_lbl,
            'suffix': suffix
        }
    
    def _create_toggle_row(self, label: str, default: bool, callback: Callable) -> dict:
        """Create a labeled toggle switch row with proper alignment."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 4, 0, 4)
        layout.setSpacing(8)
        
        # Label - fixed width matching sliders
        lbl = QLabel(label)
        lbl.setObjectName("settingLabel")
        lbl.setFixedWidth(110)
        
        # Spacer to push toggle to right
        layout.addWidget(lbl)
        layout.addStretch(1)
        
        # Checkbox styled as toggle
        toggle = QCheckBox()
        toggle.setObjectName("settingToggle")
        toggle.setChecked(default)
        toggle.stateChanged.connect(lambda state: callback(state == 2))  # Qt.CheckState.Checked = 2
        
        layout.addWidget(toggle)
        
        return {
            'layout': layout,
            'toggle': toggle
        }
    
    def _apply_styling(self):
        """Apply Nexa futuristic theme styling."""
        self.setStyleSheet("""
            #settingsContainer {
                background-color: rgba(10, 20, 40, 250);
                border: 2px solid rgba(0, 180, 255, 150);
                border-radius: 15px;
            }
            
            #panelTitle {
                color: #00D4FF;
                padding: 0;
            }
            
            #closeButton {
                background-color: rgba(255, 80, 80, 180);
                border: none;
                border-radius: 14px;
                color: white;
                font-weight: bold;
                font-size: 14px;
            }
            
            #closeButton:hover {
                background-color: rgba(255, 100, 100, 220);
            }
            
            #separator {
                background-color: rgba(0, 150, 220, 60);
                max-height: 1px;
                margin: 8px 0 4px 0;
            }
            
            #settingLabel {
                color: #E0F0FF;
                font-size: 12px;
                font-family: "Segoe UI", sans-serif;
            }
            
            #sectionHeader {
                color: #00E0FF;
                font-size: 12px;
                font-weight: bold;
                font-family: "Segoe UI", sans-serif;
                padding: 4px 0 0 0;
            }
            
            #valueLabel {
                color: #00D4FF;
                font-size: 11px;
                font-weight: bold;
                font-family: "Segoe UI", sans-serif;
            }
            
            #settingSlider {
                height: 20px;
            }
            
            #settingSlider::groove:horizontal {
                background: rgba(30, 50, 80, 200);
                height: 6px;
                border-radius: 3px;
            }
            
            #settingSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00E0FF, stop:1 #0080FF);
                width: 16px;
                height: 16px;
                margin: -5px 0;
                border-radius: 8px;
                border: 2px solid rgba(255, 255, 255, 100);
            }
            
            #settingSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #40F0FF, stop:1 #00A0FF);
            }
            
            #settingSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0060FF, stop:1 #00C0FF);
                border-radius: 3px;
            }
            
            #settingToggle {
                spacing: 10px;
            }
            
            #settingToggle::indicator {
                width: 40px;
                height: 22px;
                border-radius: 11px;
            }
            
            #settingToggle::indicator:unchecked {
                background-color: rgba(60, 70, 90, 200);
                border: 1px solid rgba(100, 110, 130, 150);
            }
            
            #settingToggle::indicator:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #0080FF, stop:1 #00D0FF);
                border: 1px solid rgba(0, 200, 255, 200);
            }
        """)
    
    def _load_current_settings(self):
        """Load current settings from config."""
        if not self.config:
            return
        
        # Load values
        scale = self.config.get('scale_percent', 100)
        opacity = int(self.config.get('opacity', 1.0) * 100)
        animations = self.config.get('animations_enabled', True)
        bubble = self.config.get('show_speech_bubble', True)
        snap = self.config.get('snap_to_edges', True)
        speed = int(self.config.get('expression_speed', 1.0) * 100)
        
        # Set slider values (blocking signals to avoid callbacks)
        self.size_slider['slider'].blockSignals(True)
        self.size_slider['slider'].setValue(scale)
        self.size_slider['value_label'].setText(f"{scale}%")
        self.size_slider['slider'].blockSignals(False)
        
        self.opacity_slider['slider'].blockSignals(True)
        self.opacity_slider['slider'].setValue(opacity)
        self.opacity_slider['value_label'].setText(f"{opacity}%")
        self.opacity_slider['slider'].blockSignals(False)
        
        self.speed_slider['slider'].blockSignals(True)
        self.speed_slider['slider'].setValue(speed)
        self.speed_slider['value_label'].setText(f"{speed}%")
        self.speed_slider['slider'].blockSignals(False)
        
        # Set toggles
        self.animations_toggle['toggle'].blockSignals(True)
        self.animations_toggle['toggle'].setChecked(animations)
        self.animations_toggle['toggle'].blockSignals(False)
        
        self.speech_bubble_toggle['toggle'].blockSignals(True)
        self.speech_bubble_toggle['toggle'].setChecked(bubble)
        self.speech_bubble_toggle['toggle'].blockSignals(False)
        
        self.snap_toggle['toggle'].blockSignals(True)
        self.snap_toggle['toggle'].setChecked(snap)
        self.snap_toggle['toggle'].blockSignals(False)
        
        # P7 Settings
        personality = self.config.get('personality_enabled', True) if self.config else True
        time_aware = self.config.get('time_aware_mode', True) if self.config else True
        idle_timeout = self.config.get('idle_timeout_minutes', 5) if self.config else 5
        
        self.personality_toggle['toggle'].blockSignals(True)
        self.personality_toggle['toggle'].setChecked(personality)
        self.personality_toggle['toggle'].blockSignals(False)
        
        self.time_aware_toggle['toggle'].blockSignals(True)
        self.time_aware_toggle['toggle'].setChecked(time_aware)
        self.time_aware_toggle['toggle'].blockSignals(False)
        
        self.idle_timeout_slider['slider'].blockSignals(True)
        self.idle_timeout_slider['slider'].setValue(idle_timeout)
        self.idle_timeout_slider['value_label'].setText(f"{idle_timeout} min")
        self.idle_timeout_slider['slider'].blockSignals(False)
        
        # Glow Settings
        glow_enabled = self.config.get('glow_enabled', True) if self.config else True
        glow_intensity = self.config.get('glow_intensity', 0.4) if self.config else 0.4
        
        self.glow_toggle['toggle'].blockSignals(True)
        self.glow_toggle['toggle'].setChecked(glow_enabled)
        self.glow_toggle['toggle'].blockSignals(False)
        
        self.glow_intensity_slider['slider'].blockSignals(True)
        self.glow_intensity_slider['slider'].setValue(int(glow_intensity * 100))
        self.glow_intensity_slider['value_label'].setText(f"{int(glow_intensity * 100)}%")
        self.glow_intensity_slider['slider'].blockSignals(False)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Callbacks
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _on_size_changed(self, value: int):
        """Handle size slider change."""
        if self.config:
            self.config.set('scale_percent', value)
        self.size_changed.emit(value)
        logger.debug(f"⚙️ Size changed: {value}%")
    
    def _on_opacity_changed(self, value: int):
        """Handle opacity slider change."""
        opacity = value / 100.0
        if self.config:
            self.config.set('opacity', opacity)
        self.opacity_changed.emit(opacity)
        logger.debug(f"⚙️ Opacity changed: {value}%")
    
    def _on_animations_toggled(self, enabled: bool):
        """Handle animations toggle."""
        if self.config:
            self.config.set('animations_enabled', enabled)
        self.animations_toggled.emit(enabled)
        logger.debug(f"⚙️ Animations: {enabled}")
    
    def _on_speech_bubble_toggled(self, enabled: bool):
        """Handle speech bubble toggle."""
        if self.config:
            self.config.set('show_speech_bubble', enabled)
        self.speech_bubble_toggled.emit(enabled)
        logger.debug(f"⚙️ Speech bubble: {enabled}")
    
    def _on_snap_toggled(self, enabled: bool):
        """Handle snap to edges toggle."""
        if self.config:
            self.config.set('snap_to_edges', enabled)
        self.snap_to_edges_toggled.emit(enabled)
        logger.debug(f"⚙️ Snap to edges: {enabled}")
    
    def _on_speed_changed(self, value: int):
        """Handle expression speed slider change."""
        speed = value / 100.0
        if self.config:
            self.config.set('expression_speed', speed)
        self.expression_speed_changed.emit(speed)
        logger.debug(f"⚙️ Expression speed: {value}%")
    
    def _on_personality_toggled(self, enabled: bool):
        """Handle personality toggle."""
        if self.config:
            self.config.set('personality_enabled', enabled)
        self.personality_toggled.emit(enabled)
        logger.debug(f"⚙️ Personality: {enabled}")
    
    def _on_time_aware_toggled(self, enabled: bool):
        """Handle time-aware mode toggle."""
        if self.config:
            self.config.set('time_aware_mode', enabled)
        self.time_aware_toggled.emit(enabled)
        logger.debug(f"⚙️ Time-aware mode: {enabled}")
    
    def _on_idle_timeout_changed(self, value: int):
        """Handle idle timeout slider change."""
        if self.config:
            self.config.set('idle_timeout_minutes', value)
        self.idle_timeout_changed.emit(value)
        logger.debug(f"⚙️ Idle timeout: {value} min")
    
    def _on_glow_toggled(self, enabled: bool):
        """Handle glow effect toggle."""
        if self.config:
            self.config.set('glow_enabled', enabled)
        self.glow_toggled.emit(enabled)
        logger.debug(f"⚙️ Glow effect: {enabled}")
    
    def _on_glow_intensity_changed(self, value: int):
        """Handle glow intensity slider change."""
        intensity = value / 100.0
        if self.config:
            self.config.set('glow_intensity', intensity)
        self.glow_intensity_changed.emit(intensity)
        logger.debug(f"⚙️ Glow intensity: {value}%")
    
    def _close_panel(self):
        """Close the settings panel with fade-out animation."""
        self.settings_closed.emit()
        self._fade_out()
    
    def _fade_in(self):
        """Smooth fade-in animation."""
        self.setWindowOpacity(0.0)
        
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)  # 200ms fade in
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.start()
    
    def _fade_out(self):
        """Smooth fade-out animation then hide."""
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(150)  # 150ms fade out
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_animation.finished.connect(self.hide)
        self.fade_animation.start()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Public Methods
    # ═══════════════════════════════════════════════════════════════════════════
    
    def show_at(self, pos: QPoint):
        """Show panel at specified position with smooth animation."""
        # Adjust to ensure on screen
        screen = QApplication.primaryScreen().geometry()
        
        x = pos.x()
        y = pos.y()
        
        # Keep on screen
        if x + self.width() > screen.width() - 10:
            x = screen.width() - self.width() - 10
        if y + self.height() > screen.height() - 10:
            y = screen.height() - self.height() - 10
        if x < 10:
            x = 10
        if y < 10:
            y = 10
        
        self.move(x, y)
        self.show()
        self.raise_()
        self._fade_in()
    
    def show_near_pet(self, pet_geometry):
        """Show panel near the pet widget with smooth animation."""
        # Position to the left of pet, or right if not enough space
        screen = QApplication.primaryScreen().geometry()
        
        # Try left side
        x = pet_geometry.x() - self.width() - 20
        y = pet_geometry.y()
        
        # If off screen, try right side
        if x < 10:
            x = pet_geometry.x() + pet_geometry.width() + 20
        
        # If still off screen, center on screen
        if x + self.width() > screen.width() - 10:
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
        
        # Keep Y on screen
        if y + self.height() > screen.height() - 10:
            y = screen.height() - self.height() - 10
        if y < 10:
            y = 10
        
        self.move(x, y)
        self.show()
        self.raise_()
        self._fade_in()  # Smooth fade-in animation
        
        logger.info("⚙️ Settings panel shown")

