"""
Intent State - Unified Follow-up Handler

Manages ALL follow-up scenarios for Smart Memory:
- Incomplete commands (e.g., "play music" without song name)
- Counting follow-ups ("how many?")
- Listing follow-ups ("what are they?")
- Pronoun resolution context ("close it")
- Cancel commands ("forget it", "never mind")
- Auto-expires after timeout (2 minutes)
- Overrides on new command detection
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict

logger = logging.getLogger(__name__)


# Cancel phrases that clear pending intent
CANCEL_PHRASES = [
    "forget it", "never mind", "cancel", "stop", 
    "don't worry", "skip it", "no thanks", "nothing",
    "forget that", "cancel that", "nevermind"
]

# Counting question patterns
COUNTING_PATTERNS = [
    r'\bhow many\b', r'\bcount\b', r'\btotal\b', r'\bnumber of\b',
    r'\bwhat\'?s the count\b', r'\bhow much\b'
]

# Listing question patterns
LISTING_PATTERNS = [
    r'\bwhat are they\b', r'\blist them\b', r'\bwhat are the\b',
    r'\bshow them\b', r'\bname them\b', r'\btell me\b',
    r'\bwhat\'?s their name\b', r'\bwhat were they\b'
]


@dataclass
class PendingIntent:
    """Represents an incomplete intent awaiting follow-up."""
    intent: str                       # e.g., "play_music" or "clarification:set"
    data_needed: str                  # e.g., "song_name" or "target" (volume/brightness)
    collected_data: Dict[str, Any] = field(default_factory=dict)
    original_command: str = ""        # Original user command (for value extraction)
    clarification_question: str = ""  # The question asked (for context)
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(default_factory=lambda: datetime.now() + timedelta(minutes=2))
    is_proactive: bool = False        # Phase 29: True if this is a proactive suggestion
    
    def is_expired(self) -> bool:
        """Check if this intent has expired."""
        return datetime.now() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON storage."""
        return {
            'intent': self.intent,
            'data_needed': self.data_needed,
            'collected_data': self.collected_data,
            'original_command': self.original_command,
            'clarification_question': self.clarification_question,
            'created_at': self.created_at.isoformat(),
            'expires_at': self.expires_at.isoformat(),
            'is_proactive': self.is_proactive,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PendingIntent':
        """Create from dictionary."""
        return cls(
            intent=data['intent'],
            data_needed=data['data_needed'],
            collected_data=data.get('collected_data', {}),
            original_command=data.get('original_command', ''),
            clarification_question=data.get('clarification_question', ''),
            created_at=datetime.fromisoformat(data['created_at']),
            expires_at=datetime.fromisoformat(data['expires_at']),
            is_proactive=data.get('is_proactive', False),
        )


class IntentState:
    """
    Manages pending intents and dynamic follow-ups.
    
    Features:
    - Set pending intent when data is missing
    - Resolve follow-up responses
    - Cancel detection ("forget it", "cancel")
    - Automatic timeout (2 minutes)
    - Override on new command
    """
    
    TIMEOUT_SECONDS = 120  # 2 minutes
    
    def __init__(self, state_file: Optional[Path] = None):
        """
        Initialize intent state manager.
        
        Args:
            state_file: Optional file for persistence (survives restarts)
        """
        self.state_file = state_file
        self._pending: Optional[PendingIntent] = None
        
        # Intent registry: maps intent to required fields
        self._registry: Dict[str, List[str]] = {}
        self._setup_default_intents()
        
        # Load any persisted state
        if state_file:
            self._load_state()
    
    def _setup_default_intents(self) -> None:
        """Register default intents and their required fields."""
        self._registry = {
            'play_music': ['song_name'],
            'open_application': ['app_name'],
            'launch_game': ['game_name'],
            'set_volume': ['level'],
            'set_brightness': ['level'],
            'search_web': ['query'],
            'navigate_to': ['url'],
            'send_email': ['recipient', 'subject'],
            'set_reminder': ['text', 'time'],
            'share_file': ['file_path', 'platform'],
            'play_youtube_result': ['number'],
        }
        
        # =====================================================================
        # UNIFIED CONTEXT: Last action/result storage for follow-ups
        # =====================================================================
        self._last_action: Optional[str] = None
        self._last_action_data: Dict[str, Any] = {}
        self._last_result: Any = None
        self._last_list: List[str] = []
        self._last_target: Optional[str] = None
        self._action_timestamp: Optional[datetime] = None
    
    # =========================================================================
    # UNIFIED FOLLOW-UP DETECTION (replaces scattered implementations)
    # =========================================================================
    
    def is_counting_question(self, text: str) -> bool:
        """
        Detect if user is asking for a count ("how many?", "what's the count?").
        
        Args:
            text: User input
            
        Returns:
            True if counting question detected
        """
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in COUNTING_PATTERNS)
    
    def is_listing_question(self, text: str) -> bool:
        """
        Detect if user wants details/names ("what are they?", "list them").
        
        Args:
            text: User input
            
        Returns:
            True if listing question detected
        """
        text_lower = text.lower()
        return any(re.search(pattern, text_lower) for pattern in LISTING_PATTERNS)
    
    def is_follow_up_question(self, text: str) -> bool:
        """
        Detect if this is any kind of follow-up question.
        
        Args:
            text: User input
            
        Returns:
            True if this is a follow-up to previous action
        """
        return self.is_counting_question(text) or self.is_listing_question(text)
    
    # =========================================================================
    # LAST ACTION CONTEXT (replaces ContextManager.action_stack)
    # =========================================================================
    
    def set_last_action(
        self, 
        action: str, 
        data: Dict[str, Any] = None, 
        result: Any = None,
        target: str = None,
        result_list: List[str] = None
    ) -> None:
        """
        Store the last executed action for follow-up reference.
        
        Args:
            action: Action identifier (e.g., 'list_games', 'open_application')
            data: Action parameters
            result: Action result (string or data)
            target: Primary target (e.g., 'chrome' for open_application)
            result_list: List result (e.g., list of games)
        """
        self._last_action = action
        self._last_action_data = data or {}
        self._last_result = result
        self._last_target = target
        self._last_list = result_list or []
        self._action_timestamp = datetime.now()
        
        logger.debug(f"📌 Stored action context: {action} (target={target})")
    
    def get_last_action(self) -> Optional[str]:
        """Get the last executed action name."""
        return self._last_action
    
    def get_last_result(self) -> Any:
        """Get the result of the last action."""
        return self._last_result
    
    def get_last_target(self) -> Optional[str]:
        """Get the last action target (e.g., app name for open/close)."""
        return self._last_target
    
    def get_last_list(self) -> List[str]:
        """Get the last list result (e.g., from list_games)."""
        return self._last_list
    
    def has_recent_context(self, max_age_seconds: int = 60) -> bool:
        """
        Check if there's recent action context (not stale).
        
        Args:
            max_age_seconds: Maximum age to consider "recent"
            
        Returns:
            True if context is recent enough
        """
        if not self._action_timestamp:
            return False
        age = (datetime.now() - self._action_timestamp).total_seconds()
        return age < max_age_seconds
    
    # =========================================================================
    # FOLLOW-UP ANSWER GENERATION
    # =========================================================================
    
    def answer_follow_up(self, text: str) -> Optional[str]:
        """
        Try to answer a follow-up question from cached context.
        
        Args:
            text: User's follow-up question
            
        Returns:
            Answer string or None if can't answer from cache
        """
        if not self.has_recent_context(max_age_seconds=120):
            return None
        
        # Handle counting questions
        if self.is_counting_question(text):
            return self._answer_counting_question()
        
        # Handle listing questions
        if self.is_listing_question(text):
            return self._answer_listing_question()
        
        return None
    
    def _answer_counting_question(self) -> Optional[str]:
        """Generate answer for counting question."""
        # If we have a list, count it
        if self._last_list:
            count = len(self._last_list)
            action = self._last_action or ""
            
            if 'game' in action:
                return f"{count} games"
            elif 'app' in action or 'running' in action:
                return f"{count} applications"
            elif 'network' in action or 'wifi' in action:
                return f"{count} networks"
            elif 'music' in action or 'song' in action:
                return f"{count} songs"
            else:
                return f"{count} items"
        
        # Try to extract count from result string
        if self._last_result:
            result_str = str(self._last_result)
            count_patterns = [
                r'Found (\d+)',
                r'(\d+) games',
                r'(\d+) apps',
                r'(\d+) applications',
                r'(\d+) networks',
                r'(\d+) songs',
            ]
            for pattern in count_patterns:
                match = re.search(pattern, result_str, re.IGNORECASE)
                if match:
                    return match.group(1)
        
        return None
    
    def _answer_listing_question(self) -> Optional[str]:
        """Generate answer for listing question."""
        if not self._last_list:
            return None
        
        items = self._last_list
        
        # Format based on count
        if len(items) <= 5:
            return ", ".join(items)
        elif len(items) <= 10:
            listed = ", ".join(items[:8])
            return f"{listed}, and {len(items) - 8} more"
        else:
            listed = ", ".join(items[:5])
            return f"{listed}, and {len(items) - 5} others"
    
    # =========================================================================
    # PRONOUN RESOLUTION CONTEXT
    # =========================================================================
    
    def resolve_ordinal(self, ordinal: str) -> Optional[str]:
        """
        Resolve ordinal reference using last list.
        
        Args:
            ordinal: Ordinal word ('first', 'second', 'last', etc.)
            
        Returns:
            Resolved item name or None
        """
        if not self._last_list:
            return None
        
        ordinal_map = {
            'first': 0, '1st': 0,
            'second': 1, '2nd': 1,
            'third': 2, '3rd': 2,
            'fourth': 3, '4th': 3,
            'fifth': 4, '5th': 4,
            'last': -1,
            'previous': -2,
        }
        
        index = ordinal_map.get(ordinal.lower())
        if index is None:
            return None
        
        try:
            return self._last_list[index]
        except IndexError:
            return None
    
    # =========================================================================
    # State Management
    # =========================================================================
    
    def set_pending_intent(
        self, 
        intent: str, 
        data_needed: str,
        collected_data: Dict[str, Any] = None,
        original_command: str = "",
        clarification_question: str = ""
    ) -> None:
        """
        Set a pending intent awaiting follow-up.
        
        Args:
            intent: Intent identifier (e.g., "play_music")
            data_needed: What data is missing (e.g., "song_name")
            collected_data: Any data already collected
            original_command: The original user command (for value extraction)
            clarification_question: The question being asked
        """
        self._pending = PendingIntent(
            intent=intent,
            data_needed=data_needed,
            collected_data=collected_data or {},
            original_command=original_command,
            clarification_question=clarification_question
        )
        
        logger.info(f"📋 Pending intent set: {intent} (need: {data_needed})")
        self._save_state()
    
    def set_clarification_pending(
        self,
        clarification_type: str,
        question: str,
        original_command: str,
        collected_data: Dict[str, Any] = None
    ) -> None:
        """
        Set a pending clarification (unified with intent system).
        
        This replaces the old ClarificationHandler storage system.
        
        Args:
            clarification_type: Type of clarification (e.g., "set", "open", "play")
            question: The clarification question being asked
            original_command: The original user command (for value extraction)
            collected_data: Any data already extracted from original command
        """
        # Extract any numbers from original command for later use
        if collected_data is None:
            collected_data = {}
        
        # Auto-extract value if it's a "set" command with a number
        if clarification_type == "set" and 'value' not in collected_data:
            number_match = re.search(r'\d+', original_command)
            if number_match:
                collected_data['value'] = int(number_match.group())
        
        self._pending = PendingIntent(
            intent=f"clarification:{clarification_type}",
            data_needed="target",  # What target (volume, brightness, app, etc.)
            collected_data=collected_data,
            original_command=original_command,
            clarification_question=question
        )
        
        logger.info(f"❓ Clarification pending: {clarification_type} (original: '{original_command}')")
        self._save_state()
    
    def resolve_clarification(self, user_answer: str) -> Optional[str]:
        """
        Resolve a pending clarification with user's answer.
        
        Args:
            user_answer: User's response to clarification question
            
        Returns:
            Reformulated command string, or None if can't resolve
        """
        if not self.has_pending_intent():
            return None
        
        pending = self._pending
        if not pending.intent.startswith("clarification:"):
            return None  # Not a clarification, let normal handler deal with it
        
        clarification_type = pending.intent.replace("clarification:", "")
        answer_lower = user_answer.lower().strip()
        original = pending.original_command
        collected = pending.collected_data
        
        # Clear the pending state
        self.clear()
        
        # Reformulate based on clarification type
        if clarification_type == "set":
            return self._reformulate_set(answer_lower, original, collected)
        elif clarification_type == "open":
            return f"open {user_answer}"
        elif clarification_type == "close":
            return f"close {user_answer}"
        elif clarification_type == "launch":
            return f"launch {user_answer}"
        elif clarification_type == "play":
            return f"play {user_answer}"
        elif clarification_type == "find":
            return f"find {user_answer}"
        elif clarification_type == "search":
            return f"search for {user_answer}"
        
        # Generic fallback
        return user_answer
    
    def _reformulate_set(self, answer: str, original: str, collected: Dict) -> str:
        """Reformulate a 'set' command with the clarified target."""
        value = collected.get('value')
        
        if 'volume' in answer:
            if value is not None:
                return f"set volume to {value}"
            return "get volume"
        elif 'brightness' in answer or 'bright' in answer:
            if value is not None:
                return f"set brightness to {value}"
            return "get brightness"
        
        # Fallback: try to construct from original + answer
        if value is not None:
            return f"set {answer} to {value}"
        return f"get {answer}"
    
    def has_pending_intent(self) -> bool:
        """Check if there's a non-expired pending intent."""
        if self._pending is None:
            return False
        
        if self._pending.is_expired():
            logger.info(f"⏰ Pending intent expired: {self._pending.intent}")
            self.clear()
            return False
        
        return True
    
    def get_pending_intent(self) -> Optional[PendingIntent]:
        """Get the current pending intent (or None if expired/missing)."""
        if self.has_pending_intent():
            return self._pending
        return None
    
    def clear(self) -> None:
        """Clear any pending intent."""
        if self._pending:
            logger.info(f"🗑️ Cleared pending intent: {self._pending.intent}")
        self._pending = None
        self._save_state()
    
    # =========================================================================
    # Follow-up Processing
    # =========================================================================
    
    def process_input(self, user_input: str) -> Dict[str, Any]:
        """
        Process user input in context of pending intent.
        
        Returns:
            Dict with:
            - action: 'cancel', 'resolve', 'new_command', or 'no_pending'
            - intent: The intent (if resolved)
            - data: The complete data (if resolved)
            - message: Human-readable status message
        """
        user_lower = user_input.lower().strip()
        
        # Priority 1: Check for cancel
        if self._is_cancel(user_lower):
            self.clear()
            return {
                'action': 'cancel',
                'message': "No problem, cancelled!"
            }
        
        # Priority 2: Check for pending intent
        if not self.has_pending_intent():
            return {
                'action': 'no_pending',
                'message': "No pending intent"
            }
        
        pending = self._pending
        
        # Priority 3: Check if expired
        if pending.is_expired():
            self.clear()
            return {
                'action': 'expired',
                'message': "Previous request has expired"
            }
        
        # Priority 4: Check if this is a new unrelated command
        if self._is_new_command(user_input):
            old_intent = pending.intent
            self.clear()
            return {
                'action': 'new_command',
                'old_intent': old_intent,
                'message': f"Cancelled '{old_intent}', processing new request"
            }
        
        # Priority 5: Resolve the follow-up
        # The user input is the answer to what we were waiting for
        pending.collected_data[pending.data_needed] = user_input
        
        complete_data = pending.collected_data.copy()
        intent = pending.intent
        
        self.clear()
        
        return {
            'action': 'resolve',
            'intent': intent,
            'data': complete_data,
            'message': f"Got it! Executing {intent}..."
        }
    
    def _is_cancel(self, text: str) -> bool:
        """Check if text is a cancel command."""
        return any(phrase in text for phrase in CANCEL_PHRASES)
    
    def _is_new_command(self, text: str) -> bool:
        """
        Check if text appears to be a new, unrelated command.
        
        Context-aware: considers the pending intent type to avoid
        false positives (e.g., "Play Bohemian Rhapsody" is NOT a new
        command when we're waiting for a song name).
        """
        text_lower = text.lower().strip()
        words = text_lower.split()
        if not words:
            return False
        
        first_word = words[0]
        
        # Map of intent types to their "expected" leading verbs
        # If the first word matches the pending intent's verb, it's likely an answer
        intent_verb_map = {
            'play_music': ['play'],
            'open_application': ['open', 'launch', 'start'],
            'launch_game': ['launch', 'play', 'start', 'open'],
            'search_web': ['search', 'find', 'look'],
            'set_volume': ['set'],
            'set_brightness': ['set'],
            'navigate_to': ['go', 'open', 'navigate'],
            'share_file': ['share'],
        }
        
        # If the first word is a verb that matches what we're waiting for, it's an answer
        if self._pending:
            expected_verbs = intent_verb_map.get(self._pending.intent, [])
            if first_word in expected_verbs:
                return False  # Likely an answer, not a new command
        
        # Command verbs that indicate a genuinely new command
        command_verbs = [
            'open', 'close', 'launch', 'start', 'stop', 'set', 'get',
            'show', 'tell', 'search', 'pause', 'skip', 'check', 'find'
        ]
        
        # Only flag as new command if it starts with a command verb AND is complex
        if first_word in command_verbs and len(words) > 4:
            return True
        
        # Questions are new commands only if they're clearly unrelated (5+ words)
        question_words = ['what', 'how', 'when', 'where', 'why', 'who']
        if first_word in question_words and len(words) >= 4:
            return True
        
        return False
    
    def get_follow_up_prompt(self) -> Optional[str]:
        """
        Get the follow-up prompt for the current pending intent.
        
        Returns:
            Question to ask user, or None if no pending intent
        """
        if not self.has_pending_intent():
            return None
        
        pending = self._pending
        
        # Generate natural prompt based on what's needed
        prompts = {
            'song_name': "Which song would you like me to play?",
            'app_name': "Which application should I open?",
            'game_name': "Which game would you like to launch?",
            'level': "What level should I set it to?",
            'query': "What would you like me to search for?",
            'url': "Which website should I navigate to?",
            'recipient': "Who should I send this to?",
            'subject': "What's the subject?",
            'text': "What should I remind you about?",
            'time': "When should I remind you?",
            'file_path': "Which file would you like to share?",
            'platform': "Where would you like to share it?",
        }
        
        return prompts.get(pending.data_needed, f"Please provide the {pending.data_needed}:")
    
    # =========================================================================
    # Intent Registry
    # =========================================================================
    
    def register_intent(self, intent: str, required_fields: List[str]) -> None:
        """
        Register an intent with its required fields.
        
        Args:
            intent: Intent identifier
            required_fields: List of required field names
        """
        self._registry[intent] = required_fields
        logger.debug(f"📝 Registered intent: {intent} → {required_fields}")
    
    def get_intent_requirements(self, intent: str) -> List[str]:
        """Get required fields for an intent."""
        return self._registry.get(intent, [])
    
    def check_missing_data(self, intent: str, provided_data: Dict[str, Any]) -> Optional[str]:
        """
        Check which data is missing for an intent.
        
        Returns:
            First missing field name, or None if complete
        """
        required = self._registry.get(intent, [])
        for field in required:
            if field not in provided_data or not provided_data[field]:
                return field
        return None
    
    # =========================================================================
    # Persistence
    # =========================================================================
    
    def _save_state(self) -> None:
        """Save state to file."""
        if not self.state_file:
            return
        
        try:
            state = {
                'pending': self._pending.to_dict() if self._pending else None,
                'saved_at': datetime.now().isoformat()
            }
            
            self.state_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
                
        except Exception as e:
            logger.error(f"Error saving intent state: {e}")
    
    def _load_state(self) -> None:
        """Load state from file."""
        if not self.state_file or not self.state_file.exists():
            return
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state = json.load(f)
            
            if state.get('pending'):
                pending = PendingIntent.from_dict(state['pending'])
                
                # Check if still valid
                if not pending.is_expired():
                    self._pending = pending
                    logger.info(f"📋 Restored pending intent: {pending.intent}")
                else:
                    logger.info("⏰ Discarded expired pending intent from disk")
                    
        except Exception as e:
            logger.error(f"Error loading intent state: {e}")
    
    def get_state_summary(self) -> Dict[str, Any]:
        """Get current state summary for debugging."""
        if not self.has_pending_intent():
            return {'status': 'idle', 'pending': None}
        
        pending = self._pending
        remaining = (pending.expires_at - datetime.now()).total_seconds()
        
        return {
            'status': 'waiting',
            'intent': pending.intent,
            'waiting_for': pending.data_needed,
            'collected': pending.collected_data,
            'expires_in_seconds': max(0, remaining),
        }
