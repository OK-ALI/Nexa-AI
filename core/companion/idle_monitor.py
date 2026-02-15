"""
Phase 29: Idle Monitor
======================
Tracks user interaction patterns and idle time to enable proactive engagement.

This module monitors:
- Last interaction time (voice commands, responses)
- Idle duration thresholds
- Proactive trigger conditions

All timing is configurable to avoid annoying the user.
"""

import time
import logging
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
from threading import Lock

logger = logging.getLogger(__name__)


class IdleState(Enum):
    """Current idle state of the user."""
    ACTIVE = "active"           # User interacting normally
    SHORT_IDLE = "short_idle"   # 2-5 minutes idle
    MEDIUM_IDLE = "medium_idle" # 5-15 minutes idle  
    LONG_IDLE = "long_idle"     # 15+ minutes idle
    AWAY = "away"               # 30+ minutes, likely AFK


@dataclass
class IdleConfig:
    """Configuration for idle detection thresholds."""
    # Thresholds in seconds
    short_idle_threshold: float = 30.0     # 30 seconds (reduced for better responsiveness)
    medium_idle_threshold: float = 120.0   # 2 minutes
    long_idle_threshold: float = 300.0     # 5 minutes
    away_threshold: float = 900.0          # 15 minutes
    
    # Proactive engagement settings
    min_proactive_interval: float = 60.0   # Minimum 1 min between proactive suggestions (reduced)
    max_proactive_per_hour: int = 3        # Maximum 3 suggestions per hour
    
    # Time-based restrictions
    quiet_hours_start: int = 22            # 10 PM
    quiet_hours_end: int = 8               # 8 AM
    respect_quiet_hours: bool = True


@dataclass
class IdleStats:
    """Statistics about idle patterns."""
    total_interactions: int = 0
    total_proactive_triggered: int = 0
    total_proactive_accepted: int = 0
    total_proactive_declined: int = 0
    average_idle_before_trigger: float = 0.0
    hourly_proactive_count: Dict[int, int] = field(default_factory=dict)


