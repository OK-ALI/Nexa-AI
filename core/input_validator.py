"""
Input Validation Module for Nexa AI
====================================

Handles edge cases and validates user input to provide helpful error messages.
This module is completely isolated and can be disabled without affecting core functionality.

Author: Nexa AI Team
Date: October 25, 2025
"""

import re
import logging
from typing import Tuple, Optional, Dict, Any

logger = logging.getLogger(__name__)


class InputValidator:
    """
    Validates user input and provides helpful error messages for edge cases.
    
    Features:
    - Empty/whitespace-only input detection
    - Excessive length detection
    - Gibberish detection (random characters, excessive repetition)
    - Semantic validation (type checking: apps vs settings)
    - Range validation (volume/brightness 0-100)
    """
    
    def __init__(self):
        """Initialize the input validator with configuration."""
        # Configuration
        self.max_input_length = 500  # Characters
        self.min_input_length = 1
        
        # Known entity types for semantic validation
        self.settings_keywords = [
            'volume', 'brightness', 'wifi', 'battery', 'bluetooth',
            'screen', 'sound', 'network', 'power', 'display'
        ]
        
        self.app_keywords = [
            'chrome', 'firefox', 'edge', 'brave', 'opera',  # Browsers
            'notepad', 'word', 'excel', 'powerpoint',  # Office
            'vscode', 'code', 'sublime', 'atom',  # Editors
            'spotify', 'vlc', 'discord', 'steam',  # Media/Games
            'explorer', 'cmd', 'terminal', 'powershell'  # System
        ]
        
        self.folder_keywords = [
            'downloads', 'documents', 'desktop', 'pictures',
            'videos', 'music', 'folder', 'directory'
        ]
    
    def validate_input(self, user_text: str) -> Tuple[bool, Optional[str]]:
        """
        Validate user input for edge cases.
        
        Args:
            user_text: Raw user input string
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
            - (True, None) if input is valid
            - (False, "error message") if input is invalid
        """
        # Validation 1: Empty or whitespace-only input
        if not user_text or not user_text.strip():
            logger.warning("⚠️ Empty input detected")
            return False, "I didn't catch that. What would you like me to do?"
        
        # Validation 2: Excessive length
        if len(user_text) > self.max_input_length:
            logger.warning(f"⚠️ Input too long: {len(user_text)} chars (max: {self.max_input_length})")
            return False, f"That command is too long ({len(user_text)} characters). Please keep it under {self.max_input_length} characters."
        
        # Validation 3: Gibberish detection (excessive special characters)
        special_char_count = len(re.findall(r'[^a-zA-Z0-9\s]', user_text))
        if special_char_count > len(user_text) * 0.5:  # More than 50% special chars
            logger.warning(f"⚠️ Gibberish detected: {special_char_count} special chars in {len(user_text)} total")
            return False, "I couldn't understand that. Please use normal words."
        
        # Validation 4: Excessive repetition (e.g., "aaaaaaaaa", "open open open")
        if self._has_excessive_repetition(user_text):
            logger.warning(f"⚠️ Excessive repetition detected: {user_text[:50]}")
            return False, "I noticed some repetition in your command. Could you rephrase that?"
        
        # All validations passed
        return True, None
    
    def _has_excessive_repetition(self, text: str) -> bool:
        """
        Detect excessive character or word repetition.
        
        Args:
            text: Input text to check
            
        Returns:
            bool: True if excessive repetition detected
        """
        # Check for character repetition (e.g., "aaaaaaa")
        char_repetition = re.search(r'(.)\1{6,}', text)  # Same char 7+ times
        if char_repetition:
            return True
        
        # Check for word repetition (e.g., "open open open open")
        words = text.lower().split()
        if len(words) >= 3:
            # Check if same word appears 3+ times consecutively
            for i in range(len(words) - 2):
                if words[i] == words[i+1] == words[i+2]:
                    return True
        
        return False
    
    def validate_semantic_type(self, action: str, target: str) -> Tuple[bool, Optional[str]]:
        """
        Validate that the action makes semantic sense with the target.
        Prevents commands like "open volume" or "set chrome to 50".
        
        Args:
            action: Action verb (open, close, set, get, etc.)
            target: Target entity (chrome, volume, etc.)
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        action_lower = action.lower()
        target_lower = target.lower()
        
        # Rule 1: Can't "open" or "launch" a setting
        if action_lower in ['open', 'launch', 'start', 'run']:
            # Exception: Folders and screenshot-related paths are okay to open
            # Use existing folder_keywords list + screenshot variants
            folder_exceptions = self.folder_keywords + ['screenshot', 'screenshots']
            is_folder = any(folder_word in target_lower for folder_word in folder_exceptions)
            
            if not is_folder and any(setting in target_lower for setting in self.settings_keywords):
                logger.warning(f"⚠️ Semantic error: trying to open setting '{target}'")
                
                # Provide helpful suggestion
                if 'volume' in target_lower or 'sound' in target_lower:
                    return False, f"You can't open {target}. Try 'get volume' or 'set volume to 50' instead."
                elif 'brightness' in target_lower:
                    return False, f"You can't open {target}. Try 'get brightness' or 'set brightness to 70' instead."
                elif 'wifi' in target_lower or 'network' in target_lower:
                    return False, f"You can't open {target}. Try 'list wifi networks' or 'get wifi status' instead."
                elif 'battery' in target_lower:
                    return False, f"You can't open {target}. Try 'get battery level' instead."
                else:
                    return False, f"You can't open {target}. It's a system setting, not an application."
        
        # Rule 2: Can't "set" an app to a value
        if action_lower in ['set', 'change', 'adjust']:
            if any(app in target_lower for app in self.app_keywords):
                logger.warning(f"⚠️ Semantic error: trying to set app '{target}'")
                return False, f"You can't set {target} to a value. Try 'open {target}' or 'close {target}' instead."
        
        # Rule 3: Can't "minimize" or "maximize" non-window entities
        if action_lower in ['minimize', 'maximize', 'close']:
            if any(setting in target_lower for setting in self.settings_keywords):
                # Exception: screenshot folders, downloads folders are okay
                if 'folder' not in target_lower and 'screenshot' not in target_lower:
                    logger.warning(f"⚠️ Semantic error: trying to {action} setting '{target}'")
                    return False, f"You can't {action} {target}. It's a system setting, not a window."
        
        # All semantic checks passed
        return True, None
    
    def validate_numeric_range(self, parameter: str, value: int) -> Tuple[bool, Optional[str]]:
        """
        Validate numeric values are within acceptable ranges.
        
        Args:
            parameter: Parameter name (volume, brightness, etc.)
            value: Numeric value to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        param_lower = parameter.lower()
        
        # Volume range: 0-100
        if 'volume' in param_lower or 'sound' in param_lower:
            if value < 0 or value > 100:
                clamped = max(0, min(100, value))
                logger.warning(f"⚠️ Volume out of range: {value} (valid: 0-100)")
                return False, f"Volume must be between 0 and 100. Did you mean {clamped}%?"
        
        # Brightness range: 0-100
        elif 'brightness' in param_lower or 'screen' in param_lower:
            if value < 0 or value > 100:
                clamped = max(0, min(100, value))
                logger.warning(f"⚠️ Brightness out of range: {value} (valid: 0-100)")
                return False, f"Brightness must be between 0 and 100. Did you mean {clamped}%?"
        
        # All range checks passed
        return True, None
    
    def validate_existence(self, entity_type: str, entity_name: str, is_running: bool = None) -> Tuple[bool, Optional[str]]:
        """
        Validate that an entity exists before performing operations on it.
        
        Args:
            entity_type: Type of entity (app, window, folder, etc.)
            entity_name: Name of the entity
            is_running: Whether the entity is currently running/available
            
        Returns:
            Tuple[bool, Optional[str]]: (is_valid, error_message)
        """
        type_lower = entity_type.lower()
        
        # If we don't know running status, we can't validate
        if is_running is None:
            return True, None
        
        # Check if app/window is running when trying to close/minimize
        if type_lower in ['app', 'window', 'application']:
            if not is_running:
                logger.warning(f"⚠️ Entity not running: {entity_name}")
                return False, f"{entity_name} is not running. Would you like to open it first?"
        
        return True, None
    
    def suggest_correction(self, user_text: str, error_type: str) -> Optional[str]:
        """
        Suggest corrections based on common mistakes.
        
        Args:
            user_text: Original user input
            error_type: Type of error detected
            
        Returns:
            Optional[str]: Suggestion for correction, or None
        """
        text_lower = user_text.lower()
        
        # Suggestion 1: "open volume" → "get volume"
        if error_type == 'semantic_open_setting':
            if 'volume' in text_lower:
                return "Try saying: 'What's the volume?' or 'Set volume to 50'"
            elif 'brightness' in text_lower:
                return "Try saying: 'What's the brightness?' or 'Set brightness to 70'"
        
        # Suggestion 2: Missing action verb
        if error_type == 'missing_action':
            # Check if user mentioned an app name without action
            for app in self.app_keywords:
                if app in text_lower:
                    return f"Try saying: 'Open {app}' or 'Close {app}'"
        
        return None


# Singleton instance for easy import
validator = InputValidator()


# Convenience functions for quick validation
def validate_input(user_text: str) -> Tuple[bool, Optional[str]]:
    """Quick validation of user input."""
    return validator.validate_input(user_text)


def validate_semantic_type(action: str, target: str) -> Tuple[bool, Optional[str]]:
    """Quick semantic validation."""
    return validator.validate_semantic_type(action, target)


def validate_numeric_range(parameter: str, value: int) -> Tuple[bool, Optional[str]]:
    """Quick numeric range validation."""
    return validator.validate_numeric_range(parameter, value)


def validate_existence(entity_type: str, entity_name: str, is_running: bool = None) -> Tuple[bool, Optional[str]]:
    """Quick existence validation."""
    return validator.validate_existence(entity_type, entity_name, is_running)
