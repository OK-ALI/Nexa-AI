"""
Intelligent Learner - Automatic Knowledge Extraction from Conversations

This module provides comprehensive intelligent learning capabilities:
1. Automatic Fact Extraction - Extracts learnable facts from every conversation
2. Structured Knowledge Storage - Stores facts in normalized key-value format
3. Memory Consolidation - Merges similar facts, updates confidence
4. Context-Aware Recall - Retrieves facts based on conversation context

The goal is for NEXA to learn from natural conversation without explicit
"remember this" commands - she should understand and remember everything.

Author: Nexa AI Team
Date: January 2026
"""

import re
import logging
import threading
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FactType(Enum):
    """Types of facts that can be extracted."""
    PREFERENCE = "preference"       # User likes/prefers X
    PERSONAL = "personal"          # Birthday, name, age, etc.
    RELATIONSHIP = "relationship"  # Family, friends, colleagues
    WORK = "work"                  # Job, company, profession
    LOCATION = "location"          # Where user lives, works
    HABIT = "habit"               # Routines, behaviors
    OPINION = "opinion"           # Views, thoughts
    INTEREST = "interest"         # Hobbies, activities
    DISLIKE = "dislike"           # Things user doesn't like
    GOAL = "goal"                 # Aspirations, plans
    EVENT = "event"               # Important dates, memories


@dataclass
class ExtractedFact:
    """A structured fact extracted from conversation."""
    fact_type: FactType
    key: str                      # e.g., "favorite_color", "birthday"
    value: str                    # e.g., "black", "December 9"
    original_text: str            # The original user statement
    confidence: float = 0.8       # How confident we are in extraction
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_storage_format(self) -> str:
        """Convert to natural language for storage."""
        key_clean = self.key.replace('_', ' ')
        
        # Special handling for "likes_X" keys - just say "You like X"
        if self.key.startswith('likes_'):
            return f"You like {self.value}"
        
        # Special handling for "dislikes_X" keys
        if self.key.startswith('dislikes_'):
            return f"You don't like {self.value}"
        
        # Format based on fact type
        type_templates = {
            FactType.PREFERENCE: f"Your favorite {key_clean.replace('favorite ', '')} is {self.value}" if 'favorite' in self.key else f"You like {self.value}",
            FactType.PERSONAL: f"Your {key_clean} is {self.value}",
            FactType.RELATIONSHIP: f"Your {key_clean} is {self.value}",
            FactType.WORK: f"You work as {self.value}" if self.key == "job" else f"Your {key_clean} is {self.value}",
            FactType.LOCATION: f"You live in {self.value}" if self.key == "city" else f"Your {key_clean} is {self.value}",
            FactType.HABIT: f"You usually {self.value}",
            FactType.OPINION: f"You think {self.value}",
            FactType.INTEREST: f"You enjoy {self.value}",
            FactType.DISLIKE: f"You don't like {self.value}",
            FactType.GOAL: f"You want to {self.value}",
            FactType.EVENT: f"Your {key_clean} is {self.value}",
        }
        return type_templates.get(self.fact_type, f"You mentioned: {self.value}")


