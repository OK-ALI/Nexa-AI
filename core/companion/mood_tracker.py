"""
Phase 30: Mood Tracker
======================
Detects and tracks user mood from text (sentiment analysis).

This module:
- Analyzes user text for emotional cues (keywords, patterns, punctuation)
- Tracks mood changes over time
- Provides mood context to the LLM for empathetic responses
- Stores mood history in JSON for persistence
- Detects mood shifts (e.g., happy → frustrated)

All analysis is text-based (voice tone analysis is a future stretch goal).
"""

import time
import json
import logging
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from enum import Enum
from collections import deque

logger = logging.getLogger(__name__)


class Mood(Enum):
    """Detected mood categories."""
    HAPPY = "happy"
    EXCITED = "excited"
    CALM = "calm"
    NEUTRAL = "neutral"
    TIRED = "tired"
    SAD = "sad"
    STRESSED = "stressed"
    FRUSTRATED = "frustrated"
    ANGRY = "angry"


# Mood valence: positive (1.0) to negative (-1.0)
MOOD_VALENCE: Dict[Mood, float] = {
    Mood.HAPPY: 0.8,
    Mood.EXCITED: 1.0,
    Mood.CALM: 0.3,
    Mood.NEUTRAL: 0.0,
    Mood.TIRED: -0.2,
    Mood.SAD: -0.6,
    Mood.STRESSED: -0.5,
    Mood.FRUSTRATED: -0.7,
    Mood.ANGRY: -0.9,
}

# Mood energy: high energy (1.0) to low energy (0.0)
MOOD_ENERGY: Dict[Mood, float] = {
    Mood.HAPPY: 0.7,
    Mood.EXCITED: 1.0,
    Mood.CALM: 0.3,
    Mood.NEUTRAL: 0.5,
    Mood.TIRED: 0.1,
    Mood.SAD: 0.2,
    Mood.STRESSED: 0.7,
    Mood.FRUSTRATED: 0.8,
    Mood.ANGRY: 0.9,
}

# Keyword patterns for mood detection (weighted)
# Each entry: (keywords, mood, weight)
_MOOD_KEYWORDS: List[Tuple[List[str], Mood, float]] = [
    # Happy
    (["happy", "glad", "great", "wonderful", "amazing", "awesome", "fantastic",
      "love it", "brilliant", "perfect", "excellent", "thanks", "thank you",
      "good day", "good morning", "blessed"], Mood.HAPPY, 0.7),
    # Excited
    (["excited", "can't wait", "hyped", "pumped", "so cool", "incredible",
      "let's go", "yes!", "finally", "wooo", "yay", "omg"], Mood.EXCITED, 0.8),
    # Calm
    (["relaxing", "peaceful", "chill", "quiet", "calm", "serene",
      "taking it easy", "winding down"], Mood.CALM, 0.6),
    # Tired
    (["tired", "exhausted", "sleepy", "drained", "burnt out", "burnout",
      "need sleep", "so tired", "fatigue", "worn out", "long day",
      "can barely", "dead tired"], Mood.TIRED, 0.7),
    # Sad
    (["sad", "depressed", "down", "unhappy", "lonely", "miss",
      "heartbroken", "upset", "crying", "tears", "lost", "grief",
      "feel bad", "feeling low", "not okay"], Mood.SAD, 0.7),
    # Stressed
    (["stressed", "overwhelmed", "anxiety", "anxious", "worried", "pressure",
      "deadline", "too much", "can't handle", "freaking out", "panicking",
      "so much to do", "swamped"], Mood.STRESSED, 0.7),
    # Frustrated
    (["frustrated", "annoying", "annoyed", "irritated", "ugh", "why won't",
      "doesn't work", "not working", "broken", "stupid", "this sucks",
      "give up", "fed up", "sick of"], Mood.FRUSTRATED, 0.7),
    # Angry
    (["angry", "furious", "mad", "rage", "hate", "pissed",
      "so angry", "infuriating", "livid"], Mood.ANGRY, 0.8),
]

