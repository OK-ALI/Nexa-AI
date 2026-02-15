"""
Pet Configuration Manager
Handles pet widget preferences, position persistence, and size settings.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class PetSize(Enum):
    """Pet widget size options."""
    SMALL = "small"
    MEDIUM = "medium"
    LARGE = "large"


class PetType(Enum):
    """Pet rendering type options."""
    SPRITE = "sprite"     # Animated PNG sprites (lighter, uses your custom images)
    LIVE2D = "live2d"     # Live2D model (heavier, more complex animations)


class PetConfig:
    """
    Manages configuration for Nexa Pet widget.
    Handles position persistence, size preferences, and enabled state.
    """
    
    # Size dimensions (width, height) - Reduced for tighter fit
    SIZES = {
        PetSize.SMALL: (200, 280),     # Compact (was 350x500)
        PetSize.MEDIUM: (300, 420),    # Normal (was 500x700)
        PetSize.LARGE: (400, 560),     # Large (was 650x900)
    }
    
    def __init__(self, config_dir: Path):
        """
        Initialize pet configuration.
        
        Args:
            config_dir: Directory to store pet_preferences.json
        """
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / 'pet_preferences.json'
        
        # Default preferences
        self.preferences = {
            'enabled': False,  # Pet disabled by default
            'pet_type': PetType.SPRITE.value,  # Default to sprite (lighter, your custom images!)
            'size': PetSize.MEDIUM.value,
            'position_x': None,  # None means auto-center on first launch
            'position_y': None,
            'snap_to_edges': True,  # Magnetic edge snapping enabled
            'snap_distance': 20,  # Pixels from edge to trigger snap
            'always_on_top': True,
            'show_in_taskbar': False,
            # P6 Settings
            'scale_percent': 100,  # 50-200%, replaces size presets for fine control
            'opacity': 1.0,  # 0.2-1.0
            'animations_enabled': True,
            'show_speech_bubble': True,
            'expression_speed': 1.0,  # 0.5-2.0 (slow to fast)
            # P7 Personality Settings
            'personality_enabled': True,       # Master toggle for personality system
            'time_aware_mode': True,           # Behavior changes by time of day
            'idle_timeout_minutes': 5,         # Minutes before sleep (1-10)
            'click_reactions': True,           # React to clicks (wave, dance, surprised)
            # Glow Effect
            'glow_enabled': True,              # Cyan glow around pet
            'glow_intensity': 0.6,             # 0.0-1.0 intensity (increased for visibility)
        }
        
        # Load saved preferences
        self.load()
    
    def load(self) -> bool:
        """
        Load preferences from JSON file.
        
        Returns:
            True if loaded successfully, False if using defaults
        """
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    saved_prefs = json.load(f)
                    self.preferences.update(saved_prefs)
                    logger.info(f"✅ Loaded pet preferences from {self.config_file}")
                    return True
            else:
                logger.info("No pet preferences found, using defaults")
                return False
        except Exception as e:
            logger.error(f"Failed to load pet preferences: {e}")
            return False
    
    def save(self) -> bool:
        """
        Save current preferences to JSON file.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure config directory exists
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.preferences, f, indent=4)
            
            logger.debug(f"Saved pet preferences to {self.config_file}")
            return True
        except Exception as e:
            logger.error(f"Failed to save pet preferences: {e}")
            return False
    
    def get_size_dimensions(self) -> Tuple[int, int]:
        """
        Get pixel dimensions for current size setting.
        
        Returns:
            Tuple of (width, height) in pixels
        """
        size_value = self.preferences.get('size', PetSize.MEDIUM.value)
        try:
            size_enum = PetSize(size_value)
            return self.SIZES[size_enum]
        except (ValueError, KeyError):
            logger.warning(f"Invalid size '{size_value}', using MEDIUM")
            return self.SIZES[PetSize.MEDIUM]
    
    def get_position(self) -> Tuple[int, int]:
        """
        Get saved position or None for auto-center.
        
        Returns:
            Tuple of (x, y) or (None, None) for auto-center
        """
        x = self.preferences.get('position_x')
        y = self.preferences.get('position_y')
        return (x, y)
    
    def set_position(self, x: int, y: int):
        """
        Save current position.
        
        Args:
            x: X coordinate
            y: Y coordinate
        """
        self.preferences['position_x'] = x
        self.preferences['position_y'] = y
        self.save()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get preference value.
        
        Args:
            key: Preference key
            default: Default value if key not found
        
        Returns:
            Preference value or default
        """
        return self.preferences.get(key, default)
    
    def set(self, key: str, value: Any):
        """
        Set preference value and save.
        
        Args:
            key: Preference key
            value: Value to set
        """
        self.preferences[key] = value
        self.save()
    
    def toggle_enabled(self) -> bool:
        """
        Toggle pet enabled state.
        
        Returns:
            New enabled state
        """
        current = self.preferences.get('enabled', False)
        self.set('enabled', not current)
        return not current
    
    def set_size(self, size: PetSize):
        """
        Set pet size.
        
        Args:
            size: PetSize enum value
        """
        self.set('size', size.value)
        logger.info(f"Pet size set to {size.value}")
    
    def is_enabled(self) -> bool:
        """
        Check if pet is enabled.
        
        Returns:
            True if enabled, False otherwise
        """
        return self.preferences.get('enabled', False)
    
    def should_snap_to_edges(self) -> bool:
        """
        Check if edge snapping is enabled.
        
        Returns:
            True if snap enabled, False otherwise
        """
        return self.preferences.get('snap_to_edges', True)
    
    def get_snap_distance(self) -> int:
        """
        Get snap distance in pixels.
        
        Returns:
            Snap distance threshold
        """
        return self.preferences.get('snap_distance', 20)

    def get_pet_type(self) -> PetType:
        """
        Get current pet rendering type.
        
        Returns:
            PetType enum value (SPRITE or LIVE2D)
        """
        type_value = self.preferences.get('pet_type', PetType.SPRITE.value)
        try:
            return PetType(type_value)
        except ValueError:
            logger.warning(f"Invalid pet type '{type_value}', using SPRITE")
            return PetType.SPRITE

    def set_pet_type(self, pet_type: PetType):
        """
        Set pet rendering type.
        
        Args:
            pet_type: PetType enum value
        """
        self.set('pet_type', pet_type.value)
        logger.info(f"Pet type set to {pet_type.value}")

    def get_size(self) -> PetSize:
        """
        Get current size setting as PetSize enum.
        
        Returns:
            PetSize enum value
        """
        size_value = self.preferences.get('size', PetSize.MEDIUM.value)
        try:
            return PetSize(size_value)
        except ValueError:
            logger.warning(f"Invalid size '{size_value}', using MEDIUM")
            return PetSize.MEDIUM

    def get_snap_enabled(self) -> bool:
        """
        Alias for should_snap_to_edges for compatibility.
        
        Returns:
            True if snap enabled
        """
        return self.should_snap_to_edges()
