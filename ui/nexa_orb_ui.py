"""
Nexa Orb UI - Brand New Design matching the reference image
Features:
- Centered glowing orb with concentric rings
- Waveform visualization
- Three-state indicator (LISTENING, THINKING, RESPONDING)
- Clean dark background with cyan accents
- Theme-aware colors
"""

import logging
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Qt, QTimer, QRectF, QPointF, Slot
from PySide6.QtGui import QPainter, QPen, QColor, QRadialGradient, QPainterPath, QLinearGradient
from Themes.theme_manager import get_theme_manager

logger = logging.getLogger(__name__)


class NexaOrbWidget(QWidget):
    """
    The central orb visualization with rings and waveforms.
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)  # Increased from 500
        
        # Theme manager
        self.theme_manager = get_theme_manager()
        
        # Connect to theme changes
        try:
            self.theme_manager.theme_changed.connect(
                self._on_theme_changed,
                Qt.ConnectionType.QueuedConnection
            )
            logger.info("✅ Orb connected to theme_changed signal")
        except Exception as e:
            logger.error(f"❌ Failed to connect theme signal: {e}")
        
        # Animation state
        self.rotation_angle = 0.0
        self.pulse_phase = 0.0
        self.audio_amplitude = 0.0
        
        # Waveform data (for audio visualization)
        self.waveform_points = [0.0] * 60  # Number of bars
        self.waveform_index = 0
        
        # State
        self.current_state = "IDLE"  # IDLE, LISTENING, THINKING, RESPONDING
        
        # Animation timer - 120 FPS for smoother animations
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(8)  # 8ms = ~120 FPS (was 16ms = 60fps)
        
        logger.info("✅ NexaOrbWidget initialized")
    
    @Slot()
    def _on_theme_changed(self):
        """Handle theme changes - force repaint with new theme colors."""
        logger.info(f"🔔 Orb received theme_changed signal! New theme: {self.theme_manager.current_theme_name}")
        # Reset debug flag so we log the new theme
        if hasattr(self, '_debug_logged'):
            delattr(self, '_debug_logged')
        self.update()  # Force repaint
        logger.info(f"🎨 Orb forced repaint for theme: {self.theme_manager.current_theme_name}")
    
    def set_state(self, state: str):
        """Update the visual state."""
        self.current_state = state.upper()
        logger.info(f"🎨 Orb state: {self.current_state}")
    
    def set_audio_amplitude(self, amplitude: float):
        """Update audio amplitude for waveform."""
        self.audio_amplitude = max(0.0, min(1.0, amplitude))
        
        # Add to waveform
        self.waveform_points[self.waveform_index] = self.audio_amplitude
        self.waveform_index = (self.waveform_index + 1) % len(self.waveform_points)
    
    def _update_animation(self):
        """Update animation state."""
        # Rotate rings
        self.rotation_angle += 0.5
        if self.rotation_angle >= 360:
            self.rotation_angle = 0
        
        # Pulse effect
        self.pulse_phase += 0.05
        if self.pulse_phase >= math.pi * 2:
            self.pulse_phase = 0
        
        self.update()
    
    def paintEvent(self, event):
        """Draw the orb and rings with optimized rendering."""
        painter = QPainter(self)
        # Use smooth pixmap transform instead of full antialiasing for better performance
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        
        # Get center and scale based on widget size
        widget_size = min(self.width(), self.height())
        # Better scaling: use percentage of widget size instead of fixed base
        scale_factor = widget_size / 400.0  # Base size is now 400 for better proportion
        center_x = self.width() / 2
        center_y = self.height() / 2
        center = QPointF(center_x, center_y)
        
        # Determine colors based on state and theme
        tm = self.theme_manager
        current_theme = tm.current_theme_name
        
        # Much lower glow alpha for subtle appearance (especially in light mode)
        glow_alpha = 170 if current_theme == "light" else 120
        glow_alpha_idle = 130 if current_theme == "light" else 90
        
        if self.current_state == "LISTENING":
            color_hex = tm.get_color('orb', 'listening')
            primary_color = QColor(color_hex)
            glow_color = QColor(primary_color)
            glow_color.setAlpha(glow_alpha)
        elif self.current_state == "THINKING":
            color_hex = tm.get_color('orb', 'thinking')
            primary_color = QColor(color_hex)
            glow_color = QColor(primary_color)
            glow_color.setAlpha(glow_alpha)
        elif self.current_state == "RESPONDING":
            color_hex = tm.get_color('orb', 'responding')
            primary_color = QColor(color_hex)
            glow_color = QColor(primary_color)
            glow_color.setAlpha(glow_alpha)
        else:
            color_hex = tm.get_color('orb', 'idle')
            primary_color = QColor(color_hex)
            glow_color = QColor(primary_color)
            glow_color.setAlpha(glow_alpha_idle)
        
        # Calculate pulse scale
        pulse_scale = 1.0 + (math.sin(self.pulse_phase) * 0.1)
        
        # --- Draw concentric rings (3 rings) with better scaled radii ---
        # Use percentage-based radii for better responsive sizing
        base_ring_radii = [160, 120, 85]  # Adjusted proportions
        ring_radii = [r * scale_factor for r in base_ring_radii]
        for i, radius in enumerate(ring_radii):
            scaled_radius = radius * pulse_scale
            
            # Rotate each ring differently
            rotation = self.rotation_angle * (1.0 + i * 0.3)
            if i % 2 == 1:
                rotation = -rotation  # Reverse direction
            
            self._draw_ring(painter, center, scaled_radius, primary_color, rotation, i)
        
        # --- Draw waveform integrated with orb ---
        waveform_radius = 65 * scale_factor  # Increased from 80
        self._draw_waveform(painter, center, waveform_radius, primary_color)
        
        # --- Draw central glowing orb ---
        orb_radius = 50 * scale_factor * pulse_scale  # Increased from 60
        self._draw_central_orb(painter, center, orb_radius, primary_color, glow_color)
    
    def _draw_ring(self, painter: QPainter, center: QPointF, radius: float, 
                   color: QColor, rotation: float, ring_index: int):
        """Draw a single concentric ring with segments that react to audio."""
        # Make rings react to audio
        audio_scale = 1.0 + (self.audio_amplitude * 0.15)
        radius *= audio_scale
        
        pen = QPen(color)
        pen.setWidth(2)  # Thinner for better performance
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Draw circle
        rect = QRectF(center.x() - radius, center.y() - radius, 
                     radius * 2, radius * 2)
        
        # Draw arc segments for a broken ring effect
        num_segments = 10  # Reduced from 12 for better performance
        gap_angle = 8  # degrees
        segment_angle = (360 / num_segments) - gap_angle
        
        # Adjust base alpha based on theme
        current_theme = self.theme_manager.current_theme_name
        base_alpha = 70 if current_theme == "light" else 35
        max_alpha = 180 if current_theme == "light" else 100
        
        # DEBUG: Log theme and alpha values once
        if not hasattr(self, '_debug_logged'):
            logger.info(f"🎨 Orb Theme: {current_theme}, Base Alpha: {base_alpha}, Max Alpha: {max_alpha}")
            self._debug_logged = True
        
        for i in range(num_segments):
            start_angle = (i * 360 / num_segments) + rotation
            
            # Lower opacity for subtle rings
            segment_alpha = base_alpha + int(self.audio_amplitude * 40) + int(math.sin(math.radians(start_angle + self.pulse_phase * 50)) * 20)
            segment_color = QColor(color)
            segment_color.setAlpha(max(30, min(max_alpha, segment_alpha)))
            
            painter.setPen(QPen(segment_color, 2))
            painter.drawArc(rect, int(start_angle * 16), int(segment_angle * 16))
    
    def _draw_waveform(self, painter: QPainter, center: QPointF, 
                       base_radius: float, color: QColor):
        """Draw audio waveform as bars around the orb."""
        num_bars = len(self.waveform_points)
        angle_step = 360.0 / num_bars
        bar_width = 4
        
        pen = QPen(color)
        pen.setWidth(bar_width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        
        for i in range(num_bars):
            # Get waveform amplitude for this bar
            idx = (self.waveform_index + i) % num_bars
            amplitude = self.waveform_points[idx]
            
            # Add some baseline movement even without audio
            if amplitude < 0.1:
                amplitude = 0.1 + (math.sin(self.pulse_phase + i * 0.3) * 0.05)
            
            # Calculate angle
            angle_deg = i * angle_step - 90  # Start from top
            angle_rad = math.radians(angle_deg)
            
            # Calculate bar position (outside the innermost ring)
            inner_radius = base_radius
            bar_length = 20 + (amplitude * 40)  # Bar extends outward based on amplitude
            
            # Start and end points of the bar
            start_x = center.x() + inner_radius * math.cos(angle_rad)
            start_y = center.y() + inner_radius * math.sin(angle_rad)
            end_x = center.x() + (inner_radius + bar_length) * math.cos(angle_rad)
            end_y = center.y() + (inner_radius + bar_length) * math.sin(angle_rad)
            
            # Subtle bar opacity - theme adaptive
            current_theme = self.theme_manager.current_theme_name
            base_bar_alpha = 70 if current_theme == "light" else 35
            max_bar_alpha = 160 if current_theme == "light" else 85
            bar_color = QColor(color)
            bar_color.setAlpha(int(base_bar_alpha + amplitude * max_bar_alpha))
            painter.setPen(QPen(bar_color, bar_width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            painter.drawLine(QPointF(start_x, start_y), QPointF(end_x, end_y))
    
    def _draw_central_orb(self, painter: QPainter, center: QPointF, 
                          radius: float, primary_color: QColor, glow_color: QColor):
        """Draw the central glowing sphere."""
        # Get theme for adaptive brightness
        current_theme = self.theme_manager.current_theme_name
        
        # Much subtler outer glow
        glow_base = 45 if current_theme == "light" else 30
        for i in range(3):
            glow_radius = radius + (i + 1) * 15
            gradient = QRadialGradient(center, glow_radius)
            gradient.setColorAt(0, QColor(glow_color.red(), glow_color.green(), 
                                         glow_color.blue(), glow_base - i * 12))
            gradient.setColorAt(1, QColor(glow_color.red(), glow_color.green(), 
                                         glow_color.blue(), 0))
            
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(gradient)
            painter.drawEllipse(center, glow_radius, glow_radius)
        
        # Main orb with gradient - theme-adaptive alpha
        orb_alpha_center = 220 if current_theme == "light" else 140
        orb_alpha_mid = 170 if current_theme == "light" else 100
        orb_alpha_edge = 120 if current_theme == "light" else 70
        
        gradient = QRadialGradient(center, radius)
        gradient.setColorAt(0, QColor(primary_color.red(), primary_color.green(), 
                                     primary_color.blue(), orb_alpha_center))
        gradient.setColorAt(0.6, QColor(primary_color.red(), primary_color.green(), 
                                       primary_color.blue(), orb_alpha_mid))
        gradient.setColorAt(1, QColor(primary_color.red() // 2, primary_color.green() // 2, 
                                     primary_color.blue() // 2, orb_alpha_edge))
        
        painter.setPen(QPen(primary_color, 2))
        painter.setBrush(gradient)
        painter.drawEllipse(center, radius, radius)
        
        # Subtle highlight shine
        shine_alpha = 120 if current_theme == "light" else 70
        shine_center = QPointF(center.x() - radius * 0.3, center.y() - radius * 0.3)
        shine_gradient = QRadialGradient(shine_center, radius * 0.4)
        shine_gradient.setColorAt(0, QColor(255, 255, 255, shine_alpha))
        shine_gradient.setColorAt(1, QColor(255, 255, 255, 0))
        
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(shine_gradient)
        painter.drawEllipse(shine_center, radius * 0.4, radius * 0.4)
