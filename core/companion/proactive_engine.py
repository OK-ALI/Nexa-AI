"""
Phase 29: Proactive Engine
==========================
Decides when and what to suggest to the user proactively.

This engine uses:
- Time of day context
- User idle duration
- Learned patterns (from pattern_learner.py)
- LLM for natural suggestion generation (no hardcoded phrases)

Conservative by design - suggests rarely but meaningfully.
"""

import time
import logging
from typing import Optional, Dict, Any, List, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class SuggestionType(Enum):
    """Types of proactive suggestions NEXA can make."""
    BREAK_REMINDER = "break_reminder"       # Suggest taking a break
    CHECK_IN = "check_in"                   # Friendly check-in
    WEATHER_UPDATE = "weather_update"       # Proactive weather info
    BATTERY_WARNING = "battery_warning"     # Battery getting low
    ROUTINE_PROMPT = "routine_prompt"       # Learned routine suggestion
    PRODUCTIVITY_TIP = "productivity_tip"   # Helpful work tip
    GREETING = "greeting"                   # Time-appropriate greeting
    # ACTION-ORIENTED SUGGESTIONS (NEXA offers to DO something)
    PLAY_MUSIC = "play_music"               # Offer to play music
    TELL_JOKE = "tell_joke"                 # Offer to lighten the mood
    FUN_FACT = "fun_fact"                   # Share an interesting fact
    TIME_UPDATE = "time_update"             # Tell the current time contextually


class TimeOfDay(Enum):
    """Time of day categories."""
    EARLY_MORNING = "early_morning"   # 5-8 AM
    MORNING = "morning"               # 8-12 PM
    AFTERNOON = "afternoon"           # 12-5 PM
    EVENING = "evening"               # 5-9 PM
    NIGHT = "night"                   # 9 PM - 12 AM
    LATE_NIGHT = "late_night"         # 12-5 AM


@dataclass
class ProactiveContext:
    """Context for generating a proactive suggestion."""
    idle_duration_seconds: float
    time_of_day: TimeOfDay
    current_hour: int
    day_of_week: int  # 0=Monday, 6=Sunday
    is_weekend: bool
    session_duration_seconds: float
    interactions_this_session: int
    battery_level: Optional[int] = None
    battery_charging: Optional[bool] = None
    last_weather_check: Optional[float] = None
    user_mood: Optional[str] = None
    recent_activities: List[str] = field(default_factory=list)


