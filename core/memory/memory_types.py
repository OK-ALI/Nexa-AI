"""
Memory Types - Data schemas for Nexa's Smart Memory System

Defines the three core memory types:
1. ConversationMemory - User/Nexa interaction pairs
2. KnowledgeMemory - Facts and learned information about user
3. SkillMemory - Action patterns and usage statistics
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any, Optional
import numpy as np


def generate_session_id() -> str:
    """Generate a session ID based on current date and a short UUID."""
    date_str = datetime.now().strftime("%Y%m%d")
    short_uuid = str(uuid.uuid4())[:8]
    return f"session_{date_str}_{short_uuid}"


@dataclass
class ConversationMemory:
    """
    Stores a single user-Nexa interaction with semantic embedding.
    
    Attributes:
        id: Unique identifier (UUID)
        user_message: What the user said
        nexa_response: What Nexa replied
        embedding: 384-dim vector for semantic search
        timestamp: When this interaction occurred
        success: Whether the action succeeded
        importance: Auto-calculated importance score (0.0 - 1.0)
        tags: Auto-extracted topic tags
        session_id: Session identifier for grouping conversations
    """
    user_message: str
    nexa_response: str
    embedding: Optional[np.ndarray] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=datetime.now)
    success: bool = True
    importance: float = 0.5
    tags: List[str] = field(default_factory=list)
    session_id: str = ""  # Will be set by ContextManager
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LanceDB storage."""
        return {
            'id': self.id,
            'user_message': self.user_message,
            'nexa_response': self.nexa_response,
            'vector': self.embedding.tolist() if self.embedding is not None else [],
            'timestamp': self.timestamp.isoformat(),
            'success': self.success,
            'importance': self.importance,
            'tags': ','.join(self.tags),  # Store as comma-separated string
            'session_id': self.session_id,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConversationMemory':
        """Create from dictionary (LanceDB retrieval)."""
        return cls(
            id=data['id'],
            user_message=data['user_message'],
            nexa_response=data['nexa_response'],
            embedding=np.array(data['vector']) if data.get('vector') else None,
            timestamp=datetime.fromisoformat(data['timestamp']),
            success=data.get('success', True),
            importance=data.get('importance', 0.5),
            tags=data.get('tags', '').split(',') if data.get('tags') else [],
            session_id=data.get('session_id', ''),
        )


# Knowledge categories for organizing personal information
KNOWLEDGE_CATEGORIES = [
    'preference',    # "I like jazz", "I prefer dark theme"
    'personal',      # "My birthday is March 15", "I'm 25 years old"
    'relationship',  # "My friend Ahmed", "My sister Sarah"
    'setting',       # "Default volume 70%", "Always use metric"
    'work',          # "I work at Microsoft", "I'm a developer"
    'location',      # "I live in Lahore", "Home address is..."
    'general',       # Anything else
]


def detect_knowledge_category(fact: str) -> str:
    """
    Auto-detect the category of a knowledge fact.
    
    Args:
        fact: The knowledge statement
        
    Returns:
        Category string
    """
    fact_lower = fact.lower()
    
    # Preference patterns
    if any(kw in fact_lower for kw in ['like', 'prefer', 'love', 'hate', 'favorite', 'favourite', 'enjoy']):
        return 'preference'
    
    # Relationship patterns
    if any(kw in fact_lower for kw in ['friend', 'brother', 'sister', 'mother', 'father', 'wife', 'husband', 
                                        'girlfriend', 'boyfriend', 'colleague', 'boss', 'family', 'relative']):
        return 'relationship'
    
    # Personal info patterns
    if any(kw in fact_lower for kw in ['birthday', 'born', 'age', 'years old', 'name is', 'nickname']):
        return 'personal'
    
    # Work patterns
    if any(kw in fact_lower for kw in ['work', 'job', 'company', 'profession', 'career', 'employee', 'developer', 
                                        'engineer', 'manager', 'office']):
        return 'work'
    
    # Location patterns
    if any(kw in fact_lower for kw in ['live', 'address', 'city', 'country', 'home', 'house', 'apartment']):
        return 'location'
    
    # Setting patterns
    if any(kw in fact_lower for kw in ['default', 'always', 'setting', 'volume', 'brightness', 'theme']):
        return 'setting'
    
    return 'general'


@dataclass
class KnowledgeMemory:
    """
    Stores facts and learned information about the user.
    
    Attributes:
        id: Unique identifier (UUID)
        fact: The knowledge statement (e.g., "User prefers dark theme")
        category: Type of knowledge (preference, personal, relationship, etc.)
        embedding: 384-dim vector for semantic search
        source: How this was learned ('user_stated' or 'learned')
        confidence: How confident we are (0.0 - 1.0)
        created_at: When first learned
        last_accessed: When last used (for relevance decay)
        access_count: How often this fact is retrieved
    """
    fact: str
    embedding: Optional[np.ndarray] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: str = 'general'  # preference, personal, relationship, setting, work, location, general
    source: str = 'learned'  # 'user_stated' or 'learned'
    confidence: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LanceDB storage."""
        return {
            'id': self.id,
            'fact': self.fact,
            'category': self.category,
            'vector': self.embedding.tolist() if self.embedding is not None else [],
            'source': self.source,
            'confidence': self.confidence,
            'created_at': self.created_at.isoformat(),
            'last_accessed': self.last_accessed.isoformat(),
            'access_count': self.access_count,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'KnowledgeMemory':
        """Create from dictionary (LanceDB retrieval)."""
        return cls(
            id=data['id'],
            fact=data['fact'],
            category=data.get('category', 'general'),
            embedding=np.array(data['vector']) if data.get('vector') else None,
            source=data.get('source', 'learned'),
            confidence=data.get('confidence', 0.5),
            created_at=datetime.fromisoformat(data['created_at']),
            last_accessed=datetime.fromisoformat(data['last_accessed']),
            access_count=data.get('access_count', 0),
        )


@dataclass
class EmotionalMemory:
    """
    Stores emotional context about the user — events, moods, goals,
    journal entries, milestones, and preferences.

    Integrated with LanceDB for vector-based semantic search and
    displayed as pink/magenta nodes in the Neural Memory Panel.

    Attributes:
        id: Unique identifier (UUID)
        content: The emotional memory content
        category: Type — event, mood, goal, preference, milestone, journal
        emotion: Associated mood at time of storage
        embedding: 384-dim vector for semantic search
        importance: Auto-calculated importance score (0.0 - 1.0)
        created_at: When this was stored
        expires_at: Optional expiry timestamp (ISO string or empty)
        tags: Comma-separated topic tags
        metadata: Extra context as JSON string
    """
    content: str
    category: str = 'event'
    emotion: str = 'neutral'
    embedding: Optional[np.ndarray] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    importance: float = 0.5
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: str = ''
    tags: List[str] = field(default_factory=list)
    metadata: str = '{}'

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LanceDB storage."""
        return {
            'id': self.id,
            'content': self.content,
            'category': self.category,
            'emotion': self.emotion,
            'vector': self.embedding.tolist() if self.embedding is not None else [],
            'importance': self.importance,
            'created_at': self.created_at.isoformat() if isinstance(self.created_at, datetime) else str(self.created_at),
            'expires_at': self.expires_at,
            'tags': ','.join(self.tags) if isinstance(self.tags, list) else str(self.tags),
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EmotionalMemory':
        """Create from dictionary (LanceDB retrieval)."""
        created = data.get('created_at', '')
        if isinstance(created, str) and created:
            try:
                created = datetime.fromisoformat(created)
            except (ValueError, TypeError):
                created = datetime.now()
        elif not isinstance(created, datetime):
            created = datetime.now()

        return cls(
            id=data['id'],
            content=data.get('content', ''),
            category=data.get('category', 'event'),
            emotion=data.get('emotion', 'neutral'),
            embedding=np.array(data['vector']) if data.get('vector') else None,
            importance=data.get('importance', 0.5),
            created_at=created,
            expires_at=data.get('expires_at', ''),
            tags=data.get('tags', '').split(',') if data.get('tags') else [],
            metadata=data.get('metadata', '{}'),
        )


@dataclass
class SkillMemory:
    """
    Tracks action patterns and usage statistics.
    
    Attributes:
        id: Unique identifier (UUID)
        action: The action/function name (e.g., 'set_volume')
        success_patterns: Common successful parameter combinations
        failure_patterns: Parameters that led to failures
        usage_count: Total times this action was used
        success_rate: Percentage of successful uses
        last_used: When this action was last invoked
        preferred_value: Most commonly used value (if applicable)
    """
    action: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    success_patterns: Dict[str, Any] = field(default_factory=dict)
    failure_patterns: List[Dict[str, Any]] = field(default_factory=list)
    usage_count: int = 0
    success_rate: float = 1.0
    last_used: datetime = field(default_factory=datetime.now)
    preferred_value: Optional[Any] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for LanceDB storage."""
        import json
        return {
            'id': self.id,
            'action': self.action,
            'success_patterns': json.dumps(self.success_patterns),
            'failure_patterns': json.dumps(self.failure_patterns),
            'usage_count': self.usage_count,
            'success_rate': self.success_rate,
            'last_used': self.last_used.isoformat(),
            'preferred_value': json.dumps(self.preferred_value) if self.preferred_value else None,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillMemory':
        """Create from dictionary (LanceDB retrieval)."""
        import json
        return cls(
            id=data['id'],
            action=data['action'],
            success_patterns=json.loads(data.get('success_patterns', '{}')),
            failure_patterns=json.loads(data.get('failure_patterns', '[]')),
            usage_count=data.get('usage_count', 0),
            success_rate=data.get('success_rate', 1.0),
            last_used=datetime.fromisoformat(data['last_used']),
            preferred_value=json.loads(data['preferred_value']) if data.get('preferred_value') else None,
        )


# Type alias for any memory type
Memory = ConversationMemory | KnowledgeMemory | SkillMemory | EmotionalMemory
