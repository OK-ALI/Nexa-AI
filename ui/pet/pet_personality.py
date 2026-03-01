"""
Pet Personality Controller - Makes Nexa feel alive!

Central controller for all personality behaviors:
- Time awareness (morning/day/evening/night moods)
- Click reactions (wave, surprised, dance)
- Command reactions (celebrate success, show concern on errors)
- Idle behavior coordination

Part of P7: Personality & Idle Behaviors
"""

import logging
from datetime import datetime
from typing import Optional, TYPE_CHECKING
from enum import Enum

from PySide6.QtCore import QObject, Signal, QTimer

from .pet_idle_manager import PetIdleManager

if TYPE_CHECKING:
    from .sprite_pet_widget import SpritePetWidget
    from .pet_config import PetConfig

logger = logging.getLogger(__name__)


class TimePeriod(Enum):
    """Time periods for mood adjustments."""
    MORNING = "morning"   # 6 AM - 10 AM
    DAY = "day"           # 10 AM - 5 PM
    EVENING = "evening"   # 5 PM - 10 PM
    NIGHT = "night"       # 10 PM - 6 AM


class PetPersonality(QObject):
    """
    Controls pet personality, moods, and reactions.
    
    Makes the pet feel like a living companion by:
    - Reacting to user interactions (clicks)
    - Responding to command outcomes
    - Showing appropriate behaviors based on time of day
    - Managing idle animations
    """
    
    # Signals for state change requests
    state_change_requested = Signal(str)  # Request pet to change state
    
    # Animation durations (ms)
    WAVE_DURATION = 2500
    DANCE_DURATION = 3500
    SURPRISED_DURATION = 2000
    CELEBRATION_DURATION = 4000
    
    def __init__(self, pet_widget: 'SpritePetWidget', config: 'PetConfig'):
        """
        Initialize the personality controller.
        
        Args:
            pet_widget: The pet widget to control
            config: PetConfig instance for settings
        """
        super().__init__()
        
        self.pet = pet_widget
        self.config = config
        self.enabled = config.get('personality_enabled', True)
        self.time_aware = config.get('time_aware_mode', True)
        self.click_reactions = config.get('click_reactions', True)
        
        # Track the original state to return to
        self._previous_state = 'idle'
        self._is_reacting = False  # Prevent reaction interruptions
        
        # Return-to-idle timer
        self._return_timer = QTimer(self)
        self._return_timer.setSingleShot(True)
        self._return_timer.timeout.connect(self._return_to_previous)
        
        # Idle manager
        self.idle_manager = PetIdleManager(self)
        self._connect_idle_signals()
        
        # Apply settings
        self._apply_settings()
        
        logger.info("🎭 Pet personality controller initialized")
    
    def _connect_idle_signals(self):
        """Connect idle manager signals to state changes."""
        self.idle_manager.do_curious.connect(lambda: self.set_state('curious'))
        self.idle_manager.do_yawn.connect(lambda: self.set_state('yawn'))
        self.idle_manager.do_sleep.connect(lambda: self.set_state('sleeping'))
        self.idle_manager.do_stretch.connect(lambda: self.set_state('stretch'))
    
    def _apply_settings(self):
        """Apply settings from config."""
        # Speed multiplier
        speed = self.config.get('expression_speed', 1.0)
        self.idle_manager.speed_multiplier = speed
        
        # Idle timeout
        timeout = self.config.get('idle_timeout_minutes', 5)
        self.idle_manager.set_idle_timeout(timeout)
        
        # Enable/disable idle behaviors based on personality setting
        self.idle_manager.set_enabled(self.enabled)
    
    def start(self):
        """Start personality behaviors."""
        if not self.enabled:
            return
        
        # Do startup greeting based on time
        self._do_startup_greeting()
        
        # Start idle behaviors
        self.idle_manager.start()
        
        logger.info("🎭 Personality behaviors started")
    
    def stop(self):
        """Stop all personality behaviors."""
        self.idle_manager.stop()
        self._return_timer.stop()
        logger.info("🎭 Personality behaviors stopped")
    
    def set_enabled(self, enabled: bool):
        """Enable or disable personality system."""
        self.enabled = enabled
        self.config.set('personality_enabled', enabled)
        
        if enabled:
            self.idle_manager.set_enabled(True)
            self.idle_manager.start()
        else:
            self.idle_manager.set_enabled(False)
            self.idle_manager.stop()
        
        logger.info(f"🎭 Personality {'enabled' if enabled else 'disabled'}")
    
    def set_time_aware(self, enabled: bool):
        """Enable or disable time awareness."""
        self.time_aware = enabled
        self.config.set('time_aware_mode', enabled)
        logger.info(f"⏰ Time awareness {'enabled' if enabled else 'disabled'}")
    
    def set_click_reactions(self, enabled: bool):
        """Enable or disable click reactions."""
        self.click_reactions = enabled
        self.config.set('click_reactions', enabled)
        logger.info(f"👆 Click reactions {'enabled' if enabled else 'disabled'}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Time Awareness
    # ═══════════════════════════════════════════════════════════════════════════
    
    def get_time_period(self) -> str:
        """
        Get the current time period.
        
        Returns:
            'morning', 'day', 'evening', or 'night'
        """
        if not self.time_aware:
            return "day"  # Default to normal behavior
        
        hour = datetime.now().hour
        
        if 6 <= hour < 10:
            return "morning"
        elif 10 <= hour < 17:
            return "day"
        elif 17 <= hour < 22:
            return "evening"
        else:
            return "night"
    
    def _do_startup_greeting(self):
        """Show appropriate greeting based on time of day."""
        if not self.enabled:
            return
        
        period = self.get_time_period()
        
        if period == "morning":
            # Morning: stretch then wave
            self.set_state('stretch')
            QTimer.singleShot(2000, lambda: self.set_state('wave'))
            QTimer.singleShot(4500, lambda: self.set_state('idle'))
            logger.info("🌅 Morning greeting: stretch + wave")
        
        elif period == "night":
            # Night: sleepy yawn
            self.set_state('yawn')
            QTimer.singleShot(3000, lambda: self.set_state('idle'))
            logger.info("🌙 Night greeting: yawn")
        
        else:
            # Day/Evening: friendly wave
            self.set_state('wave')
            QTimer.singleShot(2500, lambda: self.set_state('idle'))
            logger.info("👋 Standard greeting: wave")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # State Management
    # ═══════════════════════════════════════════════════════════════════════════
    
    def set_state(self, state: str):
        """
        Request the pet to change to a specific state.
        
        Args:
            state: The state to change to
        """
        # Store previous non-reaction state
        if state not in ('wave', 'surprised', 'dance', 'yawn', 'stretch', 'curious'):
            self._previous_state = state
        
        self.state_change_requested.emit(state)
        
        # Update pet directly
        if hasattr(self.pet, 'set_state'):
            self.pet.set_state(state)
    
    def _return_to_previous(self):
        """Return to the previous state after a reaction."""
        self._is_reacting = False
        self.set_state(self._previous_state)
    
    def _do_reaction(self, state: str, duration_ms: int):
        """
        Perform a reaction animation then return to previous state.
        
        Args:
            state: The reaction state to show
            duration_ms: How long to show the reaction
        """
        if self._is_reacting:
            return  # Don't interrupt current reaction
        
        self._is_reacting = True
        self.set_state(state)
        
        self._return_timer.stop()
        self._return_timer.start(duration_ms)
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Click Reactions
    # ═══════════════════════════════════════════════════════════════════════════
    
    def on_click(self):
        """Handle single click - friendly wave."""
        if not self.enabled or not self.click_reactions:
            return
        
        self.idle_manager.reset_on_activity()
        self._do_reaction('wave', self.WAVE_DURATION)
        logger.debug("👋 Pet waves hello!")
    
    def on_double_click(self):
        """Handle double click - happy dance."""
        if not self.enabled or not self.click_reactions:
            return
        
        self.idle_manager.reset_on_activity()
        self._do_reaction('dance', self.DANCE_DURATION)
        logger.debug("💃 Pet dances!")
    
    def on_rapid_click(self):
        """Handle rapid clicks (3+) - surprised reaction."""
        if not self.enabled or not self.click_reactions:
            return
        
        self.idle_manager.reset_on_activity()
        self._do_reaction('surprised', self.SURPRISED_DURATION)
        logger.debug("😲 Pet is surprised!")
    
    def on_drag_start(self):
        """Handle when user starts dragging the pet."""
        self.idle_manager.pause()
    
    def on_drag_end(self):
        """Handle when user stops dragging the pet."""
        self.idle_manager.reset_on_activity()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Command Reactions
    # ═══════════════════════════════════════════════════════════════════════════
    
    def on_command_start(self):
        """Called when a command starts processing."""
        if not self.enabled:
            return
        
        self.idle_manager.pause()
        self.set_state('working')
        logger.debug("💼 Pet is working")
    
    def on_command_success(self):
        """Called when a command completes successfully."""
        if not self.enabled:
            return
        
        # Celebrate! veryhappy → dance → idle
        self.set_state('happy')
        QTimer.singleShot(1500, lambda: self.set_state('dance'))
        QTimer.singleShot(self.CELEBRATION_DURATION, self._on_command_complete)
        logger.debug("🎉 Pet celebrates success!")
    
    def on_command_error(self):
        """Called when a command fails."""
        if not self.enabled:
            return
        
        # Show concern: error → surprised → idle
        self.set_state('error')
        QTimer.singleShot(1500, lambda: self.set_state('surprised'))
        QTimer.singleShot(3500, self._on_command_complete)
        logger.debug("😢 Pet shows concern for error")
    
    def _on_command_complete(self):
        """Resume normal behavior after command reaction."""
        self._previous_state = 'idle'
        self.set_state('idle')
        self.idle_manager.resume()
    
    # ═══════════════════════════════════════════════════════════════════════════
    # External State Updates (from NexaBrain)
    # ═══════════════════════════════════════════════════════════════════════════
    
    def on_brain_state_change(self, state: str):
        """
        Handle state changes from NexaBrain.
        
        This is called when the AI changes state (listening, thinking, etc.)
        We use this to pause/resume idle behaviors appropriately.
        
        Args:
            state: The new brain state
        """
        if state in ('listening', 'thinking', 'executing', 'speaking'):
            # Pause idle during active states
            self.idle_manager.pause()
        elif state == 'idle':
            # Resume idle behaviors
            self.idle_manager.resume()
