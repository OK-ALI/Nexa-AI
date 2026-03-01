"""
Volume Controller - System Volume Management
Handles all volume-related operations: get, set, increase, decrease, mute, unmute.
Extracted from executor.py for better modularity.
"""

import logging
from typing import Optional
from ctypes import cast, POINTER

logger = logging.getLogger(__name__)


class VolumeController:
    """
    Manages system volume using Windows audio APIs.
    Provides caching for the COM interface to prevent resource leaks.
    """
    
    def __init__(self):
        """Initialize volume controller."""
        # Cache for volume interface to prevent COM resource leaks
        self._volume_interface = None
        logger.debug("VolumeController initialized")
    
    def _get_volume_interface(self):
        """
        Get Windows audio interface using COM.
        Cached to prevent resource leaks.
        
        Returns:
            IAudioEndpointVolume interface or None on error
        """
        if self._volume_interface is not None:
            return self._volume_interface
            
        try:
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            self._volume_interface = volume  # Cache for reuse
            return volume
        except Exception as e:
            logger.error(f"Failed to get volume interface: {e}")
            return None
    
    def _get_volume_value(self) -> int:
        """
        Get current volume level as integer (0-100).
        Used internally for calculations.
        
        Returns:
            Volume level as integer (0-100), or -1 on error
        """
        try:
            volume = self._get_volume_interface()
            if volume:
                current_vol = volume.GetMasterVolumeLevelScalar()
                return int(current_vol * 100)
            return -1
        except Exception as e:
            logger.error(f"Error getting volume value: {e}")
            return -1
    
    def get_current_volume(self) -> str:
        """
        Get current system volume level and mute status.
        
        Returns:
            Human-readable string with volume level and mute status
        """
        try:
            volume = self._get_volume_interface()
            if volume:
                current_vol = volume.GetMasterVolumeLevelScalar()
                is_muted = volume.GetMute()
                volume_level = int(current_vol * 100)
                
                if is_muted:
                    return f"Volume is currently muted (set to {volume_level}%)"
                else:
                    return f"Volume is at {volume_level}%"
            return "Unable to get volume level"
        except Exception as e:
            logger.error(f"Error getting volume: {e}")
            return "Error getting volume level"
    
    def set_volume(self, level: int) -> str:
        """
        Set system volume to specific level.
        
        Args:
            level: Volume level (0-100)
            
        Returns:
            Result message
        """
        from core.cognition.natural_responses import NaturalResponses
        
        try:
            level = max(0, min(100, level))  # Clamp between 0-100
            volume = self._get_volume_interface()
            
            if volume:
                volume.SetMasterVolumeLevelScalar(level / 100.0, None)
                logger.info(f"Volume set to {level}%")
                return NaturalResponses.volume_set(level)
            else:
                return "I couldn't access the volume controls"
                
        except Exception as e:
            logger.error(f"Error setting volume: {e}")
            return "Sorry, I had trouble adjusting the volume"
    
    def increase_volume(self, amount: int = 10) -> str:
        """
        Increase volume by amount.
        
        Args:
            amount: Percentage to increase (default 10)
            
        Returns:
            Result message
        """
        from core.cognition.natural_responses import NaturalResponses
        
        current_vol = self._get_volume_value()
        if current_vol == -1:
            return "I couldn't get the current volume level"
        
        new_vol = min(100, current_vol + amount)
        if new_vol == current_vol:
            return "Volume is already at maximum"
        
        self.set_volume(new_vol)
        return NaturalResponses.volume_up()
    
    def decrease_volume(self, amount: int = 10) -> str:
        """
        Decrease volume by amount.
        
        Args:
            amount: Percentage to decrease (default 10)
            
        Returns:
            Result message
        """
        from core.cognition.natural_responses import NaturalResponses
        
        current_vol = self._get_volume_value()
        if current_vol == -1:
            return "I couldn't get the current volume level"
        
        new_vol = max(0, current_vol - amount)
        if new_vol == current_vol:
            return "Volume is already at minimum"
            
        self.set_volume(new_vol)
        return NaturalResponses.volume_down()
    
    def mute_volume(self) -> str:
        """
        Mute system volume.
        
        Returns:
            Result message
        """
        from core.cognition.natural_responses import NaturalResponses
        
        try:
            volume = self._get_volume_interface()
            if volume:
                volume.SetMute(1, None)
                logger.info("Volume muted")
                return NaturalResponses.volume_mute()
            return "I couldn't access the volume controls"
        except Exception as e:
            logger.error(f"Error muting volume: {e}")
            return NaturalResponses.error()
    
    def unmute_volume(self) -> str:
        """
        Unmute system volume.
        
        Returns:
            Result message
        """
        from core.cognition.natural_responses import NaturalResponses
        
        try:
            volume = self._get_volume_interface()
            if volume:
                volume.SetMute(0, None)
                logger.info("Volume unmuted")
                return NaturalResponses.volume_unmute()
            return "I couldn't access the volume controls"
        except Exception as e:
            logger.error(f"Error unmuting volume: {e}")
            return NaturalResponses.error()
    
    def toggle_mute(self) -> str:
        """
        Toggle mute status.
        
        Returns:
            Result message
        """
        try:
            volume = self._get_volume_interface()
            if volume:
                is_muted = volume.GetMute()
                if is_muted:
                    return self.unmute_volume()
                else:
                    return self.mute_volume()
            return "I couldn't access the volume controls"
        except Exception as e:
            logger.error(f"Error toggling mute: {e}")
            from core.cognition.natural_responses import NaturalResponses
            return NaturalResponses.error()