# Punctuation patterns that indicate mood
_PUNCTUATION_SIGNALS: Dict[str, Tuple[Mood, float]] = {
    "!!!": (Mood.EXCITED, 0.3),
    "??": (Mood.FRUSTRATED, 0.2),
    "...": (Mood.SAD, 0.15),
    ":(": (Mood.SAD, 0.4),
    ":)": (Mood.HAPPY, 0.3),
    "<3": (Mood.HAPPY, 0.3),
    "😊": (Mood.HAPPY, 0.4),
    "😢": (Mood.SAD, 0.4),
    "😡": (Mood.ANGRY, 0.5),
    "😴": (Mood.TIRED, 0.4),
    "😰": (Mood.STRESSED, 0.4),
}


@dataclass
class MoodReading:
    """A single mood measurement from user text."""
    mood: str                     # Mood enum value
    confidence: float             # 0.0-1.0
    valence: float                # -1.0 (negative) to 1.0 (positive)
    energy: float                 # 0.0 (low) to 1.0 (high)
    triggers: List[str]           # What keywords triggered this detection
    timestamp: float = field(default_factory=time.time)
    user_text: str = ""           # The text that was analyzed

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MoodReading':
        return cls(**data)


@dataclass
class MoodState:
    """Current aggregated mood state (smoothed over recent readings)."""
    current_mood: str = "neutral"
    confidence: float = 0.0
    valence: float = 0.0         # Running average valence
    energy: float = 0.5          # Running average energy
    trend: str = "stable"        # "improving", "declining", "stable"
    last_updated: float = 0.0
    readings_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MoodState':
        return cls(**data)


