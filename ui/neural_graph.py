"""
Neural Graph Visualization for NEXA Memory Panel

A living neural brain visualization where memories exist as nodes
in an interconnected, breathing network with 3D parallax effects.

Features:
- Force-directed graph layout for organic node positioning
- 3D parallax effect on mouse movement
- Animated synapse connections with energy flow
- Hover/select wave propagation
- LanceDB integration for auto-relationship detection
"""

import math
import random
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtCore import (
    Qt, QTimer, QPointF, Signal, QRectF, Property, QPropertyAnimation,
    QEasingCurve, QObject
)
from PySide6.QtGui import (
    QPainter, QPen, QBrush, QColor, QRadialGradient, QLinearGradient,
    QPainterPath, QFont, QMouseEvent
)

import logging

logger = logging.getLogger(__name__)


# ============================================================================
# Color Palette - Deep Space Neural Theme
# ============================================================================
NEURAL_COLORS = {
    'void_black': '#050510',
    'deep_indigo': '#0a0a2e',
    'electric_blue': '#00d4ff',
    'synapse_violet': '#8b5cf6',
    'soft_violet': '#a78bfa',
    'node_core': '#ffffff',
    'connection_glow': 'rgba(0, 212, 255, 0.3)',
    'hover_pulse': '#ff00ff',
    'select_highlight': '#00ff88',
    'dim_node': 'rgba(100, 100, 150, 0.3)',
}


# ============================================================================
# Data Classes
# ============================================================================
@dataclass
class NeuralNode:
    """Represents a single memory as a neural node."""
    
    id: str
    memory_data: Dict[str, Any]
    memory_type: str  # 'conversation', 'knowledge', 'skill'
    
    # Position in 2D space (will be animated)
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0  # Depth for 3D parallax
    
    # Velocity for physics simulation
    vx: float = 0.0
    vy: float = 0.0
    
    # Visual properties
    base_radius: float = 12.0
    importance: float = 0.5  # 0-1, affects size
    freshness: float = 1.0   # 0-1, affects brightness (time decay)
    
    # State
    is_hovered: bool = False
    is_selected: bool = False
    hover_intensity: float = 0.0  # 0-1, for smooth transitions
    select_intensity: float = 0.0
    pulse_phase: float = 0.0
    
    # Connections
    connected_ids: List[str] = field(default_factory=list)
    
    @property
    def radius(self) -> float:
        """Calculate current radius based on importance and state."""
        base = self.base_radius * (0.8 + self.importance * 0.4)
        if self.is_selected:
            base *= 1.5
        elif self.is_hovered:
            base *= 1.2
        return base
    
    @property
    def color(self) -> QColor:
        """Get node color based on type and state."""
        type_colors = {
            'conversation': QColor(0, 212, 255),    # Cyan
            'knowledge': QColor(139, 92, 246),       # Violet
            'skill': QColor(0, 255, 136),            # Green
        }
        base_color = type_colors.get(self.memory_type, QColor(0, 212, 255))
        
        # Adjust brightness based on freshness
        h, s, l, a = base_color.getHslF()
        l = 0.3 + (l * self.freshness * 0.7)  # Dim old memories
        
        return QColor.fromHslF(h, s, min(1.0, l), a)
    
    def get_display_position(self, mouse_offset: QPointF, parallax_strength: float = 0.05) -> QPointF:
        """Get position with 3D parallax applied based on mouse position."""
        # Nodes at different z-depths move differently with mouse
        parallax_x = mouse_offset.x() * self.z * parallax_strength
        parallax_y = mouse_offset.y() * self.z * parallax_strength
        return QPointF(self.x + parallax_x, self.y + parallax_y)


@dataclass  
class NeuralConnection:
    """Represents a synapse connection between two nodes."""
    
    source_id: str
    target_id: str
    strength: float = 0.5  # 0-1, affects line thickness
    
    # Animation
    energy_flow: float = 0.0  # 0-1, animated particle position along path
    flow_speed: float = 0.02
    is_active: bool = False  # True when part of selected path
    
    def update(self):
        """Update energy flow animation."""
        self.energy_flow = (self.energy_flow + self.flow_speed) % 1.0


