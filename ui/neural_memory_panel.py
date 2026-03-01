"""
Neural Memory Panel - Living Brain Visualization

A reimagined memory panel where memories exist as neural nodes
in a living, breathing brain visualization.

This replaces the tab-based list view with an immersive neural network.
"""

import logging
from typing import List, Dict, Any, Optional

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QLineEdit, QGraphicsDropShadowEffect, QSizePolicy,
    QApplication, QStackedWidget, QScrollArea
)
from PySide6.QtCore import (
    Qt, Signal, QTimer, QPoint, QPropertyAnimation, QEasingCurve, QSize,
    QMetaObject, Q_ARG, Slot
)
from PySide6.QtGui import QFont, QColor, QIcon

from ui.widgets.web_neural_graph import WebNeuralBrainWidget
from ui.widgets.memory_detail_card import MemoryDetailCard

logger = logging.getLogger(__name__)


# ============================================================================
# Styles
# ============================================================================
PANEL_STYLE = """
    QFrame#NeuralMemoryPanel {
        background: qlineargradient(
            x1:0, y1:0, x2:0.3, y2:1,
            stop:0 rgba(12, 14, 35, 0.97),
            stop:0.5 rgba(8, 10, 28, 0.96),
            stop:1 rgba(6, 8, 24, 0.95)
        );
        border: 1px solid rgba(0, 200, 255, 0.25);
        border-radius: 18px;
    }
"""

SEARCH_STYLE = """
    QLineEdit {
        background: rgba(0, 0, 0, 0.35);
        border: 1px solid rgba(0, 180, 255, 0.2);
        border-radius: 14px;
        padding: 10px 18px;
        font-size: 13px;
        color: rgba(200, 230, 255, 0.9);
    }
    
    QLineEdit:focus {
        border: 1px solid rgba(0, 200, 255, 0.6);
        background: rgba(0, 15, 35, 0.5);
    }
    
    QLineEdit::placeholder {
        color: rgba(100, 150, 200, 0.5);
    }
"""

BUTTON_STYLE = """
    QPushButton {
        background: rgba(0, 140, 220, 0.15);
        border: 1px solid rgba(0, 180, 255, 0.2);
        border-radius: 10px;
        color: rgba(200, 230, 255, 0.9);
        font-size: 12px;
        font-weight: 500;
        padding: 8px 18px;
        min-width: 80px;
    }
    
    QPushButton:hover {
        background: rgba(0, 180, 255, 0.3);
        border-color: rgba(0, 220, 255, 0.5);
    }
    
    QPushButton:pressed {
        background: rgba(0, 200, 255, 0.35);
    }
"""


