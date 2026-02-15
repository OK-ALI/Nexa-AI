"""
Pet Speech Bubble - Animated response display widget
Shows Nexa's responses in a cute speech bubble above the pet character.
"""

import sys
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTextEdit, 
    QPushButton, QGraphicsDropShadowEffect, QApplication
)
from PySide6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, QRect, QSize
from PySide6.QtGui import QPalette, QColor, QFont

from ui.typing_animator import TypingAnimator


class PetSpeechBubble(QWidget):
    """
    Speech bubble widget that displays Nexa's responses.
    
    Features:
    - Typewriter text animation
    - Auto-dismiss after timeout
    - Copy button
    - Smart positioning (above/beside pet)
    - Rounded corners with drop shadow
    - Fade in/out animations
    """
    
    def __init__(self, parent=None, auto_dismiss_ms: int = 7000):
        """
        Initialize speech bubble.
        
        Args:
            parent: Parent widget (usually the pet widget)
            auto_dismiss_ms: Auto-hide timeout in milliseconds (default 7 seconds)
        """
        super().__init__(parent)
        
        self.auto_dismiss_ms = auto_dismiss_ms
        self.typing_speed_ms = 15  # Faster typing (was 50ms)
        
        # Initialize components
        self.typing_animator = TypingAnimator(speed_ms=self.typing_speed_ms, parent=self)
        self.dismiss_timer = QTimer(self)
        self.fade_animation = None
        
        # Setup UI
        self._setup_ui()
        self._setup_animations()
        self._connect_signals()
        
        # Initially hidden
        self.hide()
    
    def _setup_ui(self) -> None:
        """Setup the speech bubble UI."""
        # Window flags for frameless, always-on-top bubble
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        # Main layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(10)
        
        # Container widget for rounded corners and background
        self.container = QWidget()
        self.container.setObjectName("bubbleContainer")
        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(15, 15, 15, 15)
        container_layout.setSpacing(10)
        
        # Text display area
        self.text_display = QTextEdit()
        self.text_display.setReadOnly(True)
        self.text_display.setMinimumWidth(300)
        self.text_display.setMaximumWidth(500)
        self.text_display.setMinimumHeight(80)
        self.text_display.setMaximumHeight(300)
        self.text_display.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.text_display.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.text_display.setFont(QFont("Segoe UI", 11))
        
        # Disable text selection during typing (re-enable after)
        self.text_display.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.setSpacing(5)
        
        # Get icon manager for PNG icons
        from ui.music_indicator import get_icon_manager
        icon_mgr = get_icon_manager()
        
        # Copy button with PNG icon
        self.copy_button = QPushButton(" Copy")
        self.copy_button.setIcon(icon_mgr.get_icon('copy', 16))
        self.copy_button.setIconSize(QSize(16, 16))
        self.copy_button.setFixedHeight(30)
        self.copy_button.setFixedWidth(80)
        self.copy_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        # Skip button (to skip typewriter animation)
        self.skip_button = QPushButton("Skip")
        self.skip_button.setFixedHeight(30)
        self.skip_button.setFixedWidth(80)
        self.skip_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.skip_button.hide()  # Only show during typing
        
        # Close button with PNG icon
        self.close_button = QPushButton()
        self.close_button.setIcon(icon_mgr.get_icon('close', 14))
        self.close_button.setIconSize(QSize(14, 14))
        self.close_button.setFixedHeight(30)
        self.close_button.setFixedWidth(30)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        
        button_layout.addWidget(self.copy_button)
        button_layout.addWidget(self.skip_button)
        button_layout.addStretch()
        button_layout.addWidget(self.close_button)
        
        # Add widgets to container
        container_layout.addWidget(self.text_display)
        container_layout.addLayout(button_layout)
        
        # Add container to main layout
        main_layout.addWidget(self.container)
        
        # Apply styling
        self._apply_styling()
        
        # Add cyan glow effect (Nexa theme)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(25)
        shadow.setColor(QColor(0, 180, 255, 120))  # Cyan glow
        shadow.setOffset(0, 3)
        self.container.setGraphicsEffect(shadow)
    
    def _apply_styling(self) -> None:
        """Apply CSS styling to the bubble - Nexa theme (cyan/blue)."""
        self.setStyleSheet("""
            #bubbleContainer {
                background-color: rgba(10, 20, 40, 250);
                border: 2px solid rgba(0, 200, 255, 180);
                border-radius: 15px;
            }
            
            QTextEdit {
                background-color: rgba(15, 30, 50, 220);
                border: 1px solid rgba(0, 150, 220, 80);
                border-radius: 8px;
                color: #E8F4FF;
                padding: 8px;
                selection-background-color: rgba(0, 180, 255, 100);
            }
            
            QPushButton {
                background-color: rgba(0, 150, 220, 200);
                border: none;
                border-radius: 5px;
                color: white;
                font-weight: bold;
                padding: 5px;
            }
            
            QPushButton:hover {
                background-color: rgba(0, 200, 255, 230);
            }
            
            QPushButton:pressed {
                background-color: rgba(0, 220, 255, 255);
            }
        """)
    
    def _setup_animations(self) -> None:
        """Setup fade in/out animations."""
        # Fade animation will be created when needed
        pass
    
    def _connect_signals(self) -> None:
        """Connect signals and slots."""
        # Typing animator signals
        self.typing_animator.text_updated.connect(self._on_text_updated)
        self.typing_animator.animation_complete.connect(self._on_typing_complete)
        
        # Button signals
        self.copy_button.clicked.connect(self._copy_text)
        self.skip_button.clicked.connect(self._skip_typing)
        self.close_button.clicked.connect(self._dismiss_bubble)
        
        # Auto-dismiss timer
        self.dismiss_timer.timeout.connect(self._fade_out)
    
    def show_response(self, text: str, position: tuple = None) -> None:
        """
        Show speech bubble with given text.
        
        Args:
            text: Response text to display
            position: Optional (x, y) position for bubble. If None, uses last position.
        """
        # Stop any existing animations/timers
        self.typing_animator.stop_animation()
        self.dismiss_timer.stop()
        
        # Clear previous text
        self.text_display.clear()
        
        # Show skip button during typing
        self.skip_button.show()
        
        # Disable copy during typing
        self.copy_button.setEnabled(False)
        
        # Disable text selection during typing
        self.text_display.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        
        # Position bubble (only if provided)
        if position:
            self.move(position[0], position[1])
        # Note: Don't center - position_above_pet() should be called before this
        
        # Calculate auto-dismiss time based on text length
        # Rough estimate: 150 words per minute speaking rate = 2.5 words per second
        # Average word length = 5 chars, so ~12.5 chars per second
        # Add 3 seconds buffer for reading after TTS finishes
        word_count = len(text.split())
        speaking_time_ms = max(5000, int(word_count * 400) + 3000)  # ~400ms per word + 3s buffer
        self._current_dismiss_time = min(speaking_time_ms, 60000)  # Cap at 60 seconds
        
        # Show with fade in
        self._fade_in()
        
        # Start typewriter animation
        self.typing_animator.start_animation(text)
    
    def _on_text_updated(self, text: str) -> None:
        """Called when typing animator reveals more text."""
        self.text_display.setPlainText(text)
        
        # Auto-scroll to bottom
        scrollbar = self.text_display.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
    
    def _on_typing_complete(self) -> None:
        """Called when typing animation finishes."""
        # Hide skip button
        self.skip_button.hide()
        
        # Enable copy button
        self.copy_button.setEnabled(True)
        
        # Enable text selection
        self.text_display.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse |
            Qt.TextInteractionFlag.TextSelectableByKeyboard
        )
        
        # Start auto-dismiss timer (use calculated time based on text length)
        dismiss_time = getattr(self, '_current_dismiss_time', self.auto_dismiss_ms)
        self.dismiss_timer.start(dismiss_time)
    
    def _skip_typing(self) -> None:
        """Skip typewriter animation and show full text."""
        self.typing_animator.skip_to_end()
    
    def _copy_text(self) -> None:
        """Copy bubble text to clipboard."""
        text = self.text_display.toPlainText()
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        # Visual feedback
        original_text = self.copy_button.text()
        self.copy_button.setText(" Copied!")
        QTimer.singleShot(1500, lambda: self.copy_button.setText(original_text))
    
    def _dismiss_bubble(self) -> None:
        """Immediately dismiss the bubble."""
        self.dismiss_timer.stop()
        self.typing_animator.stop_animation()
        self._fade_out()
    
    def _fade_in(self) -> None:
        """Fade in animation."""
        self.setWindowOpacity(0.0)
        self.show()
        
        # Create fade animation
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(150)  # Faster fade-in (was 300ms)
        self.fade_animation.setStartValue(0.0)
        self.fade_animation.setEndValue(1.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.fade_animation.start()
    
    def _fade_out(self) -> None:
        """Fade out animation and hide."""
        if self.fade_animation and self.fade_animation.state() == QPropertyAnimation.State.Running:
            self.fade_animation.stop()
        
        self.fade_animation = QPropertyAnimation(self, b"windowOpacity")
        self.fade_animation.setDuration(300)
        self.fade_animation.setStartValue(1.0)
        self.fade_animation.setEndValue(0.0)
        self.fade_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self.fade_animation.finished.connect(self.hide)
        self.fade_animation.start()
    
    def _center_on_screen(self) -> None:
        """Center bubble on screen."""
        screen = QApplication.primaryScreen().geometry()
        bubble_rect = self.geometry()
        
        x = (screen.width() - bubble_rect.width()) // 2
        y = (screen.height() - bubble_rect.height()) // 2
        
        self.move(x, y)
    
    def position_above_pet(self, pet_geometry: QRect, offset_y: int = -20) -> None:
        """
        Position bubble above the pet widget.
        
        Args:
            pet_geometry: QRect of the pet widget
            offset_y: Vertical offset from pet top (negative = above)
        """
        # Adjust size to content first
        self.adjustSize()
        
        # Calculate position above pet, centered horizontally
        pet_center_x = pet_geometry.x() + pet_geometry.width() // 2
        bubble_x = pet_center_x - self.width() // 2
        bubble_y = pet_geometry.y() + offset_y - self.height()
        
        # Ensure bubble stays on screen
        screen = QApplication.primaryScreen().geometry()
        
        # Clamp X position
        if bubble_x < 10:
            bubble_x = 10
        elif bubble_x + self.width() > screen.width() - 10:
            bubble_x = screen.width() - self.width() - 10
        
        # Clamp Y position (if too high, show beside instead)
        if bubble_y < 10:
            # Show to the right of pet instead
            bubble_x = pet_geometry.x() + pet_geometry.width() + 20
            bubble_y = pet_geometry.y()
            
            # If still off-screen, show to the left
            if bubble_x + self.width() > screen.width() - 10:
                bubble_x = pet_geometry.x() - self.width() - 20
        
        self.move(bubble_x, bubble_y)
    
    def set_typing_speed(self, speed_ms: int) -> None:
        """
        Set typewriter animation speed.
        
        Args:
            speed_ms: Milliseconds per character (lower = faster)
        """
        self.typing_speed_ms = speed_ms
        self.typing_animator.set_speed(speed_ms)
    
    def set_auto_dismiss_time(self, timeout_ms: int) -> None:
        """
        Set auto-dismiss timeout.
        
        Args:
            timeout_ms: Time to wait before auto-hiding (milliseconds)
        """
        self.auto_dismiss_ms = timeout_ms
