"""
Screenshot Manager - Screen Capture Functionality
Captures screenshots on voice command, saves to organized folder structure.
Phase 5 - Isolated module, no conflicts with existing features.
"""

import logging
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Tuple
import pyautogui
from PIL import Image
import io
from .natural_responses import NaturalResponses

logger = logging.getLogger(__name__)


class ScreenshotManager:
    """Manages screenshot capture and saving."""
    
    def __init__(self, config):
        """
        Initialize Screenshot Manager.
        
        Args:
            config: Configuration object
        """
        self.config = config
        
        # Setup screenshot directory (Pictures/Nexa Screenshots)
        self.screenshots_dir = self._setup_screenshots_directory()
        
        logger.info(f"Screenshot Manager initialized (saves to: {self.screenshots_dir})")
    
    def _setup_screenshots_directory(self) -> Path:
        """
        Setup screenshots directory in user's Pictures folder.
        
        Returns:
            Path to screenshots directory
        """
        try:
            # Get user's Pictures folder
            pictures_folder = Path.home() / "Pictures"
            
            # Create Nexa Screenshots subfolder
            screenshots_dir = pictures_folder / "Nexa Screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            logger.info(f"Screenshots directory: {screenshots_dir}")
            return screenshots_dir
            
        except Exception as e:
            logger.error(f"Error creating screenshots directory: {e}")
            # Fallback to config's data directory
            if hasattr(self.config, 'data_dir'):
                fallback_dir = self.config.data_dir / "screenshots"
            else:
                fallback_dir = Path("data/screenshots")
            fallback_dir.mkdir(parents=True, exist_ok=True)
            return fallback_dir
    
    def _sanitize_filename(self, name: str) -> str:
        """
        Sanitize a filename by removing invalid characters.
        
        Args:
            name: Raw filename
            
        Returns:
            Sanitized filename safe for Windows/Linux/Mac
        """
        # Replace invalid characters with underscores
        invalid_chars = '<>:"/\\|?*'
        sanitized = name
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '_')
        
        # Replace spaces with underscores
        sanitized = sanitized.replace(' ', '_')
        
        # Remove leading/trailing dots and spaces
        sanitized = sanitized.strip('. ')
        
        # Limit length to 100 characters (safe for most filesystems)
        if len(sanitized) > 100:
            sanitized = sanitized[:100]
        
        # If empty after sanitization, use default
        if not sanitized:
            sanitized = "screenshot"
        
        logger.debug(f"Sanitized filename: '{name}' -> '{sanitized}'")
        return sanitized
    
    def take_screenshot(self, save_to_clipboard: bool = False, custom_name: Optional[str] = None) -> Tuple[bool, str, Optional[Path]]:
        """
        Take a screenshot of the entire screen.
        
        Args:
            save_to_clipboard: If True, also copy to clipboard
            custom_name: Optional custom filename (without extension). If None, uses timestamp.
            
        Returns:
            Tuple of (success: bool, message: str, file_path: Optional[Path])
        """
        try:
            logger.info("📸 Taking screenshot...")
            
            # Capture screen using PyAutoGUI
            screenshot = pyautogui.screenshot()
            
            # Generate filename - use custom name or timestamp
            if custom_name:
                # Sanitize custom name (remove invalid characters)
                safe_name = self._sanitize_filename(custom_name)
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"{safe_name}_{timestamp}.png"
                logger.info(f"📝 Using custom filename: {filename}")
            else:
                # Use default timestamp-based name
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                filename = f"nexa_screenshot_{timestamp}.png"
            
            file_path = self.screenshots_dir / filename
            
            # Save screenshot
            screenshot.save(file_path, format='PNG')
            logger.info(f"✅ Screenshot saved: {file_path}")
            
            # Copy to clipboard if requested
            if save_to_clipboard:
                self._copy_to_clipboard(screenshot)
                if custom_name:
                    return True, f"Screenshot '{safe_name}' saved and copied to clipboard", file_path
                else:
                    return True, NaturalResponses.screenshot_clipboard(), file_path
            else:
                if custom_name:
                    return True, f"Screenshot saved as '{safe_name}'", file_path
                else:
                    return True, NaturalResponses.screenshot_taken(), file_path
            
        except Exception as e:
            logger.error(f"❌ Failed to take screenshot: {e}")
            return False, NaturalResponses.error(), None
    
    def take_screenshot_region(self, x: int, y: int, width: int, height: int, 
                               save_to_clipboard: bool = False) -> Tuple[bool, str, Optional[Path]]:
        """
        Take a screenshot of a specific screen region.
        
        Args:
            x: Left coordinate
            y: Top coordinate
            width: Width of region
            height: Height of region
            save_to_clipboard: If True, also copy to clipboard
            
        Returns:
            Tuple of (success: bool, message: str, file_path: Optional[Path])
        """
        try:
            logger.info(f"📸 Taking region screenshot: ({x}, {y}, {width}, {height})")
            
            # Capture region using PyAutoGUI
            screenshot = pyautogui.screenshot(region=(x, y, width, height))
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"nexa_screenshot_region_{timestamp}.png"
            file_path = self.screenshots_dir / filename
            
            # Save screenshot
            screenshot.save(file_path, format='PNG')
            logger.info(f"✅ Region screenshot saved: {file_path}")
            
            # Copy to clipboard if requested
            if save_to_clipboard:
                self._copy_to_clipboard(screenshot)
                message = f"Region screenshot saved and copied to clipboard: {file_path.name}"
            else:
                message = f"Region screenshot saved: {file_path.name}"
            
            return True, message, file_path
            
        except Exception as e:
            error_msg = f"Failed to take region screenshot: {str(e)}"
            logger.error(f"❌ {error_msg}")
            return False, error_msg, None
    
    def _copy_to_clipboard(self, image: Image.Image):
        """
        Copy image to system clipboard (Windows only).
        
        Args:
            image: PIL Image to copy
        """
        try:
            import win32clipboard
            from io import BytesIO
            
            # Convert to DIB format for Windows clipboard
            output = BytesIO()
            image.convert("RGB").save(output, "BMP")
            data = output.getvalue()[14:]  # Skip BMP file header
            output.close()
            
            # Copy to clipboard
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, data)
            win32clipboard.CloseClipboard()
            
            logger.info("✅ Screenshot copied to clipboard")
            
        except ImportError:
            logger.warning("win32clipboard not available - clipboard copy skipped")
        except Exception as e:
            logger.warning(f"Failed to copy to clipboard: {e}")
    
    def get_screenshots_directory(self) -> Path:
        """
        Get the screenshots directory path.
        
        Returns:
            Path to screenshots directory
        """
        return self.screenshots_dir
    
    def list_recent_screenshots(self, limit: int = 10) -> list:
        """
        List recent screenshots.
        
        Args:
            limit: Maximum number of screenshots to return
            
        Returns:
            List of screenshot file paths (most recent first)
        """
        try:
            # Get all PNG files in screenshots directory
            screenshots = sorted(
                self.screenshots_dir.glob("nexa_screenshot_*.png"),
                key=lambda p: p.stat().st_mtime,
                reverse=True
            )
            
            return screenshots[:limit]
            
        except Exception as e:
            logger.error(f"Error listing screenshots: {e}")
            return []
    
    def open_screenshots_folder(self) -> bool:
        """
        Open screenshots folder in File Explorer.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import os
            os.startfile(self.screenshots_dir)
            logger.info(f"✅ Opened screenshots folder: {self.screenshots_dir}")
            return True
        except Exception as e:
            logger.error(f"Failed to open screenshots folder: {e}")
            return False
    
    def get_screenshot_count(self) -> int:
        """
        Get total number of screenshots.
        
        Returns:
            Number of screenshots
        """
        try:
            return len(list(self.screenshots_dir.glob("nexa_screenshot_*.png")))
        except Exception as e:
            logger.error(f"Error counting screenshots: {e}")
            return 0