class IdleMonitor:
    """
    Monitors user idle time and triggers proactive engagement opportunities.
    
    This is the foundation for Phase 29's proactive engagement feature.
    It tracks when the user last interacted and determines when it's
    appropriate to make a proactive suggestion.
    """
    
    def __init__(self, config: Optional[IdleConfig] = None):
        """
        Initialize the idle monitor.
        
        Args:
            config: Optional configuration, uses defaults if not provided
        """
        self.config = config or IdleConfig()
        self.stats = IdleStats()
        self._lock = Lock()
        
        # Timing state
        self._last_interaction_time: float = time.time()
        self._last_proactive_time: float = 0.0
        self._session_start_time: float = time.time()
        
        # Callbacks
        self._on_state_change: Optional[Callable[[IdleState, IdleState], None]] = None
        self._on_proactive_opportunity: Optional[Callable[[float, IdleState], bool]] = None
        
        # Current state
        self._current_state: IdleState = IdleState.ACTIVE
        
        # Proactive tracking
        self._proactive_count_this_hour: int = 0
        self._hour_of_proactive_count: int = -1
        
        logger.info("IdleMonitor initialized with config: %s", self.config)
    
    def record_interaction(self) -> None:
        """
        Record a user interaction (voice command, response, etc.).
        
        Call this whenever the user interacts with NEXA.
        """
        with self._lock:
            self._last_interaction_time = time.time()
            self.stats.total_interactions += 1
            
            old_state = self._current_state
            self._current_state = IdleState.ACTIVE
            
            if old_state != IdleState.ACTIVE and self._on_state_change:
                self._on_state_change(old_state, IdleState.ACTIVE)
    
    def get_idle_duration(self) -> float:
        """
        Get how long the user has been idle.
        
        Returns:
            Idle duration in seconds
        """
        return time.time() - self._last_interaction_time
    
    def get_idle_state(self) -> IdleState:
        """
        Get the current idle state based on duration.
        
        Returns:
            Current IdleState enum value
        """
        duration = self.get_idle_duration()
        
        if duration >= self.config.away_threshold:
            return IdleState.AWAY
        elif duration >= self.config.long_idle_threshold:
            return IdleState.LONG_IDLE
        elif duration >= self.config.medium_idle_threshold:
            return IdleState.MEDIUM_IDLE
        elif duration >= self.config.short_idle_threshold:
            return IdleState.SHORT_IDLE
        else:
            return IdleState.ACTIVE
    
    def update_state(self) -> Optional[IdleState]:
        """
        Update the idle state and trigger callbacks if changed.
        
        Returns:
            New state if changed, None if unchanged
        """
        with self._lock:
            new_state = self.get_idle_state()
            
            if new_state != self._current_state:
                old_state = self._current_state
                self._current_state = new_state
                
                logger.debug("Idle state changed: %s -> %s", old_state.value, new_state.value)
                
                if self._on_state_change:
                    self._on_state_change(old_state, new_state)
                
                return new_state
            
            return None
    
    def can_trigger_proactive(self) -> bool:
        """
        Check if proactive engagement is allowed right now.
        
        Considers:
        - Minimum interval between suggestions
        - Maximum suggestions per hour
        - Quiet hours
        - Current idle state
        
        Returns:
            True if proactive suggestion is allowed
        """
        now = time.time()
        current_hour = time.localtime().tm_hour
        
        # Check quiet hours (10 PM to 8 AM)
        if self.config.respect_quiet_hours:
            # For overnight hours (e.g., 22:00 to 08:00), we need different logic
            if self.config.quiet_hours_start > self.config.quiet_hours_end:
                # Overnight range (e.g., 22 to 8)
                in_quiet_hours = current_hour >= self.config.quiet_hours_start or current_hour < self.config.quiet_hours_end
            else:
                # Same-day range (e.g., 8 to 22)
                in_quiet_hours = self.config.quiet_hours_start <= current_hour < self.config.quiet_hours_end
            
            if in_quiet_hours:
                logger.debug("In quiet hours (%d:00 - %d:00), proactive disabled", 
                            self.config.quiet_hours_start, self.config.quiet_hours_end)
                return False
        
        # Check minimum interval
        time_since_last_proactive = now - self._last_proactive_time
        if time_since_last_proactive < self.config.min_proactive_interval:
            logger.debug("Too soon since last proactive (%.1fs < %.1fs)",
                        time_since_last_proactive, self.config.min_proactive_interval)
            return False
        
        # Check hourly limit
        with self._lock:
            if self._hour_of_proactive_count != current_hour:
                self._hour_of_proactive_count = current_hour
                self._proactive_count_this_hour = 0
            
            if self._proactive_count_this_hour >= self.config.max_proactive_per_hour:
                logger.debug("Hourly proactive limit reached (%d/%d)",
                            self._proactive_count_this_hour, self.config.max_proactive_per_hour)
                return False
        
        # Must be at least short idle
        idle_state = self.get_idle_state()
        if idle_state == IdleState.ACTIVE:
            return False
        
        # Don't bother if user is AWAY
        if idle_state == IdleState.AWAY:
            logger.debug("User is AWAY, skipping proactive")
            return False
        
        return True
    
    def trigger_proactive_opportunity(self) -> bool:
        """
        Attempt to trigger a proactive engagement opportunity.
        
        Returns:
            True if triggered successfully, False if not allowed
        """
        if not self.can_trigger_proactive():
            return False
        
        idle_duration = self.get_idle_duration()
        idle_state = self.get_idle_state()
        
        with self._lock:
            self._last_proactive_time = time.time()
            self._proactive_count_this_hour += 1
            self.stats.total_proactive_triggered += 1
        
        logger.info("Proactive opportunity triggered after %.1fs idle (%s)",
                   idle_duration, idle_state.value)
        
        # Call callback if registered
        if self._on_proactive_opportunity:
            return self._on_proactive_opportunity(idle_duration, idle_state)
        
        return True
    
    def record_proactive_response(self, accepted: bool) -> None:
        """
        Record the user's response to a proactive suggestion.
        
        Args:
            accepted: True if user accepted, False if declined
        """
        with self._lock:
            if accepted:
                self.stats.total_proactive_accepted += 1
                logger.debug("Proactive suggestion accepted")
            else:
                self.stats.total_proactive_declined += 1
                logger.debug("Proactive suggestion declined")
    
    def set_state_change_callback(self, callback: Callable[[IdleState, IdleState], None]) -> None:
        """
        Set callback for idle state changes.
        
        Args:
            callback: Function(old_state, new_state) called on state change
        """
        self._on_state_change = callback
    
    def set_proactive_opportunity_callback(self, callback: Callable[[float, IdleState], bool]) -> None:
        """
        Set callback for proactive engagement opportunities.
        
        Args:
            callback: Function(idle_duration, idle_state) -> accepted
        """
        self._on_proactive_opportunity = callback
    
    def get_stats(self) -> IdleStats:
        """Get current idle statistics."""
        return self.stats
    
    def get_session_duration(self) -> float:
        """Get how long this session has been running."""
        return time.time() - self._session_start_time
    
    def format_idle_duration(self) -> str:
        """
        Get human-readable idle duration.
        
        Returns:
            String like "2 minutes" or "30 seconds"
        """
        duration = self.get_idle_duration()
        
        if duration < 60:
            return f"{int(duration)} seconds"
        elif duration < 3600:
            minutes = int(duration / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''}"
        else:
            hours = int(duration / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''}"


# Module-level singleton
_idle_monitor: Optional[IdleMonitor] = None


def init_idle_monitor(config: Optional[IdleConfig] = None) -> IdleMonitor:
    """
    Initialize the global idle monitor.
    
    Args:
        config: Optional configuration
        
    Returns:
        The initialized IdleMonitor instance
    """
    global _idle_monitor
    _idle_monitor = IdleMonitor(config)
    logger.info("Global IdleMonitor initialized")
    return _idle_monitor


def get_idle_monitor() -> Optional[IdleMonitor]:
    """
    Get the global idle monitor instance.
    
    Returns:
        IdleMonitor instance or None if not initialized
    """
    return _idle_monitor
