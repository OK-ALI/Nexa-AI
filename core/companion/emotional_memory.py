"""
Phase 30: Emotional Memory
==========================
Stores emotional context about user events, moods, and goals.

This module extends Smart Memory with emotional categories:
- Events: Things the user mentioned (exams, interviews, trips)
- Moods: Historical mood snapshots with context
- Goals: Dreams and aspirations the user shared
- Milestones: Achievements and notable moments

All data is stored locally via JSON for fast access, with optional
Smart Memory integration for semantic search.
"""

import time
import json
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class EmotionalCategory(Enum):
    """Categories of emotional memories."""
    EVENT = "event"             # "Exam tomorrow", "Job interview Friday"
    MOOD_SNAPSHOT = "mood"      # "User was stressed yesterday"
    GOAL = "goal"               # "Wants to learn guitar", "Working on fitness"
    PREFERENCE = "preference"   # "Prefers calm music when tired"
    MILESTONE = "milestone"     # "30 days since first conversation"
    JOURNAL = "journal"         # User's thoughts/reflections


class GoalStatus(Enum):
    """Status of a tracked goal."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass
class EmotionalEntry:
    """A single emotional memory entry."""
    id: str = ""
    category: str = "event"             # EmotionalCategory value
    content: str = ""                   # The memory content
    emotion: str = "neutral"            # Associated mood at time of storage
    importance: float = 0.5             # 0.0-1.0
    created_at: float = 0.0            # Timestamp
    expires_at: Optional[float] = None  # Optional expiry (for events)
    checked_in: bool = False            # Whether we've followed up
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())[:12]
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmotionalEntry':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at

    @property
    def age_hours(self) -> float:
        """Hours since this entry was created."""
        return (time.time() - self.created_at) / 3600


@dataclass
class GoalEntry:
    """A tracked goal/dream."""
    id: str = ""
    name: str = ""                      # Goal name
    description: str = ""               # Detailed description
    status: str = "active"              # GoalStatus value
    progress_notes: List[str] = field(default_factory=list)
    created_at: float = 0.0
    last_updated: float = 0.0
    last_checked_in: float = 0.0       # Last time we asked about it
    check_in_interval_days: int = 7    # How often to check in
    encouragement_count: int = 0       # Times we've encouraged

    def __post_init__(self):
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())[:12]
        if not self.created_at:
            self.created_at = time.time()
        if not self.last_updated:
            self.last_updated = self.created_at

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GoalEntry':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def days_since_check_in(self) -> float:
        """Days since last check-in."""
        if not self.last_checked_in:
            return (time.time() - self.created_at) / 86400
        return (time.time() - self.last_checked_in) / 86400

    @property
    def needs_check_in(self) -> bool:
        """Whether this goal is due for a check-in."""
        return (self.status == GoalStatus.ACTIVE.value and
                self.days_since_check_in >= self.check_in_interval_days)


class EmotionalMemory:
    """
    Stores and retrieves emotional context about the user.

    Manages events, mood snapshots, goals, preferences, milestones,
    and journal entries. Provides check-in suggestions for past events
    and goal tracking with encouragement.
    """

    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize emotional memory.

        Args:
            data_path: Path to store emotional data (default: data/emotional_memory.json)
        """
        self.data_path = data_path or self._get_default_path()

        # Storage by category
        self._entries: Dict[str, List[EmotionalEntry]] = defaultdict(list)
        self._goals: Dict[str, GoalEntry] = {}  # id -> GoalEntry

        # Milestone tracking
        self._first_interaction_time: Optional[float] = None
        self._total_interactions: int = 0
        self._milestones_celebrated: List[str] = []  # Milestone IDs already celebrated

        # Load existing data
        self._load()

        logger.info("EmotionalMemory initialized: %d entries, %d goals",
                     sum(len(v) for v in self._entries.values()), len(self._goals))

    def _get_default_path(self) -> Path:
        """Get the default path for emotional memory storage."""
        import sys
        if getattr(sys, 'frozen', False):
            import os
            base = Path(os.environ.get('LOCALAPPDATA', '')) / 'Nexa AI'
        else:
            base = Path(__file__).parent.parent.parent / 'data'
        base.mkdir(parents=True, exist_ok=True)
        return base / 'emotional_memory.json'

    def _load(self) -> None:
        """Load emotional memory from disk."""
        try:
            if self.data_path.exists():
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for category, entries in data.get('entries', {}).items():
                    self._entries[category] = [
                        EmotionalEntry.from_dict(e) for e in entries
                    ]

                for gid, gdata in data.get('goals', {}).items():
                    self._goals[gid] = GoalEntry.from_dict(gdata)

                self._first_interaction_time = data.get('first_interaction_time')
                self._total_interactions = data.get('total_interactions', 0)
                self._milestones_celebrated = data.get('milestones_celebrated', [])

                logger.debug("Loaded emotional memory: %d entries, %d goals",
                             sum(len(v) for v in self._entries.values()), len(self._goals))
        except Exception as e:
            logger.warning("Failed to load emotional memory: %s", e)

    def _save(self) -> None:
        """Save emotional memory to disk."""
        try:
            data = {
                'entries': {
                    cat: [e.to_dict() for e in entries]
                    for cat, entries in self._entries.items()
                },
                'goals': {
                    gid: g.to_dict() for gid, g in self._goals.items()
                },
                'first_interaction_time': self._first_interaction_time,
                'total_interactions': self._total_interactions,
                'milestones_celebrated': self._milestones_celebrated,
                'saved_at': time.time()
            }
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved emotional memory")
        except Exception as e:
            logger.warning("Failed to save emotional memory: %s", e)

    # =========================================================================
    # Store Operations
    # =========================================================================

    def store_emotional_context(
        self,
        content: str,
        category: str = "event",
        emotion: str = "neutral",
        importance: float = 0.5,
        expires_hours: Optional[float] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store an emotional memory entry.

        Args:
            content: The memory content (e.g., "User has an exam tomorrow")
            category: EmotionalCategory value
            emotion: Associated mood at time of storage
            importance: Memory importance (0.0-1.0)
            expires_hours: Optional expiry in hours
            tags: Optional tags for retrieval
            metadata: Optional extra metadata

        Returns:
            Entry ID
        """
        entry = EmotionalEntry(
            category=category,
            content=content,
            emotion=emotion,
            importance=importance,
            expires_at=(time.time() + expires_hours * 3600) if expires_hours else None,
            tags=tags or [],
            metadata=metadata or {}
        )

        self._entries[category].append(entry)
        self._save()

        logger.info("Stored emotional memory [%s]: %s (emotion=%s)",
                     category, content[:60], emotion)
        return entry.id

    def store_mood_snapshot(self, mood: str, context: str = "", valence: float = 0.0) -> str:
        """
        Store a mood snapshot for historical tracking.

        Args:
            mood: The detected mood
            context: What was happening when this mood was detected
            valence: Mood valence (-1 to 1)

        Returns:
            Entry ID
        """
        return self.store_emotional_context(
            content=f"User was feeling {mood}" + (f" while {context}" if context else ""),
            category=EmotionalCategory.MOOD_SNAPSHOT.value,
            emotion=mood,
            importance=0.3,
            expires_hours=168,  # Keep for 1 week
            metadata={'valence': valence}
        )

    def journal_thought(self, thought: str, emotion: str = "neutral") -> str:
        """
        Store a user's thought/reflection.

        Args:
            thought: The user's thought or reflection
            emotion: Current mood when journaling

        Returns:
            Entry ID
        """
        return self.store_emotional_context(
            content=thought,
            category=EmotionalCategory.JOURNAL.value,
            emotion=emotion,
            importance=0.6,
            tags=['journal', 'reflection']
        )

    # =========================================================================
    # Goal Tracking
    # =========================================================================

    def track_goal(self, name: str, description: str = "", check_in_days: int = 7) -> str:
        """
        Start tracking a new goal.

        Args:
            name: Goal name (e.g., "Learn guitar")
            description: Detailed description
            check_in_days: How often to check in (days)

        Returns:
            Goal ID
        """
        goal = GoalEntry(
            name=name,
            description=description,
            check_in_interval_days=check_in_days
        )

        self._goals[goal.id] = goal
        self._save()

        logger.info("Tracking new goal: %s (check-in every %d days)", name, check_in_days)
        return goal.id

    def update_goal(self, goal_id: str, status: Optional[str] = None,
                    progress_note: Optional[str] = None) -> bool:
        """
        Update a tracked goal.

        Args:
            goal_id: Goal identifier
            status: New status (GoalStatus value)
            progress_note: Optional progress note

        Returns:
            True if updated, False if not found
        """
        goal = self._goals.get(goal_id)
        if not goal:
            # Try to find by name
            for g in self._goals.values():
                if g.name.lower() == goal_id.lower():
                    goal = g
                    break
            if not goal:
                return False

        if status:
            goal.status = status
        if progress_note:
            goal.progress_notes.append(f"[{datetime.now().strftime('%Y-%m-%d')}] {progress_note}")
        goal.last_updated = time.time()

        self._save()
        logger.info("Updated goal '%s': status=%s", goal.name, goal.status)
        return True

    def mark_goal_checked_in(self, goal_id: str) -> None:
        """Mark a goal as recently checked in."""
        goal = self._goals.get(goal_id)
        if goal:
            goal.last_checked_in = time.time()
            self._save()

    def get_active_goals(self) -> List[GoalEntry]:
        """Get all active goals."""
        return [g for g in self._goals.values() if g.status == GoalStatus.ACTIVE.value]

    def get_goals_needing_check_in(self) -> List[GoalEntry]:
        """Get goals that are due for a check-in."""
        return [g for g in self._goals.values() if g.needs_check_in]

    def celebrate_milestone(self, milestone_type: str) -> Optional[str]:
        """
        Check and celebrate a milestone.

        Args:
            milestone_type: Type of milestone (e.g., "first_week", "100_interactions")

        Returns:
            Celebration message or None if already celebrated
        """
        if milestone_type in self._milestones_celebrated:
            return None

        self._milestones_celebrated.append(milestone_type)
        self.store_emotional_context(
            content=f"Milestone reached: {milestone_type}",
            category=EmotionalCategory.MILESTONE.value,
            emotion="happy",
            importance=0.8,
            tags=['milestone', milestone_type]
        )

        # Return a prompt for the LLM to generate a celebration message
        milestone_messages = {
            'first_day': "It's been one day since we started talking!",
            'first_week': "We've been talking for a whole week now!",
            'first_month': "A whole month together!",
            '50_interactions': "We've had 50 conversations!",
            '100_interactions': "100 conversations and counting!",
            '500_interactions': "500 conversations! That's incredible!",
            'first_goal_completed': "You completed your first tracked goal!",
        }

        return milestone_messages.get(milestone_type,
                                       f"Milestone: {milestone_type}")

    # =========================================================================
    # Retrieval Operations
    # =========================================================================

    def get_recent_entries(self, category: Optional[str] = None,
                          hours: int = 24, limit: int = 10) -> List[EmotionalEntry]:
        """
        Get recent emotional entries.

        Args:
            category: Filter by category (None for all)
            hours: Look back period in hours
            limit: Maximum entries to return

        Returns:
            List of EmotionalEntry, newest first
        """
        cutoff = time.time() - (hours * 3600)
        results = []

        categories = [category] if category else list(self._entries.keys())

        for cat in categories:
            for entry in self._entries.get(cat, []):
                if entry.created_at > cutoff and not entry.is_expired:
                    results.append(entry)

        results.sort(key=lambda e: e.created_at, reverse=True)
        return results[:limit]

    def get_unchecked_events(self, max_age_hours: int = 72) -> List[EmotionalEntry]:
        """
        Get events that we haven't followed up on yet.

        Args:
            max_age_hours: Maximum age of events to consider

        Returns:
            List of unchecked events ready for follow-up
        """
        cutoff = time.time() - (max_age_hours * 3600)
        events = self._entries.get(EmotionalCategory.EVENT.value, [])

        unchecked = [
            e for e in events
            if (not e.checked_in and
                e.created_at > cutoff and
                not e.is_expired and
                # Only follow up on events that are at least 1 hour old
                e.age_hours >= 1.0)
        ]

        # Sort by importance (most important first)
        unchecked.sort(key=lambda e: e.importance, reverse=True)
        return unchecked

    def mark_checked_in(self, entry_id: str) -> bool:
        """
        Mark an emotional entry as checked-in.

        Args:
            entry_id: Entry identifier

        Returns:
            True if found and marked
        """
        for entries in self._entries.values():
            for entry in entries:
                if entry.id == entry_id:
                    entry.checked_in = True
                    self._save()
                    return True
        return False

    def get_context_for_prompt(self, max_entries: int = 3) -> str:
        """
        Get emotional context for injection into LLM prompts.

        Returns:
            Concise emotional context string
        """
        parts = []

        # Recent events (last 48 hours)
        recent_events = self.get_recent_entries(
            category=EmotionalCategory.EVENT.value, hours=48, limit=2
        )
        if recent_events:
            events_str = "; ".join(e.content for e in recent_events[:2])
            parts.append(f"Recent events: {events_str}")

        # Active goals
        active_goals = self.get_active_goals()
        if active_goals:
            goals_str = ", ".join(g.name for g in active_goals[:3])
            parts.append(f"User goals: {goals_str}")

        # Unchecked events (follow-up opportunities)
        unchecked = self.get_unchecked_events()
        if unchecked:
            parts.append(f"Follow up on: {unchecked[0].content}")

        return " | ".join(parts) if parts else ""

    def record_interaction(self) -> Optional[str]:
        """
        Record an interaction for milestone tracking.

        Returns:
            Milestone type if a milestone was reached, None otherwise
        """
        self._total_interactions += 1

        if self._first_interaction_time is None:
            self._first_interaction_time = time.time()

        # Check interaction milestones
        count = self._total_interactions
        if count == 50:
            return '50_interactions'
        elif count == 100:
            return '100_interactions'
        elif count == 500:
            return '500_interactions'

        # Check time milestones
        if self._first_interaction_time:
            days = (time.time() - self._first_interaction_time) / 86400
            if days >= 1 and 'first_day' not in self._milestones_celebrated:
                return 'first_day'
            elif days >= 7 and 'first_week' not in self._milestones_celebrated:
                return 'first_week'
            elif days >= 30 and 'first_month' not in self._milestones_celebrated:
                return 'first_month'

        return None

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about emotional memory."""
        return {
            'total_entries': sum(len(v) for v in self._entries.values()),
            'entries_by_category': {
                cat: len(entries) for cat, entries in self._entries.items()
            },
            'total_goals': len(self._goals),
            'active_goals': len(self.get_active_goals()),
            'goals_needing_checkin': len(self.get_goals_needing_check_in()),
            'total_interactions': self._total_interactions,
            'milestones_celebrated': len(self._milestones_celebrated),
        }

    def cleanup_expired(self) -> int:
        """
        Remove expired entries.

        Returns:
            Number of entries removed
        """
        removed = 0
        for category in list(self._entries.keys()):
            original_count = len(self._entries[category])
            self._entries[category] = [
                e for e in self._entries[category] if not e.is_expired
            ]
            removed += original_count - len(self._entries[category])

        if removed > 0:
            self._save()
            logger.info("Cleaned up %d expired emotional entries", removed)

        return removed

    def save(self) -> None:
        """Force save current state."""
        self._save()


# ============================================================================
# Module-level singleton
# ============================================================================

_emotional_memory: Optional[EmotionalMemory] = None


def init_emotional_memory(data_path: Optional[Path] = None) -> EmotionalMemory:
    """
    Initialize the global emotional memory.

    Args:
        data_path: Optional path for emotional memory storage

    Returns:
        The initialized EmotionalMemory instance
    """
    global _emotional_memory
    _emotional_memory = EmotionalMemory(data_path)
    logger.info("Global EmotionalMemory initialized")
    return _emotional_memory


def get_emotional_memory() -> Optional[EmotionalMemory]:
    """Get the global emotional memory instance."""
    return _emotional_memory
