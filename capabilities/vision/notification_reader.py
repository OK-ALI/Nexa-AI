"""
Notification Reader - Read Windows Notifications
Uses mouse controller to open Action Center and Gemini Vision to read notifications.
Reuses Phase 3.5 technology (mouse + screen reader).
"""

import logging
import time
import pyautogui
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


class NotificationReader:
    """Reads Windows notifications using mouse + Gemini Vision."""
    
    def __init__(self, screen_reader, mouse_controller):
        """
        Initialize Notification Reader.
        
        Args:
            screen_reader: ScreenReader instance (Phase 3.5)
            mouse_controller: MouseController instance (Phase 3.5)
        """
        self.screen_reader = screen_reader
        self.mouse = mouse_controller
        logger.info("Notification Reader initialized")
    
    def get_notification_center_position(self) -> tuple:
        """
        Get the position of notification icon (bottom-right corner).
        
        Returns:
            (x, y) coordinates of notification icon
        """
        screen_width, screen_height = pyautogui.size()
        
        # Notification icon is typically at bottom-right
        # Windows 11: ~30-40px from right edge, ~10-15px from bottom
        # Adding some margin for safety
        x = screen_width - 35
        y = screen_height - 12
        
        logger.info(f"Notification icon position: ({x}, {y})")
        return (x, y)
    
    def open_notification_center(self) -> bool:
        """
        Open Windows Action Center by clicking notification icon.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Opening notification center...")
            
            # Get notification icon position
            x, y = self.get_notification_center_position()
            
            # Click notification icon
            self.mouse.click(x, y)
            
            # Wait for Action Center to open
            time.sleep(1.5)
            
            logger.info("✅ Notification center opened")
            return True
            
        except Exception as e:
            logger.error(f"Error opening notification center: {e}")
            return False
    
    def close_notification_center(self) -> bool:
        """
        Close Windows Action Center.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info("Closing notification center...")
            
            # Method 1: Press Escape key
            pyautogui.press('escape')
            
            # Wait for Action Center to close
            time.sleep(0.5)
            
            logger.info("✅ Notification center closed")
            return True
            
        except Exception as e:
            logger.error(f"Error closing notification center: {e}")
            return False
    
    def read_notifications(self) -> Dict[str, any]:
        """
        Read notifications from Action Center using Gemini Vision.
        
        Returns:
            Dictionary with:
            {
                'success': bool,
                'notification_text': str,
                'notification_count': int,
                'raw_text': str
            }
        """
        try:
            logger.info("📱 Reading notifications...")
            
            # Check if vision model is available (removed in Phase 24)
            if not hasattr(self.screen_reader, 'vision_model') or self.screen_reader.vision_model is None:
                logger.warning("Vision model not available — notification reading disabled")
                return {
                    'success': False,
                    'notification_text': "Notification reading is currently unavailable (vision model not loaded)",
                    'notification_count': 0,
                    'raw_text': ''
                }
            
            # Step 1: Open notification center
            if not self.open_notification_center():
                return {
                    'success': False,
                    'notification_text': "Failed to open notification center",
                    'notification_count': 0,
                    'raw_text': ''
                }
            
            # Step 2: Take screenshot and analyze with Gemini Vision
            logger.info("📸 Capturing notification center...")
            screenshot = self.screen_reader.capture_screen()
            
            # Step 3: Use Gemini Vision to read notifications
            logger.info("🤖 Analyzing notifications with AI...")
            
            # Custom prompt for notification reading
            prompt = """
            Analyze this Windows Action Center screenshot and extract notifications.
            
            Focus on the notification panel (right side of screen).
            List each notification with:
            1. App name (e.g., "Outlook", "Discord", "Teams")
            2. Notification title/subject
            3. Brief message content
            4. Time if visible
            
            Format as:
            "You have X notifications:
            1. [App]: [Title] - [Message]
            2. [App]: [Title] - [Message]
            ..."
            
            If no notifications, say: "No new notifications"
            If notification center is not visible, say: "Cannot see notification center"
            """
            
            # Generate response using Gemini Vision
            import PIL.Image
            import io
            
            # Convert screenshot to PIL Image
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)
            pil_image = PIL.Image.open(img_byte_arr)
            
            # Call Gemini Vision
            response = self.screen_reader.vision_model.generate_content([prompt, pil_image])
            notification_text = response.text.strip()
            
            # Count notifications (rough estimate)
            notification_count = notification_text.lower().count('notification')
            if 'no new notifications' in notification_text.lower():
                notification_count = 0
            
            logger.info(f"✅ Found {notification_count} notification(s)")
            
            # Step 4: Close notification center
            self.close_notification_center()
            
            return {
                'success': True,
                'notification_text': notification_text,
                'notification_count': notification_count,
                'raw_text': notification_text
            }
            
        except Exception as e:
            logger.error(f"Error reading notifications: {e}")
            
            # Try to close notification center even if error occurred
            try:
                self.close_notification_center()
            except:
                pass
            
            return {
                'success': False,
                'notification_text': f"Error reading notifications: {str(e)}",
                'notification_count': 0,
                'raw_text': ''
            }
    
    def get_notification_summary(self) -> str:
        """
        Get a simple summary of notifications for voice response.
        
        Returns:
            Simple notification summary string
        """
        result = self.read_notifications()
        
        if result['success']:
            return result['notification_text']
        else:
            return "I couldn't read your notifications right now"
    
    def has_notifications(self) -> bool:
        """
        Quick check if there are any notifications.
        
        Returns:
            True if notifications exist, False otherwise
        """
        result = self.read_notifications()
        return result['success'] and result['notification_count'] > 0
