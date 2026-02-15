"""
Response Cache Module for Nexa AI.

Extracted from brain.py to improve code organization.
Handles follow-up questions and cached data responses.

NOTE: Question detection (is_counting_question, is_listing_question) is now
delegated to IntentState in Smart Memory for unified follow-up handling.

Author: Ali Adil Waseem
"""

import re
import logging
from typing import Optional, Any, List, Dict

# Import from Smart Memory for unified follow-up detection
try:
    from .smart_memory.intent_state import IntentState
    SMART_MEMORY_AVAILABLE = True
except ImportError:
    SMART_MEMORY_AVAILABLE = False

logger = logging.getLogger(__name__)


class ResponseCache:
    """
    Handles cached responses and follow-up question answering.
    
    Provides methods for:
    - Answering follow-up questions from cached data
    - Detecting counting/listing questions (via IntentState)
    - Parsing cached results for specific data types
    """
    
    def __init__(self, intent_state: IntentState = None):
        """
        Initialize the ResponseCache.
        
        Args:
            intent_state: IntentState instance for unified follow-up detection
        """
        self._intent_state = intent_state
        
        # Fallback patterns (only used if IntentState not available)
        self._counting_patterns = [
            'how many', 'how much', "what's the count", "what is the count",
            'total number', 'count them', 'quantity', 'number of',
        ]
        self._listing_patterns = [
            'what are they', 'what are those', 'which ones', 'what were they',
            'list them', 'show them', 'name them', 'tell me their names',
        ]
    
    def set_intent_state(self, intent_state: IntentState) -> None:
        """Set the IntentState for unified follow-up detection."""
        self._intent_state = intent_state
    
    def answer_from_cache(self, user_text: str, last_action: str, last_result: Any,
                          context_manager=None) -> Optional[str]:
        """
        Answer follow-up questions using cached data instead of re-executing.
        Significantly faster and reduces redundant operations.
        
        Args:
            user_text: User's follow-up question
            last_action: Last executed action
            last_result: Result from last action (string or data)
            context_manager: ContextManager for additional context
            
        Returns:
            str: Answer from cached data, or None if can't answer
        """
        text_lower = user_text.lower().strip()
        
        # Detect question type (prefer IntentState if available)
        is_counting = self.is_counting_question(text_lower)
        is_listing = self.is_listing_question(text_lower)
        
        if not is_counting and not is_listing:
            return None
        
        # Parse the cached result based on action type
        parsed_data = self._parse_cached_result(last_action, last_result)
        
        if not parsed_data:
            logger.debug(f"⚠️ Could not parse cached data for '{last_action}'")
            return None
        
        # Answer the question
        if is_counting:
            return self._answer_counting_question(parsed_data, last_action)
        elif is_listing:
            return self._answer_listing_question(parsed_data, last_action)
        
        return None
    
    def is_counting_question(self, text: str) -> bool:
        """
        Check if text is asking for a count.
        Delegates to IntentState for unified detection.
        """
        if self._intent_state:
            return self._intent_state.is_counting_question(text)
        # Fallback to local patterns
        text_lower = text.lower().strip() if isinstance(text, str) else text
        return any(pattern in text_lower for pattern in self._counting_patterns)
    
    def is_listing_question(self, text: str) -> bool:
        """
        Check if text is asking for a list of items.
        Delegates to IntentState for unified detection.
        """
        if self._intent_state:
            return self._intent_state.is_listing_question(text)
        # Fallback to local patterns
        text_lower = text.lower().strip() if isinstance(text, str) else text
        return any(pattern in text_lower for pattern in self._listing_patterns)
    
    def _parse_cached_result(self, action: str, result: Any) -> Optional[Dict[str, Any]]:
        """
        Parse cached result into structured data.
        
        Args:
            action: The action that produced the result
            result: The result string or data
            
        Returns:
            Dict with 'count' and 'items' keys, or None
        """
        if not result:
            return None
        
        result_str = str(result)
        
        # Game listing (list_games)
        if action == 'list_games':
            return self._parse_game_list(result_str)
        
        # Running applications (get_running_applications)
        elif action == 'get_running_applications':
            return self._parse_app_list(result_str)
        
        # WiFi networks (list_wifi_networks)
        elif action == 'list_wifi_networks':
            return self._parse_network_list(result_str)
        
        # Generic parsing for unknown actions
        else:
            return self._parse_generic_list(result_str)
    
    def _parse_game_list(self, result: str) -> Optional[Dict[str, Any]]:
        """Parse game listing result."""
        # Pattern: "Found X games: game1, game2, ..."
        count_match = re.search(r'(?:Found|Detected|Have)\s+(\d+)\s+games?', result, re.IGNORECASE)
        
        # Extract game names (after colon or after "games:")
        games = []
        if ':' in result:
            games_part = result.split(':', 1)[1].strip()
            # Split by comma or newline
            games = [g.strip() for g in re.split(r'[,\n]', games_part) if g.strip()]
        
        count = int(count_match.group(1)) if count_match else len(games)
        
        if count > 0 or games:
            return {'count': count, 'items': games, 'type': 'games'}
        
        return None
    
    def _parse_app_list(self, result: str) -> Optional[Dict[str, Any]]:
        """Parse running applications result."""
        # Pattern: "Running: app1, app2, ..." or "X applications running"
        apps = []
        
        if 'Running:' in result or 'running:' in result:
            apps_part = result.split(':', 1)[1].strip() if ':' in result else result
            apps = [a.strip() for a in re.split(r'[,\n]', apps_part) if a.strip()]
        
        count_match = re.search(r'(\d+)\s+(?:apps?|applications?)\s+running', result, re.IGNORECASE)
        count = int(count_match.group(1)) if count_match else len(apps)
        
        if count > 0 or apps:
            return {'count': count, 'items': apps, 'type': 'applications'}
        
        return None
    
    def _parse_network_list(self, result: str) -> Optional[Dict[str, Any]]:
        """Parse WiFi networks result."""
        networks = []
        
        if 'Available' in result or 'Found' in result:
            networks_part = result.split(':', 1)[1].strip() if ':' in result else result
            networks = [n.strip() for n in re.split(r'[,\n]', networks_part) if n.strip()]
        
        count_match = re.search(r'(?:Found|Available)\s+(\d+)\s+networks?', result, re.IGNORECASE)
        count = int(count_match.group(1)) if count_match else len(networks)
        
        if count > 0 or networks:
            return {'count': count, 'items': networks, 'type': 'networks'}
        
        return None
    
    def _parse_generic_list(self, result: str) -> Optional[Dict[str, Any]]:
        """Parse generic list result."""
        # Try to extract count
        count_match = re.search(r'(\d+)\s+(?:items?|results?|found)', result, re.IGNORECASE)
        
        # Try to extract items after colon
        items = []
        if ':' in result:
            items_part = result.split(':', 1)[1].strip()
            items = [i.strip() for i in re.split(r'[,\n]', items_part) if i.strip() and len(i.strip()) > 2]
        
        count = int(count_match.group(1)) if count_match else len(items)
        
        if count > 0 or items:
            return {'count': count, 'items': items, 'type': 'items'}
        
        return None
    
    def _answer_counting_question(self, data: Dict[str, Any], action: str) -> str:
        """Generate answer for counting question."""
        count = data.get('count', 0)
        item_type = data.get('type', 'items')
        
        if count == 0:
            return f"I didn't find any {item_type}."
        elif count == 1:
            return f"There is 1 {item_type[:-1] if item_type.endswith('s') else item_type}."
        else:
            return f"There are {count} {item_type}."
    
    def _answer_listing_question(self, data: Dict[str, Any], action: str) -> str:
        """Generate answer for listing question."""
        items = data.get('items', [])
        item_type = data.get('type', 'items')
        
        if not items:
            return f"I don't have a list of {item_type} to show."
        
        if len(items) <= 5:
            items_str = ', '.join(items)
            return f"Here are the {item_type}: {items_str}"
        else:
            # Show first 5 with count
            items_str = ', '.join(items[:5])
            remaining = len(items) - 5
            return f"Here are the first 5 of {len(items)} {item_type}: {items_str}... and {remaining} more."


# Singleton instance
_response_cache = None


def get_response_cache(intent_state: IntentState = None) -> ResponseCache:
    """
    Get the singleton ResponseCache instance.
    
    Args:
        intent_state: Optional IntentState for unified follow-up detection
        
    Returns:
        ResponseCache: Singleton instance
    """
    global _response_cache
    if _response_cache is None:
        _response_cache = ResponseCache(intent_state=intent_state)
    elif intent_state and not _response_cache._intent_state:
        # Inject IntentState if provided and not already set
        _response_cache.set_intent_state(intent_state)
    return _response_cache
