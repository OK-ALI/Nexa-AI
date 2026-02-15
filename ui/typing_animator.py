"""
Typing Animator - Character-by-character text reveal effect
Provides typewriter animation for speech bubbles with configurable speed.
"""

from PySide6.QtCore import QObject, QTimer, Signal


class TypingAnimator(QObject):
    """
    Animates text reveal character-by-character (typewriter effect).
    
    Emits text_updated signal with progressively longer text chunks.
    Emits animation_complete when all text is revealed.
    
    Example:
        animator = TypingAnimator(speed_ms=50)
        animator.text_updated.connect(label.setText)
        animator.animation_complete.connect(on_done)
        animator.start_animation("Hello, I'm Nexa!")
    """
    
    # Signals
    text_updated = Signal(str)  # Emitted with current visible text
    animation_complete = Signal()  # Emitted when animation finishes
    
    def __init__(self, speed_ms: int = 50, parent=None):
        """
        Initialize typing animator.
        
        Args:
            speed_ms: Milliseconds per character (default 50ms = 20 chars/second)
            parent: Parent QObject
        """
        super().__init__(parent)
        
        self.speed_ms = speed_ms
        self.full_text = ""
        self.current_index = 0
        self.is_animating = False
        
        # Timer for character reveals
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._reveal_next_character)
    
    def start_animation(self, text: str) -> None:
        """
        Start typewriter animation for given text.
        
        Args:
            text: Full text to animate
        """
        # Stop any existing animation
        self.stop_animation()
        
        # Reset state
        self.full_text = text
        self.current_index = 0
        self.is_animating = True
        
        # Start timer
        self.timer.start(self.speed_ms)
    
    def stop_animation(self) -> None:
        """Stop animation and reset state."""
        self.timer.stop()
        self.is_animating = False
        self.current_index = 0
        self.full_text = ""
    
    def skip_to_end(self) -> None:
        """
        Skip animation and show full text immediately.
        Useful when user clicks to skip.
        """
        if not self.is_animating:
            return
        
        self.timer.stop()
        self.current_index = len(self.full_text)
        self.text_updated.emit(self.full_text)
        self.animation_complete.emit()
        self.is_animating = False
    
    def set_speed(self, speed_ms: int) -> None:
        """
        Change animation speed.
        
        Args:
            speed_ms: New milliseconds per character
        """
        self.speed_ms = speed_ms
        
        # Update timer if currently animating
        if self.is_animating:
            self.timer.setInterval(speed_ms)
    
    def is_running(self) -> bool:
        """Check if animation is currently running."""
        return self.is_animating
    
    def _reveal_next_character(self) -> None:
        """
        Internal method: Reveal next character in sequence.
        Called by timer on each interval.
        """
        if self.current_index < len(self.full_text):
            # Reveal one more character
            self.current_index += 1
            visible_text = self.full_text[:self.current_index]
            self.text_updated.emit(visible_text)
        else:
            # Animation complete
            self.timer.stop()
            self.is_animating = False
            self.animation_complete.emit()
    
    def get_progress(self) -> float:
        """
        Get animation progress as percentage.
        
        Returns:
            Float between 0.0 and 1.0
        """
        if not self.full_text:
            return 0.0
        return self.current_index / len(self.full_text)
    
    def get_remaining_time_ms(self) -> int:
        """
        Estimate remaining animation time in milliseconds.
        
        Returns:
            Estimated time remaining
        """
        if not self.is_animating:
            return 0
        
        remaining_chars = len(self.full_text) - self.current_index
        return remaining_chars * self.speed_ms
