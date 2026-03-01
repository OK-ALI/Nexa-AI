"""
Pet Radial Menu - Quick Actions Pie Menu
A futuristic circular radial menu with action wedges around a glowing "N" center.

Features:
- Sci-fi HUD-style design with neon glow effects
- Animated pulsing rings and particle effects
- Dynamic wedge count (supports 8-10+ items)
- Glassmorphism with holographic accents
- Smooth hover transitions with glow
- Keyboard shortcuts

Part of P5: Quick Actions & Context Menu
"""

import math
import logging
import random
from typing import List, Callable, Optional, Tuple
from dataclasses import dataclass

from PySide6.QtWidgets import QWidget, QApplication, QGraphicsDropShadowEffect
from PySide6.QtCore import (
    Qt, QPoint, QPointF, QRectF, QTimer, Signal, 
    QPropertyAnimation, QEasingCurve, Property
)
from PySide6.QtGui import (
    QPainter, QColor, QPen, QBrush, QFont, QFontMetrics,
    QPainterPath, QRadialGradient, QLinearGradient, QConicalGradient,
    QMouseEvent, QKeyEvent, QPixmap
)

logger = logging.getLogger(__name__)


@dataclass
class RadialMenuItem:
    """Single menu item (wedge) configuration."""
    icon: str           # Emoji icon
    label: str          # Action name
    action: Callable    # Function to call
    shortcut: str       # Keyboard shortcut key


