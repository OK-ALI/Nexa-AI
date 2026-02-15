"""
Nexa Pet Widget - Desktop Companion
Animated AI pet character that displays Nexa's current state.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, List
from PySide6.QtWidgets import QWidget, QLabel, QMenu
from PySide6.QtCore import Qt, QPoint, QSize, Signal, QTimer, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QCursor, QAction, QPainter, QFont
from .pet_config import PetConfig, PetSize

logger = logging.getLogger(__name__)


class NexaPetWidget(QWidget):
    """
    Desktop pet widget for Nexa AI.
    Features:
    - Transparent, frameless, always-on-top window
    - Draggable anywhere on screen
    - Displays different images based on Nexa state
    - Snaps to screen edges (magnetic docking)
    - Saves position between sessions
    """
    
    # Signal emitted when pet is closed
    closed = Signal()
    
    # State to image filename mapping
    STATE_IMAGES = {
        'idle': 'idle.png',
        'listening': 'listening.png',
        'thinking': 'thinking.png',
        'speaking': 'speaking.png',
        'executing': 'thinking.png',  # Reuse thinking for executing
        'content_mode': 'thinking.png',  # Reuse thinking for content mode
        'error': 'error.png',
        'recognizing': 'listening.png',  # Reuse listening for recognizing
    }
    
    def __init__(self, config_dir: Path, assets_dir: Path, parent=None):
        """
        Initialize pet widget.
        
        Args:
            config_dir: Directory for pet_preferences.json
            assets_dir: Directory containing pet images (assets/pet/)
            parent: Parent widget (optional)
        """
        super().__init__(parent)
        
        self.config = PetConfig(config_dir)
        self.assets_dir = Path(assets_dir)
        
        # Dragging state
        self.dragging = False
        self.drag_start_pos = QPoint()
        
        # Current state
        self.current_state = 'idle'
        
        # Image cache
        self.images: Dict[str, QPixmap] = {}
        
        # Animation system
        self.fade_animation: Optional[QPropertyAnimation] = None
        self.is_transitioning = False
        self.pending_state: Optional[str] = None
        
        # Idle breathing animation
        self.breathing_animation: Optional[QPropertyAnimation] = None
        
        # Particle effects
        self.particles: List[QLabel] = []
        self.particle_timer: Optional[QTimer] = None
        
        # Reaction animations
        self.bounce_animation: Optional[QPropertyAnimation] = None
        
        # Setup window
        self._setup_window()
        
        # Load images
        self._load_images()
        
        # Setup UI
        self._setup_ui()
        
        # Restore position
        self._restore_position()
        
        logger.info("✅ Nexa Pet Widget initialized")
    
    def _setup_window(self):
        """Configure window properties."""
        # Frameless window that stays on top
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool  # Prevents taskbar entry
        )
        
        # Transparent background - enabled now that we know widget shows
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        
        # Remove background color - let transparency work
        self.setStyleSheet("background: transparent;")
        
        # Set window title (for debugging)
        self.setWindowTitle("Nexa Pet")
        
        # Get size from config
        width, height = self.config.get_size_dimensions()
        self.resize(width, height)
        
        logger.info(f"🐾 Pet window configured: {width}x{height}")
    
    def _setup_ui(self):
        """Setup UI elements."""
        # Image label (takes full widget size)
        self.image_label = QLabel(self)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setScaledContents(False)  # We'll scale manually with aspect ratio
        self.image_label.resize(self.size())
        self.image_label.setStyleSheet("background: transparent;")  # Transparent label
        
        # Set initial image
        self.set_state('idle')
        
        # Start idle breathing animation
        QTimer.singleShot(500, self._start_breathing)  # Start after initial setup
        
        # Enable mouse tracking for dragging
        self.setMouseTracking(True)
        self.image_label.setMouseTracking(True)
        
        # Force widget to show
        self.raise_()
        self.activateWindow()
        
        logger.info(f"🐾 Image label created: {self.image_label.width()}x{self.image_label.height()}")
    
    def _load_images(self):
        """Load all state images into cache."""
        logger.info(f"Loading pet images from {self.assets_dir}")
        
        # Check if directory exists
        if not self.assets_dir.exists():
            logger.error(f"❌ Pet assets directory not found: {self.assets_dir}")
            return
        
        for state, filename in self.STATE_IMAGES.items():
            image_path = self.assets_dir / filename
            
            if image_path.exists():
                # Load image and ensure proper alpha channel handling
                image = QPixmap(str(image_path))
                if not image.isNull():
                    # Convert to ARGB32 format for proper transparency
                    pixmap = QPixmap(image.size())
                    pixmap.fill(Qt.transparent)
                    from PySide6.QtGui import QPainter
                    painter = QPainter(pixmap)
                    painter.setCompositionMode(QPainter.CompositionMode_Source)
                    painter.drawPixmap(0, 0, image)
                    painter.end()
                    
                    self.images[state] = pixmap
                    logger.info(f"✅ Loaded {state}: {filename} ({pixmap.width()}x{pixmap.height()})")
                else:
                    logger.error(f"❌ Failed to load {filename} (null pixmap)")
            else:
                logger.error(f"❌ Image not found: {image_path}")
        
        if len(self.images) == 0:
            logger.error("❌ NO IMAGES LOADED! Pet will be invisible!")
        else:
            logger.info(f"✅ Loaded {len(self.images)}/{len(self.STATE_IMAGES)} pet images")
    
    def _restore_position(self):
        """Restore saved position or auto-center."""
        # TESTING: Always center on screen for visibility
        screen = self.screen().availableGeometry()
        x = (screen.width() - self.width()) // 2  # Center horizontally
        y = (screen.height() - self.height()) // 2  # Center vertically
        self.move(x, y)
        logger.info(f"🐾 Pet positioned at CENTER: ({x}, {y})")
        logger.info(f"🐾 Screen geometry: {screen.width()}x{screen.height()}")
    
    def set_state(self, state: str):
        """
        Change pet state with smooth crossfade transition.
        
        Args:
            state: Nexa state name (idle, listening, thinking, etc.)
        """
        state_lower = state.lower()
        
        if state_lower == self.current_state:
            return  # No change
        
        # If already transitioning, queue the new state
        if self.is_transitioning:
            self.pending_state = state_lower
            logger.debug(f"🐾 Queuing state: {state_lower} (currently transitioning)")
            return
        
        # Get image for new state
        if state_lower not in self.images:
            logger.warning(f"No image for state: {state_lower}")
            return
        
        # Start crossfade transition
        self._crossfade_to_state(state_lower)
    
    def _crossfade_to_state(self, new_state: str):
        """
        Perform crossfade transition to new state.
        
        Args:
            new_state: Target state name
        """
        self.is_transitioning = True
        
        # Stop any existing animation
        if self.fade_animation:
            self.fade_animation.stop()
        
        # Create fade-out animation
        self.fade_animation = QPropertyAnimation(self.image_label, b"windowOpacity")
        self.fade_animation.setDuration(200)  # 200ms fade
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # When fade-out completes, change image and fade-in
        self.fade_animation.finished.connect(lambda: self._complete_crossfade(new_state))
        
        self.fade_animation.start()
        logger.debug(f"🐾 Crossfade: {self.current_state} → {new_state}")
    
    def _complete_crossfade(self, new_state: str):
        """
        Complete crossfade by changing image and fading in.
        
        Args:
            new_state: New state to display
        """
        # Update state and image
        self.current_state = new_state
        pixmap = self.images[new_state]
        scaled_pixmap = pixmap.scaled(
            self.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.image_label.setPixmap(scaled_pixmap)
        
        # Create fade-in animation
        self.fade_animation = QPropertyAnimation(self.image_label, b"windowOpacity")
        self.fade_animation.setDuration(200)  # 200ms fade
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.InOutQuad)
        
        # When fade-in completes, check for pending states
        self.fade_animation.finished.connect(self._on_transition_complete)
        
        self.fade_animation.start()
    
    def _on_transition_complete(self):
        """Handle transition completion and process pending states."""
        self.is_transitioning = False
        
        # Start/stop breathing animation based on state
        if self.current_state == 'idle':
            self._start_breathing()
        else:
            self._stop_breathing()
        
        # Spawn particles for certain states
        if self.current_state == 'happy':
            self._spawn_particles('heart')
        elif self.current_state == 'sleeping':
            self._spawn_particles('zzz')
        elif self.current_state == 'listening':
            self._spawn_particles('sparkle')
        
        # Process any pending state change
        if self.pending_state:
            next_state = self.pending_state
            self.pending_state = None
            self.set_state(next_state)
            logger.debug(f"🐾 Processing queued state: {next_state}")
    
    def _start_breathing(self):
        """Start subtle breathing animation for idle state."""
        # DISABLED: Widget resize causes position shift
        # Will implement proper scale transform in animation overhaul
        logger.debug("🐾 Breathing animation disabled (pending animation system redesign)")
        return
    
    def _stop_breathing(self):
        """Stop breathing animation."""
        if self.breathing_animation:
            self.breathing_animation.stop()
            logger.debug("🐾 Breathing animation stopped")
    
    def _spawn_particles(self, particle_type: str):
        """
        Spawn particle effects based on state.
        
        Args:
            particle_type: 'heart', 'sparkle', or 'zzz'
        """
        # Clear existing particles
        self._clear_particles()
        
        # Particle settings
        particle_count = 3 if particle_type == 'heart' else 5
        particle_emoji = {
            'heart': '💜',
            'sparkle': '✨',
            'zzz': '💤'
        }.get(particle_type, '✨')
        
        # Create particles
        for i in range(particle_count):
            particle = QLabel(particle_emoji, self)
            particle.setFont(QFont("Segoe UI Emoji", 20))
            particle.setStyleSheet("background: transparent; color: white;")
            particle.setAttribute(Qt.WA_TransparentForMouseEvents)
            
            # Random position around pet
            import random
            x = random.randint(10, self.width() - 40)
            y = random.randint(10, self.height() - 40)
            particle.move(x, y)
            particle.show()
            
            self.particles.append(particle)
            
            # Animate particle (float up and fade)
            self._animate_particle(particle, i * 200)  # Stagger animations
        
        logger.debug(f"🐾 Spawned {particle_count} {particle_type} particles")
    
    def _animate_particle(self, particle: QLabel, delay: int):
        """
        Animate a single particle (float up and fade out).
        
        Args:
            particle: Particle label to animate
            delay: Delay before animation starts (ms)
        """
        # Position animation (float up)
        pos_anim = QPropertyAnimation(particle, b"pos")
        pos_anim.setDuration(1500)
        pos_anim.setStartValue(particle.pos())
        pos_anim.setEndValue(QPoint(particle.x(), particle.y() - 50))
        pos_anim.setEasingCurve(QEasingCurve.OutQuad)
        
        # Opacity animation (fade out)
        opacity_anim = QPropertyAnimation(particle, b"windowOpacity")
        opacity_anim.setDuration(1500)
        opacity_anim.setStartValue(1.0)
        opacity_anim.setEndValue(0.0)
        opacity_anim.setEasingCurve(QEasingCurve.InQuad)
        
        # Clean up when done
        opacity_anim.finished.connect(particle.deleteLater)
        
        # Start animations with delay
        QTimer.singleShot(delay, pos_anim.start)
        QTimer.singleShot(delay, opacity_anim.start)
    
    def _clear_particles(self):
        """Remove all active particles."""
        for particle in self.particles:
            particle.deleteLater()
        self.particles.clear()
    
    def _play_bounce_reaction(self):
        """Play bounce animation when pet is clicked."""
        # Stop any existing bounce
        if self.bounce_animation and self.bounce_animation.state() == QPropertyAnimation.Running:
            return
        
        # Store original position
        original_y = self.y()
        
        # Create bounce animation (move up and down)
        self.bounce_animation = QPropertyAnimation(self, b"pos")
        self.bounce_animation.setDuration(600)
        
        # Bounce keyframes
        self.bounce_animation.setKeyValueAt(0.0, self.pos())
        self.bounce_animation.setKeyValueAt(0.3, QPoint(self.x(), original_y - 30))  # Jump up
        self.bounce_animation.setKeyValueAt(0.5, QPoint(self.x(), original_y))       # Land
        self.bounce_animation.setKeyValueAt(0.65, QPoint(self.x(), original_y - 10)) # Small bounce
        self.bounce_animation.setKeyValueAt(0.8, QPoint(self.x(), original_y))       # Land
        self.bounce_animation.setKeyValueAt(1.0, QPoint(self.x(), original_y))       # Settle
        
        self.bounce_animation.setEasingCurve(QEasingCurve.OutBounce)
        self.bounce_animation.start()
        
        # Spawn happy particles during bounce
        self._spawn_particles('sparkle')
        
        logger.debug("🐾 Pet bounce reaction triggered!")
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging and reactions."""
        if event.button() == Qt.LeftButton:
            # Check for double-click for bounce reaction
            if event.type() == event.Type.MouseButtonDblClick:
                self._play_bounce_reaction()
                event.accept()
                return
            
            self.dragging = True
            self.drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
        elif event.button() == Qt.RightButton:
            # Show context menu
            self._show_context_menu(event.globalPosition().toPoint())
    
    def mouseDoubleClickEvent(self, event):
        """Handle double-click for bounce reaction."""
        if event.button() == Qt.LeftButton:
            self._play_bounce_reaction()
            event.accept()
    
    def resizeEvent(self, event):
        """Handle widget resize - keep label same size and re-scale image."""
        super().resizeEvent(event)
        self.image_label.resize(self.size())
        # Re-scale current image to new widget size
        if self.current_state and self.current_state in self.images:
            pixmap = self.images[self.current_state]
            scaled_pixmap = pixmap.scaled(
                self.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.image_label.setPixmap(scaled_pixmap)
        logger.debug(f"🐾 Widget resized: {self.size().width()}x{self.size().height()}")
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if self.dragging and event.buttons() == Qt.LeftButton:
            # Calculate new position
            new_pos = event.globalPosition().toPoint() - self.drag_start_pos
            
            # Apply edge snapping if enabled
            if self.config.should_snap_to_edges():
                new_pos = self._apply_edge_snap(new_pos)
            
            self.move(new_pos)
            event.accept()
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release after dragging."""
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.setCursor(QCursor(Qt.ArrowCursor))
            
            # Save position
            pos = self.pos()
            self.config.set_position(pos.x(), pos.y())
            logger.debug(f"Pet position saved: ({pos.x()}, {pos.y()})")
            event.accept()
    
    def _apply_edge_snap(self, pos: QPoint) -> QPoint:
        """
        Apply magnetic edge snapping.
        
        Args:
            pos: Proposed position
        
        Returns:
            Adjusted position with snapping applied
        """
        screen = self.screen().availableGeometry()
        snap_dist = self.config.get_snap_distance()
        
        x = pos.x()
        y = pos.y()
        
        # Snap to left edge
        if abs(x - screen.left()) < snap_dist:
            x = screen.left()
        
        # Snap to right edge
        if abs((x + self.width()) - screen.right()) < snap_dist:
            x = screen.right() - self.width()
        
        # Snap to top edge
        if abs(y - screen.top()) < snap_dist:
            y = screen.top()
        
        # Snap to bottom edge
        if abs((y + self.height()) - screen.bottom()) < snap_dist:
            y = screen.bottom() - self.height()
        
        return QPoint(x, y)
    
    def _show_context_menu(self, pos: QPoint):
        """
        Show right-click context menu.
        
        Args:
            pos: Global position for menu
        """
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
        
        # Mark current size
        current_size = self.config.get('size')
        if current_size == PetSize.SMALL.value:
            small_action.setCheckable(True)
            small_action.setChecked(True)
        elif current_size == PetSize.MEDIUM.value:
            medium_action.setCheckable(True)
            medium_action.setChecked(True)
        elif current_size == PetSize.LARGE.value:
            large_action.setCheckable(True)
            large_action.setChecked(True)
        
        menu.addSeparator()
        
        # Hide pet action
        hide_action = QAction("Hide Pet", self)
        hide_action.triggered.connect(self.hide_pet)
        menu.addAction(hide_action)
        
        # Show menu
        menu.exec(pos)
    
    def _change_size(self, size: PetSize):
        """
        Change pet size.
        
        Args:
            size: New size
        """
        self.config.set_size(size)
        width, height = self.config.get_size_dimensions()
        
        # Resize widget and label
        self.resize(width, height)
        self.image_label.resize(width, height)
        
        # Re-scale current image to new size
        self.set_state(self.current_state)
        
        logger.info(f"Pet size changed to {size.value}: {width}x{height}")
    
    def hide_pet(self):
        """Hide pet and disable in config."""
        self.config.set('enabled', False)
        self.hide()
        self.closed.emit()
        logger.info("Pet hidden by user")
    
    def closeEvent(self, event):
        """Handle window close event."""
        # Save position before closing
        pos = self.pos()
        self.config.set_position(pos.x(), pos.y())
        
        # Disable pet
        self.config.set('enabled', False)
        
        # Emit signal
        self.closed.emit()
        
        event.accept()
        logger.info("Pet widget closed")
