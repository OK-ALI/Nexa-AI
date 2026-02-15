"""
Brightness Controller - Screen Brightness Management
Handles all brightness-related operations: get, set, increase, decrease.
Extracted from executor.py for better modularity.
"""

import logging
import subprocess
import platform

logger = logging.getLogger(__name__)


class BrightnessController:
    """
    Manages screen brightness using Windows WMI APIs.
    Uses PowerShell commands for brightness control.
    """
    
    def __init__(self):
        """Initialize brightness controller."""
        self.os_name = platform.system()
        logger.debug("BrightnessController initialized")
    
    def _get_brightness_value(self) -> int:
        """
        Get current brightness as numeric value.
        
        Returns:
            Brightness value (0-100) or -1 on error
        """
        try:
            if self.os_name == "Windows":
                result = subprocess.run(
                    'powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness',
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True
                )
                
                if result.returncode == 0 and result.stdout.strip():
                    return int(result.stdout.strip())
            return -1
        except Exception as e:
            logger.error(f"Error getting brightness value: {e}")
            return -1
    
    def get_current_brightness(self) -> str:
        """
        Get current screen brightness level.
        
        Returns:
            Human-readable string with brightness level
        """
        try:
            brightness_value = self._get_brightness_value()
            if brightness_value >= 0:
                return f"Screen brightness is at {brightness_value}%"
            return "Unable to get brightness level"
        except Exception as e:
            logger.error(f"Error getting brightness: {e}")
            return "Error getting brightness level"
    
    def set_brightness(self, level: int) -> str:
        """
        Set screen brightness to specific level.
        
        Args:
            level: Brightness level (0-100)
            
        Returns:
            Result message
        """
        from .natural_responses import NaturalResponses
        
        try:
            level = max(0, min(100, level))  # Clamp between 0-100
            
            if self.os_name == "Windows":
                command = f'powershell (Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})'
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=5,
                    shell=True
                )
                
                if result.returncode == 0:
                    logger.info(f"Brightness set to {level}%")
                    return NaturalResponses.brightness_set(level)
                else:
                    return "Could not change brightness. Your display might not support this feature."
            
            return "Brightness control only available on Windows"
            
        except Exception as e:
            logger.error(f"Error setting brightness: {e}")
            return NaturalResponses.error()
    
    def increase_brightness(self, amount: int = 10) -> str:
        """
        Increase brightness by amount.
        
        Args:
            amount: Percentage to increase (default 10)
            
        Returns:
            Result message
        """
        from .natural_responses import NaturalResponses
        
        current = self._get_brightness_value()
        if current == -1:
            return "I couldn't get the current brightness level"
        
        new_level = min(100, current + amount)
        if new_level == current:
            return "Brightness is already at maximum"
            
        self.set_brightness(new_level)
        return NaturalResponses.brightness_up()
    
    def decrease_brightness(self, amount: int = 10) -> str:
        """
        Decrease brightness by amount.
        
        Args:
            amount: Percentage to decrease (default 10)
            
        Returns:
            Result message
        """
        from .natural_responses import NaturalResponses
        
        current = self._get_brightness_value()
        if current == -1:
            return "I couldn't get the current brightness level"
        
        new_level = max(0, current - amount)
        if new_level == current:
            return "Brightness is already at minimum"
            
        self.set_brightness(new_level)
        return NaturalResponses.brightness_down()
