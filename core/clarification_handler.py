"""
Clarification Handler Module for Nexa AI.

Extracted from brain.py to improve code organization.
Handles clarification questions, ambiguity detection, and command reformulation.

NOW UNIFIED: Uses IntentState for ALL storage (no more separate buggy system).
The ClarificationHandler only handles DETECTION - IntentState handles STORAGE.

Author: Ali Adil Waseem
"""

import re
import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ClarificationHandler:
    """
    Handles clarification logic for ambiguous or incomplete commands.
    
    NOTE: Now unified with IntentState! This class only handles:
    - DETECTION: Detecting when clarification is needed
    - DELEGATION: Delegating storage to IntentState
    
    IntentState handles:
    - STORAGE: Storing pending clarifications with timeout
    - RESOLUTION: Reformulating commands when user responds
    
    Provides methods for:
    - Detecting when clarification is needed
    - Asking clarification questions (via IntentState)
    - Processing clarification responses (via IntentState)
    """
    
    def __init__(self, context_manager=None, executor=None):
        """
        Initialize the ClarificationHandler.
        
        Args:
            context_manager: ContextManager instance for storing state
            executor: Executor instance for getting suggestions
        """
        self.context_manager = context_manager
        self.executor = executor
        
        # Track current command being processed (for storing original when asking clarification)
        self._current_command = None
        
        # Vague commands that need targets
        self.vague_commands = {
            'open': 'What would you like me to open?',
            'close': 'Which app would you like me to close?',
            'launch': 'What should I launch?',
            'start': 'What would you like me to start?',
            'stop': 'What should I stop?',
            'show': 'What would you like me to show?',
            'find': 'What are you looking for?',
            'search': 'What would you like me to search for?',
            'play': 'What should I play?',
        }
    
    def set_dependencies(self, context_manager, executor):
        """
        Set dependencies after initialization.
        
        Args:
            context_manager: ContextManager instance
            executor: Executor instance
        """
        self.context_manager = context_manager
        self.executor = executor
    
    def set_current_command(self, command: str):
        """
        Set the current command being processed.
        Call this BEFORE requires_clarification() to store the original command.
        
        Args:
            command: The user's original command text
        """
        self._current_command = command
    
    def requires_clarification(self, user_text: str, func_name: str, func_params: Dict[str, Any]) -> Optional[str]:
        """
        Detect if command needs clarification due to missing parameters or ambiguity.
        
        Args:
            user_text: Original user input
            func_name: Detected function name
            func_params: Function parameters extracted by AI
            
        Returns:
            Clarification question string or None if no clarification needed
        """
        text_lower = user_text.lower().strip()
        
        # Pattern 1: Vague action verbs without objects
        for command, question in self.vague_commands.items():
            # Match exact command or "can you [command]" without any target
            if (text_lower == command or 
                text_lower == f"{command} it" or
                text_lower == f"can you {command}" or
                text_lower == f"please {command}"):
                logger.info(f"❓ Clarification needed: vague command '{command}' without target")
                return question
        
        # Pattern 2: Ambiguous "set" commands without specifying what
        if text_lower.startswith('set ') or 'set it to' in text_lower or 'set to' in text_lower:
            has_target = any(word in text_lower for word in ['volume', 'brightness', 'sound'])
            if not has_target:
                logger.info(f"❓ Clarification needed: ambiguous 'set' command")
                return "Set what? Volume or brightness?"
        
        # Pattern 3: Question about "level" without context
        if any(phrase in text_lower for phrase in ["what's the level", "what is the level", "check the level", "the level"]):
            has_context = any(word in text_lower for word in ['volume', 'brightness', 'battery'])
            if not has_context:
                logger.info(f"❓ Clarification needed: ambiguous 'level' query")
                return "Which level? Volume, brightness, or battery?"
        
        # Pattern 4: Missing required parameters for specific functions
        clarification = self._check_missing_parameters(func_name, func_params)
        if clarification:
            return clarification
        
        # No clarification needed
        return None
    
    def _check_missing_parameters(self, func_name: str, func_params: Dict[str, Any]) -> Optional[str]:
        """
        Check for missing required parameters in function calls.
        
        Args:
            func_name: Function name
            func_params: Function parameters
            
        Returns:
            Clarification question or None
        """
        if func_name == 'open_application' and not func_params.get('app_name'):
            return self._get_app_suggestion_question("open")
        
        if func_name == 'close_window' and not func_params.get('app_name'):
            return self._get_app_suggestion_question("close")
        
        if func_name == 'launch_game' and not func_params.get('game_name'):
            return "Which game would you like to launch?"
        
        if func_name == 'connect_wifi' and not func_params.get('network_name'):
            return self._get_network_suggestion_question()
        
        if func_name == 'set_volume' and 'level' not in func_params:
            return "What volume level? (0-100)"
        
        if func_name == 'set_brightness' and 'level' not in func_params:
            return "What brightness level? (0-100)"
        
        if func_name == 'find_folder' and not func_params.get('folder_name'):
            return "Which folder are you looking for?"
        
        return None
    
    def _get_app_suggestion_question(self, action: str) -> str:
        """Get clarification question with app suggestions."""
        if self.executor:
            try:
                running_apps = self.executor.get_running_applications()
                if running_apps and len(running_apps) < 100:
                    match = re.search(r'Running:?\s*(.+)', running_apps, re.IGNORECASE)
                    if match:
                        apps_str = match.group(1).strip()
                        apps = [a.strip() for a in apps_str.split(',')[:5]]
                        app_list = ', '.join(apps)
                        return f"Which app would you like to {action}? (Currently running: {app_list})"
            except Exception:
                pass
        
        return f"Which application would you like to {action}?"
    
    def _get_network_suggestion_question(self) -> str:
        """Get clarification question with network suggestions."""
        if self.executor:
            try:
                networks = self.executor.list_wifi_networks()
                if networks and 'Available' in networks:
                    match = re.search(r'(?:Available|Found)[^:]*:\s*(.+)', networks, re.IGNORECASE)
                    if match:
                        networks_str = match.group(1).strip()
                        nets = [n.strip() for n in networks_str.split(',')[:5]]
                        net_list = ', '.join(nets)
                        return f"Which network should I connect to? (Available: {net_list})"
            except Exception:
                pass
        
        return "Which WiFi network would you like to connect to?"
    
    def _get_clarification_type(self, question: str) -> str:
        """Determine the clarification type from the question."""
        question_lower = question.lower()
        
        if 'open' in question_lower:
            return 'open'
        elif 'close' in question_lower:
            return 'close'
        elif 'launch' in question_lower or 'start' in question_lower:
            return 'launch'
        elif 'play' in question_lower:
            return 'play'
        elif 'set what' in question_lower or 'volume or brightness' in question_lower:
            return 'set'
        elif 'find' in question_lower or 'looking for' in question_lower:
            return 'find'
        elif 'search' in question_lower:
            return 'search'
        elif 'network' in question_lower or 'wifi' in question_lower:
            return 'network'
        elif 'game' in question_lower:
            return 'launch'
        elif 'folder' in question_lower:
            return 'find'
        
        return 'generic'
    
    def ask_clarification(self, question: str) -> str:
        """
        Store clarification question as pending and return it to user.
        
        NOW USES INTENT STATE: Delegates to IntentState for unified storage
        with proper timeout and value preservation.
        
        Args:
            question: Clarification question to ask user
            
        Returns:
            The question string
        """
        # Get IntentState from context_manager (unified storage)
        intent_state = None
        if self.context_manager and hasattr(self.context_manager, 'intent_state'):
            intent_state = self.context_manager.intent_state
        
        if intent_state:
            # Use unified IntentState system
            clarification_type = self._get_clarification_type(question)
            intent_state.set_clarification_pending(
                clarification_type=clarification_type,
                question=question,
                original_command=self._current_command or ''
            )
            logger.info(f"❓ Clarification stored in IntentState: {clarification_type}")
        else:
            # Fallback to old system (for backwards compatibility)
            logger.warning("⚠️ IntentState not available, using legacy storage")
            if self.context_manager:
                self.context_manager.set_preference('system', 'awaiting_clarification', True)
                self.context_manager.set_preference('system', 'last_clarification_question', question)
                self.context_manager.set_preference('system', 'last_original_command', self._current_command or '')
        
        logger.info(f"❓ Asking clarification: {question}")
        return question
    
    def check_clarification_response(self, user_text: str) -> Optional[str]:
        """
        Check if user is responding to a clarification question.
        If yes, reformulate the command with the provided information.
        
        Args:
            user_text: User's response
            
        Returns:
            Reformulated command or None if not a clarification response
        """
        if not self.context_manager:
            return None
        
        # PRIORITY 1: Check IntentState for unified clarification (new system)
        intent_state = None
        if hasattr(self.context_manager, 'intent_state'):
            intent_state = self.context_manager.intent_state
        
        if intent_state and intent_state.has_pending_intent():
            pending = intent_state.get_pending_intent()
            if pending and pending.intent.startswith("clarification:"):
                # Use IntentState's resolve_clarification (handles everything correctly)
                reformulated = intent_state.resolve_clarification(user_text)
                if reformulated:
                    logger.info(f"✅ IntentState resolved clarification: '{user_text}' → '{reformulated}'")
                    return reformulated
        
        # FALLBACK: Check legacy system (for backwards compatibility)
        awaiting = self.context_manager.get_preference('system', 'awaiting_clarification', False)
        if not awaiting:
            return None
        
        last_question = self.context_manager.get_preference('system', 'last_clarification_question', '')
        
        # Clear the clarification state
        self.context_manager.set_preference('system', 'awaiting_clarification', False)
        
        # Reformulate command based on the original question
        reformulated = self._reformulate_from_question(user_text, last_question)
        
        if reformulated:
            logger.info(f"✅ Reformulated from clarification (legacy): '{user_text}' → '{reformulated}'")
            return reformulated
        
        # If we can't reformulate, just process the user's answer as-is
        logger.debug(f"⚠️ Could not reformulate clarification response, processing as new command")
        return None
    
    def _reformulate_from_question(self, user_text: str, last_question: str) -> Optional[str]:
        """
        Reformulate user response based on the last clarification question.
        
        NOTE: This is now a FALLBACK for the legacy system only.
        The new IntentState.resolve_clarification() handles this better.
        
        Args:
            user_text: User's answer
            last_question: The clarification question that was asked
            
        Returns:
            Reformulated command or None
        """
        text_lower = user_text.lower().strip()
        question_lower = last_question.lower()
        
        # Get stored original command for extracting values
        original_command = ''
        if self.context_manager:
            original_command = self.context_manager.get_preference('system', 'last_original_command', '')
            # Clear after use
            self.context_manager.set_preference('system', 'last_original_command', '')
        
        original_lower = original_command.lower() if original_command else ''
        
        # Open/Close/Launch patterns
        action_patterns = [
            ('open', 'open'),
            ('close', 'close'),
            ('launch', 'launch'),
            ('start', 'start'),
        ]
        
        for keyword, prefix in action_patterns:
            if keyword in question_lower:
                return f"{prefix} {user_text}"
        
        # Volume or brightness disambiguation - check if original was a SET command
        if 'volume or brightness' in question_lower or 'set what' in question_lower:
            # Extract number from ORIGINAL command (e.g., "set it to 50" → 50)
            original_number = None
            if original_command:
                number_match = re.search(r'\d+', original_command)
                if number_match:
                    original_number = number_match.group()
            
            # Check if this was a SET command (had "set" or "to" with a number)
            was_set_command = original_number and ('set' in original_lower or 'to' in original_lower)
            
            if 'volume' in text_lower:
                if was_set_command:
                    return f"set volume to {original_number}"
                return "what's the volume level"
            elif 'brightness' in text_lower or 'bright' in text_lower:
                if was_set_command:
                    return f"set brightness to {original_number}"
                return "what's the brightness level"
        
        # "Set what?" response
        if 'set what' in question_lower:
            return self._reformulate_set_command(user_text, text_lower)
        
        # Network/WiFi
        if 'network' in question_lower or 'wifi' in question_lower:
            return f"connect to {user_text}"
        
        # Folder
        if 'folder' in question_lower:
            return f"find {user_text} folder"
        
        # Game
        if 'game' in question_lower:
            return f"launch {user_text}"
        
        return None
    
    def _reformulate_set_command(self, user_text: str, text_lower: str) -> Optional[str]:
        """Reformulate a 'set' command response."""
        # First try to find number in user's answer
        number_match = re.search(r'\d+', user_text)
        
        # If not found, try to get from stored original command
        if not number_match and self.context_manager:
            original_command = self.context_manager.get_preference('system', 'last_original_command', '')
            if original_command:
                number_match = re.search(r'\d+', original_command)
        
        if 'volume' in text_lower:
            if number_match:
                return f"set volume to {number_match.group()}"
            return "get volume"
        
        if 'brightness' in text_lower or 'bright' in text_lower:
            if number_match:
                return f"set brightness to {number_match.group()}"
            return "get brightness"
        
        return None


# Singleton instance
_clarification_handler = None


def get_clarification_handler(context_manager=None, executor=None) -> ClarificationHandler:
    """
    Get the singleton ClarificationHandler instance.
    
    Args:
        context_manager: ContextManager instance (optional, can be set later)
        executor: Executor instance (optional, can be set later)
    """
    global _clarification_handler
    if _clarification_handler is None:
        _clarification_handler = ClarificationHandler(context_manager, executor)
    elif context_manager and executor:
        _clarification_handler.set_dependencies(context_manager, executor)
    return _clarification_handler