# ============================================================================
# Neural Brain Widget - Main Visualization
# ============================================================================
class NeuralBrainWidget(QWidget):
    """
    The central neural network visualization widget.
    
    Features:
    - Force-directed layout for organic positioning
    - 3D parallax on mouse movement
    - Smooth hover/select animations
    - Wave propagation through connections
    """
    
    # Signals
    node_selected = Signal(str)  # Emits memory ID when node selected
    node_hovered = Signal(str)   # Emits memory ID when node hovered
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Node and connection storage
        self.nodes: Dict[str, NeuralNode] = {}
        self.connections: List[NeuralConnection] = []
        
        # Mouse tracking for parallax
        self.setMouseTracking(True)
        self.mouse_pos = QPointF(0, 0)
        self.center_offset = QPointF(0, 0)  # Offset from center for parallax
        
        # Animation state
        self.global_pulse = 0.0
        self.rotation_angle = 0.0
        self.selected_node_id: Optional[str] = None
        self.hovered_node_id: Optional[str] = None
        
        # Physics settings (tuned for calm, organic movement)
        self.repulsion_strength = 150.0  # Reduced from 500 for gentler repulsion
        self.attraction_strength = 0.005  # Reduced for softer attraction
        self.damping = 0.85  # More damping = faster settling
        self.center_gravity = 0.003  # Gentle pull to center
        self.max_velocity = 3.0  # Cap maximum speed
        
        # Animation timer (60 FPS target)
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animation)
        self.animation_timer.start(16)  # ~60 FPS
        
        # Slower physics timer
        self.physics_timer = QTimer(self)
        self.physics_timer.timeout.connect(self._update_physics)
        self.physics_timer.start(33)  # ~30 FPS
        
        # Styling
        self.setMinimumSize(400, 400)
        self.setAttribute(Qt.WA_OpaquePaintEvent, False)
        
        logger.info("🧠 NeuralBrainWidget initialized")
    
    # ========================================================================
    # Data Management
    # ========================================================================
    
    def set_memories(self, memories: List[Dict[str, Any]]):
        """
        Load memories as neural nodes.
        
        Args:
            memories: List of memory dicts with 'id', 'memory_type', 'content', etc.
        """
        self.nodes.clear()
        self.connections.clear()
        
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        for i, mem in enumerate(memories):
            # Calculate initial position in a spiral pattern
            angle = i * 0.5
            radius = 50 + i * 15
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            z = random.uniform(-1, 1)  # Random depth for parallax
            
            # Calculate importance from memory data
            importance = mem.get('importance', 0.5)
            
            # Calculate freshness (time decay)
            # TODO: Calculate from timestamp
            freshness = 1.0 - (i / max(len(memories), 1)) * 0.5
            
            node = NeuralNode(
                id=mem.get('id', str(i)),
                memory_data=mem,
                memory_type=mem.get('memory_type', 'conversation'),
                x=x, y=y, z=z,
                importance=importance,
                freshness=freshness,
                pulse_phase=random.uniform(0, 2 * math.pi)
            )
            
            self.nodes[node.id] = node
        
        # Auto-detect relationships (will be async with LanceDB)
        self._create_connections()
        
        logger.info(f"🧠 Loaded {len(self.nodes)} memory nodes")
        self.update()
    
    def _create_connections(self):
        """
        Create connections between related nodes using content similarity.
        
        Connections are based on:
        - Same memory type -> base connection strength
        - Word overlap in content -> stronger connections
        - Each node connects to its top-N most similar neighbors
        """
        self.connections.clear()
        node_ids = list(self.nodes.keys())
        
        if len(node_ids) < 2:
            return
        
        # Build word sets for each node for similarity scoring
        node_words: Dict[str, set] = {}
        for nid, node in self.nodes.items():
            content = node.memory_data.get('content', '')
            if not content:
                content = (node.memory_data.get('user_message') or
                           node.memory_data.get('fact') or
                           node.memory_data.get('action') or '')
            # Tokenize: lowercase words, skip very short ones
            words = {w.lower() for w in str(content).split() if len(w) > 2}
            node_words[nid] = words
        
        # Score all pairs and keep top connections per node
        max_connections_per_node = min(4, len(node_ids) - 1)
        
        for node_id in node_ids:
            node = self.nodes[node_id]
            scores: List[Tuple[str, float]] = []
            
            for other_id in node_ids:
                if other_id == node_id:
                    continue
                other = self.nodes[other_id]
                
                # Base score from type match
                score = 0.3 if node.memory_type == other.memory_type else 0.1
                
                # Word overlap similarity (Jaccard-like)
                words_a = node_words.get(node_id, set())
                words_b = node_words.get(other_id, set())
                if words_a and words_b:
                    intersection = len(words_a & words_b)
                    union = len(words_a | words_b)
                    if union > 0:
                        score += 0.7 * (intersection / union)
                
                scores.append((other_id, score))
            
            # Sort by score descending, take top N
            scores.sort(key=lambda x: x[1], reverse=True)
            top_targets = scores[:max_connections_per_node]
            
            for target_id, strength in top_targets:
                # Skip very weak connections
                if strength < 0.15:
                    continue
                
                # Avoid duplicate connections
                existing = any(
                    (c.source_id == node_id and c.target_id == target_id) or
                    (c.source_id == target_id and c.target_id == node_id)
                    for c in self.connections
                )
                if not existing:
                    conn = NeuralConnection(
                        source_id=node_id,
                        target_id=target_id,
                        strength=min(1.0, strength)
                    )
                    self.connections.append(conn)
                    
                    # Update node connection lists
                    self.nodes[node_id].connected_ids.append(target_id)
                    self.nodes[target_id].connected_ids.append(node_id)
        
        logger.debug(f"Created {len(self.connections)} similarity-based connections")
    
    # ========================================================================
    # Physics Simulation
    # ========================================================================
    
    def _update_physics(self):
        """Update force-directed layout physics."""
        if len(self.nodes) < 2:
            return
        
        nodes = list(self.nodes.values())
        center_x = self.width() / 2
        center_y = self.height() / 2
        
        # Calculate forces
        for node in nodes:
            fx, fy = 0.0, 0.0
            
            # Repulsion from other nodes
            for other in nodes:
                if other.id == node.id:
                    continue
                
                dx = node.x - other.x
                dy = node.y - other.y
                dist_sq = dx * dx + dy * dy
                
                # Guard against zero distance (nodes at same position)
                if dist_sq < 0.01:
                    # Add small random offset to separate overlapping nodes
                    import random
                    dx = random.uniform(-5, 5)
                    dy = random.uniform(-5, 5)
                    dist_sq = dx * dx + dy * dy + 0.01
                
                dist = math.sqrt(dist_sq) + 0.1
                
                # Repulsion force (inverse square)
                force = self.repulsion_strength / dist_sq
                fx += (dx / dist) * force
                fy += (dy / dist) * force
            
            # Attraction along connections
            for conn_id in node.connected_ids:
                if conn_id in self.nodes:
                    other = self.nodes[conn_id]
                    dx = other.x - node.x
                    dy = other.y - node.y
                    dist = math.sqrt(dx * dx + dy * dy) + 0.1
                    
                    # Spring force
                    force = dist * self.attraction_strength
                    fx += (dx / dist) * force
                    fy += (dy / dist) * force
            
            # Center gravity
            dx = center_x - node.x
            dy = center_y - node.y
            fx += dx * self.center_gravity
            fy += dy * self.center_gravity
            
            # Update velocity with damping
            node.vx = (node.vx + fx) * self.damping
            node.vy = (node.vy + fy) * self.damping
            
            # Clamp velocity to prevent too-fast movement
            speed = math.sqrt(node.vx * node.vx + node.vy * node.vy)
            if speed > self.max_velocity:
                scale = self.max_velocity / speed
                node.vx *= scale
                node.vy *= scale
        
        # Update positions
        for node in nodes:
            node.x += node.vx
            node.y += node.vy
            
            # Keep within bounds
            margin = 50
            node.x = max(margin, min(self.width() - margin, node.x))
            node.y = max(margin, min(self.height() - margin, node.y))
    
    # ========================================================================
    # Animation
    # ========================================================================
    
    def _update_animation(self):
        """Update all animations each frame."""
        # Global pulse
        self.global_pulse = (self.global_pulse + 0.03) % (2 * math.pi)
        
        # Slow rotation
        self.rotation_angle += 0.001
        
        # Update node animations
        for node in self.nodes.values():
            # Individual pulse
            node.pulse_phase += 0.05
            
            # Smooth hover/select transitions
            target_hover = 1.0 if node.is_hovered else 0.0
            target_select = 1.0 if node.is_selected else 0.0
            
            node.hover_intensity += (target_hover - node.hover_intensity) * 0.2
            node.select_intensity += (target_select - node.select_intensity) * 0.15
        
        # Update connection animations
        for conn in self.connections:
            conn.update()
        
        # Trigger repaint
        self.update()
    
    # ========================================================================
    # Mouse Interaction
    # ========================================================================
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Track mouse for parallax and hover detection."""
        self.mouse_pos = event.position()
        
        # Calculate offset from center for parallax
        center_x = self.width() / 2
        center_y = self.height() / 2
        self.center_offset = QPointF(
            self.mouse_pos.x() - center_x,
            self.mouse_pos.y() - center_y
        )
        
        # Check for node hover
        hovered_id = self._get_node_at_position(self.mouse_pos)
        
        if hovered_id != self.hovered_node_id:
            # Update hover states
            if self.hovered_node_id and self.hovered_node_id in self.nodes:
                self.nodes[self.hovered_node_id].is_hovered = False
            
            self.hovered_node_id = hovered_id
            
            if hovered_id and hovered_id in self.nodes:
                self.nodes[hovered_id].is_hovered = True
                self.node_hovered.emit(hovered_id)
                self.setCursor(Qt.PointingHandCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        
        super().mouseMoveEvent(event)
    
    def mousePressEvent(self, event: QMouseEvent):
        """Handle node selection."""
        if event.button() == Qt.LeftButton:
            clicked_id = self._get_node_at_position(event.position())
            
            # Deselect previous
            if self.selected_node_id and self.selected_node_id in self.nodes:
                self.nodes[self.selected_node_id].is_selected = False
            
            self.selected_node_id = clicked_id
            
            if clicked_id and clicked_id in self.nodes:
                self.nodes[clicked_id].is_selected = True
                self.node_selected.emit(clicked_id)
                
                # Activate connections to this node
                self._activate_path_to_node(clicked_id)
        
        super().mousePressEvent(event)
    
    def _get_node_at_position(self, pos: QPointF) -> Optional[str]:
        """Find which node (if any) is at the given position."""
        for node in self.nodes.values():
            display_pos = node.get_display_position(self.center_offset)
            dx = pos.x() - display_pos.x()
            dy = pos.y() - display_pos.y()
            dist = math.sqrt(dx * dx + dy * dy)
            
            if dist <= node.radius * 1.5:  # Generous hit area
                return node.id
        return None
    
    def _activate_path_to_node(self, node_id: str):
        """Activate connections leading to the selected node."""
        # Reset all connections
        for conn in self.connections:
            conn.is_active = False
        
        # Activate connections to/from selected node
        if node_id:
            for conn in self.connections:
                if conn.source_id == node_id or conn.target_id == node_id:
                    conn.is_active = True
    
    # ========================================================================
    # Painting
    # ========================================================================
    
    def paintEvent(self, event):
        """Render the neural network visualization."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Background gradient
        self._draw_background(painter)
        
        # Draw connections first (behind nodes)
        self._draw_connections(painter)
        
        # Draw nodes
        self._draw_nodes(painter)
        
        painter.end()
    
    def _draw_background(self, painter: QPainter):
        """Draw deep space background with subtle gradient."""
        rect = self.rect()
        
        # Radial gradient from center
        gradient = QRadialGradient(rect.center(), max(rect.width(), rect.height()) / 2)
        gradient.setColorAt(0, QColor(15, 15, 45))
        gradient.setColorAt(0.5, QColor(10, 10, 30))
        gradient.setColorAt(1, QColor(5, 5, 16))
        
        painter.fillRect(rect, gradient)
    
    def _draw_connections(self, painter: QPainter):
        """Draw synapse connections with energy flow."""
        for conn in self.connections:
            if conn.source_id not in self.nodes or conn.target_id not in self.nodes:
                continue
            
            source = self.nodes[conn.source_id]
            target = self.nodes[conn.target_id]
            
            # Get positions with parallax
            p1 = source.get_display_position(self.center_offset)
            p2 = target.get_display_position(self.center_offset)
            
            # Calculate opacity based on selection state
            if self.selected_node_id:
                if conn.is_active:
                    opacity = 0.8
                else:
                    opacity = 0.1
            else:
                opacity = 0.3 + conn.strength * 0.3
            
            # Base line
            pen_width = 1 + conn.strength * 2
            color = QColor(0, 212, 255, int(opacity * 255))
            painter.setPen(QPen(color, pen_width))
            painter.drawLine(p1, p2)
            
            # Energy particle along the connection
            if conn.is_active or random.random() < 0.1:
                particle_pos = QPointF(
                    p1.x() + (p2.x() - p1.x()) * conn.energy_flow,
                    p1.y() + (p2.y() - p1.y()) * conn.energy_flow
                )
                
                particle_gradient = QRadialGradient(particle_pos, 6)
                particle_gradient.setColorAt(0, QColor(255, 255, 255, 200))
                particle_gradient.setColorAt(0.5, QColor(0, 212, 255, 150))
                particle_gradient.setColorAt(1, QColor(0, 212, 255, 0))
                
                painter.setBrush(particle_gradient)
                painter.setPen(Qt.NoPen)
                painter.drawEllipse(particle_pos, 4, 4)
    
    def _draw_nodes(self, painter: QPainter):
        """Draw neural nodes with glow effects."""
        # Sort by z-depth for proper layering
        sorted_nodes = sorted(self.nodes.values(), key=lambda n: n.z)
        
        for node in sorted_nodes:
            pos = node.get_display_position(self.center_offset)
            radius = node.radius
            pulse = math.sin(node.pulse_phase) * 0.1 + 1.0
            
            # Calculate opacity for dimming unrelated nodes
            if self.selected_node_id:
                if node.is_selected:
                    opacity = 1.0
                elif node.id in (self.nodes[self.selected_node_id].connected_ids 
                                if self.selected_node_id in self.nodes else []):
                    opacity = 0.8
                else:
                    opacity = 0.2
            else:
                opacity = 0.7 + node.freshness * 0.3
            
            # Outer glow
            glow_radius = radius * 2.5 * pulse
            glow_gradient = QRadialGradient(pos, glow_radius)
            
            glow_color = node.color
            glow_color.setAlphaF(0.3 * opacity * (1 + node.hover_intensity * 0.5))
            glow_gradient.setColorAt(0, glow_color)
            glow_gradient.setColorAt(1, QColor(0, 0, 0, 0))
            
            painter.setBrush(glow_gradient)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(pos, glow_radius, glow_radius)
            
            # Main node
            node_gradient = QRadialGradient(pos, radius)
            
            core_color = node.color
            core_color.setAlphaF(opacity)
            
            # Brighter center
            center_color = QColor(255, 255, 255, int(200 * opacity))
            node_gradient.setColorAt(0, center_color)
            node_gradient.setColorAt(0.3, core_color)
            node_gradient.setColorAt(1, core_color.darker(150))
            
            painter.setBrush(node_gradient)
            
            # Border on hover/select
            if node.is_hovered or node.is_selected:
                border_color = QColor(255, 255, 255, int(200 * node.hover_intensity))
                painter.setPen(QPen(border_color, 2))
            else:
                painter.setPen(Qt.NoPen)
            
            painter.drawEllipse(pos, radius * pulse, radius * pulse)
    
    # ========================================================================
    # Utility
    # ========================================================================
    
    def get_selected_memory(self) -> Optional[Dict[str, Any]]:
        """Get the currently selected memory data."""
        if self.selected_node_id and self.selected_node_id in self.nodes:
            return self.nodes[self.selected_node_id].memory_data
        return None
    
    def clear_selection(self):
        """Clear the current selection."""
        if self.selected_node_id and self.selected_node_id in self.nodes:
            self.nodes[self.selected_node_id].is_selected = False
        self.selected_node_id = None
        
        for conn in self.connections:
            conn.is_active = False