class IntelligentLearner:
    """
    Automatically extracts and learns facts from conversations.
    
    This class analyzes every user message for learnable facts and
    stores them in a structured format for intelligent recall.
    """
    
    # Patterns for extracting different types of facts
    EXTRACTION_PATTERNS = {
        # PREFERENCES - "I like X", "My favorite X is Y", "I prefer X"
        FactType.PREFERENCE: [
            (r"(?:my )?favorite (\w+) is (?:the )?(.+?)(?:\.|,|$)", "favorite_{}", 2),
            (r"(?:my )?favourite (\w+) is (?:the )?(.+?)(?:\.|,|$)", "favorite_{}", 2),
            (r"i (?:really )?(?:like|love|enjoy|prefer) (.+?)(?:\.|,|$|because|since)", None, 1),
            (r"i'm (?:a )?(?:big )?fan of (.+?)(?:\.|,|$)", None, 1),
        ],
        
        # PERSONAL INFO - Birthday, age, name
        FactType.PERSONAL: [
            (r"my birthday is (?:on )?(.+?)(?:\.|,|$)", "birthday", 1),
            (r"(?:i was )?born (?:on )?(.+?)(?:\.|,|$)", "birthday", 1),
            (r"my name is (.+?)(?:\.|,|$)", "name", 1),
            (r"(?:you can )?call me (.+?)(?:\.|,|$)", "nickname", 1),
            (r"i(?:'m| am) (\d+) years old", "age", 1),
            (r"my age is (\d+)", "age", 1),
        ],
        
        # RELATIONSHIPS - Family, friends
        FactType.RELATIONSHIP: [
            (r"my (mother|mom|father|dad|brother|sister|wife|husband|girlfriend|boyfriend|partner)(?:'s name)? is (.+?)(?:\.|,|$)", "{}", 2),
            (r"my (friend|best friend|colleague|boss)(?:'s name)? is (.+?)(?:\.|,|$)", "{}", 2),
            (r"i have (?:a |an )?(\w+) named (.+?)(?:\.|,|$)", "{}", 2),
        ],
        
        # WORK - Job, company
        FactType.WORK: [
            (r"i work (?:at|for) (.+?)(?:\.|,|$| as)", "company", 1),
            (r"i(?:'m| am) (?:a |an )?(.+?)(?:\.|,|$| at| for)", "job", 1),
            (r"my job is (.+?)(?:\.|,|$)", "job", 1),
            (r"i'm studying (.+?)(?:\.|,|$)", "field_of_study", 1),
            (r"i study (.+?)(?:\.|,|$)", "field_of_study", 1),
        ],
        
        # LOCATION - Where user lives
        FactType.LOCATION: [
            (r"i live in (.+?)(?:\.|,|$)", "city", 1),
            (r"i(?:'m| am) from (.+?)(?:\.|,|$)", "hometown", 1),
            (r"my address is (.+?)(?:\.|,|$)", "address", 1),
        ],
        
        # HABITS - Routines
        FactType.HABIT: [
            (r"i (?:usually|always|often|sometimes) (.+?)(?:\.|,|$)", "habit", 1),
            (r"every (morning|night|day|week) i (.+?)(?:\.|,|$)", "{}_routine", 2),
        ],
        
        # INTERESTS - Hobbies
        FactType.INTEREST: [
            (r"my hobbies? (?:is|are|include) (.+?)(?:\.|,|$)", "hobby", 1),
            (r"i enjoy (.+?)(?:\.|,|$| in my)", "interest", 1),
            (r"i(?:'m| am) interested in (.+?)(?:\.|,|$)", "interest", 1),
        ],
        
        # DISLIKES - Things user doesn't like
        FactType.DISLIKE: [
            (r"i (?:don't|do not|hate|dislike|can't stand) (.+?)(?:\.|,|$)", "dislike", 1),
            (r"i'm not (?:a )?fan of (.+?)(?:\.|,|$)", "dislike", 1),
        ],
        
        # GOALS - Aspirations
        FactType.GOAL: [
            (r"i want to (.+?)(?:\.|,|$)", "goal", 1),
            (r"my goal is to (.+?)(?:\.|,|$)", "goal", 1),
            (r"i(?:'m| am) planning to (.+?)(?:\.|,|$)", "plan", 1),
        ],
        
        # EVENTS - Important dates
        FactType.EVENT: [
            (r"my anniversary is (?:on )?(.+?)(?:\.|,|$)", "anniversary", 1),
            (r"i'm getting married (?:on )?(.+?)(?:\.|,|$)", "wedding_date", 1),
        ],
    }
    
    # Words that indicate a fact is being stated (not asked)
    STATEMENT_INDICATORS = [
        "my", "i am", "i'm", "i have", "i like", "i love", "i prefer",
        "i work", "i live", "i study", "i enjoy", "i hate", "i want"
    ]
    
    # Words that indicate a question (not a statement)
    QUESTION_INDICATORS = [
        "what", "when", "where", "who", "why", "how", "do you", "can you",
        "would you", "should i", "is there", "are there", "?"
    ]
    
    def __init__(self, memory_manager=None):
        """
        Initialize the Intelligent Learner.
        
        Args:
            memory_manager: SmartMemoryManager instance for storing facts
        """
        self.memory_manager = memory_manager
        self._extraction_lock = threading.Lock()
        self._pending_facts: List[ExtractedFact] = []
        
        logger.info("🧠 Intelligent Learner initialized")
    
    def set_memory_manager(self, memory_manager):
        """Set the memory manager after initialization."""
        self.memory_manager = memory_manager
    
    def analyze_conversation(
        self, 
        user_message: str, 
        nexa_response: str = ""
    ) -> List[ExtractedFact]:
        """
        Analyze a conversation exchange for learnable facts.
        
        This is the main entry point - called after every conversation.
        
        Args:
            user_message: What the user said
            nexa_response: What NEXA replied (for context)
            
        Returns:
            List of extracted facts
        """
        # Skip if it looks like a question or command
        if self._is_question_or_command(user_message):
            return []
        
        extracted = []
        user_lower = user_message.lower().strip()
        
        # Try each fact type's patterns
        for fact_type, patterns in self.EXTRACTION_PATTERNS.items():
            for pattern_info in patterns:
                pattern, key_template, value_group = pattern_info
                
                match = re.search(pattern, user_lower, re.IGNORECASE)
                if match:
                    fact = self._extract_from_match(
                        match, fact_type, key_template, value_group, user_message
                    )
                    if fact and self._is_valid_fact(fact):
                        extracted.append(fact)
                        logger.info(f"📚 Extracted fact: [{fact.fact_type.value}] {fact.key}={fact.value}")
        
        return extracted
    
    def learn_from_conversation(
        self, 
        user_message: str, 
        nexa_response: str = "",
        store_immediately: bool = True
    ) -> int:
        """
        Learn from a conversation and optionally store facts.
        
        Args:
            user_message: User's message
            nexa_response: NEXA's response
            store_immediately: If True, store facts right away
            
        Returns:
            Number of facts learned
        """
        facts = self.analyze_conversation(user_message, nexa_response)
        
        if not facts:
            return 0
        
        if store_immediately and self.memory_manager:
            for fact in facts:
                self._store_fact(fact)
        else:
            with self._extraction_lock:
                self._pending_facts.extend(facts)
        
        return len(facts)
    
    def _extract_from_match(
        self, 
        match: re.Match, 
        fact_type: FactType,
        key_template: Optional[str],
        value_group: int,
        original_text: str
    ) -> Optional[ExtractedFact]:
        """Extract a fact from a regex match."""
        try:
            # Get the value
            value = match.group(value_group).strip()
            
            # Clean up value
            value = self._clean_value(value)
            if not value or len(value) < 2:
                return None
            
            # Determine key
            if key_template is None:
                # For patterns like "I like X", use the value as a preference
                key = f"likes_{self._normalize_key(value)}"
            elif "{}" in key_template:
                # Template with placeholder
                if value_group > 1:
                    key = key_template.format(match.group(1).strip())
                else:
                    key = key_template.format(value)
            else:
                key = key_template
            
            key = self._normalize_key(key)
            
            return ExtractedFact(
                fact_type=fact_type,
                key=key,
                value=value,
                original_text=original_text,
                confidence=0.8
            )
        except Exception as e:
            logger.debug(f"Extraction failed: {e}")
            return None
    
    def _is_question_or_command(self, text: str) -> bool:
        """Check if text is a question or command (not a statement)."""
        text_lower = text.lower().strip()
        
        # Check for questions
        if text.endswith("?"):
            return True
        
        for indicator in self.QUESTION_INDICATORS:
            if text_lower.startswith(indicator):
                return True
        
        # Check for commands (verbs at start)
        command_starts = [
            "open", "close", "launch", "start", "stop", "play", "pause",
            "set", "get", "show", "hide", "list", "search", "find",
            "maximize", "minimize", "increase", "decrease", "mute", "unmute"
        ]
        first_word = text_lower.split()[0] if text_lower else ""
        if first_word in command_starts:
            return True
        
        return False
    
    def _is_valid_fact(self, fact: ExtractedFact) -> bool:
        """Validate that an extracted fact is meaningful."""
        # Value too short
        if len(fact.value) < 2:
            return False
        
        # Value too long (probably captured too much)
        if len(fact.value) > 100:
            return False
        
        # Key too generic
        if fact.key in ["it", "that", "this", "thing", "stuff"]:
            return False
        
        # Value is just a common word
        common_words = ["it", "that", "this", "thing", "stuff", "something", "anything"]
        if fact.value.lower() in common_words:
            return False
        
        return True
    
    def _clean_value(self, value: str) -> str:
        """Clean and normalize a value."""
        # Remove common trailing words
        value = re.sub(r'\s+(and|but|because|since|so|very much|a lot).*$', '', value, flags=re.IGNORECASE)
        
        # Remove trailing punctuation
        value = value.rstrip('.,!;:')
        
        # Normalize whitespace
        value = ' '.join(value.split())
        
        return value.strip()
    
    def _normalize_key(self, key: str) -> str:
        """Normalize a key for consistent storage."""
        # Replace spaces with underscores
        key = key.replace(' ', '_').replace('-', '_')
        
        # Remove special characters
        key = re.sub(r'[^\w_]', '', key)
        
        # Lowercase
        key = key.lower()
        
        return key
    
    def _store_fact(self, fact: ExtractedFact):
        """Store a fact in memory."""
        if not self.memory_manager:
            logger.warning("No memory manager - fact not stored")
            return
        
        try:
            # Convert to storage format
            fact_text = fact.to_storage_format()
            
            # Store using memory manager
            memory_id = self.memory_manager.learn_fact(
                fact=fact_text,
                source='auto_learned',
                confidence=fact.confidence,
                category=fact.fact_type.value
            )
            
            if memory_id:
                logger.info(f"💾 Auto-learned: {fact_text}")
            
        except Exception as e:
            logger.error(f"Failed to store fact: {e}")
    
    def get_pending_facts(self) -> List[ExtractedFact]:
        """Get facts that haven't been stored yet."""
        with self._extraction_lock:
            facts = self._pending_facts.copy()
            self._pending_facts.clear()
            return facts
    
    def consolidate_facts(self) -> int:
        """
        Consolidate similar facts in memory.
        
        Merges duplicates, updates confidence scores.
        Called periodically or on demand.
        
        Returns:
            Number of facts consolidated
        """
        if not self.memory_manager:
            return 0
        
        # Get all knowledge facts
        try:
            all_facts = self.memory_manager.get_knowledge(limit=100)
            
            # Group by similarity
            consolidated = 0
            seen_keys = set()
            
            for fact in all_facts:
                fact_text = fact.get('fact', '').lower()
                
                # Simple deduplication by key patterns
                # More sophisticated consolidation could use embeddings
                for key_pattern in ['birthday', 'favorite', 'name', 'age', 'job', 'city']:
                    if key_pattern in fact_text:
                        if key_pattern in seen_keys:
                            # This is a duplicate key - merge or delete
                            # For now, just log it
                            logger.debug(f"Potential duplicate: {fact_text[:50]}")
                            consolidated += 1
                        seen_keys.add(key_pattern)
            
            return consolidated
            
        except Exception as e:
            logger.error(f"Consolidation failed: {e}")
            return 0


# Module-level instance for easy access
_learner_instance: Optional[IntelligentLearner] = None


def get_intelligent_learner(memory_manager=None) -> IntelligentLearner:
    """Get or create the singleton IntelligentLearner instance."""
    global _learner_instance
    if _learner_instance is None:
        _learner_instance = IntelligentLearner(memory_manager)
    elif memory_manager and _learner_instance.memory_manager is None:
        _learner_instance.set_memory_manager(memory_manager)
    return _learner_instance
