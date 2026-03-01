"""
Screen Controller - Screen Operations and Vision

Handles screen reading, screenshots, and visual interactions.
Uses ScreenReader for vision and ScreenshotManager for captures.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ScreenController:
    """
    Controller for screen-related operations.
    
    Handles:
    - Taking screenshots
    - Reading screen content (OCR/Vision)
    - Finding text on screen
    - Describing screen content
    """
    
    def __init__(self, screen_reader=None, screenshot_manager=None, mouse_controller=None):
        """
        Initialize Screen Controller.
        
        Args:
            screen_reader: ScreenReader instance for vision
            screenshot_manager: ScreenshotManager instance for captures
            mouse_controller: MouseController for text selection
        """
        self.screen_reader = screen_reader
        self.screenshot_manager = screenshot_manager
        self.mouse = mouse_controller
        
        # Track last screenshot for smart sharing
        self.last_screenshot: Optional[Path] = None
        
        logger.info("📸 Screen Controller initialized")
    
    # =========================================================================
    # Screenshots
    # =========================================================================
    
    def take_screenshot(self, copy_to_clipboard: bool = False) -> Dict[str, Any]:
        """
        Take a screenshot of the entire screen.
        
        Args:
            copy_to_clipboard: If True, also copy to clipboard
            
        Returns:
            Dict with 'success', 'message', and 'file_path' keys
        """
        try:
            logger.info("Taking screenshot...")
            
            if not self.screenshot_manager:
                return {
                    'success': False,
                    'message': "Screenshot manager not available"
                }
            
            success, message, file_path = self.screenshot_manager.take_screenshot(
                save_to_clipboard=copy_to_clipboard
            )
            
            if success and file_path:
                self.last_screenshot = Path(file_path)
                logger.info(f"✅ Screenshot captured: {file_path}")
            
            return {
                'success': success,
                'message': message,
                'file_path': file_path
            }
                
        except Exception as e:
            error_msg = f"Error taking screenshot: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}
    
    def open_screenshots_folder(self) -> Dict[str, Any]:
        """
        Open the screenshots folder in File Explorer.
        
        Returns:
            Dict with 'success' and 'message' keys
        """
        try:
            if not self.screenshot_manager:
                return {'success': False, 'message': "Screenshot manager not available"}
            
            success = self.screenshot_manager.open_screenshots_folder()
            
            return {
                'success': success,
                'message': "Opening screenshots folder" if success else "Failed to open screenshots folder"
            }
        except Exception as e:
            error_msg = f"Error opening screenshots folder: {str(e)}"
            logger.error(error_msg)
            return {'success': False, 'message': error_msg}
    
    def get_screenshot_count(self) -> int:
        """
        Get the number of screenshots taken.
        
        Returns:
            Number of screenshots
        """
        try:
            if self.screenshot_manager:
                return self.screenshot_manager.get_screenshot_count()
            return 0
        except Exception as e:
            logger.error(f"Error counting screenshots: {e}")
            return 0
    
    def get_last_screenshot(self) -> Optional[Path]:
        """Get the path to the last screenshot taken."""
        return self.last_screenshot
    
    # =========================================================================
    # Screen Reading (Vision)
    # =========================================================================
    
    def read_screen_content(self, active_window_only: bool = True) -> Optional[str]:
        """
        Read all text visible on screen using Vision.
        
        Args:
            active_window_only: If True, only read the active window
            
        Returns:
            All visible text or None
        """
        try:
            if not self.screen_reader:
                logger.warning("Screen reader not available")
                return None
            
            logger.info("📄 Reading screen content")
            content = self.screen_reader.read_screen_content(active_window_only=active_window_only)
            return content
                
        except Exception as e:
            logger.error(f"Error reading screen: {e}")
            return None
    
    def describe_screen(self, active_window_only: bool = True) -> Optional[str]:
        """
        Get AI description of what's on screen.
        
        Args:
            active_window_only: If True, only describe the active window
            
        Returns:
            Natural language description or None
        """
        try:
            if not self.screen_reader:
                logger.warning("Screen reader not available")
                return None
            
            logger.info("🖼️ Describing screen")
            description = self.screen_reader.describe_screen(active_window_only=active_window_only)
            return description
                
        except Exception as e:
            logger.error(f"Error describing screen: {e}")
            return None
    
    # =========================================================================
    # Smart Text Selection (Vision + Mouse)
    # =========================================================================
    
    def find_and_select_text(self, query: str) -> Dict[str, Any]:
        """
        Find text on screen using Vision and select it.
        
        Args:
            query: Natural language query (e.g., "find the email", "locate word hello")
            
        Returns:
            Dict with 'success', 'message', and 'text' keys
        """
        try:
            if not self.screen_reader or not self.mouse:
                return {'success': False, 'message': "Screen reader or mouse controller not available"}
            
            logger.info(f"🔍 Finding and selecting: {query}")
            
            # Find text using Vision
            result = self.screen_reader.find_text_on_screen(query, active_window_only=True)
            
            if not result:
                return {'success': False, 'message': f"Could not find '{query}' on screen"}
            
            # Select the text
            success = self.mouse.select_text_region(
                result['x'], 
                result['y'], 
                result['width'], 
                result['height']
            )
            
            if success:
                return {'success': True, 'text': result['text'], 'message': f"Selected '{result['text']}'"}
            else:
                return {'success': False, 'text': result['text'], 'message': f"Found '{result['text']}' but failed to select it"}
                
        except Exception as e:
            logger.error(f"Error in find_and_select_text: {e}")
            return {'success': False, 'message': str(e)}
    
    def find_and_copy_text(self, query: str) -> Dict[str, Any]:
        """
        Find text on screen and copy it to clipboard.
        
        Args:
            query: Natural language query
            
        Returns:
            Dict with 'success', 'message', and 'text' keys
        """
        try:
            if not self.screen_reader or not self.mouse:
                return {'success': False, 'message': "Screen reader or mouse controller not available"}
            
            logger.info(f"🔍 Finding and copying: {query}")
            
            # Find text
            result = self.screen_reader.find_text_on_screen(query, active_window_only=True)
            
            if not result:
                return {'success': False, 'message': f"Could not find '{query}' on screen"}
            
            # Select the text
            if self.mouse.select_text_region(result['x'], result['y'], result['width'], result['height']):
                # Copy it
                import time
                time.sleep(0.2)  # Wait for selection
                self.mouse.copy_selection()
                return {'success': True, 'text': result['text'], 'message': f"Copied '{result['text']}' to clipboard"}
            else:
                return {'success': False, 'text': result['text'], 'message': f"Found '{result['text']}' but failed to copy it"}
                
        except Exception as e:
            logger.error(f"Error in find_and_copy_text: {e}")
            return {'success': False, 'message': str(e)}
    
    def find_and_delete_text(self, query: str) -> Dict[str, Any]:
        """
        Find text on screen and delete it.
        
        Args:
            query: Natural language query
            
        Returns:
            Dict with 'success', 'message', and 'text' keys
        """
        try:
            if not self.screen_reader or not self.mouse:
                return {'success': False, 'message': "Screen reader or mouse controller not available"}
            
            logger.info(f"🔍 Finding and deleting: {query}")
            
            # Find text
            result = self.screen_reader.find_text_on_screen(query, active_window_only=True)
            
            if not result:
                return {'success': False, 'message': f"Could not find '{query}' on screen"}
            
            # Select the text
            if self.mouse.select_text_region(result['x'], result['y'], result['width'], result['height']):
                # Delete it
                import time
                time.sleep(0.2)  # Wait for selection
                self.mouse.delete_selection()
                return {'success': True, 'text': result['text'], 'message': f"Deleted '{result['text']}'"}
            else:
                return {'success': False, 'text': result['text'], 'message': f"Found '{result['text']}' but failed to delete it"}
                
        except Exception as e:
            logger.error(f"Error in find_and_delete_text: {e}")
            return {'success': False, 'message': str(e)}
    
    def open_screenshots_folder(self) -> bool:
        """
        Open the screenshots folder in File Explorer.
        
        Returns:
            bool: True if successful
        """
        try:
            if self.screenshot_manager:
                return self.screenshot_manager.open_screenshots_folder()
            return False
        except Exception as e:
            logger.error(f"Error opening screenshots folder: {e}")
            return False


# Singleton instance for easy access
_controller_instance: Optional[ScreenController] = None


def get_screen_controller(screen_reader=None, screenshot_manager=None, mouse_controller=None) -> ScreenController:
    """
    Get or create the singleton ScreenController instance.
    
    Args:
        screen_reader: ScreenReader instance
        screenshot_manager: ScreenshotManager instance
        mouse_controller: MouseController instance
        
    Returns:
        ScreenController instance
    """
    global _controller_instance
    if _controller_instance is None:
        _controller_instance = ScreenController(
            screen_reader=screen_reader,
            screenshot_manager=screenshot_manager,
            mouse_controller=mouse_controller
        )
    return _controller_instance