@dataclass
class ProactiveSuggestion:
    """A proactive suggestion to present to the user."""
    suggestion_type: SuggestionType
    message: str                      # LLM-generated message
    context: str                      # Why this suggestion was made
    confidence: float                 # 0-1, how confident we are this is wanted
    action: Optional[str] = None      # Optional action to take if accepted
    action_params: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LLM context."""
        return {
            "type": self.suggestion_type.value,
            "message": self.message,
            "context": self.context,
            "confidence": self.confidence,
            "action": self.action,
            "action_params": self.action_params
        }


class ProactiveEngine:
    """
    Decides what proactive suggestions to make and when.
    
    Uses LLM to generate natural, non-robotic suggestions.
    All logic is designed to be conservative - NEXA should feel
    helpful, not annoying.
    """
    
    def __init__(
        self,
        llm_generator: Optional[Callable[[str], str]] = None,
        battery_check: Optional[Callable[[], Tuple[int, bool]]] = None
    ):
        """
        Initialize the proactive engine.
        
        Args:
            llm_generator: Function to generate text via LLM (prompt -> response)
            battery_check: Function returning (battery_level, is_charging)
        """
        self._llm_generator = llm_generator
        self._battery_check = battery_check
        
        # State tracking
        self._pending_suggestion: Optional[ProactiveSuggestion] = None
        self._last_suggestion_type: Optional[SuggestionType] = None
        self._suggestion_history: List[Tuple[SuggestionType, float, bool]] = []  # (type, time, accepted)
        
        # Cooldowns per suggestion type (seconds)
        self._cooldowns: Dict[SuggestionType, float] = {
            SuggestionType.BREAK_REMINDER: 1800.0,    # 30 min
            SuggestionType.CHECK_IN: 1800.0,          # 30 min (reduced - it's lower priority now)
            SuggestionType.WEATHER_UPDATE: 7200.0,    # 2 hours
            SuggestionType.BATTERY_WARNING: 600.0,    # 10 min
            SuggestionType.ROUTINE_PROMPT: 3600.0,    # 1 hour
            SuggestionType.PRODUCTIVITY_TIP: 5400.0,  # 90 min
            SuggestionType.GREETING: 14400.0,         # 4 hours
            # Action-oriented suggestions (shorter cooldowns for variety)
            SuggestionType.PLAY_MUSIC: 900.0,         # 15 min (more frequent - most useful)
            SuggestionType.TELL_JOKE: 1800.0,         # 30 min
            SuggestionType.FUN_FACT: 1200.0,          # 20 min
            SuggestionType.TIME_UPDATE: 3600.0,       # 1 hour
        }
        
        # Track last time each type was suggested
        self._last_suggestion_time: Dict[SuggestionType, float] = {}
        
        logger.info("ProactiveEngine initialized")
    
    def set_llm_generator(self, generator: Callable[[str], str]) -> None:
        """Set the LLM generator function."""
        self._llm_generator = generator
    
    def set_battery_check(self, checker: Callable[[], Tuple[int, bool]]) -> None:
        """Set the battery check function."""
        self._battery_check = checker
    
    @staticmethod
    def get_time_of_day() -> TimeOfDay:
        """Get the current time of day category."""
        hour = datetime.now().hour
        
        if 5 <= hour < 8:
            return TimeOfDay.EARLY_MORNING
        elif 8 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 17:
            return TimeOfDay.AFTERNOON
        elif 17 <= hour < 21:
            return TimeOfDay.EVENING
        elif 21 <= hour < 24:
            return TimeOfDay.NIGHT
        else:
            return TimeOfDay.LATE_NIGHT
    
    def build_context(
        self,
        idle_duration: float,
        session_duration: float,
        interaction_count: int,
        recent_activities: Optional[List[str]] = None
    ) -> ProactiveContext:
        """
        Build the context for proactive suggestion decisions.
        
        Args:
            idle_duration: How long user has been idle (seconds)
            session_duration: How long session has been running (seconds)
            interaction_count: Number of interactions this session
            recent_activities: List of recent user activities
            
        Returns:
            ProactiveContext with all relevant information
        """
        now = datetime.now()
        
        battery_level = None
        battery_charging = None
        if self._battery_check:
            try:
                battery_level, battery_charging = self._battery_check()
            except Exception as e:
                logger.debug("Battery check failed: %s", e)
        
        return ProactiveContext(
            idle_duration_seconds=idle_duration,
            time_of_day=self.get_time_of_day(),
            current_hour=now.hour,
            day_of_week=now.weekday(),
            is_weekend=now.weekday() >= 5,
            session_duration_seconds=session_duration,
            interactions_this_session=interaction_count,
            battery_level=battery_level,
            battery_charging=battery_charging,
            recent_activities=recent_activities or []
        )
    
    def _can_suggest(self, suggestion_type: SuggestionType) -> bool:
        """Check if this suggestion type is off cooldown."""
        last_time = self._last_suggestion_time.get(suggestion_type, 0)
        cooldown = self._cooldowns.get(suggestion_type, 1800.0)
        return (time.time() - last_time) >= cooldown
    
    def _get_suggestion_prompt(
        self,
        suggestion_type: SuggestionType,
        context: ProactiveContext
    ) -> str:
        """
        Generate the LLM prompt for a specific suggestion type.
        
        All prompts request natural, conversational language.
        """
        base_context = f"""
You are NEXA, a friendly AI assistant. Generate a single SHORT proactive message (1-2 sentences max).
Be warm and natural, not robotic. Don't use phrases like "I noticed" or "According to my calculations".
Time: {context.time_of_day.value.replace('_', ' ')} ({context.current_hour}:00)
User has been idle for: {int(context.idle_duration_seconds / 60)} minutes
Session duration: {int(context.session_duration_seconds / 60)} minutes
"""
        
        type_prompts = {
            SuggestionType.BREAK_REMINDER: """
Generate a friendly suggestion for the user to take a short break.
Don't be preachy - keep it light and optional.
Example tone: "Hey, how about stretching your legs for a minute?"
""",
            SuggestionType.CHECK_IN: """
Generate a friendly check-in message.
Ask how they're doing or if they need help with anything.
Example tone: "Just checking in - need any help?"
""",
            SuggestionType.WEATHER_UPDATE: """
Suggest checking the weather or mention that you could provide a weather update.
Make it casual and helpful.
Example tone: "Want me to check what the weather's looking like?"
""",
            SuggestionType.BATTERY_WARNING: f"""
