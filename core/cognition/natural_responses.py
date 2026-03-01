"""
Natural Response Generator - Makes Nexa Sound More Human
Provides varied, conversational responses instead of robotic ones.
"""

import random
from typing import List


class NaturalResponses:
    """
    Generate natural, human-like responses for common actions.
    Uses randomization to avoid repetitive robot-like speech.
    """
    
    # Volume responses
    VOLUME_SET = [
        "Volume set to {level}%",
        "Alright, volume is now at {level}%",
        "Done! Set it to {level}%",
        "Volume adjusted to {level}%",
    ]
    
    VOLUME_UP = [
        "Volume up!",
        "Turned it up for you",
        "Louder now!",
        "Increased the volume",
    ]
    
    VOLUME_DOWN = [
        "Volume down!",
        "Quieter now",
        "Turned it down",
        "Decreased the volume",
    ]
    
    VOLUME_MUTE = [
        "Muted!",
        "Sound is off",
        "Muted the volume",
        "Audio muted",
    ]
    
    VOLUME_UNMUTE = [
        "Unmuted!",
        "Sound is back on",
        "Unmuted for you",
        "Audio restored",
    ]
    
    # Brightness responses
    BRIGHTNESS_SET = [
        "Brightness set to {level}%",
        "Screen brightness is now {level}%",
        "Adjusted brightness to {level}%",
        "Done! Brightness at {level}%",
    ]
    
    BRIGHTNESS_UP = [
        "Screen brighter now!",
        "Increased the brightness",
        "Brighter!",
        "Turned up the brightness",
    ]
    
    BRIGHTNESS_DOWN = [
        "Screen dimmer now",
        "Decreased the brightness",
        "Dimmed it down",
        "Lower brightness set",
    ]
    
    # Application responses
    APP_OPENED = [
        "Opening {app}",
        "{app} is starting up",
        "Launching {app} for you",
        "Here comes {app}",
    ]
    
    APP_CLOSED = [
        "Closed {app}",
        "{app} is now closed",
        "Shut down {app}",
        "Done! {app} closed",
    ]
    
    APP_NOT_RUNNING = [
        "{app} isn't running right now",
        "{app} is not open",
        "I don't see {app} running",
        "{app} is already closed",
    ]
    
    APP_NOT_FOUND = [
        "I couldn't find {app} on your computer",
        "Hmm, {app} doesn't seem to be installed",
        "I don't see {app} installed",
        "Can't locate {app}",
    ]
    
    # Window management
    WINDOW_MAXIMIZED = [
        "Maximized!",
        "Made it fullscreen",
        "Window is now maximized",
        "Fullscreen mode!",
    ]
    
    WINDOW_MINIMIZED = [
        "Minimized!",
        "Sent it to the taskbar",
        "Window minimized",
        "Hidden away",
    ]
    
    WINDOW_RESTORED = [
        "Window restored",
        "Back to normal size",
        "Restored it for you",
        "Window resized",
    ]
    
    # Screenshot responses
    SCREENSHOT_TAKEN = [
        "Screenshot saved!",
        "Got it! Screenshot captured",
        "Screenshot taken",
        "Captured the screen for you",
    ]
    
    SCREENSHOT_CLIPBOARD = [
        "Screenshot copied to clipboard!",
        "Copied to clipboard",
        "It's on your clipboard now",
        "Screenshot ready to paste",
    ]
    
    # WiFi responses
    WIFI_CONNECTED = [
        "Connected to {network}!",
        "You're now on {network}",
        "Connected! Welcome to {network}",
        "Joined {network} successfully",
    ]
    
    WIFI_DISCONNECTED = [
        "Disconnected from WiFi",
        "You're offline now",
        "WiFi disconnected",
        "Gone offline",
    ]
    
    # Battery responses  
    BATTERY_CHARGING = [
        "Battery is at {level}% and charging",
        "Currently charging - {level}%",
        "Charging! Battery at {level}%",
        "{level}% and plugged in",
    ]
    
    BATTERY_DISCHARGING = [
        "Battery is at {level}%",
        "You've got {level}% battery left",
        "{level}% remaining",
        "Battery at {level}%",
    ]
    
    # General success
    SUCCESS = [
        "Done!",
        "All set!",
        "Got it!",
        "There you go!",
    ]
    
    # General errors
    ERROR = [
        "Oops, something went wrong",
        "Hmm, I had trouble with that",
        "Sorry, that didn't work",
        "I ran into an issue",
    ]
    
    # Confirmation
    CONFIRM = [
        "Sure thing!",
        "You got it!",
        "On it!",
        "Absolutely!",
    ]
    
    # Not found
    NOT_FOUND = [
        "I couldn't find that",
        "Hmm, I don't see that",
        "That wasn't found",
        "I can't locate that",
    ]
    
    @staticmethod
    def random_response(response_list: List[str], **kwargs) -> str:
        """
        Pick a random response from list and format with parameters.
        
        Args:
            response_list: List of response templates
            **kwargs: Format parameters
            
        Returns:
            Formatted random response
        """
        template = random.choice(response_list)
        return template.format(**kwargs) if kwargs else template
    
    @classmethod
    def volume_set(cls, level: int) -> str:
        """Natural response for setting volume."""
        return cls.random_response(cls.VOLUME_SET, level=level)
    
    @classmethod
    def volume_up(cls) -> str:
        """Natural response for increasing volume."""
        return cls.random_response(cls.VOLUME_UP)
    
    @classmethod
    def volume_down(cls) -> str:
        """Natural response for decreasing volume."""
        return cls.random_response(cls.VOLUME_DOWN)
    
    @classmethod
    def volume_mute(cls) -> str:
        """Natural response for muting volume."""
        return cls.random_response(cls.VOLUME_MUTE)
    
    @classmethod
    def volume_unmute(cls) -> str:
        """Natural response for unmuting volume."""
        return cls.random_response(cls.VOLUME_UNMUTE)
    
    @classmethod
    def brightness_set(cls, level: int) -> str:
        """Natural response for setting brightness."""
        return cls.random_response(cls.BRIGHTNESS_SET, level=level)
    
    @classmethod
    def brightness_up(cls) -> str:
        """Natural response for increasing brightness."""
        return cls.random_response(cls.BRIGHTNESS_UP)
    
    @classmethod
    def brightness_down(cls) -> str:
        """Natural response for decreasing brightness."""
        return cls.random_response(cls.BRIGHTNESS_DOWN)
    
    @classmethod
    def app_opened(cls, app: str) -> str:
        """Natural response for opening an app."""
        return cls.random_response(cls.APP_OPENED, app=app)
    
    @classmethod
    def app_closed(cls, app: str) -> str:
        """Natural response for closing an app."""
        return cls.random_response(cls.APP_CLOSED, app=app)
    
    @classmethod
    def app_not_running(cls, app: str) -> str:
        """Natural response when app is not running."""
        return cls.random_response(cls.APP_NOT_RUNNING, app=app)
    
    @classmethod
    def app_not_found(cls, app: str) -> str:
        """Natural response when app is not found."""
        return cls.random_response(cls.APP_NOT_FOUND, app=app)
    
    @classmethod
    def window_maximized(cls) -> str:
        """Natural response for maximizing window."""
        return cls.random_response(cls.WINDOW_MAXIMIZED)
    
    @classmethod
    def window_minimized(cls) -> str:
        """Natural response for minimizing window."""
        return cls.random_response(cls.WINDOW_MINIMIZED)
    
    @classmethod
    def window_restored(cls) -> str:
        """Natural response for restoring window."""
        return cls.random_response(cls.WINDOW_RESTORED)
    
    @classmethod
    def screenshot_taken(cls) -> str:
        """Natural response for taking screenshot."""
        return cls.random_response(cls.SCREENSHOT_TAKEN)
    
    @classmethod
    def screenshot_clipboard(cls) -> str:
        """Natural response for screenshot to clipboard."""
        return cls.random_response(cls.SCREENSHOT_CLIPBOARD)
    
    @classmethod
    def wifi_connected(cls, network: str) -> str:
        """Natural response for connecting to WiFi."""
        return cls.random_response(cls.WIFI_CONNECTED, network=network)
    
    @classmethod
    def wifi_disconnected(cls) -> str:
        """Natural response for disconnecting WiFi."""
        return cls.random_response(cls.WIFI_DISCONNECTED)
    
    @classmethod
    def battery_status(cls, level: int, charging: bool) -> str:
        """Natural response for battery status."""
        if charging:
            return cls.random_response(cls.BATTERY_CHARGING, level=level)
        else:
            return cls.random_response(cls.BATTERY_DISCHARGING, level=level)
    
    @classmethod
    def success(cls) -> str:
        """Natural response for generic success."""
        return cls.random_response(cls.SUCCESS)
    
    @classmethod
    def error(cls) -> str:
        """Natural response for generic error."""
        return cls.random_response(cls.ERROR)
    
    @classmethod
    def confirm(cls) -> str:
        """Natural response for confirmation."""
        return cls.random_response(cls.CONFIRM)
    
    @classmethod
    def not_found(cls) -> str:
        """Natural response for not found."""
        return cls.random_response(cls.NOT_FOUND)
