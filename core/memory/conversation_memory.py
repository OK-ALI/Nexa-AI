"""
Conversation History Module for Nexa AI.

Extracted from brain.py to improve code organization.
Handles conversation history building and formatting for LLM context.

Author: Ali Adil Waseem
"""

import re
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)


class ConversationHistoryBuilder:
    """
    Builds and formats conversation history for LLM context.
    
    Provides methods for:
    - Building Llama-optimized conversation history
    - Extracting entities from messages
    - Identifying command types
    - Formatting context for follow-up questions
    """
    
    def __init__(self):
        """Initialize the ConversationHistoryBuilder."""
        # Query keywords
        self.query_keywords = ['list', 'show', 'get', 'what', 'how many', 'tell me', 'check']
        
        # Action keywords
        self.action_keywords = ['open', 'close', 'set', 'launch', 'start', 'stop', 'minimize', 'maximize']
    
    def build_llama_history(self, recent_history: List[Dict[str, Any]], 
                           max_interactions: int = 10) -> str:
        """
        Build a Llama-optimized conversation history.
        
        Llama 3.1 benefits from:
        1. Clear separation of interactions
        2. Focus on Q&A pairs with results
        3. Add explicit follow-up hints
        4. Extract key entities for reference resolution
        
        Args:
            recent_history: Recent conversation interactions
            max_interactions: Maximum number of interactions to include
            
        Returns:
            str: Formatted history for Llama
        """
        if not recent_history:
            return ""
        
        # Limit interactions
        compact_history = recent_history[-max_interactions:]
        
        # Extract key information from each interaction
        structured_context = []
        last_command = None
        last_result = None
        last_entities = []
        
        for interaction in compact_history:
            user_msg = interaction.get('user', '').strip()
            nexa_msg = interaction.get('nexa', '').strip()
            
            if not user_msg:
                continue
            
            # Extract command type from user message
            command_type = self.identify_command_type(user_msg)
            
            # Extract entities (app names, numbers, etc.)
            entities = self.extract_entities_from_message(user_msg, nexa_msg)
            
            # Build structured entry
            entry = {
                'user': user_msg,
                'nexa': nexa_msg,
                'type': command_type,
                'entities': entities
            }
            
            structured_context.append(entry)
            
            # Remember last command for follow-up detection
            if command_type in ['query', 'list', 'get']:
                last_command = user_msg
                last_result = nexa_msg
                last_entities = entities
        
        # Build formatted history
        return self._format_history(structured_context, last_command, last_result, last_entities)
    
    def _format_history(self, structured_context: List[Dict[str, Any]], 
                       last_command: Optional[str], 
                       last_result: Optional[str],
                       last_entities: List[str]) -> str:
        """Format the structured context into a string for the LLM."""
        history_text = "\n\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        history_text += "CONVERSATION CONTEXT (for follow-up questions):\n"
        history_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        # Show last few interactions in compact format
        for idx, entry in enumerate(structured_context, 1):
            user_truncated = entry['user'][:80] + ('...' if len(entry['user']) > 80 else '')
            nexa_truncated = entry['nexa'][:100] + ('...' if len(entry['nexa']) > 100 else '')
            
            history_text += f"\n[{idx}] User: {user_truncated}\n"
            history_text += f"    Nexa: {nexa_truncated}\n"
            
            # Add entity hints for reference resolution
            if entry['entities']:
                entity_str = ', '.join(entry['entities'][:5])  # Max 5 entities
                history_text += f"    → Mentioned: {entity_str}\n"
        
        # Add explicit follow-up context
        if last_command and last_result:
            history_text += "\n" + "─" * 78 + "\n"
            history_text += "LAST QUERY RESULT (use this for follow-ups like 'how many?', 'what are they?'):\n"
            history_text += f"Question: {last_command}\n"
            
            result_truncated = last_result[:200] + ('...' if len(last_result) > 200 else '')
            history_text += f"Answer: {result_truncated}\n"
            
            if last_entities:
                history_text += f"Key Items: {', '.join(last_entities[:10])}\n"
        
        history_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        history_text += "FOLLOW-UP INSTRUCTIONS:\n"
        history_text += "• If user asks 'how many?', count items from LAST QUERY RESULT\n"
        history_text += "• If user asks 'what are they?', list items from LAST QUERY RESULT\n"
        history_text += "• If user says 'it', 'that', 'them' - refer to entities in LAST QUERY RESULT\n"
        history_text += "• If unclear, ask for clarification instead of guessing\n"
        history_text += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        
        return history_text
    
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
        if any(word in msg_lower for word in self.query_keywords):
            return 'query'
        
        # Action commands
        if any(word in msg_lower for word in self.action_keywords):
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


# Singleton instance
_history_builder = None


def get_history_builder() -> ConversationHistoryBuilder:
    """Get the singleton ConversationHistoryBuilder instance."""
    global _history_builder
    if _history_builder is None:
        _history_builder = ConversationHistoryBuilder()
    return _history_builder
