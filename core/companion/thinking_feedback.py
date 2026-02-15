"""
Thinking State Feedback Module
==============================

Provides immediate acknowledgment when NEXA starts processing,
and optional progress updates for long-running tasks.

This module makes NEXA feel responsive and alive by:
1. Immediately acknowledging the user's request
2. Providing updates during long operations
3. Using varied phrases to avoid repetition

Design Philosophy:
- Acknowledgment must be FAST (under 1 second)
- Phrases are SHORT (1-3 words)
- Non-blocking when possible
- Context-aware task classification
"""

import logging
import threading
import time
from typing import Optional, Callable, Dict, Any
from dataclasses import dataclass, field
from enum import Enum

from .phrase_pools import get_phrase_pools

logger = logging.getLogger(__name__)


class TaskType(Enum):
    """Classification of task types for appropriate feedback."""
    GENERAL = "general"
    SEARCH = "search"
    SYSTEM = "system"
    COMPLEX = "complex"
    CREATIVE = "creative"


@dataclass
class ThinkingContext:
    """Context for the current thinking state."""
    user_input: str
    task_type: TaskType = TaskType.GENERAL
    start_time: float = field(default_factory=time.time)
    acknowledged: bool = False
    progress_updates: int = 0
    is_cancelled: bool = False


class ThinkingFeedback:
    """
    Manages immediate acknowledgment and progress feedback.
    
    Usage:
        feedback = ThinkingFeedback(tts_speak_func)
        
        # At start of processing:
        feedback.start_thinking("open chrome")
        
        # During long operations (optional):
        feedback.update_progress()
        
        # When done:
        feedback.end_thinking()
    """
    
    def __init__(
        self,
        speak_func: Callable[..., None],
        emit_message_func: Optional[Callable[[str, str], None]] = None,
        enabled: bool = True
    ):
        """
        Initialize thinking feedback.
        
        Args:
            speak_func: Function to speak text. Signature: (text, ducking, silent) -> None
            emit_message_func: Optional function to emit UI messages. Signature: (role, msg) -> None
            enabled: Whether thinking feedback is enabled
        """
        self.speak_func = speak_func
        self.emit_message_func = emit_message_func
        self.enabled = enabled
        
        self.phrase_pools = get_phrase_pools()
        self.current_context: Optional[ThinkingContext] = None
        self.progress_timer: Optional[threading.Timer] = None
        self.lock = threading.Lock()
        
        # Configuration
        self.acknowledgment_delay = 0.4  # Seconds to wait before speaking (natural pause)
        self.progress_interval = 5.0  # Seconds between progress updates
        self.max_progress_updates = 3  # Maximum progress updates per task
        self.enable_progress_updates = True  # Can be disabled
        
        # Task type keywords for classification
        self._init_task_keywords()
        
        logger.info("🧠 ThinkingFeedback initialized (Phase 28)")
    
    def _init_task_keywords(self):
        """Initialize keyword patterns for task classification."""
        self.task_keywords: Dict[TaskType, list] = {
            TaskType.SEARCH: [
                "search", "find", "look up", "lookup", "what is", "who is",
                "where is", "how to", "weather", "news", "define", "meaning"
            ],
            TaskType.SYSTEM: [
                "open", "close", "launch", "start", "stop", "volume", "brightness",
                "screenshot", "maximize", "minimize", "wifi", "bluetooth", "mute",
                "unmute", "lock", "shutdown", "restart", "sleep"
            ],
            TaskType.COMPLEX: [
                "generate", "create file", "write code", "analyze", "summarize",
                "compare", "list all", "show all", "export", "download"
            ],
            TaskType.CREATIVE: [
                "write", "compose", "draft", "suggest", "help me with",
                "think about", "ideas for", "poem", "story", "email"
            ]
        }
        
        # Conversation patterns - these should NOT get acknowledgement
        # Simple greetings, questions about NEXA, casual chat
        self.conversation_patterns = [
            # Greetings
            "hi", "hello", "hey", "good morning", "good afternoon", "good evening",
            "good night", "sup", "what's up", "howdy", "yo",
            # Questions about NEXA
            "how are you", "who are you", "what are you", "what's your name",
            "what can you do", "are you there", "you okay", "how do you feel",
            "tell me about yourself", "what do you think", "do you like",
            # Casual chat
            "thank you", "thanks", "okay", "ok", "sure", "yes", "no", "maybe",
            "never mind", "nevermind", "forget it", "cool", "nice", "great",
            "i'm fine", "i am fine", "doing good", "doing well", "not much",
            "just asking", "just curious", "just wondering", "nothing",
            # Emotional/personal
            "i love you", "i like you", "you're cool", "you're awesome",
            "i'm bored", "i'm tired", "i'm happy", "i'm sad", "i'm angry",
            "tell me a joke", "make me laugh", "cheer me up"
        ]
    
    def _is_conversation(self, user_input: str) -> bool:
        """
        Check if this is casual conversation (no acknowledgement needed).
        
        Args:
            user_input: User's input text
            
        Returns:
            True if this is conversation, False if it's a task
        """
        input_lower = user_input.lower().strip()
        
        # Short inputs (under 4 words) that don't match task keywords are likely conversation
        word_count = len(input_lower.split())
        
        # Check if it matches conversation patterns
        for pattern in self.conversation_patterns:
            if pattern in input_lower or input_lower.startswith(pattern):
                return True
        
        # Very short inputs without task keywords = conversation
        if word_count <= 3:
            # Check if any task keyword is present
            for keywords in self.task_keywords.values():
                for keyword in keywords:
                    if keyword in input_lower:
                        return False  # Has task keyword, not conversation
            return True  # Short and no task keywords = conversation
        
        return False
    
    def _classify_task(self, user_input: str) -> TaskType:
        """
        Classify the task type based on user input.
        
        Args:
            user_input: User's input text
            
        Returns:
            Classified TaskType
        """
        input_lower = user_input.lower()
        
        # Check each task type's keywords
        for task_type, keywords in self.task_keywords.items():
            for keyword in keywords:
                if keyword in input_lower:
                    logger.debug(f"Task classified as {task_type.value} (matched: '{keyword}')")
                    return task_type
        
        return TaskType.GENERAL
    
    def start_thinking(self, user_input: str) -> bool:
        """
        Start thinking feedback - speak acknowledgment after natural pause.
        
        This should be called at the VERY START of processing,
        before any LLM calls or heavy operations.
        
        Acknowledgements are SKIPPED for:
        - Simple conversations (greetings, chat, questions about NEXA)
        - Short phrases without task keywords
        
        The acknowledgment is spoken in SILENT mode so NEXA stays in
        THINKING state visually (orb keeps thinking animation).
        
        Args:
            user_input: User's input text
            
        Returns:
            True if acknowledgment was spoken, False otherwise
        """
        if not self.enabled:
            logger.debug("ThinkingFeedback disabled, skipping acknowledgment")
            return False
        
        # Skip acknowledgement for casual conversation
        if self._is_conversation(user_input):
            logger.debug(f"💬 Conversation detected, skipping acknowledgement: '{user_input[:50]}...'")
            return False
        
        with self.lock:
            # Cancel any existing context
            if self.current_context:
                self._cancel_progress_timer()
            
            # Classify the task
            task_type = self._classify_task(user_input)
            
            # Create new context
            self.current_context = ThinkingContext(
                user_input=user_input,
                task_type=task_type
            )
            
            # Get appropriate acknowledgment phrase
            phrase = self.phrase_pools.get_acknowledgment(task_type.value)
            
            logger.info(f"🎯 Acknowledging ({task_type.value}): '{phrase}'")
            
            try:
                # Issue 3 Fix: Add natural pause before speaking (feels less robotic)
                # This gives the visual THINKING state time to display
                time.sleep(self.acknowledgment_delay)
                
                # Issue 1 Fix: Speak with silent=True so we stay in THINKING state
                # The TTS won't trigger state callbacks, keeping the thinking animation
                self.speak_func(phrase, True, True)  # (text, ducking=True, silent=True)
                self.current_context.acknowledged = True
                
                # Optionally emit to UI (as "thinking" not "nexa" to distinguish)
                if self.emit_message_func:
                    self.emit_message_func("thinking", phrase)
                
                # Start progress timer for long tasks
                if self.enable_progress_updates:
                    self._start_progress_timer()
                
                return True
                
            except Exception as e:
                logger.error(f"Error speaking acknowledgment: {e}")
                return False
    
    def _start_progress_timer(self):
        """Start a timer to provide progress updates for long tasks."""
        self._cancel_progress_timer()
        
        def progress_callback():
            self.update_progress()
        
        self.progress_timer = threading.Timer(self.progress_interval, progress_callback)
        self.progress_timer.daemon = True
        self.progress_timer.start()
    
    def _cancel_progress_timer(self):
        """Cancel any pending progress timer."""
        if self.progress_timer:
            self.progress_timer.cancel()
            self.progress_timer = None
    
    def update_progress(self) -> bool:
        """
        Provide a progress update during long operations.
        
        This can be called:
        1. Automatically by the timer
        2. Manually when a long operation is detected
        
        Returns:
            True if progress was spoken, False otherwise
        """
        if not self.enabled or not self.enable_progress_updates:
            return False
        
        with self.lock:
            if not self.current_context or self.current_context.is_cancelled:
                return False
            
            # Check if we've hit max updates
            if self.current_context.progress_updates >= self.max_progress_updates:
                logger.debug("Max progress updates reached")
                return False
            
            # Get progress phrase
            task_type = self.current_context.task_type
            phrase = self.phrase_pools.get_progress(task_type.value)
            
            elapsed = time.time() - self.current_context.start_time
            logger.info(f"🔄 Progress update ({elapsed:.1f}s elapsed): '{phrase}'")
            
            try:
                # Use silent=True to stay in THINKING state during progress updates
                self.speak_func(phrase, True, True)  # (text, ducking=True, silent=True)
                self.current_context.progress_updates += 1
                
                # Schedule next update if not at max
                if self.current_context.progress_updates < self.max_progress_updates:
                    self._start_progress_timer()
                
                return True
                
            except Exception as e:
                logger.error(f"Error speaking progress: {e}")
                return False
    
    def end_thinking(self, success: bool = True):
        """
        End the thinking state and clean up.
        
        Args:
            success: Whether the task completed successfully
        """
        with self.lock:
            self._cancel_progress_timer()
            
            if self.current_context:
                elapsed = time.time() - self.current_context.start_time
                updates = self.current_context.progress_updates
                logger.info(
                    f"✅ Thinking ended (elapsed: {elapsed:.2f}s, "
                    f"progress updates: {updates})"
                )
                self.current_context = None
    
    def cancel(self):
        """Cancel current thinking feedback (user interrupted)."""
        with self.lock:
            self._cancel_progress_timer()
            if self.current_context:
                self.current_context.is_cancelled = True
                logger.info("🛑 Thinking feedback cancelled")
            self.current_context = None
    
    def set_enabled(self, enabled: bool):
        """Enable or disable thinking feedback."""
        self.enabled = enabled
        if not enabled:
            self.cancel()
        logger.info(f"ThinkingFeedback {'enabled' if enabled else 'disabled'}")
    
    def set_progress_updates(self, enabled: bool):
        """Enable or disable progress updates (acknowledgments still work)."""
        self.enable_progress_updates = enabled
        if not enabled:
            self._cancel_progress_timer()
        logger.info(f"Progress updates {'enabled' if enabled else 'disabled'}")


# Module-level singleton
_thinking_feedback: Optional[ThinkingFeedback] = None


def get_thinking_feedback() -> Optional[ThinkingFeedback]:
    """Get the singleton ThinkingFeedback instance."""
    return _thinking_feedback


def init_thinking_feedback(
    speak_func: Callable[[str, bool], None],
    emit_message_func: Optional[Callable[[str, str], None]] = None,
    enabled: bool = True
) -> ThinkingFeedback:
    """
    Initialize the singleton ThinkingFeedback instance.
    
    Args:
        speak_func: Function to speak text
        emit_message_func: Optional function to emit UI messages
        enabled: Whether to enable thinking feedback
        
    Returns:
        ThinkingFeedback instance
    """
    global _thinking_feedback
    _thinking_feedback = ThinkingFeedback(speak_func, emit_message_func, enabled)
    return _thinking_feedback
