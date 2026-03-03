"""
NEXA Companion Mode Package
===========================

This package contains modules that make NEXA feel more alive and intelligent.
Each module is designed to be independent and can be enabled/disabled without
affecting core functionality.

Phase 28: Thinking State Feedback ✅
- thinking_feedback.py - Immediate acknowledgment and progress updates
- phrase_pools.py - Varied phrase pools for natural responses

Phase 29: Proactive Engagement ✅
- idle_monitor.py - Tracks user idle time and triggers proactive checks
- proactive_engine.py - Decides what/when to suggest proactively
- pattern_learner.py - Learns user patterns and routines

Phase 30: Emotional Intelligence ✅
- mood_tracker.py - Text-based mood detection and tracking
- emotional_memory.py - Emotional context, goals, milestones, journal
- event_tracker.py - Tracks mentioned events for check-in follow-ups

Phase 31: Personality & Fun (Future)
- personality_engine.py
- greeting_generator.py
- conversation_mode.py
- mini_games.py
"""

# Phase 28: Thinking State Feedback
from .thinking_feedback import ThinkingFeedback, init_thinking_feedback, get_thinking_feedback
from .phrase_pools import PhrasePools, get_phrase_pools

# Phase 29: Proactive Engagement
from .idle_monitor import IdleMonitor, IdleState, IdleConfig, init_idle_monitor, get_idle_monitor
from .proactive_engine import (
    ProactiveEngine, ProactiveSuggestion, SuggestionType, ProactiveContext,
    init_proactive_engine, get_proactive_engine
)
from .pattern_learner import PatternLearner, ActivityPattern, init_pattern_learner, get_pattern_learner

# Phase 30: Emotional Intelligence
from .mood_tracker import MoodTracker, Mood, MoodReading, MoodState, init_mood_tracker, get_mood_tracker
from .emotional_memory import (
    EmotionalMemory, EmotionalCategory, GoalStatus, EmotionalEntry, GoalEntry,
    init_emotional_memory, get_emotional_memory
)
from .event_tracker import (
    EventTracker, EventType, EventStatus, TrackedEvent,
    init_event_tracker, get_event_tracker
)

__all__ = [
    # Phase 28
    'ThinkingFeedback',
    'init_thinking_feedback',
    'get_thinking_feedback',
    'PhrasePools',
    'get_phrase_pools',
    
    # Phase 29
    'IdleMonitor',
    'IdleState',
    'IdleConfig',
    'init_idle_monitor',
    'get_idle_monitor',
    'ProactiveEngine',
    'ProactiveSuggestion',
    'SuggestionType',
    'ProactiveContext',
    'init_proactive_engine',
    'get_proactive_engine',
    'PatternLearner',
    'ActivityPattern',
    'init_pattern_learner',
    'get_pattern_learner',
    
    # Phase 30
    'MoodTracker',
    'Mood',
    'MoodReading',
    'MoodState',
    'init_mood_tracker',
    'get_mood_tracker',
    'EmotionalMemory',
    'EmotionalCategory',
    'GoalStatus',
    'EmotionalEntry',
    'GoalEntry',
    'init_emotional_memory',
    'get_emotional_memory',
    'EventTracker',
    'EventType',
    'EventStatus',
    'TrackedEvent',
    'init_event_tracker',
    'get_event_tracker',
]

__version__ = "3.0.0"
__phase__ = 30