class MoodTracker:
    """
    Tracks user mood from text analysis.

    Uses keyword matching, punctuation analysis, and contextual cues
    to detect mood. Maintains a rolling window of recent readings
    for trend detection and mood smoothing.
    """

    def __init__(self, data_path: Optional[Path] = None, window_size: int = 10):
        """
        Initialize the mood tracker.

        Args:
            data_path: Path to store mood history (default: data/mood_history.json)
            window_size: Number of recent readings to keep for smoothing
        """
        self.data_path = data_path or self._get_default_path()
        self._window_size = window_size

        # Recent mood readings (rolling window)
        self._readings: deque = deque(maxlen=window_size)

        # Current aggregated mood state
        self._state = MoodState()

        # Mood shift callback (called when mood changes significantly)
        self._on_mood_shift: Optional[callable] = None

        # Settings
        self._min_confidence = 0.3      # Minimum confidence to register a mood
        self._shift_threshold = 0.4     # Valence change needed to trigger shift
        self._smoothing_factor = 0.7    # Weight of new reading vs history (EMA)

        # Load history
        self._load_history()

        logger.info("MoodTracker initialized with %d historical readings", len(self._readings))

    def _get_default_path(self) -> Path:
        """Get the default path for mood storage."""
        import sys
        if getattr(sys, 'frozen', False):
            import os
            base = Path(os.environ.get('LOCALAPPDATA', '')) / 'Nexa AI'
        else:
            base = Path(__file__).parent.parent.parent / 'data'
        base.mkdir(parents=True, exist_ok=True)
        return base / 'mood_history.json'

    def _load_history(self) -> None:
        """Load mood history from disk."""
        try:
            if self.data_path.exists():
                with open(self.data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)

                for entry in data.get('readings', [])[-self._window_size:]:
                    self._readings.append(MoodReading.from_dict(entry))

                state_data = data.get('state')
                if state_data:
                    self._state = MoodState.from_dict(state_data)

                logger.debug("Loaded %d mood readings", len(self._readings))
        except Exception as e:
            logger.warning("Failed to load mood history: %s", e)

    def _save_history(self) -> None:
        """Save mood history to disk."""
        try:
            data = {
                'readings': [r.to_dict() for r in self._readings],
                'state': self._state.to_dict(),
                'saved_at': time.time()
            }
            with open(self.data_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.debug("Saved %d mood readings", len(self._readings))
        except Exception as e:
            logger.warning("Failed to save mood history: %s", e)

    def set_mood_shift_callback(self, callback: callable) -> None:
        """
        Set callback for mood shift events.

        Args:
            callback: Function(old_mood: str, new_mood: str, valence_delta: float) -> None
        """
        self._on_mood_shift = callback

    def analyze_text(self, text: str) -> MoodReading:
        """
        Analyze user text for mood indicators.

        Args:
            text: User's input text

        Returns:
            MoodReading with detected mood and confidence
        """
        text_lower = text.lower().strip()
        if not text_lower:
            return MoodReading(
                mood=Mood.NEUTRAL.value, confidence=0.0,
                valence=0.0, energy=0.5, triggers=[], user_text=text
            )

        # Collect mood scores from keywords
        mood_scores: Dict[Mood, float] = {}
        triggers: List[str] = []

        for keywords, mood, weight in _MOOD_KEYWORDS:
            for kw in keywords:
                if kw in text_lower:
                    current = mood_scores.get(mood, 0.0)
                    mood_scores[mood] = current + weight
                    triggers.append(kw)

        # Check punctuation signals
        for pattern, (mood, weight) in _PUNCTUATION_SIGNALS.items():
            if pattern in text:
                current = mood_scores.get(mood, 0.0)
                mood_scores[mood] = current + weight
                triggers.append(f"punct:{pattern}")

        # Check for ALL CAPS (suggests strong emotion)
        words = text.split()
        caps_words = sum(1 for w in words if w.isupper() and len(w) > 2)
        if caps_words >= 2:
            # ALL CAPS amplifies the strongest detected mood
            if mood_scores:
                top_mood = max(mood_scores, key=mood_scores.get)
                mood_scores[top_mood] *= 1.3
                triggers.append("CAPS_EMPHASIS")

        # Determine the dominant mood
        if mood_scores:
            detected_mood = max(mood_scores, key=mood_scores.get)
            raw_score = mood_scores[detected_mood]
            # Normalize confidence (cap at 1.0)
            confidence = min(1.0, raw_score)
        else:
            detected_mood = Mood.NEUTRAL
            confidence = 0.2  # Low confidence neutral

        reading = MoodReading(
            mood=detected_mood.value,
            confidence=confidence,
            valence=MOOD_VALENCE.get(detected_mood, 0.0),
            energy=MOOD_ENERGY.get(detected_mood, 0.5),
            triggers=triggers,
            user_text=text
        )

        return reading

    def update(self, text: str) -> MoodReading:
        """
        Analyze text and update the mood state.

        This is the main entry point — call it with each user message.

        Args:
            text: User's input text

        Returns:
            The new MoodReading
        """
        reading = self.analyze_text(text)

        # Only register if confidence meets threshold
        if reading.confidence < self._min_confidence:
            return reading

        # Track previous state for shift detection
        old_mood = self._state.current_mood
        old_valence = self._state.valence

        # Add to rolling window
        self._readings.append(reading)

        # Update aggregated state with exponential moving average
        alpha = self._smoothing_factor
        self._state.valence = alpha * reading.valence + (1 - alpha) * self._state.valence
        self._state.energy = alpha * reading.energy + (1 - alpha) * self._state.energy
        self._state.current_mood = reading.mood
        self._state.confidence = reading.confidence
        self._state.last_updated = time.time()
        self._state.readings_count += 1

        # Detect trend
        self._state.trend = self._detect_trend()

        # Check for significant mood shift
        valence_delta = self._state.valence - old_valence
        if (abs(valence_delta) >= self._shift_threshold and
                old_mood != reading.mood and
                self._on_mood_shift):
            try:
                self._on_mood_shift(old_mood, reading.mood, valence_delta)
            except Exception as e:
                logger.warning("Mood shift callback failed: %s", e)

        # Save periodically (every 5 readings)
        if self._state.readings_count % 5 == 0:
            self._save_history()

        logger.debug("Mood update: %s (conf=%.2f, valence=%.2f, trend=%s)",
                     reading.mood, reading.confidence, self._state.valence, self._state.trend)

        return reading

    def _detect_trend(self) -> str:
        """Detect mood trend from recent readings."""
        if len(self._readings) < 3:
            return "stable"

        recent = list(self._readings)[-5:]  # Last 5 readings
        valences = [r.valence for r in recent]

        # Simple linear trend
        if len(valences) >= 3:
            first_half = sum(valences[:len(valences)//2]) / max(1, len(valences)//2)
            second_half = sum(valences[len(valences)//2:]) / max(1, len(valences) - len(valences)//2)
            delta = second_half - first_half

            if delta > 0.2:
                return "improving"
            elif delta < -0.2:
                return "declining"

        return "stable"

    def get_current_mood(self) -> MoodState:
        """Get the current aggregated mood state."""
        return self._state

    def get_mood_for_prompt(self) -> str:
        """
        Get a concise mood description for injection into LLM prompts.

        Returns:
            Short mood context string, or empty string if no mood detected.
        """
        if self._state.readings_count == 0 or self._state.confidence < self._min_confidence:
            return ""

        mood = self._state.current_mood
        confidence = self._state.confidence
        trend = self._state.trend

        # Only include if reasonably confident
        if confidence < 0.4:
            return ""

        parts = [f"User mood: {mood}"]

        if trend == "improving":
            parts.append("(mood is improving)")
        elif trend == "declining":
            parts.append("(mood is declining)")

        # Add empathy guidance based on valence
        valence = self._state.valence
        if valence < -0.4:
            parts.append("Be extra gentle and supportive.")
        elif valence < -0.2:
            parts.append("Be warm and encouraging.")
        elif valence > 0.5:
            parts.append("Match their positive energy.")

        return " ".join(parts)

    def get_mood_summary(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get a summary of mood over the specified period.

        Args:
            hours: Number of hours to look back

        Returns:
            Summary dict with mood distribution, average valence, trend
        """
        cutoff = time.time() - (hours * 3600)
        recent = [r for r in self._readings if r.timestamp > cutoff]

        if not recent:
            return {
                'period_hours': hours,
                'readings_count': 0,
                'dominant_mood': 'neutral',
                'average_valence': 0.0,
                'average_energy': 0.5,
                'mood_distribution': {},
                'trend': 'stable'
            }

        # Count mood occurrences
        mood_counts: Dict[str, int] = {}
        total_valence = 0.0
        total_energy = 0.0

        for r in recent:
            mood_counts[r.mood] = mood_counts.get(r.mood, 0) + 1
            total_valence += r.valence
            total_energy += r.energy

        dominant_mood = max(mood_counts, key=mood_counts.get)
        avg_valence = total_valence / len(recent)
        avg_energy = total_energy / len(recent)

        return {
            'period_hours': hours,
            'readings_count': len(recent),
            'dominant_mood': dominant_mood,
            'average_valence': round(avg_valence, 2),
            'average_energy': round(avg_energy, 2),
            'mood_distribution': mood_counts,
            'trend': self._state.trend
        }

    def reset(self) -> None:
        """Reset all mood tracking data."""
        self._readings.clear()
        self._state = MoodState()
        self._save_history()
        logger.info("Mood tracker reset")

    def save(self) -> None:
        """Force save current state to disk."""
        self._save_history()


# ============================================================================
# Module-level singleton
# ============================================================================

_mood_tracker: Optional[MoodTracker] = None


def init_mood_tracker(data_path: Optional[Path] = None) -> MoodTracker:
    """
    Initialize the global mood tracker.

    Args:
        data_path: Optional path for mood history storage

    Returns:
        The initialized MoodTracker instance
    """
    global _mood_tracker
    _mood_tracker = MoodTracker(data_path)
    logger.info("Global MoodTracker initialized")
    return _mood_tracker


def get_mood_tracker() -> Optional[MoodTracker]:
    """Get the global mood tracker instance."""
    return _mood_tracker
