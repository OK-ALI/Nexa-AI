"""
Conditional Command Handler for Nexa AI
========================================

Handles conditional logic in user commands (if-then statements).
This module is completely isolated and can be disabled without affecting core functionality.

Features:
- Parse "if-then" statements
- Evaluate conditions (battery level, volume, etc.)
- Execute actions conditionally
- Support complex conditions (and/or logic)

Author: Nexa AI Team
Date: October 25, 2025
"""

import re
import logging
from typing import Optional, Dict, Any, Tuple

logger = logging.getLogger(__name__)


class ConditionalHandler:
    """
    Handles conditional command parsing and execution.
    
    Supports patterns like:
    - "if battery is low, close chrome"
    - "set volume to 50 if it's above 80"
    - "open chrome if it's not running"
    - "if battery below 20, increase brightness"
    """
    
    def __init__(self, executor=None):
        """
        Initialize the conditional handler.
        
        Args:
            executor: Command executor instance for evaluating conditions
        """
        self.executor = executor
        
        # Condition keywords
        self.condition_keywords = [
            'if', 'when', 'unless', 'while', 'whenever'
        ]
        
        # Comparison operators
        self.operators = {
            'is less than': '<',
            'less than': '<',
            'below': '<',
            'under': '<',
            'is greater than': '>',
            'greater than': '>',
            'above': '>',
            'over': '>',
            'equals': '==',
            'is': '==',
            'is not': '!=',
            'not': '!=',
        }
    
    def detect_conditional(self, user_text: str) -> bool:
        """
        Detect if user text contains conditional logic.
        
        Args:
            user_text: User input
            
        Returns:
            bool: True if conditional detected
        """
        text_lower = user_text.lower()
        
        # Check for conditional keywords
        for keyword in self.condition_keywords:
            if f' {keyword} ' in f' {text_lower} ':
                return True
        
        return False
    
    def parse_conditional(self, user_text: str) -> Optional[Dict[str, str]]:
        """
        Parse conditional command into condition and action parts.
        
        Supports two formats:
        1. "if [condition], [action]" or "if [condition] then [action]"
        2. "[action] if [condition]"
        
        Args:
            user_text: User input with conditional
            
        Returns:
            Dict with 'condition' and 'action' or None if parsing fails
        """
        text_lower = user_text.lower()
        
        # Format 1: "if X, do Y" or "if X then Y"
        if_match = re.search(r'\bif\s+(.+?)(?:,\s*|\s+then\s+)(.+)', text_lower)
        if if_match:
            condition = if_match.group(1).strip()
            action = if_match.group(2).strip()
            logger.info(f"📋 Parsed conditional (if-then): condition='{condition}', action='{action}'")
            return {'condition': condition, 'action': action}
        
        # Format 2: "do Y if X"
        reverse_match = re.search(r'(.+?)\s+if\s+(.+)', text_lower)
        if reverse_match:
            action = reverse_match.group(1).strip()
            condition = reverse_match.group(2).strip()
            logger.info(f"📋 Parsed conditional (reverse): condition='{condition}', action='{action}'")
            return {'condition': condition, 'action': action}
        
        # Could not parse
        logger.warning(f"⚠️ Failed to parse conditional: {user_text}")
        return None
    
    def evaluate_condition(self, condition: str) -> Tuple[bool, str]:
        """
        Evaluate a condition to determine if it's true or false.
        
        Args:
            condition: Condition string (e.g., "battery is low", "volume above 50")
            
        Returns:
            Tuple[bool, str]: (is_true, explanation)
        """
        if not self.executor:
            logger.warning("⚠️ No executor available for condition evaluation")
            return False, "Cannot evaluate condition (no executor)"
        
        condition_lower = condition.lower().strip()
        
        # Battery level conditions
        if 'battery' in condition_lower:
            return self._evaluate_battery_condition(condition_lower)
        
        # Volume conditions
        elif 'volume' in condition_lower:
            return self._evaluate_volume_condition(condition_lower)
        
        # Brightness conditions
        elif 'brightness' in condition_lower:
            return self._evaluate_brightness_condition(condition_lower)
        
        # Application running conditions
        elif 'running' in condition_lower or 'open' in condition_lower:
            return self._evaluate_app_running_condition(condition_lower)
        
        # WiFi connection conditions
        elif 'wifi' in condition_lower or 'connected' in condition_lower:
            return self._evaluate_wifi_condition(condition_lower)
        
        # Unknown condition type
        logger.warning(f"⚠️ Unknown condition type: {condition}")
        return False, f"Cannot evaluate condition: {condition}"
    
    def _evaluate_battery_condition(self, condition: str) -> Tuple[bool, str]:
        """Evaluate battery-related conditions."""
        try:
            # Get current battery level
            battery_result = self.executor.function_registry.call('get_battery_percentage', {})
            battery_match = re.search(r'(\d+)%', str(battery_result))
            
            if not battery_match:
                return False, "Could not get battery level"
            
            battery_level = int(battery_match.group(1))
            
            # Check condition type
            if 'low' in condition or 'below' in condition:
                # Default threshold: 20%
                threshold = 20
                # Extract custom threshold if specified
                threshold_match = re.search(r'below\s+(\d+)', condition)
                if threshold_match:
                    threshold = int(threshold_match.group(1))
                
                is_true = battery_level < threshold
                explanation = f"Battery is {battery_level}% (threshold: {threshold}%)"
                return is_true, explanation
            
            elif 'high' in condition or 'above' in condition:
                threshold = 80
                threshold_match = re.search(r'above\s+(\d+)', condition)
                if threshold_match:
                    threshold = int(threshold_match.group(1))
                
                is_true = battery_level > threshold
                explanation = f"Battery is {battery_level}% (threshold: {threshold}%)"
                return is_true, explanation
            
            else:
                return False, f"Unknown battery condition: {condition}"
                
        except Exception as e:
            logger.error(f"❌ Battery condition evaluation failed: {e}")
            return False, f"Error evaluating battery: {e}"
    
    def _evaluate_volume_condition(self, condition: str) -> Tuple[bool, str]:
        """Evaluate volume-related conditions."""
        try:
            # Get current volume
            volume_result = self.executor.function_registry.call('get_current_volume', {})
            volume_match = re.search(r'(\d+)%?', str(volume_result))
            
            if not volume_match:
                return False, "Could not get volume level"
            
            volume_level = int(volume_match.group(1))
            
            # Extract threshold
            threshold_match = re.search(r'(\d+)', condition)
            if not threshold_match:
                return False, "No threshold specified in volume condition"
            
            threshold = int(threshold_match.group(1))
            
            # Determine operator
            if any(op in condition for op in ['above', 'over', 'greater', '>']):
                is_true = volume_level > threshold
                explanation = f"Volume is {volume_level}% (threshold: >{threshold}%)"
            elif any(op in condition for op in ['below', 'under', 'less', '<']):
                is_true = volume_level < threshold
                explanation = f"Volume is {volume_level}% (threshold: <{threshold}%)"
            else:
                is_true = volume_level == threshold
                explanation = f"Volume is {volume_level}% (threshold: {threshold}%)"
            
            return is_true, explanation
            
        except Exception as e:
            logger.error(f"❌ Volume condition evaluation failed: {e}")
            return False, f"Error evaluating volume: {e}"
    
    def _evaluate_brightness_condition(self, condition: str) -> Tuple[bool, str]:
        """Evaluate brightness-related conditions."""
        try:
            # Get current brightness
            brightness_result = self.executor.function_registry.call('get_current_brightness', {})
            brightness_match = re.search(r'(\d+)%?', str(brightness_result))
            
            if not brightness_match:
                return False, "Could not get brightness level"
            
            brightness_level = int(brightness_match.group(1))
            
            # Extract threshold
            threshold_match = re.search(r'(\d+)', condition)
            if not threshold_match:
                # Use default thresholds
                if 'low' in condition:
                    threshold = 30
                    is_true = brightness_level < threshold
                elif 'high' in condition:
                    threshold = 70
                    is_true = brightness_level > threshold
                else:
                    return False, "No threshold specified in brightness condition"
            else:
                threshold = int(threshold_match.group(1))
                
                # Determine operator
                if any(op in condition for op in ['above', 'over', 'greater', '>']):
                    is_true = brightness_level > threshold
                elif any(op in condition for op in ['below', 'under', 'less', '<']):
                    is_true = brightness_level < threshold
                else:
                    is_true = brightness_level == threshold
            
            explanation = f"Brightness is {brightness_level}% (threshold: {threshold}%)"
            return is_true, explanation
            
        except Exception as e:
            logger.error(f"❌ Brightness condition evaluation failed: {e}")
            return False, f"Error evaluating brightness: {e}"
    
    def _evaluate_app_running_condition(self, condition: str) -> Tuple[bool, str]:
        """Evaluate application running conditions."""
        try:
            # Extract app name from condition
            # Patterns: "chrome is running", "chrome is not running", "chrome not open"
            app_match = re.search(r'(\w+)\s+(?:is\s+)?(?:not\s+)?(?:running|open)', condition)
            if not app_match:
                return False, "Could not extract app name from condition"
            
            app_name = app_match.group(1)
            
            # Check if app is running
            running_result = self.executor.function_registry.call('is_application_running', {'app_name': app_name})
            is_running = 'is running' in str(running_result).lower()
            
            # Check for negation
            is_negated = 'not' in condition or "n't" in condition
            
            if is_negated:
                is_true = not is_running
                explanation = f"{app_name} is {'not ' if not is_running else ''}running"
            else:
                is_true = is_running
                explanation = f"{app_name} is {'running' if is_running else 'not running'}"
            
            return is_true, explanation
            
        except Exception as e:
            logger.error(f"❌ App running condition evaluation failed: {e}")
            return False, f"Error checking app status: {e}"
    
    def _evaluate_wifi_condition(self, condition: str) -> Tuple[bool, str]:
        """Evaluate WiFi connection conditions."""
        try:
            # Get WiFi status
            wifi_result = self.executor.function_registry.call('get_wifi_status', {})
            is_connected = 'connected' in str(wifi_result).lower()
            
            # Check for negation
            is_negated = 'not' in condition or 'disconnected' in condition
            
            if is_negated:
                is_true = not is_connected
                explanation = f"WiFi is {'disconnected' if not is_connected else 'connected'}"
            else:
                is_true = is_connected
                explanation = f"WiFi is {'connected' if is_connected else 'disconnected'}"
            
            return is_true, explanation
            
        except Exception as e:
            logger.error(f"❌ WiFi condition evaluation failed: {e}")
            return False, f"Error checking WiFi: {e}"


# Singleton instance for easy import
conditional_handler = None


def initialize_handler(executor):
    """Initialize the conditional handler with executor."""
    global conditional_handler
    conditional_handler = ConditionalHandler(executor)
    return conditional_handler


def detect_conditional(user_text: str) -> bool:
    """Quick detection of conditional logic."""
    if conditional_handler:
        return conditional_handler.detect_conditional(user_text)
    return False


def parse_conditional(user_text: str) -> Optional[Dict[str, str]]:
    """Quick parsing of conditional command."""
    if conditional_handler:
        return conditional_handler.parse_conditional(user_text)
    return None


def evaluate_condition(condition: str) -> Tuple[bool, str]:
    """Quick evaluation of condition."""
    if conditional_handler:
        return conditional_handler.evaluate_condition(condition)
    return False, "Conditional handler not initialized"
