"""
Battery Manager - Battery Status Detection
Provides comprehensive battery information including charge level, 
charging status, time remaining, and power alerts.
"""

import logging
import psutil
from typing import Dict, Optional
from .natural_responses import NaturalResponses

logger = logging.getLogger(__name__)


class BatteryManager:
    """Manages battery status detection and monitoring."""
    
    def __init__(self):
        """Initialize Battery Manager."""
        self.last_status = None
        logger.info("Battery Manager initialized")
    
    def get_battery_status(self) -> Dict[str, any]:
        """
        Get comprehensive battery status.
        
        Returns:
            Dictionary with battery information:
            {
                'has_battery': bool,
                'percent': int (0-100),
                'charging': bool,
                'plugged_in': bool,
                'time_left': int (seconds) or None,
                'status_text': str,
                'power_source': str
            }
        """
        try:
            battery = psutil.sensors_battery()
            
            if battery is None:
                return {
                    'has_battery': False,
                    'percent': 100,
                    'charging': False,
                    'plugged_in': True,
                    'time_left': None,
                    'status_text': "No battery detected (Desktop PC)",
                    'power_source': 'AC Power'
                }
            
            # Calculate time remaining in human-readable format
            time_left_seconds = battery.secsleft
            time_left_text = self._format_time(time_left_seconds)
            
            # Determine charging status
            is_charging = battery.power_plugged
            percent = battery.percent
            
            # Generate status text
            if is_charging:
                if percent == 100:
                    status_text = "Fully charged (100%)"
                else:
                    status_text = f"Charging: {percent}%"
                    if time_left_text:
                        status_text += f" - {time_left_text} until full"
            else:
                if percent <= 10:
                    status_text = f"⚠️ Low battery: {percent}%"
                elif percent <= 20:
                    status_text = f"Battery low: {percent}%"
                else:
                    status_text = f"On battery: {percent}%"
                
                if time_left_text:
                    status_text += f" - {time_left_text} remaining"
            
            result = {
                'has_battery': True,
                'percent': percent,
                'charging': is_charging,
                'plugged_in': is_charging,
                'time_left': time_left_seconds,
                'time_left_text': time_left_text,
                'status_text': status_text,
                'power_source': 'AC Power' if is_charging else 'Battery'
            }
            
            self.last_status = result
            return result
            
        except Exception as e:
            logger.error(f"Error getting battery status: {e}")
            return {
                'has_battery': False,
                'percent': 0,
                'charging': False,
                'plugged_in': False,
                'time_left': None,
                'status_text': f"Error: {str(e)}",
                'power_source': 'Unknown'
            }
    
    def _format_time(self, seconds: int) -> Optional[str]:
        """
        Format time in seconds to human-readable string.
        
        Args:
            seconds: Time in seconds
            
        Returns:
            Formatted string like "2 hours 15 minutes" or None
        """
        # Check for special psutil constants
        if seconds is None:
            return None
            
        if seconds == psutil.POWER_TIME_UNLIMITED or seconds < 0:
            return None
        
        if seconds == psutil.POWER_TIME_UNKNOWN or seconds == -1:
            # Windows is still calculating - provide estimated time based on percentage
            logger.debug("Time unknown from psutil, will use percentage-based estimate")
            return None
        
        # Convert seconds to hours and minutes
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            if minutes > 0:
                return f"{hours} hour{'s' if hours != 1 else ''} {minutes} minute{'s' if minutes != 1 else ''}"
            return f"{hours} hour{'s' if hours != 1 else ''}"
        elif minutes > 0:
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            return "less than a minute"
    
    def get_battery_percentage(self) -> int:
        """
        Get battery percentage only.
        
        Returns:
            Battery percentage (0-100)
        """
        status = self.get_battery_status()
        return status.get('percent', 0)
    
    def is_charging(self) -> bool:
        """
        Check if battery is currently charging.
        
        Returns:
            True if charging, False otherwise
        """
        status = self.get_battery_status()
        return status.get('charging', False)
    
    def is_low_battery(self, threshold: int = 20) -> bool:
        """
        Check if battery is below threshold.
        
        Args:
            threshold: Percentage threshold (default: 20%)
            
        Returns:
            True if battery is low, False otherwise
        """
        status = self.get_battery_status()
        if not status.get('has_battery', False):
            return False
        return status.get('percent', 100) <= threshold
    
    def get_time_remaining(self) -> Optional[str]:
        """
        Get time remaining in human-readable format.
        
        Returns:
            Time remaining string or None
        """
        status = self.get_battery_status()
        return status.get('time_left_text')
    
    def get_simple_status(self) -> str:
        """
        Get simple battery status for voice response with natural language.
        
        Returns:
            Natural language status string
        """
        status = self.get_battery_status()
        
        if not status.get('has_battery'):
            return "No battery detected. You're running on AC power."
        
        percent = status.get('percent', 0)
        charging = status.get('charging', False)
        
        return NaturalResponses.battery_status(percent, charging)