# ============================================================================
# Demo/Test
# ============================================================================
if __name__ == "__main__":
    import sys
    
    app = QApplication(sys.argv)
    
    widget = NeuralBrainWidget()
    widget.resize(800, 600)
    widget.setWindowTitle("NEXA Neural Memory - Demo")
    
    # Load demo memories
    demo_memories = [
        {"id": "1", "memory_type": "conversation", "content": "Hello Nexa", "importance": 0.8},
        {"id": "2", "memory_type": "knowledge", "content": "User likes dark theme", "importance": 0.9},
        {"id": "3", "memory_type": "skill", "content": "set_volume", "importance": 0.6},
        {"id": "4", "memory_type": "conversation", "content": "What's the weather?", "importance": 0.5},
        {"id": "5", "memory_type": "knowledge", "content": "User lives in Lahore", "importance": 0.7},
        {"id": "6", "memory_type": "conversation", "content": "Play some music", "importance": 0.4},
        {"id": "7", "memory_type": "skill", "content": "open_browser", "importance": 0.5},
        {"id": "8", "memory_type": "knowledge", "content": "User is a developer", "importance": 0.8},
    ]
    
    widget.set_memories(demo_memories)
    
    # Connect signals for testing
    widget.node_selected.connect(lambda id: print(f"Selected: {id}"))
    widget.node_hovered.connect(lambda id: print(f"Hovered: {id}"))
    
    widget.show()
    sys.exit(app.exec())
