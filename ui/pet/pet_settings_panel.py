"""
Companion Settings Panel - Customization UI for Nexa Companion
A floating futuristic settings panel with animated toggles and modern styling.

Features:
- Size slider (50-200%)
- Opacity slider (20-100%)
- Animated toggle switches with sliding dot
- Nexa theme (cyan/blue on dark navy)
- Glassmorphism with gradient border glow
- Section cards with subtle backgrounds

Part of P6: Settings Panel & Customization
"""

import logging
from typing import Optional, Callable

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
    QPushButton, QFrame, QGraphicsDropShadowEffect,
    QApplication
)
from PySide6.QtCore import (
    Qt, Signal, QPropertyAnimation, QEasingCurve, QPoint,
    Property, QRectF
)
from PySide6.QtGui import QColor, QFont, QPainter, QPen

logger = logging.getLogger(__name__)


# ═══════════════════════════════════════════════════════════════════════════
# Animated Toggle Switch Widget
# ═══════════════════════════════════════════════════════════════════════════

class ToggleSwitch(QWidget):
    """
    Modern animated toggle switch with sliding circle handle.
    Mimics iOS/Material Design toggle with smooth animation.
    """
    toggled = Signal(bool)

    def __init__(self, checked=False, parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 24)
        self._checked = checked
        self._handle_pos = 1.0 if checked else 0.0

        # Smooth slide animation
        self._anim = QPropertyAnimation(self, b"handlePos")
        self._anim.setDuration(180)
        self._anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def get_handle_pos(self):
        return self._handle_pos

    def set_handle_pos(self, val):
        self._handle_pos = val
        self.update()

    handlePos = Property(float, get_handle_pos, set_handle_pos)

    def isChecked(self):
        return self._checked

    def setChecked(self, checked):
        if self._checked != checked:
            self._checked = checked
            self._handle_pos = 1.0 if checked else 0.0
            self.update()

    def mousePressEvent(self, event):
        self._checked = not self._checked
        self._anim.stop()
        self._anim.setStartValue(self._handle_pos)
        self._anim.setEndValue(1.0 if self._checked else 0.0)
        self._anim.start()
        self.toggled.emit(self._checked)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        r = h / 2.0
        t = self._handle_pos  # 0.0 → 1.0 interpolation

        # ── Track ──
        # Blend from dark gray (off) to cyan-blue (on)
        off_r, off_g, off_b = 40, 48, 65
        on_r, on_g, on_b = 0, 170, 240
        tr = int(off_r + (on_r - off_r) * t)
        tg = int(off_g + (on_g - off_g) * t)
        tb = int(off_b + (on_b - off_b) * t)

        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(tr, tg, tb, 220))
        p.drawRoundedRect(QRectF(0, 0, w, h), r, r)

        # ── Track border (glows when active) ──
        border_alpha = int(40 + 140 * t)
        p.setPen(QPen(QColor(0, 200, 255, border_alpha), 1.0))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(QRectF(0.5, 0.5, w - 1, h - 1), r, r)

        # ── Handle (white circle with shadow) ──
        handle_d = h - 6  # circle diameter
        handle_x = 3 + t * (w - h)
        handle_y = 3.0

        # Shadow under handle
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 35))
        p.drawEllipse(QRectF(handle_x, handle_y + 1, handle_d, handle_d))

        # Handle circle
        p.setBrush(QColor(255, 255, 255, 250))
        p.drawEllipse(QRectF(handle_x, handle_y, handle_d, handle_d))

        p.end()


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
        """Setup the panel UI with section cards and animated toggles."""
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(0)
        
        # Container for styling
        self.container = QFrame()
        self.container.setObjectName("settingsContainer")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(14, 12, 14, 14)
        container_layout.setSpacing(8)
        
        # Header with title and close button
        header = QHBoxLayout()
        header.setSpacing(10)
        
        title = QLabel("✦ Companion Settings")
        title.setObjectName("panelTitle")
        title.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        
        self.close_btn = QPushButton("✕")
        self.close_btn.setObjectName("closeButton")
        self.close_btn.setFixedSize(30, 30)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self._close_panel)
        
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.close_btn)
        container_layout.addLayout(header)
        
        container_layout.addSpacing(4)
        
        # ═══════════════════════════════════════════════════════════════
        # Appearance Section Card
        # ═══════════════════════════════════════════════════════════════
        appearance_card, appearance_layout = self._create_section_card("Appearance")
        
        self.size_slider = self._create_slider_row(
            "Size", 50, 200, 100, "%", self._on_size_changed
        )
        appearance_layout.addLayout(self.size_slider['layout'])
        
        self.opacity_slider = self._create_slider_row(
            "Opacity", 20, 100, 100, "%", self._on_opacity_changed
        )
        appearance_layout.addLayout(self.opacity_slider['layout'])
        
        container_layout.addWidget(appearance_card)
        
        # ═══════════════════════════════════════════════════════════════
        # Visual Effects Section Card
        # ═══════════════════════════════════════════════════════════════
        effects_card, effects_layout = self._create_section_card("Effects")
        
        self.glow_toggle = self._create_toggle_row(
            "Cyan Glow", True, self._on_glow_toggled
        )
        effects_layout.addLayout(self.glow_toggle['layout'])
        
        self.glow_intensity_slider = self._create_slider_row(
            "Glow Power", 10, 100, 60, "%", self._on_glow_intensity_changed
        )
        effects_layout.addLayout(self.glow_intensity_slider['layout'])
        
        self.animations_toggle = self._create_toggle_row(
            "Animations", True, self._on_animations_toggled
        )
        effects_layout.addLayout(self.animations_toggle['layout'])
        
        container_layout.addWidget(effects_card)
        
        # ═══════════════════════════════════════════════════════════════
        # Behavior Section Card
        # ═══════════════════════════════════════════════════════════════
        behavior_card, behavior_layout = self._create_section_card("Behavior")
        
        self.speech_bubble_toggle = self._create_toggle_row(
            "Speech Bubble", True, self._on_speech_bubble_toggled
        )
        behavior_layout.addLayout(self.speech_bubble_toggle['layout'])
        
        self.snap_toggle = self._create_toggle_row(
            "Snap to Edges", True, self._on_snap_toggled
        )
        behavior_layout.addLayout(self.snap_toggle['layout'])
        
        self.speed_slider = self._create_slider_row(
            "Expression Speed", 50, 200, 100, "%", self._on_speed_changed
        )
        behavior_layout.addLayout(self.speed_slider['layout'])
        
        container_layout.addWidget(behavior_card)
        
        # ═══════════════════════════════════════════════════════════════
        # Personality Section Card
        # ═══════════════════════════════════════════════════════════════
        personality_card, personality_layout = self._create_section_card("Personality")
        
        self.personality_toggle = self._create_toggle_row(
            "Enable Personality", True, self._on_personality_toggled
        )
        personality_layout.addLayout(self.personality_toggle['layout'])
        
        self.time_aware_toggle = self._create_toggle_row(
            "Time-Aware Mode", True, self._on_time_aware_toggled
        )
        personality_layout.addLayout(self.time_aware_toggle['layout'])
        
        self.idle_timeout_slider = self._create_slider_row(
            "Sleep After", 1, 10, 5, " min", self._on_idle_timeout_changed
        )
        personality_layout.addLayout(self.idle_timeout_slider['layout'])
        
        container_layout.addWidget(personality_card)
        
        # End spacer
        container_layout.addSpacing(6)
        
        main_layout.addWidget(self.container)
        
        # Add glow effect to container
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(50)
        shadow.setColor(QColor(0, 160, 255, 90))
        shadow.setOffset(0, 3)
        self.container.setGraphicsEffect(shadow)
    
    def _create_section_card(self, title: str):
        """Create a section card with header and subtle background."""
        card = QFrame()
        card.setObjectName("sectionCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(12, 8, 12, 10)
        card_layout.setSpacing(4)
        
        # Section header label
        header = QLabel(title)
        header.setObjectName("sectionHeader")
        card_layout.addWidget(header)
        
        return card, card_layout
    
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
        """Create a labeled toggle switch row with animated ToggleSwitch."""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 3, 0, 3)
        layout.setSpacing(8)
        
        # Label - fixed width matching sliders
        lbl = QLabel(label)
        lbl.setObjectName("settingLabel")
        lbl.setFixedWidth(110)
        
        # Spacer to push toggle to right
        layout.addWidget(lbl)
        layout.addStretch(1)
        
        # Animated toggle switch
        toggle = ToggleSwitch(checked=default)
        toggle.toggled.connect(callback)
        
        layout.addWidget(toggle)
        
        return {
            'layout': layout,
            'toggle': toggle
        }
    
    def _apply_styling(self):
        """Apply modern Nexa futuristic theme styling with section cards."""
        self.setStyleSheet("""
            #settingsContainer {
                background: qlineargradient(
                    x1:0, y1:0, x2:0.2, y2:1,
                    stop:0 rgba(14, 22, 45, 252),
                    stop:0.5 rgba(10, 18, 38, 250),
                    stop:1 rgba(8, 14, 32, 248)
                );
                border: 1px solid rgba(0, 180, 255, 0.2);
                border-radius: 16px;
            }
            
            #panelTitle {
                color: #00D4FF;
                padding: 0;
                letter-spacing: 1px;
            }
            
            #closeButton {
                background-color: rgba(255, 60, 60, 0.15);
                border: 1px solid rgba(255, 80, 80, 0.3);
                border-radius: 15px;
                color: rgba(255, 140, 140, 0.9);
                font-weight: bold;
                font-size: 13px;
            }
            
            #closeButton:hover {
                background-color: rgba(255, 80, 80, 0.35);
                border-color: rgba(255, 100, 100, 0.5);
                color: #FF9999;
            }
            
            #sectionCard {
                background: rgba(15, 30, 60, 0.5);
                border: 1px solid rgba(0, 160, 255, 0.08);
                border-radius: 12px;
            }
            
            #sectionCard:hover {
                border-color: rgba(0, 180, 255, 0.15);
                background: rgba(18, 35, 65, 0.55);
            }
            
            #separator {
                background-color: rgba(0, 150, 220, 50);
                max-height: 1px;
                margin: 8px 0 4px 0;
            }
            
            #settingLabel {
                color: rgba(210, 230, 255, 0.85);
                font-size: 12px;
                font-family: "Segoe UI", sans-serif;
            }
            
            #sectionHeader {
                color: rgba(0, 210, 255, 0.9);
                font-size: 11px;
                font-weight: bold;
                font-family: "Segoe UI", sans-serif;
                letter-spacing: 1px;
                padding: 2px 0 4px 0;
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
                background: rgba(25, 45, 75, 200);
                height: 5px;
                border-radius: 2px;
            }
            
            #settingSlider::handle:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #00E0FF, stop:1 #0080FF);
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
                border: 1.5px solid rgba(255, 255, 255, 80);
            }
            
            #settingSlider::handle:horizontal:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #40F0FF, stop:1 #00A0FF);
                border: 1.5px solid rgba(255, 255, 255, 120);
            }
            
            #settingSlider::sub-page:horizontal {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(0, 96, 255, 0.7), stop:1 rgba(0, 192, 255, 0.8));
                border-radius: 2px;
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

