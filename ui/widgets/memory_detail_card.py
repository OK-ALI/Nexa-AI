"""
Memory Detail Card - Glassmorphism Floating Panel

A floating detail panel that appears near a selected neural node,
showing memory information with a frosted glass effect.

Features:
- Glassmorphism blur effect
- Slides in from the side with animation
- Action buttons: Edit, Delete, Pin, Lock, Export
- Follows the selected node position
"""

from typing import Dict, Any, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QGraphicsBlurEffect,
    QScrollArea, QSizePolicy
)
from PySide6.QtCore import (
    Qt, Signal, QPropertyAnimation, QEasingCurve, QPoint, QSize,
    QTimer, Property
)
from PySide6.QtGui import (
    QFont, QColor, QPainter, QPen, QBrush, QLinearGradient,
    QPainterPath
)

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Color Palette
# ============================================================================
CARD_COLORS = {
    'glass_bg': 'rgba(15, 20, 40, 0.85)',
    'glass_border': 'rgba(0, 212, 255, 0.4)',
    'glass_border_glow': 'rgba(0, 212, 255, 0.8)',
    'text_primary': '#ffffff',
    'text_secondary': '#a0c8ff',
    'text_muted': '#6b7280',
    'accent_cyan': '#00d4ff',
    'accent_violet': '#8b5cf6',
    'accent_green': '#00ff88',
    'danger': '#ff3366',
    'button_bg': 'rgba(0, 150, 220, 0.3)',
    'button_hover': 'rgba(0, 180, 255, 0.5)',
}


