"""
Pet Idle Manager - Handles idle behavior timing and transitions.

Manages the idle animation cycle:
- Random curious glances (30-60 seconds)
- Yawning when bored (2-3 minutes)
- Falling asleep after inactivity (5 minutes, 2 min at night)

Part of P7: Personality & Idle Behaviors
"""

import logging
import random
from typing import Optional, Callable, TYPE_CHECKING
from datetime import datetime

from PySide6.QtCore import QTimer, QObject, Signal

if TYPE_CHECKING:
    from .pet_personality import PetPersonality

logger = logging.getLogger(__name__)


class PetIdleManager(QObject):
    """
    Manages idle behavior timing and automatic state transitions.
    
    Emits signals when the pet should change to idle-related states.
    The personality controller handles the actual state changes.
    """
    
    # Signals for idle state changes
    do_curious = Signal()      # Time for a curious look
    do_yawn = Signal()         # Time to yawn
    do_sleep = Signal()        # Time to sleep
    do_stretch = Signal()      # Wake up stretch
    
    # Default timing (in milliseconds)
    CURIOUS_MIN_MS = 30000     # 30 seconds minimum
    CURIOUS_MAX_MS = 60000     # 60 seconds maximum
    YAWN_INTERVAL_MS = 150000  # 2.5 minutes (between 2-3 min)
    SLEEP_INTERVAL_MS = 300000 # 5 minutes
    NIGHT_SLEEP_INTERVAL_MS = 120000  # 2 minutes at night
    
    # State duration (how long each state displays)
    CURIOUS_DURATION_MS = 3000   # 3 seconds
    YAWN_DURATION_MS = 4000      # 4 seconds
    STRETCH_DURATION_MS = 3000   # 3 seconds
    
    def __init__(self, personality: 'PetPersonality'):
        """
        Initialize the idle manager.
        
        Args:
            personality: Parent PetPersonality controller
        """
        super().__init__()
        
        self.personality = personality
        self.enabled = True
        self.is_sleeping = False
        self.idle_minutes = 0  # Track total idle time
        
        # Speed multiplier from settings (0.5 = slow, 2.0 = fast)
        self._speed_multiplier = 1.0
        
        # Timers
        self.curious_timer = QTimer(self)
        self.curious_timer.timeout.connect(self._on_curious_timer)
        
        self.yawn_timer = QTimer(self)
        self.yawn_timer.timeout.connect(self._on_yawn_timer)
        
        self.sleep_timer = QTimer(self)
        self.sleep_timer.timeout.connect(self._on_sleep_timer)
        
        self.return_timer = QTimer(self)  # Returns to idle after animation
        self.return_timer.setSingleShot(True)
        
        logger.info("💤 Pet idle manager initialized")
    
    @property
    def speed_multiplier(self) -> float:
        """Get speed multiplier (affects timing)."""
        return self._speed_multiplier
    
    @speed_multiplier.setter
    def speed_multiplier(self, value: float):
        """Set speed multiplier and restart timers."""
        self._speed_multiplier = max(0.5, min(2.0, value))
        if self.enabled and not self.is_sleeping:
            self.restart_timers()
    
    def set_idle_timeout(self, minutes: int):
        """
        Set the idle timeout before sleeping.
        
        Args:
            minutes: Minutes before pet falls asleep (1-10)
        """
        minutes = max(1, min(10, minutes))
        self.SLEEP_INTERVAL_MS = minutes * 60 * 1000
        logger.debug(f"😴 Idle timeout set to {minutes} minutes")
    
    def start(self):
        """Start the idle behavior cycle."""
        if not self.enabled:
            return
            
        self.is_sleeping = False
        self.idle_minutes = 0
        self.restart_timers()
        logger.debug("▶️ Idle timers started")
    
    def stop(self):
        """Stop all idle timers."""
        self.curious_timer.stop()
        self.yawn_timer.stop()
        self.sleep_timer.stop()
        self.return_timer.stop()
        logger.debug("⏹️ Idle timers stopped")
    
    def restart_timers(self):
        """Restart all timers (called after activity)."""
        self.stop()
        
        if not self.enabled:
            return
        
        # Apply speed multiplier (faster = shorter intervals)
        speed = self._speed_multiplier
        
        # Random curious interval
        curious_interval = random.randint(
            int(self.CURIOUS_MIN_MS / speed),
            int(self.CURIOUS_MAX_MS / speed)
        )
        self.curious_timer.start(curious_interval)
        
        # Yawn timer
        yawn_interval = int(self.YAWN_INTERVAL_MS / speed)
        self.yawn_timer.start(yawn_interval)
        
        # Sleep timer (shorter at night)
        if self.personality.get_time_period() == "night":
            sleep_interval = int(self.NIGHT_SLEEP_INTERVAL_MS / speed)
        else:
            sleep_interval = int(self.SLEEP_INTERVAL_MS / speed)
        self.sleep_timer.start(sleep_interval)
    
    def reset_on_activity(self):
        """
        Reset all timers when user interacts with the pet.
        Called when clicking, dragging, or receiving commands.
        """
        if self.is_sleeping:
            # Wake up!
            self.is_sleeping = False
            self.do_stretch.emit()
            logger.info("🌅 Pet waking up!")
            
            # After stretch, return to idle
            try:
                self.return_timer.timeout.disconnect()
            except (RuntimeError, TypeError):
                pass
            self.return_timer.timeout.connect(lambda: self.personality.set_state('idle'))
            self.return_timer.start(self.STRETCH_DURATION_MS)
        
        self.idle_minutes = 0
        self.restart_timers()
        logger.debug("🔄 Idle timers reset on activity")
    
    def pause(self):
        """Pause idle behaviors (e.g., during commands)."""
        self.stop()
        logger.debug("⏸️ Idle behaviors paused")
    
    def resume(self):
        """Resume idle behaviors."""
        if not self.is_sleeping:
            self.restart_timers()
            logger.debug("▶️ Idle behaviors resumed")
    
    def set_enabled(self, enabled: bool):
        """Enable or disable idle behaviors."""
        self.enabled = enabled
        if enabled:
            self.restart_timers()
        else:
            self.stop()
        logger.info(f"💤 Idle behaviors {'enabled' if enabled else 'disabled'}")
    
    # ═══════════════════════════════════════════════════════════════════════════
    # Timer Callbacks
    # ═══════════════════════════════════════════════════════════════════════════
    
    def _on_curious_timer(self):
        """Called when it's time for a curious look."""
        if self.is_sleeping or not self.enabled:
            return
        
        self.do_curious.emit()
        logger.debug("👀 Pet is curious")
        
        # Return to idle after curious animation
        self.return_timer.stop()
        try:
            self.return_timer.timeout.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.return_timer.timeout.connect(lambda: self.personality.set_state('idle'))
        self.return_timer.start(self.CURIOUS_DURATION_MS)
        
        # Reschedule next curious with random interval
        speed = self._speed_multiplier
        next_interval = random.randint(
            int(self.CURIOUS_MIN_MS / speed),
            int(self.CURIOUS_MAX_MS / speed)
        )
        self.curious_timer.start(next_interval)
    
    def _on_yawn_timer(self):
        """Called when it's time to yawn."""
        if self.is_sleeping or not self.enabled:
            return
        
        # Yawn more frequently at night
        if self.personality.get_time_period() == "night":
            # 80% chance to yawn at night
            if random.random() > 0.8:
                return
        else:
            # 50% chance during day
            if random.random() > 0.5:
                return
        
        self.do_yawn.emit()
        logger.debug("😪 Pet is yawning")
        
        # Return to idle after yawn
        self.return_timer.stop()
        try:
            self.return_timer.timeout.disconnect()
        except (RuntimeError, TypeError):
            pass
        self.return_timer.timeout.connect(lambda: self.personality.set_state('idle'))
        self.return_timer.start(self.YAWN_DURATION_MS)
    
    def _on_sleep_timer(self):
        """Called when it's time to sleep."""
        if self.is_sleeping or not self.enabled:
            return
        
        self.is_sleeping = True
        self.do_sleep.emit()
        logger.info("😴 Pet is falling asleep")
        
        # Stop other timers while sleeping
        self.curious_timer.stop()
        self.yawn_timer.stop()
