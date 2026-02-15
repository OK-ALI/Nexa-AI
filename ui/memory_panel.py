"""
Memory Panel - Neural Interface / Multiverse Theme

A futuristic neural interface styled panel for viewing and managing
Nexa's Smart Memory. Features animated particles, holographic cards,
glowing neural connections, and a cyberpunk aesthetic.

Design: Neural Interface with Multiverse/Timeline branches
Colors: Cyan, Magenta, Purple gradients with dark background
"""

import logging
import math
import random
from typing import List, Dict, Any, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QTabWidget, QMessageBox,
    QGraphicsDropShadowEffect, QSizePolicy, QGraphicsOpacityEffect
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, 
    QPoint, QRect, QSequentialAnimationGroup, QParallelAnimationGroup,
    Property, QObject, QSize
)
from PySide6.QtGui import (
    QFont, QColor, QPalette, QIcon, QPainter, QPen, QBrush,
    QLinearGradient, QRadialGradient, QPainterPath
)

logger = logging.getLogger(__name__)


# ============================================================================
# Color Scheme - Neural Interface / Cyberpunk Theme
# ============================================================================
COLORS = {
    # Base colors
    'void': '#050510',           # Deep space background
    'background': '#0a0a1a',     # Dark purple-black
    'surface': 'rgba(15, 15, 35, 0.85)',
    
    # Neural colors
    'synapse_cyan': '#00ffff',    # Primary cyan
    'synapse_light': '#7dfdfe',   # Light cyan
    'neural_magenta': '#ff00ff',  # Magenta accent
    'neural_pink': '#ff6bff',     # Light magenta
    'plasma_purple': '#bf00ff',   # Purple
    'plasma_light': '#d580ff',    # Light purple
    
    # Timeline/Portal colors
    'timeline_blue': '#0088ff',
    'portal_glow': '#00ffcc',
    'dimension_orange': '#ff8800',
    
    # Text
    'text': '#ffffff',
    'text_secondary': '#a0c8ff',
    'text_glow': '#00ffff',
    
    # Status
    'danger': '#ff3366',
    'success': '#00ff88',
    'warning': '#ffaa00',
    'star': '#ffdd00',
    
    # Cards
    'card': 'rgba(20, 25, 50, 0.6)',
    'card_hover': 'rgba(30, 40, 80, 0.8)',
    'card_border': 'rgba(0, 255, 255, 0.3)',
    'card_border_hover': 'rgba(0, 255, 255, 0.8)',
}


