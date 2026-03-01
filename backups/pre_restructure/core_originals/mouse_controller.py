"""
Mouse Controller - Precise Mouse and Keyboard Control
Handles text selection, clicking, and keyboard shortcuts.
"""

import logging
import time
from typing import Optional, Tuple
import pyautogui

logger = logging.getLogger(__name__)


class MouseController:
    """
    Controls mouse and keyboard for text selection and manipulation.
    Uses PyAutoGUI for cross-platform compatibility.
    """
    
    def __init__(self):
        """Initialize mouse controller."""
        # Configure PyAutoGUI
        pyautogui.PAUSE = 0.1  # Small pause between actions (100ms)
        pyautogui.FAILSAFE = True  # Move mouse to corner to abort
        
        # Get screen size
        self.screen_width, self.screen_height = pyautogui.size()
        
        logger.info(f"Mouse Controller initialized (Screen: {self.screen_width}x{self.screen_height})")
    
    def click(self, x: int, y: int, button: str = 'left', clicks: int = 1) -> bool:
        """
        Click at specific coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            button: 'left', 'right', or 'middle'
            clicks: Number of clicks (1=single, 2=double, 3=triple)
            
        Returns:
            True if successful
        """
        try:
            # Validate coordinates
            if not self._validate_coordinates(x, y):
                logger.error(f"Invalid coordinates: ({x}, {y})")
                return False
            
            # Perform click
            pyautogui.click(x, y, clicks=clicks, button=button)
            logger.info(f"Clicked at ({x}, {y}) - {button} button x{clicks}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to click: {e}")
            return False
    
    def double_click(self, x: int, y: int) -> bool:
        """
        Double-click at coordinates (selects word).
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if successful
        """
        return self.click(x, y, clicks=2)
    
    def triple_click(self, x: int, y: int) -> bool:
        """
        Triple-click at coordinates (selects line/paragraph).
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if successful
        """
        return self.click(x, y, clicks=3)
    
    def select_text_region(self, x: int, y: int, width: int, height: int) -> bool:
        """
        Select text by clicking and dragging.
        
        Args:
            x: Start X coordinate (center of text)
            y: Start Y coordinate (center of text)
            width: Text width in pixels
            height: Text height in pixels
            
        Returns:
            True if successful
        """
        try:
            # Calculate start and end points
            start_x = x - (width // 2)
            start_y = y
            end_x = x + (width // 2)
            end_y = y
            
            # Validate coordinates
            if not self._validate_coordinates(start_x, start_y):
                logger.error(f"Invalid start coordinates: ({start_x}, {start_y})")
                return False
            
            if not self._validate_coordinates(end_x, end_y):
                logger.error(f"Invalid end coordinates: ({end_x}, {end_y})")
                return False
            
            # Click and drag to select
            logger.info(f"Selecting text from ({start_x}, {start_y}) to ({end_x}, {end_y})")
            
            # Move to start position
            pyautogui.moveTo(start_x, start_y, duration=0.2)
            
            # Click and drag to end position
            pyautogui.drag(width, 0, duration=0.3, button='left')
            
            logger.info("✅ Text region selected")
            return True
            
        except Exception as e:
            logger.error(f"Failed to select text region: {e}")
            return False
    
    def select_word_at(self, x: int, y: int) -> bool:
        """
        Select word at coordinates using double-click.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Selecting word at ({x}, {y})")
            return self.double_click(x, y)
            
        except Exception as e:
            logger.error(f"Failed to select word: {e}")
            return False
    
    def select_line_at(self, x: int, y: int) -> bool:
        """
        Select line at coordinates using triple-click.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if successful
        """
        try:
            logger.info(f"Selecting line at ({x}, {y})")
            return self.triple_click(x, y)
            
        except Exception as e:
            logger.error(f"Failed to select line: {e}")
            return False
    
    def select_all(self) -> bool:
        """
        Select all text using Ctrl+A (ENHANCED with delay).
        
        Returns:
            True if successful
        """
        try:
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.1)  # Wait for selection to complete
            logger.info("Selected all text (Ctrl+A)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to select all: {e}")
            return False
    
    def copy_selection(self) -> bool:
        """
        Copy selected text using Ctrl+C.
        
        Returns:
            True if successful
        """
        try:
            pyautogui.hotkey('ctrl', 'c')
            time.sleep(0.1)  # Wait for clipboard
            logger.info("Copied selection (Ctrl+C)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to copy: {e}")
            return False
    
    def cut_selection(self) -> bool:
        """
        Cut selected text using Ctrl+X.
        
        Returns:
            True if successful
        """
        try:
            pyautogui.hotkey('ctrl', 'x')
            time.sleep(0.1)  # Wait for clipboard
            logger.info("Cut selection (Ctrl+X)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cut: {e}")
            return False
    
    def paste(self) -> bool:
        """
        Paste clipboard content using Ctrl+V.
        
        Returns:
            True if successful
        """
        try:
            pyautogui.hotkey('ctrl', 'v')
            logger.info("Pasted (Ctrl+V)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to paste: {e}")
            return False
    
    def delete_selection(self) -> bool:
        """
        Delete selected text using Delete key.
        
        Returns:
            True if successful
        """
        try:
            pyautogui.press('delete')
            logger.info("Deleted selection (Delete key)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete: {e}")
            return False
    
    def type_text(self, text: str, interval: float = 0.05) -> bool:
        """
        Type text at current cursor position.
        
        Args:
            text: Text to type
            interval: Delay between keystrokes (seconds)
            
        Returns:
            True if successful
        """
        try:
            pyautogui.write(text, interval=interval)
            logger.info(f"Typed: {text[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"Failed to type text: {e}")
            return False
    
    def move_to(self, x: int, y: int, duration: float = 0.2) -> bool:
        """
        Move mouse to coordinates.
        
        Args:
            x: X coordinate
            y: Y coordinate
            duration: Time to move (seconds)
            
        Returns:
            True if successful
        """
        try:
            if not self._validate_coordinates(x, y):
                return False
            
            pyautogui.moveTo(x, y, duration=duration)
            return True
            
        except Exception as e:
            logger.error(f"Failed to move mouse: {e}")
            return False
    
    def get_mouse_position(self) -> Tuple[int, int]:
        """
        Get current mouse position.
        
        Returns:
            (x, y) tuple
        """
        return pyautogui.position()
    
    def _validate_coordinates(self, x: int, y: int) -> bool:
        """
        Validate coordinates are within screen bounds.
        
        Args:
            x: X coordinate
            y: Y coordinate
            
        Returns:
            True if valid
        """
        if x < 0 or x >= self.screen_width:
            logger.error(f"X coordinate {x} out of bounds (0-{self.screen_width})")
            return False
        
        if y < 0 or y >= self.screen_height:
            logger.error(f"Y coordinate {y} out of bounds (0-{self.screen_height})")
            return False
        
        return True


# Convenience functions
def quick_click(x: int, y: int):
    """Quick click at coordinates."""
    pyautogui.click(x, y)


def quick_select_and_copy(x: int, y: int, width: int, height: int):
    """Quick select and copy text region."""
    controller = MouseController()
    if controller.select_text_region(x, y, width, height):
        time.sleep(0.2)
        controller.copy_selection()
