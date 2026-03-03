"""
Phase 30: Event Tracker
=======================
Parses and tracks events mentioned in user conversation for follow-up.

This module:
- Detects event mentions in user text ("exam tomorrow", "interview Friday")
- Stores events with estimated dates
- Provides check-in suggestions at appropriate times
- Integrates with ProactiveEngine for automated follow-ups

Uses keyword/pattern matching (no external NLP dependencies).
"""

import re
import time
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum

logger = logging.getLogger(__name__)


class EventType(Enum):
    """Types of tracked events."""
    EXAM = "exam"
    INTERVIEW = "interview"
    MEETING = "meeting"
    DEADLINE = "deadline"
    TRIP = "trip"
    APPOINTMENT = "appointment"
    CELEBRATION = "celebration"
    GENERAL = "general"


class EventStatus(Enum):
    """Status of a tracked event."""
    UPCOMING = "upcoming"
    PASSED = "passed"
    CHECKED_IN = "checked_in"
    DISMISSED = "dismissed"


# Event detection patterns: (regex_pattern, EventType, importance)
_EVENT_PATTERNS: List[Tuple[str, EventType, float]] = [
    # Exams and tests
    (r'\b(?:exam|test|quiz|midterm|final|finals)\b', EventType.EXAM, 0.8),
    # Interviews
    (r'\b(?:interview|job interview|phone screen)\b', EventType.INTERVIEW, 0.9),
    # Meetings
    (r'\b(?:meeting|appointment|call with|video call|zoom|teams call)\b', EventType.MEETING, 0.6),
    # Deadlines
    (r'\b(?:deadline|due date|submission|due|hand in|turn in)\b', EventType.DEADLINE, 0.8),
    # Travel
    (r'\b(?:trip|travel|flight|vacation|holiday|going to)\b', EventType.TRIP, 0.7),
    # Appointments
    (r'\b(?:doctor|dentist|hospital|clinic|checkup|check-up)\b', EventType.APPOINTMENT, 0.7),
    # Celebrations
    (r'\b(?:birthday|anniversary|party|wedding|graduation|ceremony)\b', EventType.CELEBRATION, 0.7),
]

# Time reference patterns for date estimation
_TIME_PATTERNS: List[Tuple[str, int]] = [
    # Pattern → days from now
    (r'\btoday\b', 0),
    (r'\btonight\b', 0),
    (r'\btomorrow\b', 1),
    (r'\bday after tomorrow\b', 2),
    (r'\bnext week\b', 7),
    (r'\bthis week\b', 3),          # Middle of week estimate
    (r'\bthis weekend\b', 5),       # Approximate
    (r'\bnext month\b', 30),
    (r'\bin (\d+) days?\b', -1),    # Special: extract number
    (r'\bin (\d+) weeks?\b', -2),   # Special: extract number * 7
    (r'\bin (\d+) hours?\b', 0),    # Same day
]

# Day of week patterns
_DAY_PATTERNS: Dict[str, int] = {
    'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
    'friday': 4, 'saturday': 5, 'sunday': 6,
    'mon': 0, 'tue': 1, 'wed': 2, 'thu': 3,
    'fri': 4, 'sat': 5, 'sun': 6,
}


@dataclass
class TrackedEvent:
    """A tracked event from user conversation."""
    id: str = ""
    event_type: str = "general"         # EventType value
    description: str = ""               # Full event description
    original_text: str = ""             # The user text that triggered detection
    estimated_date: Optional[float] = None  # Estimated timestamp
    status: str = "upcoming"            # EventStatus value
    importance: float = 0.5
    created_at: float = 0.0
    checked_in_at: Optional[float] = None
    check_in_message: str = ""          # Generated check-in prompt

    def __post_init__(self):
        if not self.id:
            import uuid
            self.id = str(uuid.uuid4())[:12]
        if not self.created_at:
            self.created_at = time.time()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TrackedEvent':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})

    @property
    def has_passed(self) -> bool:
        """Check if event's estimated date has passed."""
        if self.estimated_date is None:
            # If no date, consider it passed after 48 hours
            return (time.time() - self.created_at) > 48 * 3600
        return time.time() > self.estimated_date

    @property
    def is_ready_for_checkin(self) -> bool:
        """Check if event is ready for a check-in."""
        if self.status != EventStatus.UPCOMING.value:
            return False
        if not self.has_passed:
            return False
        # Don't check in too early — wait at least 2 hours after event time
        if self.estimated_date:
            return (time.time() - self.estimated_date) >= 2 * 3600
        return True

    @property
    def hours_until(self) -> Optional[float]:
        """Hours until event (None if no date or already passed)."""
        if self.estimated_date is None:
            return None
        delta = self.estimated_date - time.time()
        return delta / 3600 if delta > 0 else None