# ============================================================================
# Animated Background Widget - Starfield/Neural Network
# ============================================================================
class NeuralBackground(QWidget):
    """Animated neural network / starfield background."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        
        # Particles (stars/nodes)
        self.particles = []
        self.connections = []
        self._init_particles()
        
        # Animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_particles)
        self.timer.start(50)  # 20 FPS
        
        # Pulse phase for glow effects
        self.pulse_phase = 0
    
    def _init_particles(self):
        """Initialize neural particles."""
        for _ in range(40):
            self.particles.append({
                'x': random.uniform(0, 1),
                'y': random.uniform(0, 1),
                'vx': random.uniform(-0.001, 0.001),
                'vy': random.uniform(-0.001, 0.001),
                'size': random.uniform(1, 3),
                'brightness': random.uniform(0.3, 1.0),
                'pulse_offset': random.uniform(0, 2 * math.pi),
            })
    
    def _update_particles(self):
        """Update particle positions."""
        self.pulse_phase += 0.1
        
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            
            # Wrap around
            if p['x'] < 0: p['x'] = 1
            if p['x'] > 1: p['x'] = 0
            if p['y'] < 0: p['y'] = 1
            if p['y'] > 1: p['y'] = 0
        
        # Update connections (connect nearby particles)
        self.connections = []
        for i, p1 in enumerate(self.particles):
            for j, p2 in enumerate(self.particles[i+1:], i+1):
                dist = math.sqrt((p1['x'] - p2['x'])**2 + (p1['y'] - p2['y'])**2)
                if dist < 0.15:
                    self.connections.append((i, j, dist))
        
        self.update()
    
    def paintEvent(self, event):
        """Paint neural network background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        
        # Draw radial gradient background
        gradient = QRadialGradient(w/2, h/2, max(w, h))
        gradient.setColorAt(0, QColor(15, 15, 40))
        gradient.setColorAt(0.5, QColor(10, 10, 25))
        gradient.setColorAt(1, QColor(5, 5, 15))
        painter.fillRect(self.rect(), gradient)
        
        # Draw connections (neural pathways)
        for i, j, dist in self.connections:
            p1, p2 = self.particles[i], self.particles[j]
            
            # Pulse effect
            pulse = (math.sin(self.pulse_phase + p1['pulse_offset']) + 1) / 2
            alpha = int((1 - dist / 0.15) * 80 * (0.5 + 0.5 * pulse))
            
            # Gradient color based on position
            color_mix = (p1['x'] + p2['x']) / 2
            if color_mix < 0.33:
                color = QColor(0, 255, 255, alpha)  # Cyan
            elif color_mix < 0.66:
                color = QColor(191, 0, 255, alpha)  # Purple
            else:
                color = QColor(255, 0, 255, alpha)  # Magenta
            
            pen = QPen(color, 1)
            painter.setPen(pen)
            painter.drawLine(
                int(p1['x'] * w), int(p1['y'] * h),
                int(p2['x'] * w), int(p2['y'] * h)
            )
        
        # Draw particles (neural nodes)
        for p in self.particles:
            pulse = (math.sin(self.pulse_phase + p['pulse_offset']) + 1) / 2
            alpha = int(p['brightness'] * 255 * (0.6 + 0.4 * pulse))
            size = p['size'] * (1 + 0.3 * pulse)
            
            # Color based on position (creates gradient effect across screen)
            r = int(p['x'] * 100)
            g = int(200 + p['y'] * 55)
            b = 255
            
            # Draw glow
            glow_color = QColor(r, g, b, alpha // 3)
            glow_brush = QBrush(glow_color)
            painter.setPen(Qt.NoPen)
            painter.setBrush(glow_brush)
            painter.drawEllipse(
                int(p['x'] * w - size * 2),
                int(p['y'] * h - size * 2),
                int(size * 4),
                int(size * 4)
            )
            
            # Draw core
            core_color = QColor(r, g, b, alpha)
            painter.setBrush(QBrush(core_color))
            painter.drawEllipse(
                int(p['x'] * w - size / 2),
                int(p['y'] * h - size / 2),
                int(size),
                int(size)
            )


# ============================================================================
# Neural Activity Indicator
# ============================================================================
class NeuralActivityBar(QWidget):
    """Animated neural activity indicator."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(40)
        self.activity_level = 0.5
        self.bars = []
        self.phase = 0
        
        # Initialize bars
        for i in range(30):
            self.bars.append({
                'height': random.uniform(0.2, 0.8),
                'phase_offset': i * 0.2,
                'speed': random.uniform(0.8, 1.2),
            })
        
        # Animation timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._animate)
        self.timer.start(50)
    
    def set_activity(self, level: float):
        """Set activity level (0.0 to 1.0)."""
        self.activity_level = max(0, min(1, level))
    
    def _animate(self):
        self.phase += 0.15
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        w, h = self.width(), self.height()
        bar_width = w / len(self.bars)
        
        for i, bar in enumerate(self.bars):
            # Calculate animated height
            wave = math.sin(self.phase * bar['speed'] + bar['phase_offset'])
            height = (0.3 + 0.7 * (wave + 1) / 2) * bar['height'] * self.activity_level
            bar_h = int(h * height * 0.8)
            
            # Gradient color (cyan to magenta)
            t = i / len(self.bars)
            r = int(t * 255)
            g = int((1 - abs(t - 0.5) * 2) * 255)
            b = 255
            
            # Draw bar with glow
            x = int(i * bar_width)
            y = h - bar_h
            
            # Glow
            glow = QRadialGradient(x + bar_width/2, y + bar_h/2, bar_width)
            glow.setColorAt(0, QColor(r, g, b, 100))
            glow.setColorAt(1, QColor(r, g, b, 0))
            painter.fillRect(int(x-2), int(y-2), int(bar_width+4), int(bar_h+4), glow)
            
            # Bar
            color = QColor(r, g, b, 200)
            painter.fillRect(int(x + 1), y, int(bar_width - 2), bar_h, color)


# ============================================================================
# Holographic Memory Card
# ============================================================================
class HolographicCard(QFrame):
    """Futuristic holographic memory card with scan-line effect."""
    
    deleted = Signal(str)
    marked_important = Signal(str, bool)
    
    def __init__(self, memory_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.memory_data = memory_data
        self.memory_id = memory_data.get('id', '')
        self.is_important = memory_data.get('importance', 0.5) > 0.7
        self.hover = False
        self.scan_offset = random.uniform(0, 100)
        
        self.setFixedHeight(100)
        self.setCursor(Qt.PointingHandCursor)
        
        self._setup_ui()
        
        # Scan line animation
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self._update_scan)
        self.scan_timer.start(50)
    
    def _setup_ui(self):
        # Get icon manager
        from ui.music_indicator import get_icon_manager
        icon_mgr = get_icon_manager()
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)
        
        # Top row: Type + Timeline indicator
        top_row = QHBoxLayout()
        
        # Type icon with PNG - map memory types to icon names
        memory_type = self.memory_data.get('memory_type', 'conversation')
        icon_name_map = {
            'conversation': 'conversation',
            'knowledge': 'memory',
            'skill': 'lightning',
        }
        icon_name = icon_name_map.get(memory_type, 'thought')
        
        type_label = QLabel()
        type_label.setPixmap(icon_mgr.get_pixmap(icon_name, 24))
        type_label.setFixedSize(28, 28)
        type_label.setStyleSheet("background: transparent;")
        top_row.addWidget(type_label)
        
        # Timeline branch indicator
        branch_colors = ['#00ffff', '#ff00ff', '#bf00ff']
        branch_idx = hash(self.memory_id) % 3
        branch = QLabel("◆")
        branch.setStyleSheet(f"""
            color: {branch_colors[branch_idx]};
            font-size: 10px;
            background: transparent;
        """)
        top_row.addWidget(branch)
        
        top_row.addStretch()
        
        # Star button with PNG icon
        self.star_btn = QPushButton()
        self.star_btn.setIcon(icon_mgr.get_icon('favourite', 20))
        self.star_btn.setIconSize(QSize(20, 20))
        self.star_btn.setFixedSize(28, 28)
        self.star_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                padding: 2px;
                opacity: {1.0 if self.is_important else 0.4};
            }}
            QPushButton:hover {{
                background: rgba(255, 215, 0, 0.1);
            }}
        """)
        self.star_btn.setCursor(Qt.PointingHandCursor)
        self.star_btn.clicked.connect(self._toggle_important)
        top_row.addWidget(self.star_btn)
        
        # Delete button with PNG icon
        delete_btn = QPushButton()
        delete_btn.setIcon(icon_mgr.get_icon('close', 18))
        delete_btn.setIconSize(QSize(18, 18))
        delete_btn.setFixedSize(24, 24)
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                padding: 2px;
            }}
            QPushButton:hover {{
                background: rgba(255, 51, 102, 0.2);
            }}
        """)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.clicked.connect(self._confirm_delete)
        top_row.addWidget(delete_btn)
        
        layout.addLayout(top_row)
        
        # Content
        content = self._get_content_preview()
        content_label = QLabel(content)
        content_label.setWordWrap(True)
        content_label.setStyleSheet(f"""
            color: {COLORS['text']};
            font-size: 12px;
            background: transparent;
            padding: 4px 0;
        """)
        layout.addWidget(content_label)
        
        # Bottom: Timestamp with clock icon
        timestamp = self._format_timestamp()
        time_container = QHBoxLayout()
        time_container.setSpacing(4)
        
        clock_icon = QLabel()
        clock_icon.setPixmap(icon_mgr.get_pixmap('clock', 14))
        clock_icon.setFixedSize(16, 16)
        clock_icon.setStyleSheet("background: transparent;")
        time_container.addWidget(clock_icon)
        
        time_label = QLabel(timestamp)
        time_label.setStyleSheet(f"""
            color: {COLORS['text_secondary']};
            font-size: 10px;
            background: transparent;
        """)
        time_container.addWidget(time_label)
        time_container.addStretch()
        layout.addLayout(time_container)
    
    def _update_scan(self):
        self.scan_offset = (self.scan_offset + 2) % 100
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Card background with gradient
        rect = self.rect()
        
        # Determine glow color based on hover
        if self.hover:
            border_color = QColor(0, 255, 255, 200)
            bg_alpha = 0.7
        else:
            border_color = QColor(0, 255, 255, 60)
            bg_alpha = 0.4
        
        # Background gradient
        gradient = QLinearGradient(0, 0, rect.width(), rect.height())
        gradient.setColorAt(0, QColor(20, 30, 60, int(255 * bg_alpha)))
        gradient.setColorAt(0.5, QColor(30, 20, 50, int(255 * bg_alpha)))
        gradient.setColorAt(1, QColor(20, 30, 60, int(255 * bg_alpha)))
        
        # Draw rounded rect
        path = QPainterPath()
        path.addRoundedRect(rect.x() + 1, rect.y() + 1, 
                           rect.width() - 2, rect.height() - 2, 12, 12)
        
        painter.fillPath(path, QBrush(gradient))
        
        # Draw border with glow
        pen = QPen(border_color, 1)
        painter.setPen(pen)
        painter.drawRoundedRect(rect.x() + 1, rect.y() + 1,
                               rect.width() - 2, rect.height() - 2, 12, 12)
        
        # Scan line effect (holographic)
        if self.hover:
            scan_y = int((self.scan_offset / 100) * rect.height())
            scan_gradient = QLinearGradient(0, scan_y - 10, 0, scan_y + 10)
            scan_gradient.setColorAt(0, QColor(0, 255, 255, 0))
            scan_gradient.setColorAt(0.5, QColor(0, 255, 255, 60))
            scan_gradient.setColorAt(1, QColor(0, 255, 255, 0))
            
            painter.fillRect(rect.x(), scan_y - 10, rect.width(), 20, scan_gradient)
        
        # Corner accents
        accent_size = 15
        painter.setPen(QPen(QColor(0, 255, 255, 150), 2))
        
        # Top-left
        painter.drawLine(rect.x() + 5, rect.y() + 5, rect.x() + 5 + accent_size, rect.y() + 5)
        painter.drawLine(rect.x() + 5, rect.y() + 5, rect.x() + 5, rect.y() + 5 + accent_size)
        
        # Bottom-right
        painter.drawLine(rect.right() - 5, rect.bottom() - 5, 
                        rect.right() - 5 - accent_size, rect.bottom() - 5)
        painter.drawLine(rect.right() - 5, rect.bottom() - 5,
                        rect.right() - 5, rect.bottom() - 5 - accent_size)
    
    def enterEvent(self, event):
        self.hover = True
        self.update()
    
    def leaveEvent(self, event):
        self.hover = False
        self.update()
    
    def _get_content_preview(self) -> str:
        """Get preview text from memory data."""
        if 'user_message' in self.memory_data:
            user_msg = self.memory_data['user_message']
            nexa_resp = self.memory_data.get('nexa_response', '')
            if nexa_resp:
                text = f"You: {user_msg[:40]}..." if len(user_msg) > 40 else f"You: {user_msg}"
            else:
                text = user_msg
        elif 'fact' in self.memory_data:
            text = self.memory_data['fact']
        elif 'action' in self.memory_data:
            text = f"Skill: {self.memory_data['action']}"
        else:
            text = "Memory fragment"
        
        return text[:80] + "..." if len(text) > 80 else text
    
    def _format_timestamp(self) -> str:
        """Format timestamp as relative time."""
        try:
            ts_str = self.memory_data.get('timestamp', '') or self.memory_data.get('created_at', '')
            if not ts_str:
                return "Unknown timeline"
            
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            now = datetime.now()
            delta = now - ts.replace(tzinfo=None)
            
            if delta.days > 7:
                return ts.strftime("%b %d, %Y")
            elif delta.days > 0:
                return f"{delta.days}d ago"
            elif delta.seconds > 3600:
                return f"{delta.seconds // 3600}h ago"
            elif delta.seconds > 60:
                return f"{delta.seconds // 60}m ago"
            else:
                return "Just now"
        except:
            return "Unknown"
    
    def _toggle_important(self):
        self.is_important = not self.is_important
        self.star_btn.setText("★" if self.is_important else "☆")
        self.star_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: 18px;
                color: {COLORS['star'] if self.is_important else 'rgba(255,255,255,0.3)'};
            }}
            QPushButton:hover {{
                color: {COLORS['star']};
            }}
        """)
        self.marked_important.emit(self.memory_id, self.is_important)
    
    def _confirm_delete(self):
        reply = QMessageBox.question(
            self, 
            "⚠️ Delete Memory Fragment",
            "Erase this memory from the neural network?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.deleted.emit(self.memory_id)


# ============================================================================
# Stylesheets for Neural Theme
# ============================================================================
PANEL_STYLE = f"""
QWidget#MemoryPanel {{
    background: transparent;
}}
"""

SEARCH_STYLE = f"""
QLineEdit#SearchBar {{
    background: rgba(20, 30, 60, 0.7);
    border: 1px solid rgba(0, 255, 255, 0.3);
    border-radius: 20px;
    padding: 12px 20px;
    color: {COLORS['text']};
    font-size: 14px;
    selection-background-color: {COLORS['synapse_cyan']};
}}
QLineEdit#SearchBar:focus {{
    border: 1px solid {COLORS['synapse_cyan']};
    background: rgba(30, 40, 80, 0.8);
}}
"""

TAB_STYLE = f"""
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: rgba(255, 255, 255, 0.5);
    padding: 12px 24px;
    margin-right: 4px;
    font-size: 12px;
    font-weight: bold;
    border: 1px solid transparent;
    border-radius: 8px;
}}
QTabBar::tab:selected {{
    color: {COLORS['synapse_cyan']};
    background: rgba(0, 255, 255, 0.1);
    border: 1px solid rgba(0, 255, 255, 0.3);
}}
QTabBar::tab:hover {{
    color: {COLORS['text']};
    background: rgba(255, 255, 255, 0.05);
}}
"""

BUTTON_STYLE = f"""
QPushButton#ActionButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                stop:0 {COLORS['synapse_cyan']}, 
                stop:1 {COLORS['neural_magenta']});
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    color: white;
    font-weight: bold;
    font-size: 12px;
}}
QPushButton#ActionButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                stop:0 {COLORS['synapse_light']}, 
                stop:1 {COLORS['neural_pink']});
}}
QPushButton#SecondaryButton {{
    background: rgba(30, 40, 80, 0.6);
    border: 1px solid rgba(0, 255, 255, 0.3);
    border-radius: 8px;
    padding: 10px 20px;
    color: {COLORS['text']};
    font-size: 12px;
}}
QPushButton#SecondaryButton:hover {{
    border-color: {COLORS['synapse_cyan']};
    background: rgba(0, 255, 255, 0.1);
}}
QPushButton#DangerButton {{
    background: rgba(255, 51, 102, 0.2);
    border: 1px solid rgba(255, 51, 102, 0.5);
    border-radius: 8px;
    padding: 10px 20px;
    color: {COLORS['danger']};
    font-size: 12px;
}}
QPushButton#DangerButton:hover {{
    background: rgba(255, 51, 102, 0.4);
    border-color: {COLORS['danger']};
}}
"""


# ============================================================================
# Main Memory Panel Widget
# ============================================================================
class MemoryPanel(QWidget):
    """Neural Interface Memory Management Panel."""
    
    closed = Signal()
    
    def __init__(self, context_manager=None, parent=None):
        super().__init__(parent)
        self.context = context_manager
        self.memories = {'conversations': [], 'knowledge': [], 'skills': []}
        
        self.setObjectName("MemoryPanel")
        self.setWindowTitle("Neural Memory Interface")
        self.setFixedSize(600, 750)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._setup_ui()
        self._load_memories()
    
    def _setup_ui(self):
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Container frame
        container = QFrame(self)
        container.setObjectName("MemoryPanel")
        container.setStyleSheet("""
            QFrame#MemoryPanel {
                background: rgba(10, 10, 30, 0.95);
                border: 1px solid rgba(0, 255, 255, 0.3);
                border-radius: 20px;
            }
        """)
        
        # Add neural background
        self.background = NeuralBackground(container)
        self.background.setGeometry(0, 0, 600, 750)
        self.background.lower()
        
        # Content layout
        content_layout = QVBoxLayout(container)
        content_layout.setContentsMargins(24, 20, 24, 24)
        content_layout.setSpacing(16)
        
        # Header
        header = self._create_header()
        content_layout.addLayout(header)
        
        # Neural activity bar
        self.activity_bar = NeuralActivityBar()
        content_layout.addWidget(self.activity_bar)
        
        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchBar")
        self.search_input.setPlaceholderText("Search neural pathways...")
        self.search_input.setStyleSheet(SEARCH_STYLE)
        self.search_input.textChanged.connect(self._on_search)
        content_layout.addWidget(self.search_input)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_STYLE)
        
        # Create tab content
        self.conv_scroll = self._create_scroll_area()
        self.know_scroll = self._create_scroll_area()
        self.skill_scroll = self._create_scroll_area()
        
        self.tabs.addTab(self.conv_scroll, "Synapses (0)")
        self.tabs.addTab(self.know_scroll, "Knowledge (0)")
        self.tabs.addTab(self.skill_scroll, "Skills (0)")
        
        content_layout.addWidget(self.tabs, 1)
        
        # Bottom buttons
        buttons = self._create_buttons()
        content_layout.addLayout(buttons)
        
        main_layout.addWidget(container)
        
        # Outer glow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 255, 255, 80))
        container.setGraphicsEffect(shadow)
    
    def _create_header(self) -> QHBoxLayout:
        """Create header with title and close button."""
        layout = QHBoxLayout()
        
        # Animated title
        title_container = QHBoxLayout()
        
        # Brain icon with PNG
        from ui.music_indicator import get_icon_manager
        icon_mgr = get_icon_manager()
        icon = QLabel()
        icon.setPixmap(icon_mgr.get_pixmap('memory', 32))
        icon.setFixedSize(36, 36)
        icon.setStyleSheet("background: transparent;")
        title_container.addWidget(icon)
        
        # Title with gradient effect
        title = QLabel("NEURAL MEMORY INTERFACE")
        title.setStyleSheet(f"""
            color: {COLORS['synapse_cyan']};
            font-size: 16px;
            font-weight: bold;
            letter-spacing: 2px;
            background: transparent;
        """)
        title_container.addWidget(title)
        
        layout.addLayout(title_container)
        layout.addStretch()
        
        # Status indicator
        status = QLabel("● ONLINE")
        status.setStyleSheet(f"""
            color: {COLORS['success']};
            font-size: 10px;
            font-weight: bold;
            background: transparent;
        """)
        layout.addWidget(status)
        
        # Close button
        close_btn = QPushButton("✕")
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: 1px solid rgba(255, 51, 102, 0.3);
                border-radius: 15px;
                color: rgba(255, 255, 255, 0.5);
                font-size: 14px;
                padding: 5px 10px;
            }}
            QPushButton:hover {{
                color: {COLORS['danger']};
                border-color: {COLORS['danger']};
                background: rgba(255, 51, 102, 0.1);
            }}
        """)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.clicked.connect(self._close_panel)
        layout.addWidget(close_btn)
        
        return layout
    
    def _create_scroll_area(self) -> QScrollArea:
        """Create a scroll area for memory cards."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background: transparent;
                border: none;
            }
            QScrollBar:vertical {
                background: rgba(20, 30, 60, 0.5);
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                            stop:0 #00ffff, stop:1 #ff00ff);
                border-radius: 4px;
                min-height: 30px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(12)
        layout.addStretch()
        
        scroll.setWidget(container)
        return scroll
    
    def _create_buttons(self) -> QHBoxLayout:
        """Create bottom action buttons."""
        layout = QHBoxLayout()
        layout.setSpacing(12)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setObjectName("SecondaryButton")
        refresh_btn.setStyleSheet(BUTTON_STYLE)
        refresh_btn.setCursor(Qt.PointingHandCursor)
        refresh_btn.clicked.connect(self._refresh_panel)
        layout.addWidget(refresh_btn)
        
        # Reseed knowledge from user_prefs.json
        reseed_btn = QPushButton("🌱 Reseed")
        reseed_btn.setObjectName("SecondaryButton")
        reseed_btn.setStyleSheet(BUTTON_STYLE)
        reseed_btn.setCursor(Qt.PointingHandCursor)
        reseed_btn.setToolTip("Reseed personal knowledge from user_prefs.json")
        reseed_btn.clicked.connect(self._reseed_knowledge)
        layout.addWidget(reseed_btn)
        
        export_btn = QPushButton("📤 Export")
        export_btn.setObjectName("SecondaryButton")
        export_btn.setStyleSheet(BUTTON_STYLE)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_memories)
        layout.addWidget(export_btn)
        
        clear_btn = QPushButton("🧹 Prune Old")
        clear_btn.setObjectName("SecondaryButton")
        clear_btn.setStyleSheet(BUTTON_STYLE)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setToolTip("Delete memories older than 30 days")
        clear_btn.clicked.connect(self._clear_old)
        layout.addWidget(clear_btn)
        
        clear_all_btn = QPushButton("⚠ PURGE ALL")
        clear_all_btn.setObjectName("DangerButton")
        clear_all_btn.setStyleSheet(BUTTON_STYLE)
        clear_all_btn.setCursor(Qt.PointingHandCursor)
        clear_all_btn.setToolTip("Delete ALL memories permanently")
        clear_all_btn.clicked.connect(self._clear_all)
        layout.addWidget(clear_all_btn)
        
        return layout
    
    def _refresh_panel(self):
        """Refresh the memory panel."""
        current_tab = self.tabs.currentIndex()
        self._load_memories()
        self.tabs.setCurrentIndex(current_tab)
    
    def _reseed_knowledge(self):
        """Reseed personal knowledge from user_prefs.json."""
        if not self.context:
            return
        
        reply = QMessageBox.question(
            self,
            "🌱 Reseed Personal Knowledge",
            "This will reload personal data from user_prefs.json\n"
            "(relationships, user info, etc.)\n\n"
            "Existing duplicate facts will be updated.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                self.context.refresh_personal_knowledge()
                self._load_memories()
                QMessageBox.information(
                    self,
                    "✅ Knowledge Reseeded",
                    "Personal knowledge has been refreshed from user_prefs.json!"
                )
            except Exception as e:
                logger.error(f"Reseed error: {e}")
                QMessageBox.critical(self, "Reseed Failed", str(e))
    
    def _load_memories(self):
        """Load memories from context manager."""
        if not self.context or not hasattr(self.context, 'smart_memory'):
            logger.warning("Smart Memory not available")
            return
        
        try:
            sm = self.context.smart_memory
            if not sm:
                return
            
            # Load from each table
            self.memories['conversations'] = sm.recall_recent(limit=50)
            self.memories['knowledge'] = sm.store.get_all('knowledge', limit=50)
            self.memories['skills'] = sm.store.get_all('skills', limit=50)
            
            # Update activity bar based on memory count
            total = sum(len(v) for v in self.memories.values())
            self.activity_bar.set_activity(min(1.0, total / 100))
            
            # Update tabs and display
            self._update_tab_counts()
            self._display_memories('conversations', self.conv_scroll)
            self._display_memories('knowledge', self.know_scroll)
            self._display_memories('skills', self.skill_scroll)
            
        except Exception as e:
            logger.error(f"Error loading memories: {e}")
    
    def _update_tab_counts(self):
        """Update tab titles with counts."""
        conv_count = len(self.memories.get('conversations', []))
        know_count = len(self.memories.get('knowledge', []))
        skill_count = len(self.memories.get('skills', []))
        
        self.tabs.setTabText(0, f"💬 Synapses ({conv_count})")
        self.tabs.setTabText(1, f"🧠 Knowledge ({know_count})")
        self.tabs.setTabText(2, f"⚡ Skills ({skill_count})")
    
    def _display_memories(self, memory_type: str, scroll_area: QScrollArea):
        """Display memories in a scroll area."""
        container = scroll_area.widget()
        layout = container.layout()
        
        # Clear existing cards (except stretch)
        while layout.count() > 1:
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        memories = self.memories.get(memory_type, [])
        
        if not memories:
            # Show empty state
            empty_label = QLabel("No neural pathways found")
            empty_label.setStyleSheet(f"""
                color: rgba(0, 255, 255, 0.5);
                padding: 40px;
                font-style: italic;
                background: transparent;
            """)
            empty_label.setAlignment(Qt.AlignCenter)
            layout.insertWidget(0, empty_label)
            return
        
        # Add memory type to each memory for display
        type_map = {
            'conversations': 'conversation',
            'knowledge': 'knowledge',
            'skills': 'skill',
        }
        
        for i, mem in enumerate(memories):
            mem['memory_type'] = type_map.get(memory_type, 'conversation')
            card = HolographicCard(mem)
            card.deleted.connect(self._on_memory_deleted)
            card.marked_important.connect(self._on_marked_important)
            layout.insertWidget(i, card)
    
    def _on_search(self, query: str):
        """Handle search input."""
        if not query.strip():
            self._load_memories()
            return
        
        if not self.context or not hasattr(self.context, 'recall_similar_memories'):
            return
        
        try:
            results = self.context.recall_similar_memories(query, limit=20)
            
            # Group by type
            self.memories = {'conversations': [], 'knowledge': [], 'skills': []}
            for mem in results:
                mem_type = mem.get('memory_type', 'conversation')
                if mem_type == 'conversation':
                    self.memories['conversations'].append(mem)
                elif mem_type == 'knowledge':
                    self.memories['knowledge'].append(mem)
                else:
                    self.memories['skills'].append(mem)
            
            self._update_tab_counts()
            self._display_memories('conversations', self.conv_scroll)
            self._display_memories('knowledge', self.know_scroll)
            self._display_memories('skills', self.skill_scroll)
            
        except Exception as e:
            logger.error(f"Search error: {e}")
    
    def _on_memory_deleted(self, memory_id: str):
        """Handle memory deletion - stays in current tab."""
        if not self.context or not hasattr(self.context, 'smart_memory'):
            return
        
        try:
            # Remember current tab index before refresh
            current_tab_index = self.tabs.currentIndex()
            
            self.context.smart_memory.forget_memory(memory_id)
            self._load_memories()
            
            # Restore to the same tab after refresh
            self.tabs.setCurrentIndex(current_tab_index)
        except Exception as e:
            logger.error(f"Delete error: {e}")
    
    def _on_marked_important(self, memory_id: str, is_important: bool):
        """Handle importance toggle."""
        logger.info(f"⭐ Toggle importance: {memory_id} → {is_important}")
        
        if not self.context or not hasattr(self.context, 'smart_memory'):
            return
        
        try:
            importance = 0.9 if is_important else 0.5
            self.context.smart_memory.mark_important(memory_id, importance)
        except Exception as e:
            logger.error(f"Mark important error: {e}")
    
    def _export_memories(self):
        """Export memories to JSON."""
        try:
            import json
            from pathlib import Path
            
            export_path = Path.home() / "Documents" / "nexa_neural_export.json"
            
            data = {
                'exported_at': datetime.now().isoformat(),
                'interface': 'Neural Memory Interface v2.0',
                'conversations': self.memories.get('conversations', []),
                'knowledge': self.memories.get('knowledge', []),
                'skills': self.memories.get('skills', []),
            }
            
            def clean_for_json(obj):
                if isinstance(obj, dict):
                    return {k: clean_for_json(v) for k, v in obj.items() 
                            if k != 'vector' and k != 'embedding'}
                elif isinstance(obj, list):
                    return [clean_for_json(i) for i in obj]
                else:
                    return obj
            
            data = clean_for_json(data)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            QMessageBox.information(
                self,
                "📤 Export Complete",
                f"Neural data exported to:\n{export_path}"
            )
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            QMessageBox.warning(self, "Export Failed", str(e))
    
    def _clear_old(self):
        """Clear old memories (30+ days)."""
        reply = QMessageBox.question(
            self,
            "🧹 Prune Old Pathways",
            "Remove neural pathways older than 30 cycles?\n\n"
            "(Critical memories will be preserved)",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        if not self.context or not hasattr(self.context, 'smart_memory'):
            return
        
        try:
            deleted = self.context.smart_memory.prune_old_memories(days=30)
            self._load_memories()
            QMessageBox.information(
                self,
                "✨ Pruning Complete",
                f"Removed {deleted} dormant pathways"
            )
        except Exception as e:
            logger.error(f"Clear old error: {e}")
    
    def _clear_all(self):
        """Clear ALL memories (with confirmation)."""
        reply = QMessageBox.warning(
            self,
            "⚠️ NEURAL PURGE WARNING",
            "⚡ INITIATING COMPLETE MEMORY PURGE ⚡\n\n"
            "This will PERMANENTLY erase:\n"
            "• All conversation synapses\n"
            "• All knowledge pathways\n"
            "• All learned skills\n\n"
            "This action is IRREVERSIBLE.\n\n"
            "Proceed with neural purge?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Double confirmation
        reply2 = QMessageBox.critical(
            self,
            "⚠️ FINAL CONFIRMATION",
            "🔴 POINT OF NO RETURN 🔴\n\n"
            "All neural pathways will be destroyed.\n\n"
            "Type 'PURGE' to confirm... just kidding.\n"
            "Click Yes to proceed.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply2 != QMessageBox.Yes:
            return
        
        if not self.context or not hasattr(self.context, 'smart_memory'):
            return
        
        try:
            result = self.context.smart_memory.clear_all_memory(include_knowledge=True)
            total = sum(result.values())
            self._load_memories()
            QMessageBox.information(
                self,
                "🌀 PURGE COMPLETE",
                f"Neural network reset:\n\n"
                f"• Synapses erased: {result['conversations']}\n"
                f"• Knowledge purged: {result['knowledge']}\n"
                f"• Skills forgotten: {result['skills']}\n\n"
                f"Total pathways removed: {total}"
            )
        except Exception as e:
            logger.error(f"Clear all error: {e}")
            QMessageBox.critical(self, "Purge Failed", str(e))
    
    def _close_panel(self):
        """Close the panel."""
        self.closed.emit()
        self.hide()
    
    # Enable dragging the frameless window
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and hasattr(self, '_drag_pos'):
            self.move(event.globalPos() - self._drag_pos)
            event.accept()