class PetRadialMenu(QWidget):
    """
    Futuristic radial pie menu for pet quick actions.
    
    Features a sci-fi HUD design with neon glows, animated rings,
    and holographic styling around a pulsing "N" center.
    """
    
    # Signals
    action_triggered = Signal(str)  # Emits action label when triggered
    menu_closed = Signal()
    
    # Geometry constants
    INNER_RADIUS = 50      # Center "N" area radius
    OUTER_RADIUS = 150     # Total menu radius
    DEFAULT_WEDGE_COUNT = 10
    
    @property
    def WEDGE_COUNT(self):
        """Dynamic wedge count based on items."""
        return len(self.items) if self.items else self.DEFAULT_WEDGE_COUNT
    
    @property
    def WEDGE_ANGLE(self):
        """Degrees per wedge (calculated dynamically)."""
        return 360 / self.WEDGE_COUNT if self.WEDGE_COUNT > 0 else 36
    
    # Futuristic color scheme - Cyan/Blue neon on dark
    COLORS = {
        # Background layers
        'bg_outer': QColor(5, 10, 20, 250),         # Deep space black
        'bg_inner': QColor(10, 20, 40, 245),        # Dark navy
        
        # Neon accents
        'neon_cyan': QColor(0, 255, 255),           # Pure cyan
        'neon_blue': QColor(0, 150, 255),           # Electric blue
        'neon_purple': QColor(150, 50, 255),        # Neon purple
        'neon_pink': QColor(255, 50, 150),          # Hot pink accent
        
        # Wedge colors
        'wedge_fill': QColor(15, 30, 60, 180),      # Translucent dark
        'wedge_hover': QColor(0, 100, 180, 200),    # Hover fill
        'wedge_border': QColor(0, 150, 220, 100),   # Subtle border
        'wedge_glow': QColor(0, 200, 255, 150),     # Hover glow
        
        # Text
        'text_bright': QColor(255, 255, 255),       # Pure white
        'text_dim': QColor(150, 180, 210),          # Muted blue-white
        'text_glow': QColor(100, 200, 255),         # Glowing text
        
        # Center
        'center_bg': QColor(10, 25, 50, 250),       # Dark center
        'center_glow': QColor(0, 200, 255),         # Cyan glow
        'center_ring': QColor(0, 255, 255, 100),    # Ring color
    }
    
    def __init__(self, parent=None):
        # Create as standalone top-level window
        super().__init__(None)
        
        self.parent_widget = parent
        self.items: List[RadialMenuItem] = []
        self.hovered_index: int = -1
        self.visible = False
        
        # Animation state
        self._pulse_phase = 0.0
        self._ring_rotation = 0.0
        self._particles = []
        
        # Setup
        self._setup_window()
        self._setup_default_items()
        self._setup_animations()
        self._setup_icons()
        
        logger.info("🎯 Radial menu initialized")
    
    def _setup_window(self):
        """Configure window properties."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # Size based on outer radius + glow padding
        size = self.OUTER_RADIUS * 2 + 60
        self.setFixedSize(size, size)
        
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def _setup_default_items(self):
        """Setup default menu items."""
        self.items = [
            RadialMenuItem("🔊", "Volume", lambda: None, "V"),
            RadialMenuItem("📸", "Screenshot", lambda: None, "S"),
            RadialMenuItem("🎵", "Music", lambda: None, "M"),
            RadialMenuItem("📱", "Share", lambda: None, "H"),
            RadialMenuItem("🌐", "Mode", lambda: None, "O"),
            RadialMenuItem("⚙️", "Settings", lambda: None, ","),
            RadialMenuItem("💤", "Sleep/Wake", lambda: None, "Z"),
            RadialMenuItem("📝", "Content", lambda: None, "C"),
            RadialMenuItem("🎤", "Mic", lambda: None, "N"),
            RadialMenuItem("❌", "Exit", lambda: None, "Esc"),
        ]
    
    def _setup_animations(self):
        """Setup animation timers."""
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animations)
        self.fade_animation = None
        
        # Initialize particles
        self._init_particles()
    
    def _setup_icons(self):
        """Setup PNG icons for menu items."""
        from ui.music_indicator import get_icon_manager
        self.icon_manager = get_icon_manager()
        
        # Map menu labels to icon names
        self.ICON_MAP = {
            'Volume': 'volume',
            'Screenshot': 'capture',
            'Music': 'music_dark',
            'Share': 'share',
            'Mode': 'mode',
            'Settings': 'settings',
            'Sleep/Wake': 'sleep',  # Could switch to 'wake' when awake
            'Content': 'content',
            'Mic': 'mic_on',        # Could switch to 'mic_off' when muted
            'Exit': 'exit',
        }
        
        # Pre-load icon pixmaps for radial menu (40px for better visibility)
        self._icon_cache = {}
        for label, icon_name in self.ICON_MAP.items():
            self._icon_cache[label] = self.icon_manager.get_pixmap(icon_name, 40)
    
    def _init_particles(self):
        """Initialize floating particle effects."""
        self._particles = []
        for _ in range(15):
            self._particles.append({
                'angle': random.uniform(0, 360),
                'radius': random.uniform(self.INNER_RADIUS + 10, self.OUTER_RADIUS - 10),
                'speed': random.uniform(0.3, 1.0),
                'size': random.uniform(1.5, 3.0),
                'alpha': random.uniform(0.3, 0.8),
            })
    
    def _update_animations(self):
        """Update animation state."""
        # Pulse effect (0-1 oscillation)
        self._pulse_phase = (self._pulse_phase + 0.05) % (2 * math.pi)
        
        # Rotating ring effect
        self._ring_rotation = (self._ring_rotation + 0.5) % 360
        
        # Update particles
        for p in self._particles:
            p['angle'] = (p['angle'] + p['speed']) % 360
        
        self.update()
    
    def set_items(self, items: List[RadialMenuItem]):
        """Set menu items with actions."""
        self.items = items
        self.update()
    
    def show_at(self, global_pos: QPoint):
        """Show menu centered at the given global position."""
        center_offset = self.width() // 2
        x = global_pos.x() - center_offset
        y = global_pos.y() - center_offset
        
        # Ensure menu stays on screen
        screen = QApplication.primaryScreen().geometry()
        x = max(10, min(x, screen.width() - self.width() - 10))
        y = max(10, min(y, screen.height() - self.height() - 10))
        
        self.move(x, y)
        self.show()
        self.raise_()
        self.setFocus()
        self.visible = True
        
        # Start animations
        self.animation_timer.start(33)  # ~30fps
        
        # Fade in
        self._fade_in()
        
        logger.debug(f"🎯 Radial menu shown at ({x}, {y})")
    
    def _fade_in(self):
        """Animate fade in."""
        self.setWindowOpacity(0.0)
        
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(200)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.start()
    
    def _fade_out_and_close(self):
        """Animate fade out then close."""
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(150)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_animation.finished.connect(self._on_fade_out_finished)
        self.fade_animation.start()
    
    def _on_fade_out_finished(self):
        """Called when fade out completes."""
        self.animation_timer.stop()
        self.hide()
        self.visible = False
        self.menu_closed.emit()
    
    def close_menu(self):
        """Close the menu with animation."""
        if self.visible:
            self._fade_out_and_close()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Painting - Futuristic Design
    # ═══════════════════════════════════════════════════════════════════════════
    
    def paintEvent(self, event):
        """Paint the futuristic radial menu."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = QPointF(self.width() / 2, self.height() / 2)
        
        # Layer 1: Outer glow halo
        self._paint_outer_glow(painter, center)
        
        # Layer 2: Background circle
        self._paint_background(painter, center)
        
        # Layer 3: Animated outer ring
        self._paint_outer_ring(painter, center)
        
        # Layer 4: Wedges
        for i in range(self.WEDGE_COUNT):
            self._paint_wedge(painter, center, i, i == self.hovered_index)
        
        # Layer 5: Divider lines between wedges
        self._paint_dividers(painter, center)
        
        # Layer 6: Floating particles
        self._paint_particles(painter, center)
        
        # Layer 7: Inner ring (border around center)
        self._paint_inner_ring(painter, center)
        
        # Layer 8: Center "N" logo with glow
        self._paint_center(painter, center)
        
        painter.end()
    
    def _paint_outer_glow(self, painter: QPainter, center: QPointF):
        """Paint the outer neon glow halo."""
        pulse = 0.5 + 0.5 * math.sin(self._pulse_phase)
        
        # Multi-layer glow for depth
        glow_layers = [
            (self.OUTER_RADIUS + 30, 20 + int(pulse * 15)),
            (self.OUTER_RADIUS + 20, 40 + int(pulse * 20)),
            (self.OUTER_RADIUS + 10, 30),
        ]
        
        for radius, alpha in glow_layers:
            glow = QRadialGradient(center, radius)
            glow.setColorAt(0.5, QColor(0, 180, 255, alpha))
            glow.setColorAt(0.8, QColor(0, 100, 200, alpha // 2))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, radius, radius)
    
    def _paint_background(self, painter: QPainter, center: QPointF):
        """Paint the main background circle."""
        # Gradient background
        bg = QRadialGradient(center, self.OUTER_RADIUS)
        bg.setColorAt(0.0, self.COLORS['bg_inner'])
        bg.setColorAt(0.7, self.COLORS['bg_outer'])
        bg.setColorAt(1.0, QColor(0, 5, 15, 250))
        
        painter.setBrush(QBrush(bg))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, self.OUTER_RADIUS, self.OUTER_RADIUS)
    
    def _paint_outer_ring(self, painter: QPainter, center: QPointF):
        """Paint the animated rotating outer ring."""
        # Rotating conical gradient for sci-fi effect
        conical = QConicalGradient(center, self._ring_rotation)
        conical.setColorAt(0.0, QColor(0, 255, 255, 80))
        conical.setColorAt(0.25, QColor(0, 100, 200, 30))
        conical.setColorAt(0.5, QColor(0, 255, 255, 80))
        conical.setColorAt(0.75, QColor(0, 100, 200, 30))
        conical.setColorAt(1.0, QColor(0, 255, 255, 80))
        
        pen = QPen(QBrush(conical), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, self.OUTER_RADIUS - 2, self.OUTER_RADIUS - 2)
        
        # Secondary dashed ring
        pulse = 0.5 + 0.5 * math.sin(self._pulse_phase * 0.5)
        dash_pen = QPen(QColor(0, 200, 255, int(40 + pulse * 40)), 1, Qt.PenStyle.DashLine)
        painter.setPen(dash_pen)
        painter.drawEllipse(center, self.OUTER_RADIUS - 8, self.OUTER_RADIUS - 8)
    
    def _paint_wedge(self, painter: QPainter, center: QPointF, index: int, highlighted: bool):
        """Paint a single wedge section with futuristic style."""
        start_angle = -90 + (index * self.WEDGE_ANGLE)
        gap = 2  # Gap between wedges in degrees
        
        # Create wedge path
        path = QPainterPath()
        
        inner_start = self._polar_to_cartesian(center, self.INNER_RADIUS + 5, start_angle + gap/2)
        path.moveTo(inner_start)
        
        # Inner arc
        inner_rect = QRectF(
            center.x() - (self.INNER_RADIUS + 5),
            center.y() - (self.INNER_RADIUS + 5),
            (self.INNER_RADIUS + 5) * 2,
            (self.INNER_RADIUS + 5) * 2
        )
        path.arcTo(inner_rect, -(start_angle + gap/2), -(self.WEDGE_ANGLE - gap))
        
        # Line to outer
        outer_end = self._polar_to_cartesian(center, self.OUTER_RADIUS - 12, start_angle + self.WEDGE_ANGLE - gap/2)
        path.lineTo(outer_end)
        
        # Outer arc
        outer_rect = QRectF(
            center.x() - (self.OUTER_RADIUS - 12),
            center.y() - (self.OUTER_RADIUS - 12),
            (self.OUTER_RADIUS - 12) * 2,
            (self.OUTER_RADIUS - 12) * 2
        )
        path.arcTo(outer_rect, -(start_angle + self.WEDGE_ANGLE - gap/2), self.WEDGE_ANGLE - gap)
        
        path.closeSubpath()
        
        # Fill and border based on state
        if highlighted:
            # Glowing hover effect
            fill = QRadialGradient(center, self.OUTER_RADIUS)
            fill.setColorAt(0.3, QColor(0, 150, 255, 180))
            fill.setColorAt(0.6, QColor(0, 100, 200, 150))
            fill.setColorAt(1.0, QColor(0, 50, 100, 100))
            painter.setBrush(QBrush(fill))
            
            # Bright glow border
            painter.setPen(QPen(self.COLORS['neon_cyan'], 2))
        else:
            # Normal state - subtle translucent
            painter.setBrush(QBrush(self.COLORS['wedge_fill']))
            painter.setPen(QPen(self.COLORS['wedge_border'], 1))
        
        painter.drawPath(path)
        
        # Draw content
        self._paint_wedge_content(painter, center, index, highlighted)
    
    def _paint_wedge_content(self, painter: QPainter, center: QPointF, index: int, highlighted: bool):
        """Paint icon and label inside a wedge."""
        if index >= len(self.items):
            return
        
        item = self.items[index]
        
        # Position at middle of wedge
        mid_angle = -90 + (index * self.WEDGE_ANGLE) + (self.WEDGE_ANGLE / 2)
        mid_radius = (self.INNER_RADIUS + self.OUTER_RADIUS) / 2 + 5
        
        pos = self._polar_to_cartesian(center, mid_radius, mid_angle)
        
        # Get icon pixmap from cache
        pixmap = self._icon_cache.get(item.label)
        icon_size = 40  # Match the pre-loaded size
        
        if pixmap and not pixmap.isNull():
            # Calculate icon position (centered at pos, slightly above for label space)
            icon_x = int(pos.x() - icon_size / 2)
            icon_y = int(pos.y() - icon_size / 2 - 4)
            
            if highlighted:
                # Draw glow effect behind icon
                painter.setOpacity(0.4)
                for dx, dy in [(-2, 0), (2, 0), (0, -2), (0, 2), (-1, -1), (1, 1), (-1, 1), (1, -1)]:
                    painter.drawPixmap(icon_x + dx, icon_y + dy, pixmap)
                painter.setOpacity(1.0)
            
            # Draw main icon
            painter.drawPixmap(icon_x, icon_y, pixmap)
        else:
            # Fallback to emoji if no pixmap available
            icon_font = QFont("Segoe UI Emoji", 16)
            painter.setFont(icon_font)
            
            if highlighted:
                painter.setPen(QColor(0, 200, 255, 100))
                for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    icon_rect = QRectF(pos.x() - 14 + dx, pos.y() - 16 + dy, 28, 22)
                    painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, item.icon)
            
            painter.setPen(self.COLORS['text_bright'])
            icon_rect = QRectF(pos.x() - 14, pos.y() - 16, 28, 22)
            painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, item.icon)
        
        # Label
        label_font = QFont("Segoe UI", 7, QFont.Weight.Medium)
        painter.setFont(label_font)
        
        if highlighted:
            painter.setPen(self.COLORS['text_bright'])
        else:
            painter.setPen(self.COLORS['text_dim'])
        
        label_rect = QRectF(pos.x() - 28, pos.y() + 14, 56, 14)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignCenter, item.label)
    
    def _paint_dividers(self, painter: QPainter, center: QPointF):
        """Paint subtle divider lines between wedges."""
        pen = QPen(QColor(0, 150, 220, 40), 1)
        painter.setPen(pen)
        
        for i in range(self.WEDGE_COUNT):
            angle = -90 + (i * self.WEDGE_ANGLE)
            inner_pt = self._polar_to_cartesian(center, self.INNER_RADIUS + 8, angle)
            outer_pt = self._polar_to_cartesian(center, self.OUTER_RADIUS - 15, angle)
            painter.drawLine(inner_pt, outer_pt)
    
    def _paint_particles(self, painter: QPainter, center: QPointF):
        """Paint floating particle effects."""
        for p in self._particles:
            pos = self._polar_to_cartesian(center, p['radius'], p['angle'])
            
            # Particle glow
            color = QColor(0, 200, 255, int(p['alpha'] * 200))
            painter.setBrush(QBrush(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(pos, p['size'], p['size'])
    
    def _paint_inner_ring(self, painter: QPainter, center: QPointF):
        """Paint the inner ring around center."""
        pulse = 0.5 + 0.5 * math.sin(self._pulse_phase)
        
        # Glowing inner ring
        pen = QPen(QColor(0, 255, 255, int(100 + pulse * 80)), 2)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(center, self.INNER_RADIUS, self.INNER_RADIUS)
        
        # Inner secondary ring
        pen2 = QPen(QColor(0, 200, 255, int(40 + pulse * 30)), 1)
        painter.setPen(pen2)
        painter.drawEllipse(center, self.INNER_RADIUS + 3, self.INNER_RADIUS + 3)
    
    def _paint_center(self, painter: QPainter, center: QPointF):
        """Paint the glowing 'N' center logo with futuristic style."""
        pulse = 0.5 + 0.5 * math.sin(self._pulse_phase * 1.5)
        
        # Multi-layer glow
        for i, (radius, alpha) in enumerate([(45, 60), (40, 80), (35, 100)]):
            glow = QRadialGradient(center, radius)
            glow.setColorAt(0.0, QColor(0, 200, 255, int(alpha * pulse)))
            glow.setColorAt(0.5, QColor(0, 100, 200, int(alpha * 0.5 * pulse)))
            glow.setColorAt(1.0, QColor(0, 0, 0, 0))
            
            painter.setBrush(QBrush(glow))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(center, radius, radius)
        
        # Center circle background
        center_gradient = QRadialGradient(center, self.INNER_RADIUS - 5)
        center_gradient.setColorAt(0.0, QColor(20, 40, 70, 250))
        center_gradient.setColorAt(0.7, QColor(10, 25, 50, 250))
        center_gradient.setColorAt(1.0, QColor(5, 15, 35, 250))
        
        painter.setBrush(QBrush(center_gradient))
        painter.setPen(QPen(QColor(0, 200, 255, int(100 + pulse * 100)), 2))
        painter.drawEllipse(center, self.INNER_RADIUS - 5, self.INNER_RADIUS - 5)
        
        # "N" letter with glow
        n_font = QFont("Segoe UI", 26, QFont.Weight.Bold)
        painter.setFont(n_font)
        
        # Multi-layer glow for "N"
        glow_colors = [
            (QColor(0, 255, 255, int(80 * pulse)), 2),
            (QColor(0, 200, 255, int(120 * pulse)), 1),
        ]
        
        for color, offset in glow_colors:
            painter.setPen(color)
            for dx, dy in [(-offset, 0), (offset, 0), (0, -offset), (0, offset)]:
                n_rect = QRectF(center.x() - 18 + dx, center.y() - 15 + dy, 36, 30)
                painter.drawText(n_rect, Qt.AlignmentFlag.AlignCenter, "N")
        
        # Main "N"
        painter.setPen(QColor(150, 230, 255))
        n_rect = QRectF(center.x() - 18, center.y() - 15, 36, 30)
        painter.drawText(n_rect, Qt.AlignmentFlag.AlignCenter, "N")
    
    def _polar_to_cartesian(self, center: QPointF, radius: float, angle_deg: float) -> QPointF:
        """Convert polar coordinates to cartesian."""
        angle_rad = math.radians(angle_deg)
        x = center.x() + radius * math.cos(angle_rad)
        y = center.y() + radius * math.sin(angle_rad)
        return QPointF(x, y)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Mouse Handling
    # ═══════════════════════════════════════════════════════════════════════════
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Track mouse for hover effects."""
        pos = event.position()
        new_hover = self._get_wedge_at(pos)
        
        if new_hover != self.hovered_index:
            self.hovered_index = new_hover
            self.update()
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle click to execute action."""
        if event.button() == Qt.MouseButton.LeftButton:
            pos = event.position()
            wedge = self._get_wedge_at(pos)
            
            if wedge >= 0:
                self._execute_action(wedge)
            else:
                # Clicked on center or outside - close menu
                self.close_menu()
    
    def _get_wedge_at(self, pos: QPointF) -> int:
        """Determine which wedge the mouse is over. Returns -1 if none."""
        center = QPointF(self.width() / 2, self.height() / 2)
        
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        distance = math.sqrt(dx * dx + dy * dy)
        
        # Check if within wedge area
        if distance < self.INNER_RADIUS or distance > self.OUTER_RADIUS:
            return -1
        
        # Calculate angle
        angle = math.degrees(math.atan2(dy, dx))
        angle = (angle + 90) % 360
        
        wedge = int(angle / self.WEDGE_ANGLE)
        return wedge if 0 <= wedge < self.WEDGE_COUNT else -1
    
    def _execute_action(self, index: int):
        """Execute the action for a wedge."""
        if 0 <= index < len(self.items):
            item = self.items[index]
            logger.info(f"🎯 Radial menu action: {item.label}")
            
            self.close_menu()
            
            try:
                if item.action:
                    item.action()
                self.action_triggered.emit(item.label)
            except Exception as e:
                logger.error(f"Error executing radial menu action '{item.label}': {e}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Keyboard Handling
    # ═══════════════════════════════════════════════════════════════════════════
    
    def keyPressEvent(self, event: QKeyEvent):
        """Handle keyboard shortcuts."""
        key = event.text().upper()
        
        if event.key() == Qt.Key.Key_Escape:
            self.close_menu()
            return
        
        for i, item in enumerate(self.items):
            if item.shortcut.upper() == key:
                self._execute_action(i)
                return
        
        super().keyPressEvent(event)
    
    def focusOutEvent(self, event):
        """Close menu when focus is lost."""
        QTimer.singleShot(100, self._check_focus)
    
    def _check_focus(self):
        """Check if we should close due to focus loss."""
        if not self.isActiveWindow() and self.visible:
            self.close_menu()
    
    def leaveEvent(self, event):
        """Clear hover when mouse leaves."""
        self.hovered_index = -1
        self.update()

    def set_action(self, index: int, action: Callable):
        """Set action for a specific menu item."""
        if 0 <= index < len(self.items):
            self.items[index].action = action
