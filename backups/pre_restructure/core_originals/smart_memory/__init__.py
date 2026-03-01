"""
Smart Memory Package - Nexa's Intelligent Memory System
Uses LanceDB for vector storage and sentence-transformers for embeddings.
"""

from .memory_types import ConversationMemory, KnowledgeMemory, SkillMemory
from .embedding_engine import EmbeddingEngine
from .memory_store import MemoryStore
from .memory_manager import SmartMemoryManager
from .context_constructor import ContextConstructor
from .intent_state import IntentState
from .intelligent_learner import IntelligentLearner, get_intelligent_learner

__all__ = [
    'ConversationMemory',
    'KnowledgeMemory', 
    'SkillMemory',
    'EmbeddingEngine',
    'MemoryStore',
    'SmartMemoryManager',
    'ContextConstructor',
    'IntentState',
    'IntelligentLearner',
    'get_intelligent_learner',
]
