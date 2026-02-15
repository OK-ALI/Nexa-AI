"""
Phase 29: Pattern Learner
=========================
Learns user patterns and routines to make smarter proactive suggestions.

This module:
- Tracks command usage by time of day
- Learns daily/weekly routines
- Stores patterns in Smart Memory for persistence
- Predicts what user might want at different times

All learning is passive and respects user privacy.
"""

import time
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


@dataclass
class ActivityPattern:
    """A learned pattern of user activity."""
    activity: str              # e.g., "open_application:spotify"
    hour: int                  # 0-23
    day_of_week: int          # 0=Monday, 6=Sunday
    frequency: int            # How many times this pattern occurred
    last_occurrence: float    # Timestamp of last occurrence
    confidence: float = 0.5   # How confident we are this is a routine
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ActivityPattern':
        return cls(**data)


@dataclass
class TimeSlot:
    """A time slot for pattern matching."""
    hour: int
    day_of_week: int
    is_weekend: bool = False
    
    def matches(self, other: 'TimeSlot', hour_tolerance: int = 1) -> bool:
        """Check if two time slots match within tolerance."""
        hour_match = abs(self.hour - other.hour) <= hour_tolerance
        day_match = self.day_of_week == other.day_of_week
        return hour_match and day_match


class PatternLearner:
    """
    Learns and predicts user behavior patterns.
    
    This enables smarter proactive suggestions by understanding
    when users typically do certain activities.
    """
    
    def __init__(self, data_path: Optional[Path] = None):
        """
        Initialize the pattern learner.
        
        Args:
            data_path: Path to store pattern data (default: data/patterns.json)
        """
        self.data_path = data_path or self._get_default_path()
        
        # Activity patterns: {activity: [ActivityPattern, ...]}
        self._patterns: Dict[str, List[ActivityPattern]] = defaultdict(list)
        
        # Recent activities for pattern detection
        self._recent_activities: List[Tuple[str, float]] = []  # (activity, timestamp)
        self._max_recent = 100
        
        # Settings
        self._min_frequency_for_pattern = 3  # Need 3 occurrences to consider it a pattern
        self._pattern_decay_days = 14        # Patterns decay after 2 weeks of non-use
        
        # Load existing patterns
        self._load_patterns()
        
        logger.info("PatternLearner initialized with %d patterns", 
                   sum(len(p) for p in self._patterns.values()))
    
    def _get_default_path(self) -> Path:
        """Get the default path for pattern storage."""
        import sys
        if getattr(sys, 'frozen', False):
            import os
            base = Path(os.environ.get('LOCALAPPDATA', '')) / 'Nexa AI'
        else:
            base = Path(__file__).parent.parent.parent / 'data'
        
        base.mkdir(parents=True, exist_ok=True)
        return base / 'patterns.json'
    
    def _load_patterns(self) -> None:
        """Load patterns from disk."""
        try:
            if self.data_path.exists():
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                for activity, pattern_list in data.get('patterns', {}).items():
                    self._patterns[activity] = [
                        ActivityPattern.from_dict(p) for p in pattern_list
                    ]
                
                logger.debug("Loaded %d pattern groups", len(self._patterns))
        except Exception as e:
            logger.warning("Failed to load patterns: %s", e)
    
    def _save_patterns(self) -> None:
        """Save patterns to disk."""
        try:
            data = {
                'patterns': {
                    activity: [p.to_dict() for p in patterns]
                    for activity, patterns in self._patterns.items()
                },
                'saved_at': time.time()
            }
            
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            logger.debug("Saved %d pattern groups", len(self._patterns))
        except Exception as e:
            logger.warning("Failed to save patterns: %s", e)
    
    def record_activity(self, activity: str, category: str = "general") -> None:
        """
        Record a user activity to learn patterns.
        
        Args:
            activity: The activity performed (e.g., "open_application")
            category: Optional category for grouping
        """
        now = datetime.now()
        timestamp = time.time()
        hour = now.hour
        day_of_week = now.weekday()
        
        # Create activity key
        activity_key = f"{category}:{activity}" if category else activity
        
        # Track recent activities
        self._recent_activities.append((activity_key, timestamp))
        if len(self._recent_activities) > self._max_recent:
            self._recent_activities = self._recent_activities[-self._max_recent:]
        
        # Find or create pattern for this time slot
        existing_pattern = self._find_pattern(activity_key, hour, day_of_week)
        
        if existing_pattern:
            existing_pattern.frequency += 1
            existing_pattern.last_occurrence = timestamp
            existing_pattern.confidence = self._calculate_confidence(existing_pattern)
        else:
            new_pattern = ActivityPattern(
                activity=activity_key,
                hour=hour,
                day_of_week=day_of_week,
                frequency=1,
                last_occurrence=timestamp,
                confidence=0.3
            )
            self._patterns[activity_key].append(new_pattern)
        
        # Save periodically
        if len(self._recent_activities) % 10 == 0:
            self._save_patterns()
        
        logger.debug("Recorded activity: %s at hour %d, day %d", 
                    activity_key, hour, day_of_week)
    
    def _find_pattern(
        self,
        activity: str,
        hour: int,
        day_of_week: int,
        hour_tolerance: int = 1
    ) -> Optional[ActivityPattern]:
        """Find an existing pattern matching this time slot."""
        for pattern in self._patterns.get(activity, []):
            if (abs(pattern.hour - hour) <= hour_tolerance and
                pattern.day_of_week == day_of_week):
                return pattern
        return None
    
    def _calculate_confidence(self, pattern: ActivityPattern) -> float:
        """
        Calculate confidence score for a pattern.
        
        Based on frequency and recency.
        """
        # Base confidence from frequency
        freq_confidence = min(1.0, pattern.frequency / 10.0)
        
        # Recency factor (decays over 2 weeks)
        days_since_last = (time.time() - pattern.last_occurrence) / 86400
        recency_factor = max(0.0, 1.0 - (days_since_last / self._pattern_decay_days))
        
        return freq_confidence * recency_factor
    
    def get_predictions(
        self,
        hour: Optional[int] = None,
        day_of_week: Optional[int] = None,
        min_confidence: float = 0.5
    ) -> List[ActivityPattern]:
        """
        Get predicted activities for a time slot.
        
        Args:
            hour: Hour to predict for (default: current)
            day_of_week: Day to predict for (default: current)
            min_confidence: Minimum confidence threshold
            
        Returns:
            List of ActivityPatterns sorted by confidence
        """
        now = datetime.now()
        hour = hour if hour is not None else now.hour
        day_of_week = day_of_week if day_of_week is not None else now.weekday()
        
        predictions = []
        
        for activity, patterns in self._patterns.items():
            for pattern in patterns:
                # Check if pattern matches this time slot
                if (abs(pattern.hour - hour) <= 1 and
                    pattern.day_of_week == day_of_week and
                    pattern.frequency >= self._min_frequency_for_pattern):
                    
                    # Recalculate confidence
                    pattern.confidence = self._calculate_confidence(pattern)
                    
                    if pattern.confidence >= min_confidence:
                        predictions.append(pattern)
        
        # Sort by confidence
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        
        logger.debug("Found %d predictions for hour %d, day %d",
                    len(predictions), hour, day_of_week)
        
        return predictions
    
    def get_top_prediction(
        self,
        hour: Optional[int] = None,
        day_of_week: Optional[int] = None
    ) -> Optional[ActivityPattern]:
        """
        Get the single most likely activity for a time slot.
        
        Returns:
            Top prediction or None
        """
        predictions = self.get_predictions(hour, day_of_week)
        return predictions[0] if predictions else None
    
    def get_routine_summary(self) -> Dict[str, Any]:
        """
        Get a summary of learned routines.
        
        Returns:
            Summary dict with patterns by day/time
        """
        day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 
                     'Friday', 'Saturday', 'Sunday']
        
        summary = {day: {} for day in day_names}
        
        for activity, patterns in self._patterns.items():
            for pattern in patterns:
                if pattern.frequency >= self._min_frequency_for_pattern:
                    day = day_names[pattern.day_of_week]
                    hour_label = f"{pattern.hour:02d}:00"
                    
                    if hour_label not in summary[day]:
                        summary[day][hour_label] = []
                    
                    summary[day][hour_label].append({
                        'activity': activity,
                        'frequency': pattern.frequency,
                        'confidence': round(pattern.confidence, 2)
                    })
        
        return summary
    
    def clear_patterns(self) -> None:
        """Clear all learned patterns."""
        self._patterns.clear()
        self._recent_activities.clear()
        self._save_patterns()
        logger.info("All patterns cleared")
    
    def decay_old_patterns(self, max_age_days: int = 30) -> int:
        """
        Remove patterns that haven't been used recently.
        
        Args:
            max_age_days: Maximum age in days before removal
            
        Returns:
            Number of patterns removed
        """
        cutoff = time.time() - (max_age_days * 86400)
        removed = 0
        
        for activity in list(self._patterns.keys()):
            original_count = len(self._patterns[activity])
            self._patterns[activity] = [
                p for p in self._patterns[activity]
                if p.last_occurrence > cutoff
            ]
            removed += original_count - len(self._patterns[activity])
            
            # Remove empty activity entries
            if not self._patterns[activity]:
                del self._patterns[activity]
        
        if removed > 0:
            self._save_patterns()
            logger.info("Decayed %d old patterns", removed)
        
        return removed
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about learned patterns."""
        all_patterns = [p for patterns in self._patterns.values() for p in patterns]
        
        return {
            'total_patterns': len(all_patterns),
            'total_activities': len(self._patterns),
            'high_confidence_patterns': sum(1 for p in all_patterns if p.confidence >= 0.7),
            'recent_activities': len(self._recent_activities),
            'most_frequent_activity': max(
                self._patterns.keys(),
                key=lambda a: sum(p.frequency for p in self._patterns[a]),
                default=None
            )
        }


# Module-level singleton
_pattern_learner: Optional[PatternLearner] = None


def init_pattern_learner(data_path: Optional[Path] = None) -> PatternLearner:
    """
    Initialize the global pattern learner.
    
    Args:
        data_path: Optional path for pattern storage
        
    Returns:
        The initialized PatternLearner instance
    """
    global _pattern_learner
    _pattern_learner = PatternLearner(data_path)
    logger.info("Global PatternLearner initialized")
    return _pattern_learner


def get_pattern_learner() -> Optional[PatternLearner]:
    """Get the global pattern learner instance."""
    return _pattern_learner