Battery is at {context.battery_level}% and {'charging' if context.battery_charging else 'not charging'}.
Generate a helpful battery low warning if needed.
Keep it informative but not alarming.
Example tone: "Heads up, battery's getting a bit low."
""",
            SuggestionType.ROUTINE_PROMPT: """
Suggest a common activity based on the time of day.
Morning: coffee, news, planning the day
Afternoon: lunch break, quick task
Evening: winding down, music
Example tone: "Evening vibes - want me to put on some music?"
""",
            SuggestionType.PRODUCTIVITY_TIP: """
Offer a brief, helpful productivity suggestion.
Keep it simple and optional.
Example tone: "Quick tip - want to clear out old tabs?"
""",
            SuggestionType.GREETING: """
Generate a time-appropriate greeting.
Morning: good morning type message
Evening: hope your day went well type message
Keep it warm but brief.
""",
            # ACTION-ORIENTED: NEXA offers to DO something
            SuggestionType.PLAY_MUSIC: """
Offer to play some music for the user. Be enthusiastic but not pushy.
Suggest a mood or genre based on time of day.
Morning: upbeat, energizing
Afternoon: focus, instrumental  
Evening: relaxing, chill
Example tone: "How about I put on some chill evening music?"
""",
            SuggestionType.TELL_JOKE: """
Offer to tell a joke or share something funny to lighten the mood.
Keep it playful and optional.
Example tone: "Want to hear something funny? I've got a good one!"
""",
            SuggestionType.FUN_FACT: """
Share an interesting, random fun fact. Just say it - don't ask permission.
Make it genuinely interesting and brief.
Topics: science, history, animals, space, weird facts
Example: "Did you know octopuses have three hearts? Pretty wild, right?"
""",
            SuggestionType.TIME_UPDATE: """