class EventTracker:
    """
    Detects and tracks events mentioned in user conversations.

    Provides check-in suggestions when events have passed,
    enabling empathetic follow-ups like "How did your exam go?"
    """

    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize the event tracker.

        Args:
            data_path: Path to store event data (default: data/tracked_events.json)
        """
        self.data_path = data_path or self._get_default_path()

        # Active and historical events
        self._events: List[TrackedEvent] = []

        # Dedup: track recently stored event descriptions to avoid duplicates
        self._recent_descriptions: List[str] = []
        self._max_recent = 20

        # Settings
        self._max_events = 50       # Max events to keep
        self._max_age_days = 14     # Remove events older than 2 weeks

        # Load existing data
        self._load()

        logger.info("EventTracker initialized with %d events", len(self._events))

    def _get_default_path(self) -> Path:
        """Get default path for event storage."""
        import sys
        if getattr(sys, 'frozen', False):
            import os
            base = Path(os.environ.get('LOCALAPPDATA', '')) / 'Nexa AI'
        else:
            base = Path(__file__).parent.parent.parent / 'data'
        base.mkdir(parents=True, exist_ok=True)
        return base / 'tracked_events.json'

    def _load(self) -> None:
        """Load events from disk."""
        try:
            if self.data_path.exists():
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self._events = [
                    TrackedEvent.from_dict(e) for e in data.get('events', [])
                ]
                self._recent_descriptions = data.get('recent_descriptions', [])
                logger.debug("Loaded %d tracked events", len(self._events))
        except Exception as e:
            logger.warning("Failed to load events: %s", e)

    def _save(self) -> None:
        """Save events to disk."""
        try:
            data = {
                'events': [e.to_dict() for e in self._events],
                'recent_descriptions': self._recent_descriptions[-self._max_recent:],
                'saved_at': time.time()
            }
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved %d tracked events", len(self._events))
        except Exception as e:
            logger.warning("Failed to save events: %s", e)

    def detect_events(self, text: str) -> List[TrackedEvent]:
        """
        Detect event mentions in user text.

        Args:
            text: User's input text

        Returns:
            List of detected events (not yet stored)
        """
        text_lower = text.lower().strip()
        if not text_lower or len(text_lower) < 5:
            return []

        detected = []

        for pattern, event_type, importance in _EVENT_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                # Estimate the date
                estimated_date = self._estimate_date(text_lower)

                # Build description
                description = self._build_description(text, event_type, match.group())

                # Check for duplicates
                if self._is_duplicate(description):
                    continue

                event = TrackedEvent(
                    event_type=event_type.value,
                    description=description,
                    original_text=text,
                    estimated_date=estimated_date,
                    importance=importance,
                )

                # Generate check-in message
                event.check_in_message = self._generate_check_in_prompt(event)

                detected.append(event)

        return detected

    def process_text(self, text: str) -> List[TrackedEvent]:
        """
        Detect and store events from user text.

        This is the main entry point — call with each user message.

        Args:
            text: User's input text

        Returns:
            List of newly stored events
        """
        detected = self.detect_events(text)

        for event in detected:
            self._events.append(event)
            self._recent_descriptions.append(event.description.lower())
            logger.info("Tracked event [%s]: %s (est. date: %s)",
                        event.event_type, event.description,
                        datetime.fromtimestamp(event.estimated_date).strftime('%Y-%m-%d %H:%M')
                        if event.estimated_date else "unknown")

        if detected:
            self._cleanup_old()
            self._save()

        return detected

    def _estimate_date(self, text_lower: str) -> Optional[float]:
        """
        Estimate when an event will occur based on time references.

        Args:
            text_lower: Lowercase user text

        Returns:
            Estimated timestamp or None
        """
        now = datetime.now()

        # Check explicit time patterns
        for pattern, days_offset in _TIME_PATTERNS:
            match = re.search(pattern, text_lower)
            if match:
                if days_offset == -1:  # "in N days"
                    try:
                        n = int(match.group(1))
                        return (now + timedelta(days=n)).timestamp()
                    except (ValueError, IndexError):
                        continue
                elif days_offset == -2:  # "in N weeks"
                    try:
                        n = int(match.group(1))
                        return (now + timedelta(weeks=n)).timestamp()
                    except (ValueError, IndexError):
                        continue
                else:
                    return (now + timedelta(days=days_offset)).timestamp()

        # Check day of week references
        for day_name, day_num in _DAY_PATTERNS.items():
            if day_name in text_lower:
                # Find the next occurrence of this day
                current_day = now.weekday()
                days_ahead = day_num - current_day
                if days_ahead <= 0:  # Target day already passed this week
                    days_ahead += 7
                target = now + timedelta(days=days_ahead)
                # Set to morning (9 AM) by default
                target = target.replace(hour=9, minute=0, second=0)
                return target.timestamp()

        # No time reference found — default to tomorrow
        return (now + timedelta(days=1)).timestamp()

    def _build_description(self, text: str, event_type: EventType, matched: str) -> str:
        """Build a human-readable event description."""
        # Try to extract a meaningful snippet around the matched keyword
        text_clean = text.strip()
        if len(text_clean) <= 80:
            return text_clean

        # Find the matched keyword position and extract surrounding context
        lower_text = text_clean.lower()
        pos = lower_text.find(matched)
        if pos >= 0:
            start = max(0, pos - 30)
            end = min(len(text_clean), pos + len(matched) + 30)
            snippet = text_clean[start:end].strip()
            if start > 0:
                snippet = "..." + snippet
            if end < len(text_clean):
                snippet = snippet + "..."
            return snippet

        return text_clean[:80]

    def _generate_check_in_prompt(self, event: TrackedEvent) -> str:
        """Generate a check-in question for the LLM to personalize."""
        templates = {
            EventType.EXAM.value: f"Ask how {event.description} went. Be encouraging.",
            EventType.INTERVIEW.value: f"Ask about {event.description}. Be supportive regardless of outcome.",
            EventType.MEETING.value: f"Briefly ask how {event.description} went.",
            EventType.DEADLINE.value: f"Ask if they managed to meet {event.description}.",
            EventType.TRIP.value: f"Ask about {event.description}. Show genuine interest.",
            EventType.APPOINTMENT.value: f"Gently ask how {event.description} went.",
            EventType.CELEBRATION.value: f"Ask about {event.description}. Be enthusiastic!",
            EventType.GENERAL.value: f"Follow up on: {event.description}",
        }
        return templates.get(event.event_type, f"Follow up on: {event.description}")

    def _is_duplicate(self, description: str) -> bool:
        """Check if a similar event was already tracked recently."""
        desc_lower = description.lower()
        for recent in self._recent_descriptions:
            # Simple overlap check
            if desc_lower == recent or desc_lower in recent or recent in desc_lower:
                return True
        return False

    # =========================================================================
    # Check-in Operations
    # =========================================================================

    def get_events_for_checkin(self) -> List[TrackedEvent]:
        """
        Get events that are ready for check-in follow-up.

        Returns:
            List of events ready for check-in, sorted by importance
        """
        ready = [e for e in self._events if e.is_ready_for_checkin]
        ready.sort(key=lambda e: e.importance, reverse=True)
        return ready

    def mark_event_checked_in(self, event_id: str) -> bool:
        """
        Mark an event as checked-in.

        Args:
            event_id: Event identifier

        Returns:
            True if found and marked
        """
        for event in self._events:
            if event.id == event_id:
                event.status = EventStatus.CHECKED_IN.value
                event.checked_in_at = time.time()
                self._save()
                return True
        return False

    def dismiss_event(self, event_id: str) -> bool:
        """
        Dismiss an event (don't check in).

        Args:
            event_id: Event identifier

        Returns:
            True if found and dismissed
        """
        for event in self._events:
            if event.id == event_id:
                event.status = EventStatus.DISMISSED.value
                self._save()
                return True
        return False

    def get_upcoming_events(self, hours: int = 48) -> List[TrackedEvent]:
        """
        Get upcoming events within the specified window.

        Args:
            hours: Look-ahead window in hours

        Returns:
            List of upcoming events, sorted by estimated date
        """
        now = time.time()
        window = now + (hours * 3600)

        upcoming = [
            e for e in self._events
            if (e.status == EventStatus.UPCOMING.value and
                e.estimated_date and
                now < e.estimated_date <= window)
        ]

        upcoming.sort(key=lambda e: e.estimated_date or float('inf'))
        return upcoming

    def get_context_for_prompt(self) -> str:
        """
        Get event context for injection into LLM prompts.

        Returns:
            Concise event context string
        """
        parts = []

        # Upcoming events (next 48 hours)
        upcoming = self.get_upcoming_events(hours=48)
        if upcoming:
            for e in upcoming[:2]:
                hours_left = e.hours_until
                if hours_left is not None:
                    if hours_left < 1:
                        parts.append(f"Upcoming soon: {e.description}")
                    elif hours_left < 24:
                        parts.append(f"In ~{int(hours_left)}h: {e.description}")
                    else:
                        days = int(hours_left / 24)
                        parts.append(f"In ~{days}d: {e.description}")

        # Events ready for check-in
        checkin = self.get_events_for_checkin()
        if checkin:
            parts.append(f"Check in about: {checkin[0].description}")

        return " | ".join(parts) if parts else ""

    # =========================================================================
    # Maintenance
    # =========================================================================

    def _cleanup_old(self) -> int:
        """Remove old events beyond max age."""
        cutoff = time.time() - (self._max_age_days * 86400)
        original_count = len(self._events)

        self._events = [
            e for e in self._events
            if (e.created_at > cutoff or
                e.status == EventStatus.UPCOMING.value)
        ]

        # Enforce max events limit
        if len(self._events) > self._max_events:
            # Keep the most recent
            self._events.sort(key=lambda e: e.created_at, reverse=True)
            self._events = self._events[:self._max_events]

        removed = original_count - len(self._events)
        if removed > 0:
            logger.info("Cleaned up %d old events", removed)
        return removed

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about tracked events."""
        return {
            'total_events': len(self._events),
            'upcoming': len([e for e in self._events if e.status == EventStatus.UPCOMING.value]),
            'checked_in': len([e for e in self._events if e.status == EventStatus.CHECKED_IN.value]),
            'dismissed': len([e for e in self._events if e.status == EventStatus.DISMISSED.value]),
            'events_by_type': {
                etype.value: len([e for e in self._events if e.event_type == etype.value])
                for etype in EventType
            }
        }

    def save(self) -> None:
        """Force save current state."""
        self._save()


# ============================================================================
# Module-level singleton
# ============================================================================

_event_tracker: Optional[EventTracker] = None


def init_event_tracker(data_path: Optional[Path] = None) -> EventTracker:
    """
    Initialize the global event tracker.

    Args:
        data_path: Optional path for event storage

    Returns:
        The initialized EventTracker instance
    """
    global _event_tracker
    _event_tracker = EventTracker(data_path)
    logger.info("Global EventTracker initialized")
    return _event_tracker


def get_event_tracker() -> Optional[EventTracker]:
    """Get the global event tracker instance."""
    return _event_tracker