class MemoryDetailCard(QWidget):
    """
    Floating glassmorphism card showing memory details.
    
    Appears near the selected node in the neural graph.
    """
    
    # Signals
    edit_requested = Signal(str)      # memory_id
    delete_requested = Signal(str)    # memory_id
    pin_toggled = Signal(str, bool)   # memory_id, is_pinned
    lock_toggled = Signal(str, bool)  # memory_id, is_locked
    export_requested = Signal(str)    # memory_id
    close_requested = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.current_memory_id: Optional[str] = None
        self.current_memory_data: Optional[Dict[str, Any]] = None
        self.is_pinned = False
        self.is_locked = False
        
        self._setup_window()
        self._setup_ui()
        self._apply_styling()
        
        # Initially hidden
        self.hide()
        
        logger.info("📋 MemoryDetailCard initialized")
    
    def _setup_window(self):
        """Configure window properties."""
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self.setFixedWidth(320)
        self.setMinimumHeight(280)
        self.setMaximumHeight(450)
    
    def _setup_ui(self):
        """Build the card UI."""
        # Main layout with margins for glow effect
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(15, 15, 15, 15)
        
        # Container for glass effect
        self.container = QFrame()
        self.container.setObjectName("glassContainer")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(16, 14, 16, 16)
        container_layout.setSpacing(12)
        
        # ── Header ──
        header = QHBoxLayout()
        header.setSpacing(10)
        
        # Type icon (will be set dynamically)
        self.type_icon = QLabel()
        self.type_icon.setFixedSize(28, 28)
        self.type_icon.setStyleSheet("background: transparent;")
        header.addWidget(self.type_icon)
        
        # Title
        self.title_label = QLabel("Memory")
        self.title_label.setObjectName("titleLabel")
        self.title_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.title_label.setWordWrap(True)
        header.addWidget(self.title_label, 1)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setObjectName("closeBtn")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self._close_card)
        header.addWidget(close_btn)
        
        container_layout.addLayout(header)
        
        # ── Separator ──
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setObjectName("separator")
        container_layout.addWidget(separator)
        
        # ── Metadata ──
        meta_layout = QVBoxLayout()
        meta_layout.setSpacing(6)
        
        # Type row
        type_row = QHBoxLayout()
        type_label = QLabel("Type:")
        type_label.setObjectName("metaLabel")
        self.type_value = QLabel("Conversation")
        self.type_value.setObjectName("metaValue")
        type_row.addWidget(type_label)
        type_row.addWidget(self.type_value, 1)
        meta_layout.addLayout(type_row)
        
        # Created row
        created_row = QHBoxLayout()
        created_label = QLabel("Created:")
        created_label.setObjectName("metaLabel")
        self.created_value = QLabel("2 hours ago")
        self.created_value.setObjectName("metaValue")
        created_row.addWidget(created_label)
        created_row.addWidget(self.created_value, 1)
        meta_layout.addLayout(created_row)
        
        # Importance row
        importance_row = QHBoxLayout()
        importance_label = QLabel("Importance:")
        importance_label.setObjectName("metaLabel")
        self.importance_value = QLabel("★★★★☆")
        self.importance_value.setObjectName("importanceValue")
        importance_row.addWidget(importance_label)
        importance_row.addWidget(self.importance_value, 1)
        meta_layout.addLayout(importance_row)
        
        container_layout.addLayout(meta_layout)
        
        # ── Tags ──
        self.tags_container = QHBoxLayout()
        self.tags_container.setSpacing(6)
        container_layout.addLayout(self.tags_container)
        
        # ── Content Preview ──
        content_frame = QFrame()
        content_frame.setObjectName("contentFrame")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(10, 8, 10, 8)
        
        self.content_label = QLabel("Memory content preview...")
        self.content_label.setObjectName("contentLabel")
        self.content_label.setWordWrap(True)
        self.content_label.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.content_label.setMinimumHeight(60)
        self.content_label.setMaximumHeight(120)
        content_layout.addWidget(self.content_label)
        
        container_layout.addWidget(content_frame)
        
        # ── Get icon manager for button icons ──
        self._icon_mgr = None
        try:
            from ui.music_indicator import get_icon_manager
            self._icon_mgr = get_icon_manager()
        except Exception as e:
            logger.warning(f"Could not load icon manager: {e}")
        
        # ── Action Buttons ──
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)
        
        # Edit button
        self.edit_btn = QPushButton(" Edit")
        self.edit_btn.setObjectName("actionBtn")
        self.edit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if self._icon_mgr:
            self.edit_btn.setIcon(self._icon_mgr.get_icon('edit', 16))
            self.edit_btn.setIconSize(QSize(16, 16))
        self.edit_btn.clicked.connect(self._on_edit)
        buttons_layout.addWidget(self.edit_btn)
        
        # Delete button
        self.delete_btn = QPushButton(" Delete")
        self.delete_btn.setObjectName("deleteBtn")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if self._icon_mgr:
            self.delete_btn.setIcon(self._icon_mgr.get_icon('trash', 16))
            self.delete_btn.setIconSize(QSize(16, 16))
        self.delete_btn.clicked.connect(self._on_delete)
        buttons_layout.addWidget(self.delete_btn)
        
        container_layout.addLayout(buttons_layout)
        
        # Second row of buttons
        buttons_layout2 = QHBoxLayout()
        buttons_layout2.setSpacing(8)
        
        # Pin button (disabled - no backend support yet)
        self.pin_btn = QPushButton(" Pin")
        self.pin_btn.setObjectName("actionBtn")
        self.pin_btn.setCheckable(True)
        self.pin_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pin_btn.setEnabled(False)
        self.pin_btn.setToolTip("Coming soon")
        if self._icon_mgr:
            self.pin_btn.setIcon(self._icon_mgr.get_icon('pin', 16))
            self.pin_btn.setIconSize(QSize(16, 16))
        self.pin_btn.clicked.connect(self._on_pin_toggle)
        buttons_layout2.addWidget(self.pin_btn)
        
        # Lock button (disabled - no backend support yet)
        self.lock_btn = QPushButton(" Lock")
        self.lock_btn.setObjectName("actionBtn")
        self.lock_btn.setCheckable(True)
        self.lock_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lock_btn.setEnabled(False)
        self.lock_btn.setToolTip("Coming soon")
        self.lock_btn.clicked.connect(self._on_lock_toggle)
        buttons_layout2.addWidget(self.lock_btn)
        
        # Export button
        self.export_btn = QPushButton(" Export")
        self.export_btn.setObjectName("actionBtn")
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        if self._icon_mgr:
            self.export_btn.setIcon(self._icon_mgr.get_icon('export', 16))
            self.export_btn.setIconSize(QSize(16, 16))
        self.export_btn.clicked.connect(self._on_export)
        buttons_layout2.addWidget(self.export_btn)
        
        container_layout.addLayout(buttons_layout2)
        
        outer_layout.addWidget(self.container)
        
        # Add glow effect
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(30)
        shadow.setColor(QColor(0, 180, 255, 100))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)
    
    def _apply_styling(self):
        """Apply glassmorphism styling."""
        self.setStyleSheet(f"""
            #glassContainer {{
                background-color: {CARD_COLORS['glass_bg']};
                border: 1px solid {CARD_COLORS['glass_border']};
                border-radius: 16px;
            }}
            
            #titleLabel {{
                color: {CARD_COLORS['text_primary']};
                background: transparent;
            }}
            
            #closeBtn {{
                background: rgba(255, 80, 80, 0.3);
                border: none;
                border-radius: 12px;
                color: white;
                font-size: 16px;
                font-weight: bold;
            }}
            
            #closeBtn:hover {{
                background: rgba(255, 100, 100, 0.5);
            }}
            
            #separator {{
                background: {CARD_COLORS['glass_border']};
                max-height: 1px;
            }}
            
            #metaLabel {{
                color: {CARD_COLORS['text_muted']};
                font-size: 11px;
                min-width: 70px;
                background: transparent;
            }}
            
            #metaValue {{
                color: {CARD_COLORS['text_secondary']};
                font-size: 11px;
                background: transparent;
            }}
            
            #importanceValue {{
                color: #ffd700;
                font-size: 12px;
                background: transparent;
            }}
            
            #contentFrame {{
                background: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(0, 150, 220, 0.2);
                border-radius: 8px;
            }}
            
            #contentLabel {{
                color: {CARD_COLORS['text_secondary']};
                font-size: 12px;
                background: transparent;
            }}
            
            #actionBtn {{
                background: {CARD_COLORS['button_bg']};
                border: 1px solid rgba(0, 150, 220, 0.3);
                border-radius: 6px;
                color: white;
                font-size: 11px;
                padding: 6px 12px;
                min-width: 60px;
            }}
            
            #actionBtn:hover {{
                background: {CARD_COLORS['button_hover']};
                border-color: {CARD_COLORS['accent_cyan']};
            }}
            
            #actionBtn:checked {{
                background: rgba(0, 255, 136, 0.3);
                border-color: {CARD_COLORS['accent_green']};
            }}
            
            #deleteBtn {{
                background: rgba(255, 50, 100, 0.2);
                border: 1px solid rgba(255, 50, 100, 0.3);
                border-radius: 6px;
                color: #ff6b8a;
                font-size: 11px;
                padding: 6px 12px;
                min-width: 60px;
            }}
            
            #deleteBtn:hover {{
                background: rgba(255, 50, 100, 0.4);
                border-color: {CARD_COLORS['danger']};
            }}
        """)
    
    # ========================================================================
    # Public Methods
    # ========================================================================
    
    def show_memory(self, memory_data: Dict[str, Any], position: QPoint = None):
        """
        Display memory details in the card.
        
        Args:
            memory_data: Memory dictionary with id, content, type, etc.
            position: Optional position to show the card at
        """
        self.current_memory_id = memory_data.get('id', '')
        self.current_memory_data = memory_data
        
        # Update content
        memory_type = memory_data.get('memory_type', 'conversation')
        
        # Title (first line of content or truncated)
        content = memory_data.get('content', memory_data.get('user_message', 'Memory'))
        title = content[:50] + '...' if len(content) > 50 else content
        self.title_label.setText(title)
        
        # Type
        type_display = memory_type.capitalize()
        self.type_value.setText(type_display)
        
        # Set type icon
        self._set_type_icon(memory_type)
        
        # Created timestamp
        created = memory_data.get('created_at', memory_data.get('timestamp'))
        if created:
            self.created_value.setText(self._format_timestamp(created))
        else:
            self.created_value.setText("Unknown")
        
        # Importance
        importance = memory_data.get('importance', 0.5)
        stars = int(importance * 5)
        self.importance_value.setText('★' * stars + '☆' * (5 - stars))
        
        # Content
        full_content = memory_data.get('content', memory_data.get('user_message', ''))
        nexa_response = memory_data.get('nexa_response', '')
        if nexa_response:
            full_content = f"User: {full_content}\nNexa: {nexa_response}"
        self.content_label.setText(full_content[:300])
        
        # Position and show
        if position:
            self._position_at(position)
        
        self._fade_in()
    
    def _set_type_icon(self, memory_type: str):
        """Set the type icon based on memory type."""
        try:
            from ui.music_indicator import get_icon_manager
            icon_mgr = get_icon_manager()
            
            icon_map = {
                'conversation': 'conversation',
                'knowledge': 'memory',
                'skill': 'lightning',
                'emotional': 'heart',
            }
            icon_name = icon_map.get(memory_type, 'thought')
            self.type_icon.setPixmap(icon_mgr.get_pixmap(icon_name, 24))
        except Exception as e:
            logger.warning(f"Could not load type icon: {e}")
    
    def _format_timestamp(self, timestamp) -> str:
        """Format timestamp as relative time."""
        if isinstance(timestamp, str):
            try:
                dt = datetime.fromisoformat(timestamp)
            except:
                return timestamp
        elif isinstance(timestamp, datetime):
            dt = timestamp
        else:
            return str(timestamp)
        
        now = datetime.now()
        diff = now - dt
        
        if diff.days > 30:
            return dt.strftime("%b %d, %Y")
        elif diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''} ago"
        elif diff.seconds > 60:
            mins = diff.seconds // 60
            return f"{mins} minute{'s' if mins > 1 else ''} ago"
        else:
            return "Just now"
    
    def _position_at(self, position: QPoint):
        """Position the card near the given point, staying on screen."""
        from PySide6.QtWidgets import QApplication
        
        screen = QApplication.primaryScreen().geometry()
        
        # Try to position to the right of the point
        x = position.x() + 20
        y = position.y() - self.height() // 2
        
        # Adjust if off screen
        if x + self.width() > screen.width() - 20:
            x = position.x() - self.width() - 20
        
        if y < 20:
            y = 20
        elif y + self.height() > screen.height() - 20:
            y = screen.height() - self.height() - 20
        
        self.move(x, y)
    
    def _fade_in(self):
        """Animate fade in."""
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(200)
        self.fade_anim.setStartValue(0.0)
        self.fade_anim.setEndValue(1.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_anim.start()
    
    def _fade_out(self):
        """Animate fade out and hide."""
        self.fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self.fade_anim.setDuration(150)
        self.fade_anim.setStartValue(1.0)
        self.fade_anim.setEndValue(0.0)
        self.fade_anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_anim.finished.connect(self.hide)
        self.fade_anim.start()
    
    def _close_card(self):
        """Close the card with animation."""
        self._fade_out()
        self.close_requested.emit()
    
    # ========================================================================
    # Button Handlers
    # ========================================================================
    
    def _on_edit(self):
        if self.current_memory_id:
            self.edit_requested.emit(self.current_memory_id)
    
    def _on_delete(self):
        if self.current_memory_id:
            self.delete_requested.emit(self.current_memory_id)
            self._close_card()
    
    def _on_pin_toggle(self):
        self.is_pinned = self.pin_btn.isChecked()
        self.pin_btn.setText(" Pinned" if self.is_pinned else " Pin")
        if self.current_memory_id:
            self.pin_toggled.emit(self.current_memory_id, self.is_pinned)
    
    def _on_lock_toggle(self):
        self.is_locked = self.lock_btn.isChecked()
        self.lock_btn.setText(" Locked" if self.is_locked else " Lock")
        if self.current_memory_id:
            self.lock_toggled.emit(self.current_memory_id, self.is_locked)
    
    def _on_export(self):
        if self.current_memory_id:
            self.export_requested.emit(self.current_memory_id)


# ============================================================================
# Demo/Test
# ============================================================================
if __name__ == "__main__":
    import sys
    from PySide6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    card = MemoryDetailCard()
    
    demo_memory = {
        "id": "test-123",
        "memory_type": "conversation",
        "content": "What's the weather like today?",
        "nexa_response": "The weather in Lahore is currently 25°C and sunny.",
        "importance": 0.7,
        "created_at": datetime.now().isoformat(),
    }
    
    card.show_memory(demo_memory, QPoint(100, 100))
    
    sys.exit(app.exec())