Give a casual time update with context. Don't just say the time - add personality.
Example tone: "It's almost 6 PM - evening's rolling in!"
"""
        }
        
        return base_context + type_prompts.get(suggestion_type, "Generate a friendly message.")
    
    def decide_suggestion(self, context: ProactiveContext) -> Optional[ProactiveSuggestion]:
        """
        Decide what (if any) proactive suggestion to make.
        
        This is the core decision logic. It's designed to be conservative.
        
        Args:
            context: Current proactive context
            
        Returns:
            ProactiveSuggestion if one should be made, None otherwise
        """
        # Priority order of suggestion types to consider
        candidates: List[Tuple[SuggestionType, float]] = []  # (type, confidence)
        
        logger.debug(f"💜 Evaluating proactive: idle={context.idle_duration_seconds:.1f}s, time_of_day={context.time_of_day.value}, hour={context.current_hour}")
        
        # Battery warning - highest priority if critical
        if context.battery_level is not None:
            if context.battery_level <= 15 and not context.battery_charging:
                if self._can_suggest(SuggestionType.BATTERY_WARNING):
                    candidates.append((SuggestionType.BATTERY_WARNING, 0.9))
        
        # Break reminder - after long work session
        if context.session_duration_seconds > 5400:  # 90 minutes
            if context.idle_duration_seconds > 120:  # At least 2 min idle
                if self._can_suggest(SuggestionType.BREAK_REMINDER):
                    # Higher confidence for longer sessions
                    confidence = min(0.8, 0.5 + (context.session_duration_seconds / 36000))
                    candidates.append((SuggestionType.BREAK_REMINDER, confidence))
        
        # Check-in - after short idle during waking hours (morning through evening)
        # REDUCED confidence so action-oriented suggestions take priority
        if context.time_of_day in [TimeOfDay.MORNING, TimeOfDay.AFTERNOON, TimeOfDay.EVENING]:
            if 30 < context.idle_duration_seconds < 1200:  # 30sec - 20 min idle
                if self._can_suggest(SuggestionType.CHECK_IN):
                    candidates.append((SuggestionType.CHECK_IN, 0.25))  # Lower confidence
        
        # Routine prompts - time-based
        if context.time_of_day == TimeOfDay.MORNING and context.current_hour in [8, 9]:
            if self._can_suggest(SuggestionType.ROUTINE_PROMPT):
                candidates.append((SuggestionType.ROUTINE_PROMPT, 0.6))
        elif context.time_of_day == TimeOfDay.EVENING and context.current_hour in [17, 18]:
            if self._can_suggest(SuggestionType.ROUTINE_PROMPT):
                candidates.append((SuggestionType.ROUTINE_PROMPT, 0.5))
        
        # Late night check-in
        if context.time_of_day == TimeOfDay.LATE_NIGHT:
            if context.session_duration_seconds > 7200:  # 2+ hours at night
                if self._can_suggest(SuggestionType.CHECK_IN):
                    candidates.append((SuggestionType.CHECK_IN, 0.7))
        
        # ============================================================
        # ACTION-ORIENTED SUGGESTIONS (NEXA offers to DO something)
        # These have HIGHER confidence to prioritize helpful actions
        # ============================================================
        
        # Play music - any time of day when idle (most common helpful action)
        if 45 < context.idle_duration_seconds < 600:  # 45s - 10 min idle
            if self._can_suggest(SuggestionType.PLAY_MUSIC):
                # Higher confidence during evening/night
                if context.time_of_day in [TimeOfDay.EVENING, TimeOfDay.NIGHT]:
                    candidates.append((SuggestionType.PLAY_MUSIC, 0.7))
                elif context.time_of_day == TimeOfDay.AFTERNOON:
                    candidates.append((SuggestionType.PLAY_MUSIC, 0.55))
                else:
                    candidates.append((SuggestionType.PLAY_MUSIC, 0.45))
        
        # Tell a joke - when user seems bored (longer idle, any time)
        if 60 < context.idle_duration_seconds < 600:  # 1-10 min idle
            if self._can_suggest(SuggestionType.TELL_JOKE):
                candidates.append((SuggestionType.TELL_JOKE, 0.5))
        
        # Fun fact - share something interesting (slightly random, delightful)
        if 45 < context.idle_duration_seconds < 480:  # 45s - 8 min idle
            if self._can_suggest(SuggestionType.FUN_FACT):
                candidates.append((SuggestionType.FUN_FACT, 0.5))
        
        # Time update - contextual time check during transitions
        if context.current_hour in [12, 17, 21]:  # Noon, 5 PM, 9 PM
            if 30 < context.idle_duration_seconds < 300:  # 30s - 5 min idle
                if self._can_suggest(SuggestionType.TIME_UPDATE):
                    candidates.append((SuggestionType.TIME_UPDATE, 0.45))
        
        # ============================================================
        # CONTEXTUAL SUGGESTIONS (previously unreachable - now enabled)
        # ============================================================
        
        # Greeting - time-appropriate greeting (morning/evening transitions)
        if context.current_hour in [8, 9] and context.time_of_day == TimeOfDay.MORNING:
            if 30 < context.idle_duration_seconds < 300:
                if self._can_suggest(SuggestionType.GREETING):
                    candidates.append((SuggestionType.GREETING, 0.55))
        elif context.current_hour in [17, 18] and context.time_of_day == TimeOfDay.EVENING:
            if 30 < context.idle_duration_seconds < 300:
                if self._can_suggest(SuggestionType.GREETING):
                    candidates.append((SuggestionType.GREETING, 0.45))
        
        # Weather update - proactive weather info during morning/afternoon
        if context.time_of_day in [TimeOfDay.MORNING, TimeOfDay.AFTERNOON]:
            if 60 < context.idle_duration_seconds < 600:
                if self._can_suggest(SuggestionType.WEATHER_UPDATE):
                    candidates.append((SuggestionType.WEATHER_UPDATE, 0.4))
        
        # Productivity tip - helpful work tip during work hours
        if context.time_of_day in [TimeOfDay.MORNING, TimeOfDay.AFTERNOON]:
            if 90 < context.idle_duration_seconds < 600:
                if not context.is_weekend:
                    if self._can_suggest(SuggestionType.PRODUCTIVITY_TIP):
                        candidates.append((SuggestionType.PRODUCTIVITY_TIP, 0.35))
        
        # Fallback check-in - only if no other candidates and user has been idle
        # This is the LAST resort, not the first choice
        if not candidates and 45 < context.idle_duration_seconds < 300:
            if self._can_suggest(SuggestionType.CHECK_IN):
                candidates.append((SuggestionType.CHECK_IN, 0.3))
                logger.debug(f"💜 Added fallback check-in (no other candidates)")
        
        logger.info(f"💜 Proactive candidates: {[(c[0].value, round(c[1], 2)) for c in candidates]}")
        
        if not candidates:
            logger.debug("No suitable proactive suggestions")
            return None
        
        # Sort by confidence and pick the best
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_type, confidence = candidates[0]
        
        logger.info("Selected proactive suggestion: %s (confidence: %.2f)",
                   best_type.value, confidence)
        
        # Generate the message via LLM
        message = self._generate_message(best_type, context)
        if not message:
            logger.warning("Failed to generate message for %s", best_type.value)
            return None
        
        suggestion = ProactiveSuggestion(
            suggestion_type=best_type,
            message=message,
            context=f"Idle {int(context.idle_duration_seconds/60)}min, {context.time_of_day.value}",
            confidence=confidence
        )
        
        # Record that we're making this suggestion
        self._last_suggestion_time[best_type] = time.time()
        self._pending_suggestion = suggestion
        
        return suggestion
    
    def _generate_message(
        self,
        suggestion_type: SuggestionType,
        context: ProactiveContext
    ) -> Optional[str]:
        """
        Generate a natural message using the LLM.
        
        Falls back to simple templates if LLM not available.
        """
        if self._llm_generator:
            try:
                prompt = self._get_suggestion_prompt(suggestion_type, context)
                response = self._llm_generator(prompt)
                if response and len(response.strip()) > 5:
                    return response.strip()
            except Exception as e:
                logger.error("LLM generation failed: %s", e)
        
        # Fallback templates (only used if LLM fails)
        fallbacks = {
            SuggestionType.BREAK_REMINDER: "How about a quick stretch?",
            SuggestionType.CHECK_IN: "Need any help?",
            SuggestionType.WEATHER_UPDATE: "Want me to check the weather?",
            SuggestionType.BATTERY_WARNING: f"Battery's at {context.battery_level}%.",
            SuggestionType.ROUTINE_PROMPT: "Anything I can help with?",
            SuggestionType.PRODUCTIVITY_TIP: "Want me to help organize something?",
            SuggestionType.GREETING: "Hey there!",
            # Action-oriented fallbacks
            SuggestionType.PLAY_MUSIC: "How about I put on some music?",
            SuggestionType.TELL_JOKE: "Want to hear something funny?",
            SuggestionType.FUN_FACT: "Did you know honey never spoils? Pretty cool, right!",
            SuggestionType.TIME_UPDATE: f"It's {context.current_hour}:00 - time flies!",
        }
        
        return fallbacks.get(suggestion_type, "Need anything?")
    
    def record_response(self, accepted: bool) -> None:
        """
        Record the user's response to the last suggestion.
        
        Args:
            accepted: True if user engaged with suggestion
        """
        if self._pending_suggestion:
            self._suggestion_history.append((
                self._pending_suggestion.suggestion_type,
                self._pending_suggestion.timestamp,
                accepted
            ))
            self._pending_suggestion = None
            
            logger.info("Proactive suggestion %s", "accepted" if accepted else "declined")
    
    def get_acceptance_rate(self, suggestion_type: Optional[SuggestionType] = None) -> float:
        """
        Get the acceptance rate for suggestions.
        
        Args:
            suggestion_type: Specific type, or None for overall rate
            
        Returns:
            Acceptance rate from 0.0 to 1.0
        """
        if not self._suggestion_history:
            return 0.5  # Default assumption
        
        relevant = self._suggestion_history
        if suggestion_type:
            relevant = [(t, ts, a) for t, ts, a in relevant if t == suggestion_type]
        
        if not relevant:
            return 0.5
        
        accepted = sum(1 for _, _, a in relevant if a)
        return accepted / len(relevant)
    
    def get_pending_suggestion(self) -> Optional[ProactiveSuggestion]:
        """Get the current pending suggestion if any."""
        return self._pending_suggestion
    
    def clear_pending(self) -> None:
        """Clear any pending suggestion."""
        self._pending_suggestion = None


# Module-level singleton
_proactive_engine: Optional[ProactiveEngine] = None


def init_proactive_engine(
    llm_generator: Optional[Callable[[str], str]] = None,
    battery_check: Optional[Callable[[], Tuple[int, bool]]] = None
) -> ProactiveEngine:
    """
    Initialize the global proactive engine.
    
    Args:
        llm_generator: Function to generate LLM responses
        battery_check: Function to check battery status
        
    Returns:
        The initialized ProactiveEngine instance
    """
    global _proactive_engine
    _proactive_engine = ProactiveEngine(llm_generator, battery_check)
    logger.info("Global ProactiveEngine initialized")
    return _proactive_engine


def get_proactive_engine() -> Optional[ProactiveEngine]:
    """Get the global proactive engine instance."""
    return _proactive_engine
