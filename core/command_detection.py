"""
Command Detection Module for Nexa AI.

Extracted from brain.py to improve code organization.
Handles command type identification, mode switching detection, and vision request detection.

Author: Ali Adil Waseem
"""

import re
import logging
from typing import Optional, List

logger = logging.getLogger(__name__)


class CommandDetector:
    """
    Detects and classifies user commands for Nexa AI.
    
    Provides methods for:
    - Command type identification (query, action, conversation)
    - Mode switching detection (online/offline)
    - Vision request detection
    - Entity extraction from messages
    """
    
    def __init__(self):
        """Initialize the CommandDetector."""
        # Mode switching triggers
        self.online_triggers = [
            'go online', 'switch to online', 'switch online',
            'change to online', 'enable online', 'turn on online',
            'use online mode', 'activate online'
        ]
        
        self.offline_triggers = [
            'go offline', 'switch to offline', 'switch offline',
            'change to offline', 'enable offline', 'turn on offline',
            'use offline mode', 'activate offline'
        ]
        
        # Vision request patterns (Phase 23)
        self.vision_patterns = [
            r'\b(look|see|describe|analyze|read|show me|what\'s on|check).*(screen|display|monitor)\b',
            r'\b(what|describe|explain).*(see|seeing|looking at)\b',
            r'\b(read|tell me).*(screen|text on screen)\b',
            r'\bcurrent screen\b',
            r'\bshow me what\'s on\b',
        ]
    
    def identify_command_type(self, user_msg: str) -> str:
        """
        Identify the type of command from user message.
        
        Args:
            user_msg: User's message
            
        Returns:
            str: Command type (query, action, conversation)
        """
        msg_lower = user_msg.lower()
        
        # Query/Information commands
        if any(word in msg_lower for word in ['list', 'show', 'get', 'what', 'how many', 'tell me', 'check']):
            return 'query'
        
        # Action commands
        if any(word in msg_lower for word in ['open', 'close', 'set', 'launch', 'start', 'stop', 'minimize', 'maximize']):
            return 'action'
        
        # Conversational
        return 'conversation'
    
    def extract_entities_from_message(self, user_msg: str, nexa_msg: str) -> List[str]:
        """
        Extract key entities (app names, numbers, items) from messages.
        
        Args:
            user_msg: User's message
            nexa_msg: Nexa's response
            
        Returns:
            List[str]: Extracted entities
        """
        entities = []
        
        # Extract from Nexa's response (more reliable - contains actual data)
        # Extract numbers (counts)
        numbers = re.findall(r'\b(\d+)\s+(games|apps|applications|items|networks)', nexa_msg.lower())
        for num, item_type in numbers:
            entities.append(f"{num} {item_type}")
        
        # Extract app/game names (capitalized words or quoted strings)
        # Pattern: Word starting with capital, or "quoted text"
        names = re.findall(r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b', nexa_msg)
        entities.extend(names[:5])  # Max 5 names
        
        # Extract quoted items
        quoted = re.findall(r'"([^"]+)"', nexa_msg)
        entities.extend(quoted[:3])  # Max 3 quoted items
        
        # Remove duplicates while preserving order
        seen = set()
        unique_entities = []
        for entity in entities:
            if entity.lower() not in seen:
                seen.add(entity.lower())
                unique_entities.append(entity)
        
        return unique_entities[:10]  # Max 10 entities
    
    def detect_mode_switch_command(self, user_input: str, current_mode, llm_manager) -> Optional[str]:
        """
        Detect explicit mode switching commands (go online/offline, switch mode).
        
        Args:
            user_input: User's message
            current_mode: Current LLM mode
            llm_manager: LLM manager instance to change mode
            
        Returns:
            str: Response message if mode switched, None otherwise
        """
        from core.llm_manager import LLMMode
        
        user_lower = user_input.lower().strip()
        
        # Check for online mode switch
        if any(trigger in user_lower for trigger in self.online_triggers):
            if current_mode == LLMMode.ONLINE:
                return "I'm already in online mode with internet features available."
            else:
                logger.info("🌐 User requested mode switch: OFFLINE → ONLINE (Phase 24)")
                llm_manager.set_mode(LLMMode.ONLINE)
                return "Switching to online mode. Internet-dependent features (vision, web search, weather) are now available."
        
        # Check for offline mode switch
        if any(trigger in user_lower for trigger in self.offline_triggers):
            if current_mode == LLMMode.OFFLINE:
                return "I'm already in offline mode. All core features work perfectly without internet."
            else:
                logger.info("📴 User requested mode switch: ONLINE → OFFLINE (Phase 24)")
                llm_manager.set_mode(LLMMode.OFFLINE)
                return "Switching to offline mode. All core features available, but internet-dependent features (vision, web search, weather) are disabled."
        
        return None  # Not a mode switch command
    
    def detect_vision_request(self, user_input: str, current_mode) -> bool:
        """
        Detect if user is requesting AI vision analysis.
        
        IMPORTANT DISTINCTION:
        - Vision Request = AI analyzing screen content (requires online, Phase 23)
        - Screenshot = Taking a picture of the screen (works offline)
        
        Args:
            user_input: User's message
            current_mode: Current LLM mode
            
        Returns:
            bool: True if vision request detected
        """
        from core.llm_manager import LLMMode
        
        user_lower = user_input.lower().strip()
        
        # Exclude screenshot requests (these work offline)
        screenshot_keywords = ['screenshot', 'screen shot', 'capture screen', 'take a picture of screen']
        if any(kw in user_lower for kw in screenshot_keywords):
            logger.debug("📷 Screenshot request detected (not a vision request)")
            return False
        
        # Check vision patterns
        for pattern in self.vision_patterns:
            if re.search(pattern, user_lower):
                logger.info(f"👁️ Vision request detected: '{user_input}'")
                return True
        
        return False
    
    def get_vision_unavailable_response(self, is_online: bool) -> str:
        """
        Get appropriate response when vision is requested but unavailable.
        
        Args:
            is_online: Whether currently in online mode
            
        Returns:
            str: Response message
        """
        if not is_online:
            return ("I can't see the screen right now because I'm in offline mode. "
                   "Say 'go online' to enable vision features, or say 'take a screenshot' "
                   "to capture and save what's on screen.")
        else:
            return ("Vision analysis is currently being developed. "
                   "I can take a screenshot if you'd like to save what's on screen.")


# Singleton instance
_command_detector = None


def get_command_detector() -> CommandDetector:
    """Get the singleton CommandDetector instance."""
    global _command_detector
    if _command_detector is None:
        _command_detector = CommandDetector()
    return _command_detector
