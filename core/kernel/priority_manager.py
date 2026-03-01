"""
Priority Manager
================
Defines strict numeric priority levels and rules for task preemption.

Priority values follow the NEXA Architecture Refactor Plan:
  EMERGENCY         = 110  (critical system override — above everything)
  VOICE_INPUT       = 100  (live microphone — always wins)
  USER_COMMAND      = 90   (explicit user request)
  NOTIFICATION_ALERT= 80   (system health alerts)
  SCREEN_QUERY      = 70   (reading screen state)
  MEDIA_PLAYBACK    = 60   (NVP / YouTube playback)
  BACKGROUND_SYNC   = 40   (background data sync)
  DOWNLOAD          = 30   (background file downloads)
  IDLE_SUGGESTION   = 20   (proactive suggestions — lowest interactive)
  MEMORY_CLEANUP    = 10   (silent housekeeping — never interrupts anything)

Gaps are intentionally wide so future levels can be inserted between any two
existing ones without renumbering the whole table.
"""

import logging
from enum import IntEnum

logger = logging.getLogger(__name__)


class PriorityLevel(IntEnum):
    """
    Strict numeric priority levels — higher value = higher priority.

    Governance guarantees:
    • Any task with a higher numeric value can preempt a lower one.
    • IDLE_SUGGESTION / MEMORY_CLEANUP are rejected when any other task is active.
    • EMERGENCY overrides the locked state (e.g. battery-critical shutdown).
    """
    MEMORY_CLEANUP     = 10   # Silent housekeeping (log rotation, vector cleanup)
    IDLE_SUGGESTION    = 20   # Proactive assistant suggestions
    DOWNLOAD           = 30   # Background file downloads (YouTube, updates)
    BACKGROUND_SYNC    = 40   # Background data sync (weather cache, etc.)
    MEDIA_PLAYBACK     = 60   # Music / NVP video playback
    SCREEN_QUERY       = 70   # Screen reading / window state queries
    NOTIFICATION_ALERT = 80   # Urgent system alerts (battery critical, etc.)
    USER_COMMAND       = 90   # Explicit voice / text command
    VOICE_INPUT        = 100  # Live microphone capture — always processed
    EMERGENCY          = 110  # Critical system override (shutdown, crash guard)


# Convenience aliases used by kernel
BACKGROUND_LEVELS = frozenset({
    PriorityLevel.MEMORY_CLEANUP,
    PriorityLevel.IDLE_SUGGESTION,
    PriorityLevel.DOWNLOAD,
    PriorityLevel.BACKGROUND_SYNC,
})


class PriorityManager:
    """
    Manages priority comparison and rejection rules.

    Rules:
    1. Higher numeric priority preempts lower numeric priority.
    2. Equal priority tasks queue FIFO.
    3. Background-class tasks (≤ BACKGROUND_SYNC) are rejected when any other
       task is active OR when media is playing.
    4. Locked state blocks everything below VOICE_INPUT, except EMERGENCY.
    """

    def can_preempt(self, new_priority: PriorityLevel,
                    active_priority: PriorityLevel) -> bool:
        """Return True if new_priority should preempt the active task."""
        return int(new_priority) > int(active_priority)

    def should_reject(self, priority: PriorityLevel,
                      is_locked: bool = False,
                      media_active: bool = False,
                      has_active_task: bool = False) -> bool:
        """
        Determine if a task should be outright rejected based on system state.

        Args:
            priority: Priority of the incoming task.
            is_locked: Whether NEXA is in locked state.
            media_active: Whether media (NVP, music) is currently playing.
            has_active_task: Whether any task is currently active.

        Returns:
            True if the task should be rejected (not queued, just dropped).
        """
        # EMERGENCY always passes — even through locked state
        if priority >= PriorityLevel.EMERGENCY:
            return False

        # Rule 1: Locked state blocks everything below VOICE_INPUT
        if is_locked and priority < PriorityLevel.VOICE_INPUT:
            logger.debug(f"🚫 Rejected task (P{int(priority)}): system is locked")
            return True

        # Rule 2 & 3: Background-class tasks are suppressed by any active work
        if priority in BACKGROUND_LEVELS:
            if has_active_task:
                logger.debug(f"🚫 Rejected background task (P{int(priority)}): active task running")
                return True
            if media_active:
                logger.debug(f"🚫 Rejected background task (P{int(priority)}): media is active")
                return True

        return False

