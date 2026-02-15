"""
Live2D Pet Widget - OpenGL-based animated character display
Renders Live2D Cubism models with real-time animation playback using live2d-py.
"""

import logging
from pathlib import Path
from typing import Optional, List
from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtWidgets import QMenu
from PySide6.QtCore import Qt, QPoint, QTimer, Signal
from PySide6.QtGui import QCursor, QAction, QImage, QContextMenuEvent
from OpenGL.GL import *
from OpenGL.GLU import *
import time

from core.live2d_engine import (
    Live2DModel, PetExpression, init_live2d, 
    gl_init_live2d, cleanup_live2d, clear_buffer
)
from ui.pet_config import PetConfig, PetSize
from ui.pet_radial_menu import PetRadialMenu

logger = logging.getLogger(__name__)


class Live2DPetWidget(QOpenGLWidget):
    """
    Desktop pet widget with Live2D character animation.
    Features:
    - OpenGL rendering of Live2D models using live2d-py
    - Transparent, frameless, always-on-top window
    - Draggable anywhere on screen
    - Automatic motion playback based on Nexa state
    - Snaps to screen edges
    """
    
    # Signal emitted when pet is closed
    closed = Signal()
    
    # State to PetExpression mapping (using custom Nexa expressions)
    STATE_EXPRESSIONS = {
        'idle': PetExpression.IDLE,
        'listening': PetExpression.LISTENING,
        'thinking': PetExpression.THINKING,
        'speaking': PetExpression.SPEAKING,
        'executing': PetExpression.THINKING,
        'content_mode': PetExpression.THINKING,
        'error': PetExpression.ERROR,  # Now uses dedicated error expression
        'recognizing': PetExpression.LISTENING,
        'happy': PetExpression.HAPPY,
        'sleeping': PetExpression.SLEEPING,
    }
    
    def __init__(self, config_dir: Path, model_path: Optional[Path] = None, parent=None):
        """
        Initialize Live2D pet widget.
        
        Args:
            config_dir: Directory for pet_preferences.json
            model_path: Path to .model3.json file (optional, can be set later)
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        
        self.config = PetConfig(config_dir)
        self.model_path = Path(model_path) if model_path else None
        
        # Live2D model (live2d-py)
        self.model: Optional[Live2DModel] = None
        self._gl_initialized = False
        self._model_ready = False
        
        # Dragging state
        self.dragging = False
        self.drag_start_pos = QPoint()
        
        # Current state
        self.current_state = 'idle'
        
        # Radial menu (P5 feature)
        self.radial_menu: Optional[PetRadialMenu] = None
        self.quick_actions = None  # Set by NexaModernWindow
        
        # Animation timing
        self.last_update_time = time.time()
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self._on_update_timer)
        
        # Initialize Live2D system (non-GL part)
        init_live2d()
        
        # Setup window
        self._setup_window()
        
        # Start update loop
        self.update_timer.start(16)  # ~60 FPS
        
        logger.info("✅ Live2D Pet Widget initialized")
    
    def _setup_window(self):
        """Configure window properties."""
        # Frameless window that stays on top
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        
        # Transparent background
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        
        # Set window title (for debugging)
        self.setWindowTitle("Nexa Companion (Live2D)")
        
        # Get size from config
        width, height = self.config.get_size_dimensions()
        self.resize(width, height)
        
        # Center on screen initially
        self._center_on_screen()
        
        logger.info(f"🐾 Live2D Pet window configured: {width}x{height}")
    
    def _center_on_screen(self):
        """Center widget on screen."""
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        logger.info(f"🐾 Pet centered at: ({x}, {y})")
    
    def set_model(self, model_path: Path):
        """
        Load a Live2D model.
        
        Args:
            model_path: Path to .model3.json file
        """
        self.model_path = Path(model_path)
        
        if self._gl_initialized:
            self._load_model()
        # Otherwise, model will be loaded in initializeGL
    
    def _load_model(self):
        """Load the Live2D model (must be called after OpenGL init)."""
        if not self.model_path or not self._gl_initialized:
            return
        
        logger.info(f"🔄 Loading Live2D model: {self.model_path}")
        
        try:
            # Create and load model
            self.model = Live2DModel(str(self.model_path))
            if self.model.load():
                # Resize to widget dimensions
                self.model.resize(self.width(), self.height())
                
                # Start idle motion
                if 'Idle' in self.model.motion_groups:
                    self.model.start_random_motion('Idle', 1)
                
                self._model_ready = True
                logger.info(f"✅ Live2D model loaded: {self.model.name}")
            else:
                logger.error(f"❌ Failed to load Live2D model")
                self.model = None
        except Exception as e:
            logger.error(f"❌ Error loading Live2D model: {e}")
            import traceback
            traceback.print_exc()
            self.model = None
    
    def set_state(self, state: str):
        """
        Change pet state and play corresponding motion.
        
        Args:
            state: Nexa state name (idle, listening, thinking, etc.)
        """
        state_lower = state.lower()
        
        if state_lower == self.current_state:
            return  # No change
        
        logger.info(f"🐾 Pet state changing: {self.current_state} → {state_lower}")
        self.current_state = state_lower
        
        # Map state to expression
        expression = self.STATE_EXPRESSIONS.get(state_lower, PetExpression.IDLE)
        
        # Set expression if model is loaded
        if self.model and self._model_ready:
            self.model.set_pet_expression(expression)
            logger.info(f"🐾 Pet expression set: {state_lower} → {expression.value}")
        else:
            logger.warning(f"🐾 State changed to {state_lower} but model not ready")
    
    def _on_update_timer(self):
        """Update timer callback - update model and redraw."""
        # Trigger OpenGL redraw (which will call update() and draw())
        self.update()
    
    # ===== OpenGL Methods =====
    
    def initializeGL(self):
        """Initialize OpenGL context."""
        # Set up OpenGL state
        glClearColor(0.0, 0.0, 0.0, 0.0)  # Transparent background
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        
        # Initialize Live2D OpenGL resources
        gl_init_live2d()
        self._gl_initialized = True
        
        logger.info("✅ OpenGL initialized for Live2D rendering")
        
        # Now load the model if path was provided
        if self.model_path:
            self._load_model()
    
    def resizeGL(self, w: int, h: int):
        """Handle OpenGL viewport resize."""
        glViewport(0, 0, w, h)
        
        # Resize Live2D model
        if self.model and self._model_ready:
            self.model.resize(w, h)
        
        logger.debug(f"🔄 Viewport resized: {w}x{h}")
    
    def paintGL(self):
        """Render Live2D model."""
        # Clear with transparent background
        clear_buffer()
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        
        if self.model and self._model_ready:
            # Update model (physics, motion, lip sync, etc.)
            self.model.update()
            
            # Draw model
            self.model.draw()
        else:
            # Placeholder: Draw a simple colored quad
            self._draw_placeholder()
    
    def _draw_placeholder(self):
        """Draw placeholder until Live2D model is loaded."""
        glBegin(GL_QUADS)
        glColor4f(0.5, 0.3, 0.8, 0.5)  # Purple semi-transparent
        glVertex2f(-0.5, -0.5)
        glVertex2f(0.5, -0.5)
        glVertex2f(0.5, 0.5)
        glVertex2f(-0.5, 0.5)
        glEnd()
    
    # ===== Mouse Events =====
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging."""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
        elif event.button() == Qt.RightButton:
            # P5: Show radial menu instead of old context menu
            self._show_radial_menu(event.globalPosition().toPoint())
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click for reaction."""
        if event.button() == Qt.LeftButton:
            # Trigger happy motion
            self.set_state('happy')
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if self.dragging and event.buttons() == Qt.LeftButton:
            new_pos = event.globalPosition().toPoint() - self.drag_start_pos
            self.move(new_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.LeftButton:
            self.dragging = False
            self.setCursor(QCursor(Qt.OpenHandCursor))
            event.accept()
    
    def _show_context_menu(self, pos: QPoint):
        """Show right-click context menu."""
        menu = QMenu(self)
        
        # Size submenu
        size_menu = menu.addMenu("Size")
        
        small_action = QAction("Small", self)
        small_action.triggered.connect(lambda: self._change_size(PetSize.SMALL))
        size_menu.addAction(small_action)
        
        medium_action = QAction("Medium", self)
        medium_action.triggered.connect(lambda: self._change_size(PetSize.MEDIUM))
        size_menu.addAction(medium_action)
        
        large_action = QAction("Large", self)
        large_action.triggered.connect(lambda: self._change_size(PetSize.LARGE))
        size_menu.addAction(large_action)
        
        menu.addSeparator()
        
        # Hide companion action
        hide_action = QAction("Hide Companion", self)
        hide_action.triggered.connect(self.hide_pet)
        menu.addAction(hide_action)
        
        menu.exec(pos)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Radial Menu (P5 Feature)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _init_radial_menu(self):
        """Initialize the radial menu widget."""
        self.radial_menu = PetRadialMenu(parent=self)
        
        # Connect menu items if quick_actions is set
        if self.quick_actions:
            self.radial_menu.set_items(self.quick_actions.get_menu_items())
        
        logger.info("🎯 Radial menu initialized (Live2D)")
    
    def set_quick_actions(self, quick_actions):
        """
        Set the quick actions handler for the radial menu.
        
        Args:
            quick_actions: PetQuickActions instance
        """
        self.quick_actions = quick_actions
        
        # Update radial menu if already created
        if self.radial_menu and quick_actions:
            self.radial_menu.set_items(quick_actions.get_menu_items())
    
    def contextMenuEvent(self, event: QContextMenuEvent):
        """
        Show radial menu on right-click.
        
        P5 feature: Quick Actions radial menu.
        """
        # Initialize radial menu if needed
        if not self.radial_menu:
            self._init_radial_menu()
        
        # Show menu at click position
        self.radial_menu.show_at(event.globalPos())
        event.accept()
        
        logger.debug("🎯 Radial menu opened via right-click (Live2D)")
    
    def _show_radial_menu(self, pos: QPoint):
        """
        Show radial menu at the given position.
        
        Called from mousePressEvent on right-click.
        """
        # Initialize radial menu if needed
        if not self.radial_menu:
            self._init_radial_menu()
        
        # Show menu at click position
        self.radial_menu.show_at(pos)
        logger.info("🎯 Radial menu opened via right-click (Live2D)")
    
    def _change_size(self, size: PetSize):
        """Change pet size."""
        self.config.set_size(size)
        width, height = self.config.get_size_dimensions()
        self.resize(width, height)
        logger.info(f"Pet size changed to {size.value}: {width}x{height}")
    
    def hide_pet(self):
        """Hide pet and disable in config."""
        self.config.set('enabled', False)
        self.hide()
        self.closed.emit()
        logger.info("Pet hidden by user")
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Stop update timer
        self.update_timer.stop()
        
        # Save position
        pos = self.pos()
        self.config.set_position(pos.x(), pos.y())
        
        # Disable pet
        self.config.set('enabled', False)
        
        # Cleanup Live2D
        cleanup_live2d()
        
        # Emit signal
        self.closed.emit()
        
        event.accept()
        logger.info("Live2D Pet widget closed")
