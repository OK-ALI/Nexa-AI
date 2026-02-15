"""
Nexa Sprite Pet Widget - Animated Desktop Companion
Uses your custom Nexa pet images with smooth programmatic animations.
Features floating, breathing, bounce effects, and smooth state transitions.
"""

import logging
import math
from pathlib import Path
from typing import Optional, Dict
from PySide6.QtWidgets import QWidget, QLabel, QMenu, QGraphicsOpacityEffect
from PySide6.QtCore import (
    Qt, QPoint, QSize, Signal, QTimer, QPropertyAnimation, 
    QEasingCurve, Property, QSequentialAnimationGroup, QParallelAnimationGroup
)
from PySide6.QtGui import QPixmap, QCursor, QAction, QPainter, QTransform, QContextMenuEvent, QColor, QImage, QRadialGradient
from .pet_config import PetConfig, PetSize
from .pet_speech_bubble import PetSpeechBubble
from .pet_radial_menu import PetRadialMenu

logger = logging.getLogger(__name__)


class SpritePetWidget(QWidget):
    """
    Animated sprite-based desktop pet for Nexa AI.
    
    Features:
    - Transparent, frameless, always-on-top window
    - Draggable anywhere on screen
    - Smooth state transitions with crossfade
    - Breathing animation (subtle scale pulse)
    - Floating animation (gentle up-down bobbing)
    - Bounce effect on state changes
    - Uses YOUR custom Nexa pet images
    """
    
    # Signal emitted when pet is closed
    closed = Signal()
    
    # State to image filename mapping
    STATE_IMAGES = {
        'idle': 'idle.png',
        'listening': 'listening.png',
        'thinking': 'thinking.png',
        'speaking': 'speaking.png',
        'executing': 'thinking.png',
        'content_mode': 'content_mode.png',  # Dedicated study mode image!
        'error': 'error.png',
        'happy': 'veryhappy.png',
        'sleeping': 'sleeping.png',
        'recognizing': 'listening.png',
        # P7 Personality states
        'wave': 'wave.png',
        'yawn': 'yawn.png',
        'stretch': 'stretch.png',
        'surprised': 'surprised.png',
        'dance': 'dance.png',
        'curious': 'curious.png',
        'working': 'working.png',
    }
    
    def __init__(self, config_dir: Path, assets_dir: Path, parent=None):
        """
        Initialize sprite pet widget.
        
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
        self.scaled_images: Dict[str, QPixmap] = {}  # Pre-scaled for current size
        
        # Animation state
        self._float_offset = 0.0
        self._breath_scale = 1.0
        self._opacity = 1.0
        self.is_transitioning = False
        self.pending_state: Optional[str] = None
        
        # Animation timers
        self.animation_timer: Optional[QTimer] = None
        self.float_phase = 0.0  # Radians for sine wave
        self.breath_phase = 0.0  # Radians for breathing
        
        # Transition animation
        self.fade_timer: Optional[QTimer] = None
        self.fade_progress = 0.0
        self.fade_from_state: Optional[str] = None
        self.fade_to_state: Optional[str] = None
        
        # Bounce animation
        self.bounce_offset = 0.0
        self.bounce_velocity = 0.0
        
        # Speech bubble (P4 feature)
        self.speech_bubble: Optional[PetSpeechBubble] = None
        
        # Radial menu (P5 feature)
        self.radial_menu: Optional[PetRadialMenu] = None
        self.quick_actions = None  # Set by NexaModernWindow
        
        # P7 Personality system
        self.personality = None  # Initialized after widget setup
        self._click_count = 0
        self._click_timer = QTimer(self)
        self._click_timer.setSingleShot(True)
        self._click_timer.timeout.connect(self._process_clicks)
        
        # Setup window
        self._setup_window()
        
        # Load images
        self._load_images()
        
        # Setup UI
        self._setup_ui()
        
        # Restore position
        self._restore_position()
        
        # Start animations
        self._start_animations()
        
        # Initialize speech bubble
        self._init_speech_bubble()
        
        logger.info("✅ Sprite Pet Widget initialized with animations")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Properties for animation
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_float_offset(self):
        return self._float_offset
    
    def set_float_offset(self, value):
        self._float_offset = value
        self.update()
    
    float_offset = Property(float, get_float_offset, set_float_offset)
    
    def get_breath_scale(self):
        return self._breath_scale
    
    def set_breath_scale(self, value):
        self._breath_scale = value
        self.update()
    
    breath_scale = Property(float, get_breath_scale, set_breath_scale)
    
    def get_opacity(self):
        return self._opacity
    
    def set_opacity(self, value):
        """Set pet opacity (0.0-1.0). Also updates window opacity."""
        self._opacity = max(0.2, min(1.0, value))  # Clamp between 0.2-1.0
        self.setWindowOpacity(self._opacity)
        self.update()
    
    opacity = Property(float, get_opacity, set_opacity)
    
    def set_scale(self, percent: int):
        """
        Set pet size as percentage of base size.
        
        Args:
            percent: Scale percentage (50-200)
        """
        percent = max(50, min(200, percent))  # Clamp 50-200%
        
        # Base size is MEDIUM (300x420) - reduced for tighter fit
        base_w, base_h = 300, 420
        new_w = int(base_w * percent / 100)
        new_h = int(base_h * percent / 100)
        
        self.resize(new_w, new_h)
        
        # Save to config if available
        if hasattr(self, 'config') and self.config:
            self.config.set('scale_percent', percent)
        
        logger.debug(f"📐 Pet scaled to {percent}% ({new_w}x{new_h})")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Window Setup
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _setup_window(self):
        """Configure window properties."""
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_NoSystemBackground, True)
        self.setStyleSheet("background: transparent;")
        self.setWindowTitle("Nexa Pet")
        
        # Get size from config
        width, height = self.config.get_size_dimensions()
        self.resize(width, height)
        
        logger.info(f"🐾 Sprite pet window: {width}x{height}")
    
    def _setup_ui(self):
        """Setup UI - we paint directly, no child widgets needed."""
        self.setMouseTracking(True)
        self.raise_()
        self.activateWindow()
    
    def _load_images(self):
        """Load all state images into cache."""
        logger.info(f"📸 Loading sprite images from {self.assets_dir}")
        
        if not self.assets_dir.exists():
            logger.error(f"❌ Pet assets directory not found: {self.assets_dir}")
            return
        
        for state, filename in self.STATE_IMAGES.items():
            image_path = self.assets_dir / filename
            
            if image_path.exists():
                pixmap = QPixmap(str(image_path))
                if not pixmap.isNull():
                    # Ensure proper alpha channel
                    proper_pixmap = QPixmap(pixmap.size())
                    proper_pixmap.fill(Qt.transparent)
                    painter = QPainter(proper_pixmap)
                    painter.setCompositionMode(QPainter.CompositionMode_Source)
                    painter.drawPixmap(0, 0, pixmap)
                    painter.end()
                    
                    self.images[state] = proper_pixmap
                    logger.info(f"✅ Loaded {state}: {filename}")
                else:
                    logger.error(f"❌ Failed to load {filename}")
            else:
                logger.warning(f"⚠️ Image not found: {image_path}")
        
        # Pre-scale images for current size
        self._scale_images()
        
        logger.info(f"✅ Loaded {len(self.images)} sprite images")
    
    def _scale_images(self):
        """Pre-scale all images to current widget size."""
        self.scaled_images.clear()
        target_size = self.size()
        
        for state, pixmap in self.images.items():
            scaled = pixmap.scaled(
                target_size,
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.scaled_images[state] = scaled
    
    def _restore_position(self):
        """Restore saved position or auto-center."""
        saved_pos = self.config.get_position()
        
        if saved_pos[0] is not None and saved_pos[1] is not None:
            self.move(saved_pos[0], saved_pos[1])
            logger.info(f"🐾 Restored position: {saved_pos}")
        else:
            # Center on screen
            screen = self.screen().availableGeometry()
            x = screen.right() - self.width() - 50  # Bottom-right with margin
            y = screen.bottom() - self.height() - 50
            self.move(x, y)
            logger.info(f"🐾 Default position: ({x}, {y})")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Speech Bubble (P4 Feature)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _init_speech_bubble(self):
        """Initialize the speech bubble widget."""
        # Create as standalone window (no parent) so it positions correctly
        # Using global screen coordinates
        self.speech_bubble = PetSpeechBubble(parent=None, auto_dismiss_ms=7000)
        logger.info("💬 Speech bubble initialized")
    
    def show_response(self, text: str):
        """
        Show a response in the speech bubble above the pet.
        
        Args:
            text: Response text to display
        """
        # Check if speech bubble is enabled in settings
        if not self.config.get('show_speech_bubble', True):
            logger.debug("💬 Speech bubble disabled in settings, skipping")
            return
        
        if not self.speech_bubble:
            self._init_speech_bubble()
        
        # Position bubble above pet using global screen coordinates
        # frameGeometry() returns position on screen, not relative to parent
        self.speech_bubble.position_above_pet(self.frameGeometry(), offset_y=-20)
        
        # Show with typewriter animation
        self.speech_bubble.show_response(text)
        
        logger.info(f"💬 Showing response: {text[:50]}...")
    
    def hide_speech_bubble(self):
        """Hide the speech bubble."""
        if self.speech_bubble and self.speech_bubble.isVisible():
            self.speech_bubble._dismiss_bubble()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Radial Menu (P5 Feature)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _init_radial_menu(self):
        """Initialize the radial menu widget."""
        self.radial_menu = PetRadialMenu(parent=self)
        
        # Connect menu items if quick_actions is set
        if self.quick_actions:
            self.radial_menu.set_items(self.quick_actions.get_menu_items())
        
        logger.info("🎯 Radial menu initialized")
    
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
        
        logger.info("🎯 Radial menu opened via right-click")
    
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
        logger.info("🎯 Radial menu opened via right-click")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # P7 Personality System
    # ═══════════════════════════════════════════════════════════════════════════
    
    def init_personality(self):
        """
        Initialize the personality system.
        
        Called by NexaModernWindow after the pet widget is fully set up.
        The personality controller needs access to the config, which is
        why it's initialized separately.
        """
        from .pet_personality import PetPersonality
        
        self.personality = PetPersonality(self, self.config)
        self.personality.start()
        logger.info("🎭 Pet personality system initialized")
    
    def stop_personality(self):
        """Stop the personality system."""
        if self.personality:
            self.personality.stop()
            logger.info("🎭 Pet personality system stopped")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Settings Control Methods (P6)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def set_animations_enabled(self, enabled: bool):
        """
        Enable or disable all pet animations (breathing, floating).
        
        Args:
            enabled: True to enable animations, False to pause them
        """
        self._animations_enabled = enabled
        if hasattr(self, 'animation_timer') and self.animation_timer:
            if enabled:
                if not self.animation_timer.isActive():
                    self.animation_timer.start(16)
                    logger.info("🎬 Animations resumed")
            else:
                self.animation_timer.stop()
                logger.info("⏸️ Animations paused")
        
        # Save to config
        if hasattr(self, 'config') and self.config:
            self.config.set('animations_enabled', enabled)
    
    @property
    def snap_enabled(self) -> bool:
        """Check if snap-to-edges is enabled."""
        if hasattr(self, 'config') and self.config:
            return self.config.get('snap_to_edges', True)
        return True
    
    @snap_enabled.setter
    def snap_enabled(self, enabled: bool):
        """Enable or disable snap-to-edges behavior."""
        if hasattr(self, 'config') and self.config:
            self.config.set('snap_to_edges', enabled)
            logger.info(f"📍 Snap to edges: {'enabled' if enabled else 'disabled'}")
    
    def set_expression_speed(self, speed: float):
        """
        Set the speed multiplier for expressions and state transitions.
        
        Args:
            speed: Speed multiplier (0.5 = slow, 1.0 = normal, 2.0 = fast)
        """
        self._expression_speed = speed
        
        # Update personality idle manager if exists
        if hasattr(self, 'personality') and self.personality:
            if hasattr(self.personality, 'idle_manager') and self.personality.idle_manager:
                # Inverse speed: faster = shorter idle intervals
                self.personality.idle_manager.speed_multiplier = 1.0 / speed
        
        # Save to config
        if hasattr(self, 'config') and self.config:
            self.config.set('expression_speed', speed)
        
        logger.info(f"⚡ Expression speed: {speed:.1f}x")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Animation System
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _start_animations(self):
        """Start the main animation loop."""
        self.animation_timer = QTimer(self)
        self.animation_timer.timeout.connect(self._update_animations)
        self.animation_timer.start(16)  # ~60fps
        logger.info("🎬 Started sprite animations (60fps)")
    
    def _update_animations(self):
        """Update all animations each frame."""
        dt = 0.016  # 16ms per frame
        
        # Floating animation (gentle bobbing)
        self.float_phase += dt * 1.5  # Speed of float
        self._float_offset = math.sin(self.float_phase) * 8  # 8px amplitude
        
        # Breathing animation (subtle scale pulse)
        self.breath_phase += dt * 2.0  # Breathing speed
        self._breath_scale = 1.0 + math.sin(self.breath_phase) * 0.015  # 1.5% scale variation
        
        # Bounce decay
        if abs(self.bounce_offset) > 0.1 or abs(self.bounce_velocity) > 0.1:
            self.bounce_velocity -= self.bounce_offset * 0.3  # Spring force
            self.bounce_velocity *= 0.85  # Damping
            self.bounce_offset += self.bounce_velocity
        else:
            self.bounce_offset = 0
            self.bounce_velocity = 0
        
        # Fade transition
        if self.is_transitioning and self.fade_timer is None:
            self._update_fade()
        
        # Trigger repaint
        self.update()
    
    def _update_fade(self):
        """Update crossfade transition."""
        fade_speed = 0.08  # 0-1 in ~12 frames (~200ms)
        self.fade_progress += fade_speed
        
        if self.fade_progress >= 1.0:
            self.fade_progress = 1.0
            self.current_state = self.fade_to_state
            self.fade_from_state = None
            self.fade_to_state = None
            self.is_transitioning = False
            
            # Process any pending state
            if self.pending_state:
                next_state = self.pending_state
                self.pending_state = None
                self.set_state(next_state)
    
    def _trigger_bounce(self):
        """Trigger a bounce animation on state change."""
        self.bounce_velocity = -15  # Initial upward velocity
    
    # ═══════════════════════════════════════════════════════════════════════════
    # State Management
    # ═══════════════════════════════════════════════════════════════════════════
    
    def set_state(self, state: str):
        """
        Change pet state with smooth crossfade transition.
        
        Args:
            state: Nexa state name (idle, listening, thinking, etc.)
        """
        state_lower = state.lower()
        
        if state_lower == self.current_state and not self.is_transitioning:
            return  # No change
        
        # Queue if transitioning
        if self.is_transitioning:
            self.pending_state = state_lower
            return
        
        # Check if we have the image
        if state_lower not in self.scaled_images:
            logger.warning(f"No image for state: {state_lower}, falling back to idle")
            state_lower = 'idle'
        
        # Start crossfade
        self.fade_from_state = self.current_state
        self.fade_to_state = state_lower
        self.fade_progress = 0.0
        self.is_transitioning = True
        
        # Trigger bounce effect
        self._trigger_bounce()
        
        logger.info(f"🐾 State: {self.current_state} → {state_lower}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Painting
    # ═══════════════════════════════════════════════════════════════════════════
    
    def paintEvent(self, event):
        """Custom paint with animations."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setRenderHint(QPainter.SmoothPixmapTransform)
        
        # Calculate center position with animations
        center_x = self.width() / 2
        center_y = self.height() / 2 + self._float_offset + self.bounce_offset
        
        # Get current image(s)
        if self.is_transitioning and self.fade_from_state and self.fade_to_state:
            # Crossfade between two states
            from_pixmap = self.scaled_images.get(self.fade_from_state)
            to_pixmap = self.scaled_images.get(self.fade_to_state)
            
            if from_pixmap and to_pixmap:
                # Draw fading-out image
                painter.setOpacity(1.0 - self.fade_progress)
                self._draw_scaled_pixmap(painter, from_pixmap, center_x, center_y)
                
                # Draw fading-in image
                painter.setOpacity(self.fade_progress)
                self._draw_scaled_pixmap(painter, to_pixmap, center_x, center_y)
        else:
            # Single state
            pixmap = self.scaled_images.get(self.current_state)
            if pixmap:
                painter.setOpacity(self._opacity)
                self._draw_scaled_pixmap(painter, pixmap, center_x, center_y)
        
        painter.end()
    
    def _draw_scaled_pixmap(self, painter: QPainter, pixmap: QPixmap, center_x: float, center_y: float):
        """Draw pixmap with breathing scale effect and cyan glow centered at position."""
        # Calculate scaled size
        scaled_width = pixmap.width() * self._breath_scale
        scaled_height = pixmap.height() * self._breath_scale
        
        # Draw cyan glow behind the character
        if self.config.get('glow_enabled', True):
            self._draw_glow(painter, pixmap, center_x, center_y)
        
        # Draw with scale transform
        painter.save()
        painter.translate(center_x, center_y)
        painter.scale(self._breath_scale, self._breath_scale)
        painter.translate(-pixmap.width() / 2, -pixmap.height() / 2)
        painter.drawPixmap(0, 0, pixmap)
        painter.restore()
    
    def _draw_glow(self, painter: QPainter, pixmap: QPixmap, center_x: float, center_y: float):
        """
        Draw a cyan glow effect behind the pet.
        Creates a soft ambient glow around the character body only.
        """
        glow_intensity = self.config.get('glow_intensity', 0.6)  # 0.0 - 1.0
        
        # Glow parameters - tighter around character
        glow_spread = 15  # How far the glow extends beyond character (was 50)
        
        painter.save()
        painter.translate(center_x, center_y)
        painter.scale(self._breath_scale, self._breath_scale)
        painter.translate(-pixmap.width() / 2, -pixmap.height() / 2)
        
        # Get pixmap dimensions
        glow_w = pixmap.width()
        glow_h = pixmap.height()
        
        # Calculate character body bounds (estimate: upper 35% is head, lower 65% is body)
        # Draw glow focused on the body area, not the whole image rectangle
        body_top = glow_h * 0.25  # Start below head
        body_height = glow_h * 0.65  # Body portion
        body_width = glow_w * 0.6  # Narrower body width
        body_left = (glow_w - body_width) / 2  # Center horizontally
        
        # Create elliptical gradient centered on body
        center_gx = glow_w / 2
        center_gy = body_top + body_height * 0.5  # Center of body area
        radius = max(body_width, body_height) * 0.5 + glow_spread
        
        gradient = QRadialGradient(center_gx, center_gy, radius)
        # Softer colors that fade to transparent quickly
        gradient.setColorAt(0, QColor(0, 200, 255, int(100 * glow_intensity)))  # Soft cyan center
        gradient.setColorAt(0.4, QColor(0, 180, 255, int(60 * glow_intensity)))  # Mid fade
        gradient.setColorAt(0.7, QColor(0, 150, 255, int(25 * glow_intensity)))  # Outer fade
        gradient.setColorAt(1, QColor(0, 100, 255, 0))  # Transparent edge
        
        painter.setOpacity(1.0)
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        
        # Draw ellipse matching body shape (not full image rectangle)
        painter.drawEllipse(
            int(body_left - glow_spread),
            int(body_top - glow_spread),
            int(body_width + glow_spread * 2),
            int(body_height + glow_spread * 2)
        )
        
        painter.restore()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Mouse Events (Dragging)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging and P7 click tracking."""
        if event.button() == Qt.LeftButton:
            self.dragging = True
            self.drag_start_pos = event.globalPosition().toPoint() - self.pos()
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            # P7: Track clicks for personality reactions
            self._on_single_click()
            event.accept()
        elif event.button() == Qt.RightButton:
            # P5: Show radial menu instead of old context menu
            self._show_radial_menu(event.globalPosition().toPoint())
            event.accept()
    
    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging."""
        if self.dragging:
            new_pos = event.globalPosition().toPoint() - self.drag_start_pos
            
            # Edge snapping
            if self.config.get_snap_enabled():
                new_pos = self._snap_to_edges(new_pos)
            
            self.move(new_pos)
            event.accept()
        else:
            self.setCursor(QCursor(Qt.OpenHandCursor))
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release."""
        if event.button() == Qt.LeftButton and self.dragging:
            self.dragging = False
            self.setCursor(QCursor(Qt.OpenHandCursor))
            
            # Save position
            self.config.set_position(self.x(), self.y())
            self.config.save()
            
            event.accept()
    
    def mouseDoubleClickEvent(self, event):
        """Handle double click - P7 dance reaction."""
        if event.button() == Qt.LeftButton:
            self._click_count = 2  # Mark as double click
            if self.personality:
                self.personality.on_double_click()
            else:
                self.set_state('happy')
                QTimer.singleShot(2000, lambda: self.set_state('idle'))
            event.accept()
    
    def _on_single_click(self):
        """Track clicks for P7 personality reactions."""
        self._click_count += 1
        # Start timer to process clicks after delay
        if not self._click_timer.isActive():
            self._click_timer.start(350)  # 350ms window
    
    def _process_clicks(self):
        """Process accumulated clicks for personality reactions."""
        if not self.personality:
            self._click_count = 0
            return
        
        if self._click_count >= 3:
            self.personality.on_rapid_click()  # surprised
        elif self._click_count == 1:
            self.personality.on_click()  # wave
        # Double click is handled by mouseDoubleClickEvent
        
        self._click_count = 0
    
    def _snap_to_edges(self, pos: QPoint) -> QPoint:
        """Snap position to screen edges if close enough."""
        screen = self.screen().availableGeometry()
        snap_distance = self.config.get_snap_distance()
        
        x, y = pos.x(), pos.y()
        
        # Left edge
        if x < screen.left() + snap_distance:
            x = screen.left()
        # Right edge
        elif x + self.width() > screen.right() - snap_distance:
            x = screen.right() - self.width()
        
        # Top edge
        if y < screen.top() + snap_distance:
            y = screen.top()
        # Bottom edge
        elif y + self.height() > screen.bottom() - snap_distance:
            y = screen.bottom() - self.height()
        
        return QPoint(x, y)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Context Menu
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _show_context_menu(self, pos: QPoint):
        """Show right-click context menu."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #2d2d2d;
                color: #ffffff;
                border: 1px solid #555;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #9c27b0;
            }
        """)
        
        # Size submenu
        size_menu = menu.addMenu("📐 Size")
        
        for size in PetSize:
            action = size_menu.addAction(size.value.capitalize())
            action.setCheckable(True)
            action.setChecked(self.config.get_size() == size)
            action.triggered.connect(lambda checked, s=size: self._set_size(s))
        
        menu.addSeparator()
        
        # Expression test submenu
        expr_menu = menu.addMenu("😊 Test Expression")
        for state in ['idle', 'listening', 'thinking', 'speaking', 'happy', 'sleeping', 'error']:
            action = expr_menu.addAction(state.capitalize())
            action.triggered.connect(lambda checked, s=state: self.set_state(s))
        
        menu.addSeparator()
        
        # Close
        close_action = menu.addAction("❌ Hide Pet")
        close_action.triggered.connect(self._close_pet)
        
        menu.exec_(pos)
    
    def _set_size(self, size: PetSize):
        """Change pet size."""
        self.config.set_size(size)
        self.config.save()
        
        width, height = self.config.get_size_dimensions()
        self.resize(width, height)
        
        # Re-scale images
        self._scale_images()
        
        logger.info(f"🐾 Size changed to: {size.value}")
    
    def _close_pet(self):
        """Close the pet widget."""
        self.config.set_position(self.x(), self.y())
        self.config.save()
        self.closed.emit()
        self.hide()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Resize Event
    # ═══════════════════════════════════════════════════════════════════════════
    
    def resizeEvent(self, event):
        """Handle resize - rescale images."""
        super().resizeEvent(event)
        if self.images:
            self._scale_images()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Cleanup
    # ═══════════════════════════════════════════════════════════════════════════
    
    def closeEvent(self, event):
        """Clean up on close."""
        if self.animation_timer:
            self.animation_timer.stop()
        
        # Clean up speech bubble
        if self.speech_bubble:
            self.speech_bubble.close()
            self.speech_bubble = None
        
        self.config.set_position(self.x(), self.y())
        self.config.save()
        
        self.closed.emit()
        event.accept()