class NeuralMemoryPanel(QWidget):
    """
    Neural Memory Panel with living brain visualization.
    
    Features:
    - Central neural graph showing memories as nodes
    - 3D parallax effect on mouse movement
    - Floating detail card on node selection
    - Search filtering with neural activation effect
    """
    
    # Signals
    closed = Signal()
    memory_deleted = Signal(str)
    memory_updated = Signal(str, dict)
    
    def __init__(self, context_manager=None, auth_manager=None, parent=None):
        super().__init__(parent)
        
        self.context = context_manager
        self.auth_manager = auth_manager
        self.all_memories: List[Dict[str, Any]] = []
        
        # Window setup
        self.setObjectName("NeuralMemoryPanel")
        self.setWindowTitle("NEXA Neural Memory")
        self.setFixedSize(900, 700)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        
        # Drag state
        self._drag_pos = None
        
        self._setup_ui()
        self._connect_signals()
        self._load_memories()
        
        # Debounce timer for auto-refresh (prevents rapid reloads)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.setInterval(800)  # 800ms debounce
        self._refresh_timer.timeout.connect(self._refresh_memories)
        
        logger.info("🧠 NeuralMemoryPanel initialized")
    
    def set_event_bus(self, event_bus) -> None:
        """Subscribe to memory.updated events for live sync."""
        self._event_bus = event_bus
        event_bus.subscribe("memory.updated", self._on_memory_updated)
        logger.info("🔗 NeuralMemoryPanel subscribed to memory.updated events")
    
    def _on_memory_updated(self, **kwargs):
        """
        Auto-refresh when new memory is stored (debounced).
        
        THREAD-SAFETY: This callback is invoked from background threads
        (context_manager.store_async).  QTimer.start() must only be called
        from the owning (main) thread, so we marshal via QMetaObject.
        """
        if self.isVisible():
            # Safe cross-thread invocation → runs _schedule_refresh on Qt main thread
            QMetaObject.invokeMethod(
                self, "_schedule_refresh", Qt.ConnectionType.QueuedConnection
            )
    
    @Slot()
    def _schedule_refresh(self):
        """Start the debounce timer (must run on the Qt main thread)."""
        self._refresh_timer.start()
    
    def _setup_ui(self):
        """Build the panel UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Container frame with glass effect
        self.container = QFrame(self)
        self.container.setObjectName("NeuralMemoryPanel")
        self.container.setStyleSheet(PANEL_STYLE)
        
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(20, 16, 20, 20)
        container_layout.setSpacing(12)
        
        # ── Header ──
        header = self._create_header()
        container_layout.addLayout(header)
        
        # ── Search bar ──
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search neural pathways...")
        self.search_input.setStyleSheet(SEARCH_STYLE)
        self.search_input.textChanged.connect(self._on_search)
        container_layout.addWidget(self.search_input)
        
        # ── Neural Brain Widget (web-based visualization) ──
        self.neural_brain = WebNeuralBrainWidget()
        self.neural_brain.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # ── Users View ──
        self.users_widget = self._create_users_widget()
        
        # ── Stacked container (memories / users) ──
        self.view_stack = QStackedWidget()
        self.view_stack.addWidget(self.neural_brain)      # index 0
        self.view_stack.addWidget(self.users_widget)       # index 1
        self.view_stack.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        container_layout.addWidget(self.view_stack, 1)
        
        # ── Bottom controls ──
        controls = self._create_controls()
        container_layout.addLayout(controls)
        
        main_layout.addWidget(self.container)
        
        # Outer glow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(60)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 160, 255, 80))
        self.container.setGraphicsEffect(shadow)
        
        # ── Floating detail card (created but hidden) ──
        self.detail_card = MemoryDetailCard(None)  # Separate window
    
    def _create_header(self) -> QHBoxLayout:
        """Create the header with title and close button."""
        layout = QHBoxLayout()
        layout.setSpacing(12)
        
        # Brain icon
        try:
            from ui.music_indicator import get_icon_manager
            icon_mgr = get_icon_manager()
            icon_label = QLabel()
            icon_label.setPixmap(icon_mgr.get_pixmap('memory', 28))
            icon_label.setStyleSheet("background: transparent;")
            layout.addWidget(icon_label)
        except Exception as e:
            logger.warning(f"Could not load icon: {e}")
        
        # Title
        title = QLabel("NEURAL MEMORY INTERFACE")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        title.setStyleSheet("""
            color: #00d4ff;
            background: transparent;
            letter-spacing: 2px;
        """)
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Stats label
        self.stats_label = QLabel("0 memories")
        self.stats_label.setStyleSheet("""
            color: rgba(150, 200, 255, 0.7);
            font-size: 11px;
            background: transparent;
        """)
        layout.addWidget(self.stats_label)
        
        # Close button
        close_btn = QPushButton("×")
        close_btn.setFixedSize(32, 32)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 80, 80, 0.2);
                border: 1px solid rgba(255, 80, 80, 0.3);
                border-radius: 16px;
                color: rgba(255, 150, 150, 0.9);
                font-size: 18px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: rgba(255, 100, 100, 0.4);
                border-color: rgba(255, 100, 100, 0.6);
            }
        """)
        close_btn.clicked.connect(self._close_panel)
        layout.addWidget(close_btn)
        
        return layout
    
    def _create_controls(self) -> QVBoxLayout:
        """Create bottom control buttons in two rows."""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        
        # Get icon manager for button icons
        icon_mgr = None
        try:
            from ui.music_indicator import get_icon_manager
            icon_mgr = get_icon_manager()
        except Exception as e:
            logger.warning(f"Could not load icon manager: {e}")
        
        # === Row 1: Action buttons ===
        action_row = QHBoxLayout()
        action_row.setSpacing(8)
        
        # Export button
        export_btn = QPushButton(" Export")
        export_btn.setStyleSheet(BUTTON_STYLE)
        export_btn.setMinimumWidth(75)
        if icon_mgr:
            export_btn.setIcon(icon_mgr.get_icon('export', 16))
            export_btn.setIconSize(QSize(16, 16))
        export_btn.clicked.connect(self._export_memories)
        action_row.addWidget(export_btn)
        
        # Clear old button
        clear_old_btn = QPushButton(" Clear Old")
        clear_old_btn.setStyleSheet(BUTTON_STYLE)
        clear_old_btn.setMinimumWidth(85)
        clear_old_btn.setToolTip("Delete memories older than 30 days")
        if icon_mgr:
            clear_old_btn.setIcon(icon_mgr.get_icon('trash', 16))
            clear_old_btn.setIconSize(QSize(16, 16))
        clear_old_btn.clicked.connect(self._clear_old_memories)
        action_row.addWidget(clear_old_btn)
        
        # Refresh button
        refresh_btn = QPushButton(" Refresh")
        refresh_btn.setStyleSheet(BUTTON_STYLE)
        refresh_btn.setMinimumWidth(75)
        refresh_btn.setToolTip("Refresh memory view")
        refresh_btn.clicked.connect(self._refresh_memories)
        action_row.addWidget(refresh_btn)
        
        # Reseed button  
        reseed_btn = QPushButton(" Reseed")
        reseed_btn.setStyleSheet(BUTTON_STYLE)
        reseed_btn.setMinimumWidth(75)
        reseed_btn.setToolTip("Reload personal knowledge from user_prefs.json")
        reseed_btn.clicked.connect(self._reseed_knowledge)
        action_row.addWidget(reseed_btn)
        
        # Purge All button
        purge_btn = QPushButton(" Purge All")
        purge_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 50, 50, 0.2);
                border: 1px solid rgba(255, 80, 80, 0.3);
                border-radius: 8px;
                color: rgba(255, 150, 150, 0.9);
                font-size: 12px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background: rgba(255, 80, 80, 0.4);
                border-color: rgba(255, 100, 100, 0.6);
            }
        """)
        purge_btn.setToolTip("Delete ALL memories permanently")
        purge_btn.clicked.connect(self._purge_all_memories)
        action_row.addWidget(purge_btn)
        
        action_row.addStretch()
        main_layout.addLayout(action_row)
        
        # === Row 2: Filter buttons ===
        filter_row = QHBoxLayout()
        filter_row.setSpacing(8)
        
        filter_label = QLabel("Filter:")
        filter_label.setStyleSheet("color: rgba(255, 255, 255, 0.6); font-size: 11px;")
        filter_row.addWidget(filter_label)
        
        self.filter_all_btn = QPushButton(" All")
        self.filter_all_btn.setCheckable(True)
        self.filter_all_btn.setChecked(True)
        self.filter_all_btn.setStyleSheet(BUTTON_STYLE)
        self.filter_all_btn.setMinimumWidth(60)
        if icon_mgr:
            self.filter_all_btn.setIcon(icon_mgr.get_icon('memory', 16))
            self.filter_all_btn.setIconSize(QSize(16, 16))
        self.filter_all_btn.clicked.connect(lambda: self._filter_by_type(None))
        filter_row.addWidget(self.filter_all_btn)
        
        self.filter_conv_btn = QPushButton(" Conversations")
        self.filter_conv_btn.setCheckable(True)
        self.filter_conv_btn.setStyleSheet(BUTTON_STYLE)
        self.filter_conv_btn.setMinimumWidth(110)
        if icon_mgr:
            self.filter_conv_btn.setIcon(icon_mgr.get_icon('conversation', 16))
            self.filter_conv_btn.setIconSize(QSize(16, 16))
        self.filter_conv_btn.clicked.connect(lambda: self._filter_by_type('conversation'))
        filter_row.addWidget(self.filter_conv_btn)
        
        self.filter_know_btn = QPushButton(" Knowledge")
        self.filter_know_btn.setCheckable(True)
        self.filter_know_btn.setStyleSheet(BUTTON_STYLE)
        self.filter_know_btn.setMinimumWidth(95)
        if icon_mgr:
            self.filter_know_btn.setIcon(icon_mgr.get_icon('thought', 16))
            self.filter_know_btn.setIconSize(QSize(16, 16))
        self.filter_know_btn.clicked.connect(lambda: self._filter_by_type('knowledge'))
        filter_row.addWidget(self.filter_know_btn)
        
        self.filter_skill_btn = QPushButton(" Skills")
        self.filter_skill_btn.setCheckable(True)
        self.filter_skill_btn.setStyleSheet(BUTTON_STYLE)
        self.filter_skill_btn.setMinimumWidth(70)
        if icon_mgr:
            self.filter_skill_btn.setIcon(icon_mgr.get_icon('lightning', 16))
            self.filter_skill_btn.setIconSize(QSize(16, 16))
        self.filter_skill_btn.clicked.connect(lambda: self._filter_by_type('skill'))
        filter_row.addWidget(self.filter_skill_btn)
        
        # Separator between memory filters and users
        separator = QLabel("|")
        separator.setStyleSheet("color: rgba(255, 255, 255, 0.2); font-size: 14px; padding: 0 4px;")
        filter_row.addWidget(separator)
        
        # Users filter button
        self.filter_users_btn = QPushButton(" Users")
        self.filter_users_btn.setCheckable(True)
        self.filter_users_btn.setStyleSheet(BUTTON_STYLE)
        self.filter_users_btn.setMinimumWidth(70)
        if icon_mgr:
            self.filter_users_btn.setIcon(icon_mgr.get_icon('assistant', 16))
            self.filter_users_btn.setIconSize(QSize(16, 16))
        self.filter_users_btn.clicked.connect(self._show_users_view)
        filter_row.addWidget(self.filter_users_btn)
        
        filter_row.addStretch()
        main_layout.addLayout(filter_row)
        
        return main_layout
    
    def _connect_signals(self):
        """Connect neural brain signals."""
        self.neural_brain.node_selected.connect(self._on_node_selected)
        self.neural_brain.node_hovered.connect(self._on_node_hovered)
        
        # Detail card signals
        self.detail_card.delete_requested.connect(self._on_delete_memory)
        self.detail_card.close_requested.connect(self._on_detail_closed)
        self.detail_card.edit_requested.connect(self._on_edit_memory)
        self.detail_card.export_requested.connect(self._on_export_single_memory)
    
    # ========================================================================
    # Data Loading
    # ========================================================================
    
    def _load_memories(self):
        """Load memories from context manager."""
        self.all_memories.clear()
        
        if not self.context:
            logger.warning("No context manager - using demo data")
            self._load_demo_data()
            return
        
        try:
            # Get smart memory (not memory_manager)
            sm = getattr(self.context, 'smart_memory', None)
            if not sm:
                logger.warning("No smart_memory found in context")
                self._load_demo_data()
                return
            
            # Load conversation memories
            conversations = sm.recall_recent(limit=100) or []
            for conv in conversations:
                if hasattr(conv, 'to_dict'):
                    mem_dict = conv.to_dict()
                elif isinstance(conv, dict):
                    mem_dict = conv
                else:
                    mem_dict = {}
                
                mem_dict['memory_type'] = 'conversation'
                self.all_memories.append(mem_dict)
            
            # Load knowledge memories
            knowledge = sm.get_knowledge(limit=100) or []
            for know in knowledge:
                if hasattr(know, 'to_dict'):
                    mem_dict = know.to_dict()
                elif isinstance(know, dict):
                    mem_dict = know
                else:
                    mem_dict = {}
                
                mem_dict['memory_type'] = 'knowledge'
                self.all_memories.append(mem_dict)
            
            # Load skill memories
            skills = sm.store.get_all('skills', limit=100) if hasattr(sm, 'store') else []
            for skill in skills:
                if hasattr(skill, 'to_dict'):
                    mem_dict = skill.to_dict()
                elif isinstance(skill, dict):
                    mem_dict = skill
                else:
                    mem_dict = {}
                
                mem_dict['memory_type'] = 'skill'
                self.all_memories.append(mem_dict)
            
            logger.info(f"📚 Loaded {len(self.all_memories)} memories")
            
        except Exception as e:
            logger.error(f"Failed to load memories: {e}")
            self._load_demo_data()
        
        # Update the neural graph
        self._update_graph()
    
    def _load_demo_data(self):
        """Load demo data for testing."""
        self.all_memories = [
            {"id": "1", "memory_type": "conversation", "user_message": "Hello Nexa", "nexa_response": "Hi! How can I help?", "importance": 0.8},
            {"id": "2", "memory_type": "knowledge", "fact": "User prefers dark theme", "importance": 0.9},
            {"id": "3", "memory_type": "skill", "action": "set_volume", "importance": 0.6},
            {"id": "4", "memory_type": "conversation", "user_message": "What's the weather?", "nexa_response": "It's 25°C and sunny.", "importance": 0.5},
            {"id": "5", "memory_type": "knowledge", "fact": "User lives in Lahore", "importance": 0.7},
            {"id": "6", "memory_type": "conversation", "user_message": "Play some music", "nexa_response": "Playing your favorites.", "importance": 0.4},
            {"id": "7", "memory_type": "skill", "action": "open_browser", "importance": 0.5},
            {"id": "8", "memory_type": "knowledge", "fact": "User is a developer", "importance": 0.8},
            {"id": "9", "memory_type": "conversation", "user_message": "Set a reminder", "nexa_response": "Reminder set for 3 PM.", "importance": 0.6},
            {"id": "10", "memory_type": "skill", "action": "take_screenshot", "importance": 0.7},
        ]
        logger.info("📚 Loaded demo memories")
        self._update_graph()
    
    def _update_graph(self):
        """Update the neural graph with current memories."""
        # Convert to format expected by neural brain
        formatted = []
        for mem in self.all_memories:
            # Determine content for display
            content = mem.get('user_message') or mem.get('fact') or mem.get('action') or 'Memory'
            
            formatted.append({
                'id': mem.get('id', str(len(formatted))),
                'memory_type': mem.get('memory_type', 'conversation'),
                'content': content,
                'importance': mem.get('importance', 0.5),
                **mem  # Include all original data
            })
        
        self.neural_brain.set_memories(formatted)
        self.stats_label.setText(f"{len(formatted)} memories")
    
    # ========================================================================
    # Event Handlers
    # ========================================================================
    
    def _on_node_selected(self, memory_id: str):
        """Handle node selection - show detail card."""
        node = self.neural_brain.nodes.get(memory_id)
        if not node:
            return
        
        # Get screen position of the node
        node_pos = node.get_display_position(self.neural_brain.center_offset)
        global_pos = self.neural_brain.mapToGlobal(QPoint(int(node_pos.x()), int(node_pos.y())))
        
        # Show detail card
        self.detail_card.show_memory(node.memory_data, global_pos)
    
    def _on_node_hovered(self, memory_id: str):
        """Handle node hover - could show tooltip."""
        pass  # Could implement tooltip here
    
    def _on_delete_memory(self, memory_id: str):
        """Handle memory deletion request."""
        if self.context and hasattr(self.context, 'smart_memory'):
            try:
                # Determine type and delete
                for mem in self.all_memories:
                    if mem.get('id') == memory_id:
                        mem_type = mem.get('memory_type', 'conversation')
                        table_map = {
                            'conversation': 'conversations',
                            'knowledge': 'knowledge',
                            'skill': 'skills'
                        }
                        table = table_map.get(mem_type, 'conversations')
                        
                        self.context.smart_memory.store.delete(table, memory_id)
                        logger.info(f"🗑️ Deleted memory: {memory_id}")
                        break
            except Exception as e:
                logger.error(f"Failed to delete memory: {e}")
        
        # Remove from local list and refresh
        self.all_memories = [m for m in self.all_memories if m.get('id') != memory_id]
        self._update_graph()
        self.memory_deleted.emit(memory_id)
    
    def _on_detail_closed(self):
        """Handle detail card close."""
        self.neural_brain.clear_selection()
    
    def _on_edit_memory(self, memory_id: str):
        """Handle edit memory request — show inline content editor."""
        from PySide6.QtWidgets import QInputDialog
        
        # Find the memory
        mem = next((m for m in self.all_memories if m.get('id') == memory_id), None)
        if not mem:
            return
        
        # Get current content
        current = mem.get('content') or mem.get('user_message') or mem.get('fact') or mem.get('action') or ''
        
        new_text, ok = QInputDialog.getMultiLineText(
            self, "Edit Memory", "Content:", current
        )
        
        if ok and new_text and new_text != current:
            # Update the field that was present
            if 'fact' in mem:
                mem['fact'] = new_text
            elif 'user_message' in mem:
                mem['user_message'] = new_text
            elif 'action' in mem:
                mem['action'] = new_text
            mem['content'] = new_text
            
            self._update_graph()
            logger.info(f"✏️ Edited memory: {memory_id}")
    
    def _on_export_single_memory(self, memory_id: str):
        """Export a single memory to a JSON file."""
        from PySide6.QtWidgets import QFileDialog
        import json
        
        mem = next((m for m in self.all_memories if m.get('id') == memory_id), None)
        if not mem:
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Memory", f"memory_{memory_id}.json", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(mem, f, indent=2, default=str)
                logger.info(f"📤 Exported memory {memory_id} to {file_path}")
            except Exception as e:
                logger.error(f"Export failed: {e}")
    
    def _on_search(self, query: str):
        """Filter memories by search query."""
        query = query.lower().strip()
        
        if not query:
            self._update_graph()
            return
        
        # Filter memories that match
        filtered = []
        for mem in self.all_memories:
            searchable = ' '.join(str(v) for v in mem.values() if v).lower()
            if query in searchable:
                filtered.append(mem)
        
        # Update graph with filtered data
        formatted = []
        for mem in filtered:
            content = mem.get('user_message') or mem.get('fact') or mem.get('action') or 'Memory'
            formatted.append({
                'id': mem.get('id', str(len(formatted))),
                'memory_type': mem.get('memory_type', 'conversation'),
                'content': content,
                'importance': mem.get('importance', 0.5),
                **mem
            })
        
        self.neural_brain.set_memories(formatted)
        self.stats_label.setText(f"{len(formatted)} of {len(self.all_memories)} memories")
    
    def _filter_by_type(self, memory_type: Optional[str]):
        """Filter by memory type."""
        # Switch to memories view
        self.view_stack.setCurrentIndex(0)
        
        # Update button states
        self.filter_all_btn.setChecked(memory_type is None)
        self.filter_conv_btn.setChecked(memory_type == 'conversation')
        self.filter_know_btn.setChecked(memory_type == 'knowledge')
        self.filter_skill_btn.setChecked(memory_type == 'skill')
        self.filter_users_btn.setChecked(False)
        
        if memory_type is None:
            self._update_graph()
        else:
            filtered = [m for m in self.all_memories if m.get('memory_type') == memory_type]
            formatted = []
            for mem in filtered:
                content = mem.get('user_message') or mem.get('fact') or mem.get('action') or 'Memory'
                formatted.append({
                    'id': mem.get('id', str(len(formatted))),
                    'memory_type': mem.get('memory_type', 'conversation'),
                    'content': content,
                    'importance': mem.get('importance', 0.5),
                    **mem
                })
            
            self.neural_brain.set_memories(formatted)
            self.stats_label.setText(f"{len(formatted)} {memory_type} memories")
    
    def _export_memories(self):
        """Export memories to JSON file."""
        from PySide6.QtWidgets import QFileDialog
        import json
        
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Export Memories", "nexa_memories.json", "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.all_memories, f, indent=2, default=str)
                logger.info(f"📤 Exported {len(self.all_memories)} memories to {file_path}")
            except Exception as e:
                logger.error(f"Export failed: {e}")
    
    def _clear_old_memories(self):
        """Clear memories older than 30 days."""
        from PySide6.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self, "Clear Old Memories",
            "Delete all memories older than 30 days?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                if self.context and hasattr(self.context, 'smart_memory'):
                    result = self.context.smart_memory.prune_old_memories(days=30)
                    self._load_memories()
                    QMessageBox.information(
                        self, "Cleanup Complete",
                        f"Deleted {result} old memories."
                    )
            except Exception as e:
                logger.error(f"Clear old failed: {e}")
                QMessageBox.critical(self, "Error", str(e))
    
    def _refresh_memories(self):
        """Refresh the memory panel."""
        self._load_memories()
        logger.info("🔄 Memory panel refreshed")
    
    def _reseed_knowledge(self):
        """Reseed personal knowledge from user_prefs.json."""
        from PySide6.QtWidgets import QMessageBox
        
        if not self.context:
            return
        
        reply = QMessageBox.question(
            self, "🌱 Reseed Personal Knowledge",
            "This will reload personal data from user_prefs.json\n"
            "(relationships, user info, etc.)\n\n"
            "Existing duplicate facts will be updated.\n\n"
            "Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.context.refresh_personal_knowledge()
                self._load_memories()
                QMessageBox.information(
                    self, "✅ Knowledge Reseeded",
                    "Personal knowledge has been refreshed from user_prefs.json!"
                )
            except Exception as e:
                logger.error(f"Reseed error: {e}")
                QMessageBox.critical(self, "Reseed Failed", str(e))
    
    def _purge_all_memories(self):
        """Delete ALL memories permanently."""
        from PySide6.QtWidgets import QMessageBox
        
        reply = QMessageBox.warning(
            self, "⚠️ PURGE ALL MEMORIES",
            "⚡ WARNING: This will DELETE ALL memories! ⚡\n\n"
            "• All conversations\n"
            "• All knowledge facts\n"
            "• All learned skills\n\n"
            "This action CANNOT be undone!\n\n"
            "Are you absolutely sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Double confirmation
            confirm = QMessageBox.critical(
                self, "Final Confirmation",
                "LAST CHANCE!\n\nType 'yes' in your mind and click OK to confirm purge.",
                QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel
            )
            
            if confirm == QMessageBox.StandardButton.Ok:
                try:
                    if self.context and hasattr(self.context, 'smart_memory'):
                        result = self.context.smart_memory.clear_all_memory(include_knowledge=True)
                        self._load_memories()
                        QMessageBox.information(
                            self, "🌀 Purge Complete",
                            f"All memories have been cleared:\n"
                            f"• Conversations: {result.get('conversations', 0)}\n"
                            f"• Knowledge: {result.get('knowledge', 0)}\n"
                            f"• Skills: {result.get('skills', 0)}"
                        )
                except Exception as e:
                    logger.error(f"Purge failed: {e}")
                    QMessageBox.critical(self, "Purge Failed", str(e))
    
    # ========================================================================
    # Users View
    # ========================================================================
    
    def _create_users_widget(self) -> QWidget:
        """Create the users list widget for the stacked view."""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Header with user count
        header_layout = QHBoxLayout()
        self.users_header_label = QLabel("👤 Registered Users")
        self.users_header_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        self.users_header_label.setStyleSheet("color: #00d4ff; background: transparent;")
        header_layout.addWidget(self.users_header_label)
        
        header_layout.addStretch()
        
        self.users_count_label = QLabel("0 users")
        self.users_count_label.setStyleSheet(
            "color: rgba(150, 200, 255, 0.7); font-size: 11px; background: transparent;"
        )
        header_layout.addWidget(self.users_count_label)
        
        # Refresh users button
        refresh_users_btn = QPushButton("↻")
        refresh_users_btn.setFixedSize(28, 28)
        refresh_users_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_users_btn.setToolTip("Refresh user list")
        refresh_users_btn.setStyleSheet("""
            QPushButton {
                background: rgba(0, 150, 220, 0.2);
                border: 1px solid rgba(0, 180, 255, 0.3);
                border-radius: 14px;
                color: rgba(200, 230, 255, 0.9);
                font-size: 14px;
            }
            QPushButton:hover {
                background: rgba(0, 180, 255, 0.35);
            }
        """)
        refresh_users_btn.clicked.connect(self._load_users)
        header_layout.addWidget(refresh_users_btn)
        
        layout.addLayout(header_layout)
        
        # Scrollable user cards area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
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
                height: 0;
            }
        """)
        
        self.users_scroll_content = QWidget()
        self.users_scroll_content.setStyleSheet("background: transparent;")
        self.users_scroll_layout = QVBoxLayout(self.users_scroll_content)
        self.users_scroll_layout.setContentsMargins(0, 0, 8, 0)
        self.users_scroll_layout.setSpacing(8)
        self.users_scroll_layout.addStretch()
        
        scroll.setWidget(self.users_scroll_content)
        layout.addWidget(scroll, 1)
        
        return container
    
    def _show_users_view(self):
        """Switch to users view and load user data."""
        # Update filter button states
        self.filter_all_btn.setChecked(False)
        self.filter_conv_btn.setChecked(False)
        self.filter_know_btn.setChecked(False)
        self.filter_skill_btn.setChecked(False)
        self.filter_users_btn.setChecked(True)
        
        # Switch stacked view
        self.view_stack.setCurrentIndex(1)
        
        # Update stats
        self.stats_label.setText("Users view")
        
        # Load users
        self._load_users()
    
    def _load_users(self):
        """Load users from AuthManager and populate the cards."""
        # Clear existing cards
        while self.users_scroll_layout.count() > 1:
            item = self.users_scroll_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        users = []
        if self.auth_manager:
            try:
                users = self.auth_manager.list_users()
            except Exception as e:
                logger.error(f"Failed to load users: {e}")
        
        if not users:
            # Show placeholder
            placeholder = QLabel("No registered users found")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            placeholder.setStyleSheet("""
                color: rgba(150, 200, 255, 0.5);
                font-size: 14px;
                padding: 60px 20px;
                background: transparent;
            """)
            self.users_scroll_layout.insertWidget(0, placeholder)
            self.users_count_label.setText("0 users")
            return
        
        current_user = getattr(self.auth_manager, 'current_user', None)
        
        for user in users:
            card = self._create_user_card(user, is_active=(user.get('username') == current_user))
            self.users_scroll_layout.insertWidget(self.users_scroll_layout.count() - 1, card)
        
        self.users_count_label.setText(f"{len(users)} user{'s' if len(users) != 1 else ''}")
        logger.info(f"👤 Loaded {len(users)} users into Users view")
    
    def _create_user_card(self, user: dict, is_active: bool = False) -> QFrame:
        """Create a styled user card widget."""
        card = QFrame()
        card.setFixedHeight(80)
        
        active_border = "rgba(0, 255, 150, 0.5)" if is_active else "rgba(0, 180, 255, 0.2)"
        active_bg = "rgba(0, 255, 150, 0.08)" if is_active else "rgba(0, 20, 50, 0.4)"
        
        card.setStyleSheet(f"""
            QFrame {{
                background: {active_bg};
                border: 1px solid {active_border};
                border-radius: 12px;
                padding: 12px 16px;
            }}
            QFrame:hover {{
                background: rgba(0, 40, 80, 0.5);
                border-color: rgba(0, 220, 255, 0.5);
            }}
        """)
        
        layout = QHBoxLayout(card)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(14)
        
        # Avatar circle
        avatar = QLabel(user.get('username', '?')[0].upper())
        avatar.setFixedSize(44, 44)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar_color = "#00ff96" if is_active else "#00d4ff"
        avatar.setStyleSheet(f"""
            QLabel {{
                background: rgba({self._hex_to_rgba(avatar_color, 0.2)});
                border: 2px solid {avatar_color};
                border-radius: 22px;
                color: {avatar_color};
                font-size: 18px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(avatar)
        
        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(3)
        
        # Username + active badge
        name_layout = QHBoxLayout()
        name_layout.setSpacing(8)
        
        name_label = QLabel(user.get('username', 'Unknown'))
        name_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        name_label.setStyleSheet("color: #e0f0ff; background: transparent; border: none;")
        name_layout.addWidget(name_label)
        
        if is_active:
            badge = QLabel("● ACTIVE")
            badge.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            badge.setStyleSheet("""
                color: #00ff96;
                background: rgba(0, 255, 150, 0.15);
                border: 1px solid rgba(0, 255, 150, 0.3);
                border-radius: 8px;
                padding: 1px 8px;
            """)
            name_layout.addWidget(badge)
        
        name_layout.addStretch()
        info_layout.addLayout(name_layout)
        
        # Timestamps
        created = user.get('created_at', '')
        last_login = user.get('last_login', '')
        
        # Format dates nicely
        created_display = self._format_date(created)
        login_display = self._format_date(last_login) if last_login else "Never"
        
        meta_label = QLabel(f"Created: {created_display}  •  Last login: {login_display}")
        meta_label.setFont(QFont("Segoe UI", 10))
        meta_label.setStyleSheet("color: rgba(150, 200, 255, 0.6); background: transparent; border: none;")
        info_layout.addWidget(meta_label)
        
        layout.addLayout(info_layout, 1)
        
        return card
    
    @staticmethod
    def _format_date(iso_str: str) -> str:
        """Format an ISO date string to a short readable form."""
        if not iso_str:
            return "N/A"
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(iso_str)
            return dt.strftime("%b %d, %Y  %I:%M %p")
        except Exception:
            return iso_str[:16] if len(iso_str) > 16 else iso_str
    
    @staticmethod
    def _hex_to_rgba(hex_color: str, alpha: float) -> str:
        """Convert hex color to rgba values string (without rgba() wrapper)."""
        hex_color = hex_color.lstrip('#')
        if len(hex_color) == 6:
            r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
            return f"{r}, {g}, {b}, {alpha}"
        return f"0, 212, 255, {alpha}"
    
    def _close_panel(self):
        """Close the panel."""
        self.detail_card.hide()
        self.closed.emit()
        self.hide()
    
    # ========================================================================
    # Mouse Events (for dragging)
    # ========================================================================
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            # Only start drag if click is NOT on the neural brain widget
            click_pos = event.position().toPoint()
            brain_rect = self.neural_brain.geometry()
            if not brain_rect.contains(click_pos):
                self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            else:
                self._drag_pos = None
            event.accept()
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()


# ============================================================================
# Demo/Test
# ============================================================================
if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    
    panel = NeuralMemoryPanel()
    panel.show()
    
    sys.exit(app.exec())
