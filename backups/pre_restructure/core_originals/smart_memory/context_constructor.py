"""
Context Constructor - RAG-style Context Building for AI Prompts

Builds intelligent context for Nexa's AI by:
1. Retrieving relevant past conversations
2. Finding applicable knowledge facts
3. Formatting context for the LLM prompt
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class ContextConstructor:
    """
    Builds context from Smart Memory for AI prompts.
    
    Uses RAG (Retrieval-Augmented Generation) approach:
    1. Embed current query
    2. Search for similar past interactions
    3. Find relevant knowledge
    4. Format as context string
    """
    
    def __init__(self, memory_manager):
        """
        Initialize context constructor.
        
        Args:
            memory_manager: SmartMemoryManager instance
        """
        self.memory = memory_manager
    
    def build_context(
        self, 
        current_query: str, 
        max_tokens: int = 800,
        include_knowledge: bool = True
    ) -> str:
        """
        Build context string for AI prompt.
        
        Args:
            current_query: Current user query
            max_tokens: Approximate max tokens for context
            include_knowledge: Whether to include knowledge facts
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        # 1. Get relevant knowledge facts
        if include_knowledge:
            knowledge_context = self._get_knowledge_context(current_query)
            if knowledge_context:
                context_parts.append(knowledge_context)
        
        # 2. Get similar past conversations
        conversation_context = self._get_conversation_context(
            current_query, 
            max_items=3
        )
        if conversation_context:
            context_parts.append(conversation_context)
        
        # 3. Get recent context (last 2 interactions)
        recent_context = self._get_recent_context(max_items=2)
        if recent_context:
            context_parts.append(recent_context)
        
        if not context_parts:
            return ""
        
        # Combine and format
        full_context = "\n\n".join(context_parts)
        
        # Truncate if too long (rough token estimate: 4 chars per token)
        max_chars = max_tokens * 4
        if len(full_context) > max_chars:
            full_context = full_context[:max_chars] + "..."
        
        return f"[MEMORY CONTEXT]\n{full_context}\n[END CONTEXT]"
    
    def _get_knowledge_context(self, query: str, max_items: int = 3) -> str:
        """Get relevant knowledge facts."""
        try:
            results = self.memory.recall_similar(
                query, 
                limit=max_items, 
                memory_type='knowledge'
            )
            
            if not results:
                return ""
            
            # Filter by relevance
            relevant = [r for r in results if r.get('similarity', 0) > 0.4]
            
            if not relevant:
                return ""
            
            facts = []
            for r in relevant:
                fact = r.get('fact', '')
                confidence = r.get('confidence', 0.5)
                if confidence > 0.6:
                    facts.append(f"• {fact}")
            
            if facts:
                return "Known facts about user:\n" + "\n".join(facts)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error getting knowledge context: {e}")
            return ""
    
    def _get_conversation_context(self, query: str, max_items: int = 3) -> str:
        """Get similar past conversations."""
        try:
            results = self.memory.recall_similar(
                query, 
                limit=max_items, 
                memory_type='conversations'
            )
            
            if not results:
                return ""
            
            # Filter by relevance
            relevant = [r for r in results if r.get('similarity', 0) > 0.5]
            
            if not relevant:
                return ""
            
            conversations = []
            for r in relevant:
                user_msg = r.get('user_message', '')[:100]
                nexa_msg = r.get('nexa_response', '')[:100]
                success = "✓" if r.get('success', True) else "✗"
                conversations.append(f"• User: \"{user_msg}\" → Nexa: \"{nexa_msg}\" {success}")
            
            if conversations:
                return "Similar past interactions:\n" + "\n".join(conversations)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error getting conversation context: {e}")
            return ""
    
    def _get_recent_context(self, max_items: int = 2) -> str:
        """Get most recent interactions."""
        try:
            results = self.memory.recall_recent(limit=max_items)
            
            if not results:
                return ""
            
            recent = []
            for r in results:
                user_msg = r.get('user_message', '')[:80]
                nexa_msg = r.get('nexa_response', '')[:80]
                recent.append(f"• \"{user_msg}\" → \"{nexa_msg}\"")
            
            if recent:
                return "Recent conversation:\n" + "\n".join(recent)
            
            return ""
            
        except Exception as e:
            logger.error(f"Error getting recent context: {e}")
            return ""
    
    # =========================================================================
    # Dynamic Reference Resolution (for follow-ups)
    # =========================================================================
    
    def resolve_reference(
        self, 
        query: str, 
        action_stack: List[Dict] = None,
        preferred_type: str = None
    ) -> Optional[str]:
        """
        Resolve vague references like "it", "that", "the previous one".
        
        Priority:
        1. Check action_stack (immediate context)
        2. Search Smart Memory (historical context)
        
        Args:
            query: User query containing reference
            action_stack: Recent action stack from context_manager
            preferred_type: Preferred entity type ('app', 'game', 'file', etc.)
            
        Returns:
            Resolved reference or None
        """
        query_lower = query.lower()
        
        # Check for reference words
        reference_words = ['it', 'that', 'this', 'the same', 'previous', 'last']
        has_reference = any(word in query_lower for word in reference_words)
        
        if not has_reference:
            return None
        
        # Priority 1: Check action_stack (most recent actions)
        if action_stack:
            for action in reversed(action_stack):
                action_name = action.get('action', '')
                action_data = action.get('data', {})
                
                # Try to extract target from action
                target = self._extract_target_from_action(action_name, action_data)
                if target:
                    logger.debug(f"🎯 Resolved reference from action_stack: {target}")
                    return target
        
        # Priority 2: Search Smart Memory
        # Look for recent similar interactions
        results = self.memory.recall_recent(limit=5)
        for r in results:
            user_msg = r.get('user_message', '').lower()
            
            # Extract entities from recent messages
            target = self._extract_entity_from_text(user_msg, preferred_type)
            if target:
                logger.debug(f"🎯 Resolved reference from memory: {target}")
                return target
        
        return None
    
    def _extract_target_from_action(
        self, 
        action_name: str, 
        action_data: Dict
    ) -> Optional[str]:
        """Extract target entity from an action."""
        # App actions
        if action_name in ['open_application', 'close_window', 'minimize_window']:
            return action_data.get('app_name')
        
        # Game actions
        if action_name in ['launch_game', 'list_games']:
            return action_data.get('game_name') or 'games'
        
        # File actions
        if action_name in ['open_folder', 'take_screenshot']:
            return action_data.get('folder_name') or action_data.get('path')
        
        return None
    
    def _extract_entity_from_text(
        self, 
        text: str, 
        preferred_type: str = None
    ) -> Optional[str]:
        """Extract entity from text based on patterns."""
        import re
        
        # Common patterns
        patterns = {
            'app': r'open(?:ed)?\s+(\w+)',
            'game': r'(?:launch|play)(?:ed)?\s+(.+?)(?:\s|$)',
            'file': r'(?:file|folder)\s+(.+?)(?:\s|$)',
        }
        
        if preferred_type and preferred_type in patterns:
            match = re.search(patterns[preferred_type], text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        # Try all patterns
        for entity_type, pattern in patterns.items():
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def get_context_for_query(self, query: str, action_stack: List = None) -> Dict[str, Any]:
        """
        Get full context package for a query.
        
        Returns dict with:
        - context_string: Formatted context for prompt
        - resolved_reference: Any resolved vague references
        - knowledge_used: Knowledge facts applied
        """
        context_string = self.build_context(query)
        resolved = self.resolve_reference(query, action_stack)
        
        return {
            'context_string': context_string,
            'resolved_reference': resolved,
            'has_context': bool(context_string),
        }
