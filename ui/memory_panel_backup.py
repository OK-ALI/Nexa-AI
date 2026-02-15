"""
Memory Panel - Smart Memory Management GUI

A modern glassmorphism-styled panel for viewing, editing, and managing
Nexa's Smart Memory. Features semantic search, category tabs, and
memory card management.

Design: Blue Nexa theme with dark background and translucent cards.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QScrollArea, QFrame, QTabWidget, QMessageBox,
    QGraphicsDropShadowEffect, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QFont, QColor, QPalette, QIcon

logger = logging.getLogger(__name__)


# ============================================================================
# Color Scheme - Nexa Blue Theme
# ============================================================================
COLORS = {
    'background': '#0d1117',
    'card': 'rgba(30, 40, 60, 0.7)',
    'card_hover': 'rgba(40, 55, 80, 0.85)',
    'accent': '#00a8ff',
    'accent_light': '#00d4ff',
    'text': '#ffffff',
    'text_secondary': '#a0b4c8',
    'border': '#1e3a5f',
    'danger': '#ff4757',
    'success': '#2ed573',
    'star': '#ffd32a',
}


# ============================================================================
# Stylesheets
# ============================================================================
PANEL_STYLE = f"""
QWidget#MemoryPanel {{
    background-color: {COLORS['background']};
    border-radius: 16px;
    border: 1px solid {COLORS['border']};
}}
"""

HEADER_STYLE = f"""
QLabel#HeaderTitle {{
    color: {COLORS['text']};
    font-size: 18px;
    font-weight: bold;
    padding: 8px;
}}
QPushButton#CloseButton {{
    background: transparent;
    border: none;
    color: {COLORS['text_secondary']};
    font-size: 18px;
    padding: 8px;
}}
QPushButton#CloseButton:hover {{
    color: {COLORS['danger']};
}}
"""

SEARCH_STYLE = f"""
QLineEdit#SearchBar {{
    background-color: rgba(30, 50, 70, 0.6);
    border: 1px solid {COLORS['border']};
    border-radius: 10px;
    padding: 10px 15px;
    color: {COLORS['text']};
    font-size: 14px;
}}
QLineEdit#SearchBar:focus {{
    border: 1px solid {COLORS['accent']};
}}
QLineEdit#SearchBar::placeholder {{
    color: {COLORS['text_secondary']};
}}
"""

TAB_STYLE = f"""
QTabWidget::pane {{
    border: none;
    background: transparent;
}}
QTabBar::tab {{
    background: transparent;
    color: {COLORS['text_secondary']};
    padding: 10px 20px;
    margin-right: 5px;
    font-size: 13px;
    border-bottom: 2px solid transparent;
}}
QTabBar::tab:selected {{
    color: {COLORS['accent']};
    border-bottom: 2px solid {COLORS['accent']};
}}
QTabBar::tab:hover {{
    color: {COLORS['text']};
}}
"""

BUTTON_STYLE = f"""
QPushButton#ActionButton {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS['accent']}, stop:1 {COLORS['accent_light']});
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    color: white;
    font-weight: bold;
    font-size: 13px;
}}
QPushButton#ActionButton:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {COLORS['accent_light']}, stop:1 {COLORS['accent']});
}}
QPushButton#ActionButton:pressed {{
    background: {COLORS['accent']};
}}
QPushButton#SecondaryButton {{
    background: rgba(30, 50, 70, 0.6);
    border: 1px solid {COLORS['border']};
    border-radius: 8px;
    padding: 10px 20px;
    color: {COLORS['text']};
    font-size: 13px;
}}
QPushButton#SecondaryButton:hover {{
    background: rgba(40, 60, 90, 0.8);
    border-color: {COLORS['accent']};
}}
"""

CARD_STYLE = f"""
QFrame#MemoryCard {{
    background-color: {COLORS['card']};
    border: 1px solid {COLORS['border']};
    border-radius: 12px;
    padding: 12px;
}}
QFrame#MemoryCard:hover {{
    background-color: {COLORS['card_hover']};
    border-color: {COLORS['accent']};
}}
"""


# ============================================================================
# Memory Card Widget
# ============================================================================
class MemoryCard(QFrame):
    """Individual memory card widget with content, timestamp, and actions."""
    
    deleted = Signal(str)  # Emits memory ID when deleted
    marked_important = Signal(str, bool)  # Emits (id, is_important)
    
    def __init__(self, memory_data: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.memory_data = memory_data
        self.memory_id = memory_data.get('id', '')
        self.is_important = memory_data.get('importance', 0.5) > 0.7
        
        self.setObjectName("MemoryCard")
        self.setStyleSheet(CARD_STYLE)
        self.setCursor(Qt.PointingHandCursor)
        
        self._setup_ui()
        self._add_shadow()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # Top row: Type icon + content
        top_row = QHBoxLayout()
        
        # Type icon
        memory_type = self.memory_data.get('memory_type', 'conversation')
        icon_map = {
            'conversation': '💬',
            'knowledge': '📚',
            'skill': '🎯',
        }
        type_label = QLabel(icon_map.get(memory_type, '💭'))
        type_label.setFont(QFont('Segoe UI Emoji', 14))
        top_row.addWidget(type_label)
        
        # Content preview
        content = self._get_content_preview()
        content_label = QLabel(content)
        content_label.setStyleSheet(f"color: {COLORS['text']}; font-size: 13px;")
        content_label.setWordWrap(True)
        top_row.addWidget(content_label, 1)
        
        layout.addLayout(top_row)
        
        # Bottom row: Timestamp + actions
        bottom_row = QHBoxLayout()
        
        # Timestamp
        timestamp = self._format_timestamp()
        time_label = QLabel(timestamp)
        time_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 11px;")
        bottom_row.addWidget(time_label)
        
        bottom_row.addStretch()
        
        # Star button (importance)
        self.star_btn = QPushButton("⭐" if self.is_important else "☆")
        self.star_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: 16px;
                color: {COLORS['star'] if self.is_important else COLORS['text_secondary']};
                padding: 4px;
            }}
            QPushButton:hover {{
                color: {COLORS['star']};
            }}
        """)
        self.star_btn.setCursor(Qt.PointingHandCursor)
        self.star_btn.clicked.connect(self._toggle_important)
        bottom_row.addWidget(self.star_btn)
        
        # Delete button
        delete_btn = QPushButton("🗑️")
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: 14px;
                color: {COLORS['text_secondary']};
                padding: 4px;
            }}
            QPushButton:hover {{
                color: {COLORS['danger']};
            }}
        """)
        delete_btn.setCursor(Qt.PointingHandCursor)
        delete_btn.clicked.connect(self._confirm_delete)
        bottom_row.addWidget(delete_btn)
        
        layout.addLayout(bottom_row)
    
    def _get_content_preview(self) -> str:
        """Get preview text from memory data."""
        if 'user_message' in self.memory_data:
            # Conversation: Show user message with response hint
            user_msg = self.memory_data['user_message']
            nexa_resp = self.memory_data.get('nexa_response', '')
            
            # Format: "User: [message] → [response preview]"
            if nexa_resp:
                text = f"You: {user_msg}"
                # Add response preview if space allows
                if len(text) < 60:
                    resp_preview = nexa_resp[:50 - len(text)] + "..." if len(nexa_resp) > 50 - len(text) else nexa_resp
                    text = f"{text} → {resp_preview}"
            else:
                text = user_msg
        elif 'fact' in self.memory_data:
            text = self.memory_data['fact']
        elif 'action' in self.memory_data:
            text = f"Action: {self.memory_data['action']}"
        else:
            text = "Memory content"
        
        # Truncate
        if len(text) > 100:
            text = text[:97] + "..."
        return text
    
    def _format_timestamp(self) -> str:
        """Format timestamp as relative time."""
        try:
            ts_str = self.memory_data.get('timestamp', '')
            if not ts_str:
                return "Unknown time"
            
            ts = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
            now = datetime.now()
            delta = now - ts.replace(tzinfo=None)
            
            if delta.days > 7:
                return ts.strftime("%b %d, %Y")
            elif delta.days > 0:
                return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
            elif delta.seconds > 3600:
                hours = delta.seconds // 3600
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            elif delta.seconds > 60:
                mins = delta.seconds // 60
                return f"{mins} min{'s' if mins > 1 else ''} ago"
            else:
                return "Just now"
        except:
            return "Unknown time"
    
    def _add_shadow(self):
        """Add drop shadow effect."""
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(15)
        shadow.setXOffset(0)
        shadow.setYOffset(4)
        shadow.setColor(QColor(0, 0, 0, 80))
        self.setGraphicsEffect(shadow)
    
    def _toggle_important(self):
        """Toggle importance status."""
        self.is_important = not self.is_important
        self.star_btn.setText("⭐" if self.is_important else "☆")
        self.star_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent;
                border: none;
                font-size: 16px;
                color: {COLORS['star'] if self.is_important else COLORS['text_secondary']};
                padding: 4px;
            }}
            QPushButton:hover {{
                color: {COLORS['star']};
            }}
        """)
        self.marked_important.emit(self.memory_id, self.is_important)
    
    def _confirm_delete(self):
        """Show delete confirmation."""
        reply = QMessageBox.question(
            self, 
            "Delete Memory",
            "Are you sure you want to delete this memory?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.deleted.emit(self.memory_id)


# ============================================================================
# Memory Panel Widget
# ============================================================================
class MemoryPanel(QWidget):
    """Main Memory Management Panel."""
    
    closed = Signal()
    
    def __init__(self, context_manager=None, parent=None):
        super().__init__(parent)
        self.context = context_manager
        self.memories = {'conversations': [], 'knowledge': [], 'skills': []}
        
        self.setObjectName("MemoryPanel")
        self.setWindowTitle("Nexa Memory")
        self.setFixedSize(550, 700)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        self._setup_ui()
        self._load_memories()
    
    def _setup_ui(self):
        # Main container with background
        container = QFrame(self)
        container.setObjectName("MemoryPanel")
        container.setStyleSheet(PANEL_STYLE)
        container.setGeometry(0, 0, 550, 700)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header = self._create_header()
        layout.addLayout(header)
        
        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setObjectName("SearchBar")
        self.search_input.setPlaceholderText("🔍 Search memories...")
        self.search_input.setStyleSheet(SEARCH_STYLE)
        self.search_input.textChanged.connect(self._on_search)
        layout.addWidget(self.search_input)
        
        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(TAB_STYLE)
        
        # Create tab content
        self.conv_scroll = self._create_scroll_area()
        self.know_scroll = self._create_scroll_area()
        self.skill_scroll = self._create_scroll_area()
        
        self.tabs.addTab(self.conv_scroll, "💬 Conversations (0)")
        self.tabs.addTab(self.know_scroll, "📚 Knowledge (0)")
        self.tabs.addTab(self.skill_scroll, "🎯 Skills (0)")
        
        layout.addWidget(self.tabs, 1)
        
        # Bottom buttons
        buttons = self._create_buttons()
        layout.addLayout(buttons)
        
        # Add shadow to panel
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(30)
        shadow.setXOffset(0)
        shadow.setYOffset(8)
        shadow.setColor(QColor(0, 0, 0, 120))
        container.setGraphicsEffect(shadow)
    
    def _create_header(self) -> QHBoxLayout:
        """Create header with title and close button."""
        layout = QHBoxLayout()
        
        title = QLabel("🧠 Nexa Memory")
        title.setObjectName("HeaderTitle")
        title.setStyleSheet(HEADER_STYLE)
        layout.addWidget(title)
        
        layout.addStretch()
        
        close_btn = QPushButton("✕")
        close_btn.setObjectName("CloseButton")
        close_btn.setStyleSheet(HEADER_STYLE)
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
                background: transparent;
                width: 8px;
            }
            QScrollBar::handle:vertical {
                background: rgba(100, 120, 150, 0.5);
                border-radius: 4px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 8, 0)
        layout.setSpacing(10)
        layout.addStretch()
        
        scroll.setWidget(container)
        return scroll
    
    def _create_buttons(self) -> QHBoxLayout:
        """Create bottom action buttons."""
        layout = QHBoxLayout()
        layout.setSpacing(12)
        
        export_btn = QPushButton("📤 Export")
        export_btn.setObjectName("SecondaryButton")
        export_btn.setStyleSheet(BUTTON_STYLE)
        export_btn.setCursor(Qt.PointingHandCursor)
        export_btn.clicked.connect(self._export_memories)
        layout.addWidget(export_btn)
        
        clear_btn = QPushButton("🧹 Clear Old")
        clear_btn.setObjectName("SecondaryButton")
        clear_btn.setStyleSheet(BUTTON_STYLE)
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.clicked.connect(self._clear_old)
        layout.addWidget(clear_btn)
        
        clear_all_btn = QPushButton("🗑️ Clear All")
        clear_all_btn.setObjectName("ActionButton")
        clear_all_btn.setStyleSheet(BUTTON_STYLE)
        clear_all_btn.setCursor(Qt.PointingHandCursor)
        clear_all_btn.clicked.connect(self._clear_all)
        layout.addWidget(clear_all_btn)
        
        return layout
    
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
        
        self.tabs.setTabText(0, f"💬 Conversations ({conv_count})")
        self.tabs.setTabText(1, f"📚 Knowledge ({know_count})")
        self.tabs.setTabText(2, f"🎯 Skills ({skill_count})")
    
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
            empty_label = QLabel("No memories yet")
            empty_label.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 40px;")
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
            card = MemoryCard(mem)
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
        """Handle memory deletion."""
        if not self.context or not hasattr(self.context, 'smart_memory'):
            return
        
        try:
            self.context.smart_memory.forget_memory(memory_id)
            self._load_memories()
        except Exception as e:
            logger.error(f"Delete error: {e}")
    
    def _on_marked_important(self, memory_id: str, is_important: bool):
        """Handle importance toggle."""
        logger.info(f"⭐ Toggle importance: {memory_id} → {is_important}")
        
        if not self.context or not hasattr(self.context, 'smart_memory'):
            logger.warning("❌ Cannot toggle importance: smart_memory not available")
            return
        
        try:
            importance = 0.9 if is_important else 0.5
            result = self.context.smart_memory.mark_important(memory_id, importance)
            logger.info(f"✅ Importance updated: {memory_id} → {importance} (success={result})")
        except Exception as e:
            logger.error(f"❌ Mark important error: {e}")
    
    def _export_memories(self):
        """Export memories to JSON."""
        try:
            import json
            from pathlib import Path
            
            export_path = Path.home() / "Documents" / "nexa_memories_export.json"
            
            data = {
                'exported_at': datetime.now().isoformat(),
                'conversations': self.memories.get('conversations', []),
                'knowledge': self.memories.get('knowledge', []),
                'skills': self.memories.get('skills', []),
            }
            
            # Remove numpy arrays for JSON serialization
            def clean_for_json(obj):
                if isinstance(obj, dict):
                    return {k: clean_for_json(v) for k, v in obj.items() if k != 'vector' and k != 'embedding'}
                elif isinstance(obj, list):
                    return [clean_for_json(i) for i in obj]
                else:
                    return obj
            
            data = clean_for_json(data)
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            QMessageBox.information(
                self,
                "Export Complete",
                f"Memories exported to:\n{export_path}"
            )
            
        except Exception as e:
            logger.error(f"Export error: {e}")
            QMessageBox.warning(self, "Export Failed", str(e))
    
    def _clear_old(self):
        """Clear old memories (30+ days)."""
        reply = QMessageBox.question(
            self,
            "Clear Old Memories",
            "Delete memories older than 30 days?\n(Important memories will be kept)",
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
                "Cleanup Complete",
                f"Deleted {deleted} old memories"
            )
        except Exception as e:
            logger.error(f"Clear old error: {e}")
    
    def _clear_all(self):
        """Clear ALL memories (with confirmation)."""
        reply = QMessageBox.warning(
            self,
            "⚠️ Clear All Memory",
            "This will DELETE ALL your memories including:\n\n"
            "• All conversations\n"
            "• All knowledge facts (preferences, personal info)\n"
            "• All learned skills\n\n"
            "This action CANNOT be undone. Are you sure?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        # Double confirmation for safety
        reply2 = QMessageBox.critical(
            self,
            "⚠️ Final Confirmation",
            "Are you ABSOLUTELY sure?\n\nAll your memories will be permanently deleted.",
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
                "Memory Cleared",
                f"Deleted all memories:\n\n"
                f"• Conversations: {result['conversations']}\n"
                f"• Knowledge: {result['knowledge']}\n"
                f"• Skills: {result['skills']}\n\n"
                f"Total: {total} items"
            )
        except Exception as e:
            logger.error(f"Clear all error: {e}")
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to clear memory: {str(e)}"
            )
    
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
