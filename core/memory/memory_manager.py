"""
Memory Manager - High-Level API for Smart Memory

Provides the main interface for storing, recalling, and managing memories.
Integrates EmbeddingEngine and MemoryStore for seamless operation.
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, timedelta

from .memory_types import ConversationMemory, KnowledgeMemory, SkillMemory, EmotionalMemory
from .embedding_engine import EmbeddingEngine, get_embedding_engine
from .memory_store import MemoryStore

logger = logging.getLogger(__name__)


class SmartMemoryManager:
    """
    High-level API for Nexa's Smart Memory System.
    
    Provides methods for:
    - Storing conversations, facts, and skills
    - Recalling similar memories (semantic search)
    - Managing memories (forget, update, mark important)
    - Memory consolidation and pruning
    """
    
    def __init__(self, data_dir: Union[str, Path]):
        """
        Initialize Smart Memory Manager.
        
        Args:
            data_dir: Directory for database storage
        """
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "smart_memory"
        
        # Initialize components
        self.embedding = get_embedding_engine()
        self.store = MemoryStore(self.db_path)
        
        logger.info("🧠 Smart Memory Manager initialized")
        
        # Session tracking
        self._current_session_id: Optional[str] = None
    
    def start_session(self) -> str:
        """
        Start a new session for grouping conversations.
        Called when Nexa starts or resumes.
        
        Returns:
            Session ID
        """
        from .memory_types import generate_session_id
        self._current_session_id = generate_session_id()
        logger.info(f"🆕 Started new session: {self._current_session_id}")
        return self._current_session_id
    
    def get_current_session(self) -> Optional[str]:
        """Get current session ID."""
        return self._current_session_id
    
    def get_session_memories(self, session_id: str = None, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get all memories from a specific session.
        
        Args:
            session_id: Session ID (uses current if not provided)
            limit: Maximum memories to return
            
        Returns:
            List of memories from that session
        """
        sid = session_id or self._current_session_id
        if not sid:
            return []
        
        try:
            results = self.store.get_all(
                MemoryStore.TABLE_CONVERSATIONS,
                filter_condition=f"session_id = '{sid}'",
                limit=limit
            )
            results.sort(key=lambda x: x.get('timestamp', ''))
            return results
        except Exception as e:
            logger.warning(f"Session query failed (session_id column may not exist): {e}")
            return []
    
    # =========================================================================
    # Store Operations
    # =========================================================================
    
    def store_memory(
        self, 
        user_message: str, 
        nexa_response: str, 
        success: bool = True,
        tags: Optional[List[str]] = None,
        session_id: Optional[str] = None
    ) -> str:
        """
        Store a conversation interaction.
        
        Args:
            user_message: What the user said
            nexa_response: What Nexa replied
            success: Whether the action succeeded
            tags: Optional topic tags
            session_id: Session ID (uses current session if not provided)
            
        Returns:
            Memory ID
        """
        # Generate embedding for semantic search
        combined_text = f"{user_message} {nexa_response}"
        embedding = self.embedding.embed(combined_text)
        
        # Calculate importance based on message length and success
        importance = self._calculate_importance(user_message, nexa_response, success)
        
        # Auto-extract tags if not provided
        if tags is None:
            tags = self._extract_tags(user_message)
        
        # Use current session if not provided
        sid = session_id or self._current_session_id or ""
        
        # Create memory object
        memory = ConversationMemory(
            user_message=user_message,
            nexa_response=nexa_response,
            embedding=embedding,
            success=success,
            importance=importance,
            tags=tags,
            session_id=sid
        )
        
        # Store in database
        data = memory.to_dict()
        data['vector'] = embedding.tolist()  # LanceDB expects 'vector' field
        
        self.store.add(MemoryStore.TABLE_CONVERSATIONS, data)
        
        logger.debug(f"💾 Stored conversation memory: {memory.id[:8]}... (session: {sid[:16] if sid else 'none'})")
        return memory.id
    
    def learn_fact(
        self, 
        fact: str, 
        source: str = 'learned',
        confidence: float = 0.7,
        category: str = None
    ) -> str:
        """
        Store a knowledge fact about the user.
        
        Args:
            fact: The knowledge statement
            source: 'user_stated' or 'learned'
            confidence: Confidence level (0.0 - 1.0)
            category: Category (auto-detected if not provided)
            
        Returns:
            Memory ID
        """
        # Auto-detect category if not provided
        from .memory_types import detect_knowledge_category
        if category is None:
            category = detect_knowledge_category(fact)
        
        # Check if similar fact already exists
        embedding = self.embedding.embed(fact)
        similar = self.store.search_similar(
            MemoryStore.TABLE_KNOWLEDGE, 
            embedding, 
            limit=1
        )
        
        # If very similar fact exists, update confidence instead
        # Use L2-safe similarity: 1/(1+distance) — works for any distance range
        if similar and (1 / (1 + similar[0].get('_distance', 999))) > 0.85:
            existing_id = similar[0]['id']
            new_confidence = min(1.0, similar[0].get('confidence', 0.5) + 0.1)
            self.store.update(
                MemoryStore.TABLE_KNOWLEDGE,
                existing_id,
                {'confidence': new_confidence, 'last_accessed': datetime.now().isoformat()}
            )
            logger.debug(f"🔄 Updated existing fact confidence: {existing_id[:8]}...")
            return existing_id
        
        # Create new knowledge memory with category
        knowledge = KnowledgeMemory(
            fact=fact,
            embedding=embedding,
            category=category,
            source=source,
            confidence=confidence
        )
        
        data = knowledge.to_dict()
        data['vector'] = embedding.tolist()
        
        self.store.add(MemoryStore.TABLE_KNOWLEDGE, data)
        
        logger.debug(f"📚 Learned new fact [{category}]: {knowledge.id[:8]}...")
        return knowledge.id
    
    def get_knowledge_by_category(self, category: str, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get knowledge facts by category.
        
        Args:
            category: preference, personal, relationship, work, location, setting, general
            limit: Maximum results
            
        Returns:
            List of knowledge facts in that category
        """
        try:
            results = self.store.get_all(
                MemoryStore.TABLE_KNOWLEDGE,
                filter_condition=f"category = '{category}'",
                limit=limit
            )
            return results
        except Exception as e:
            logger.warning(f"Category query failed (column may not exist): {e}")
            return []
    
    def track_skill(
        self, 
        action: str, 
        params: Dict[str, Any],
        success: bool = True
    ) -> str:
        """
        Track action usage for skill learning.
        
        Args:
            action: Action/function name
            params: Parameters used
            success: Whether it succeeded
            
        Returns:
            Skill ID
        """
        import json
        
        # Check if skill already exists
        existing = self.store.get_all(
            MemoryStore.TABLE_SKILLS,
            filter_condition=f"action = '{action}'",
            limit=1
        )
        
        if existing:
            # Update existing skill
            skill_data = existing[0]
            skill_data['usage_count'] = skill_data.get('usage_count', 0) + 1
            skill_data['last_used'] = datetime.now().isoformat()
            
            # Update success rate
            old_rate = skill_data.get('success_rate', 1.0)
            old_count = skill_data.get('usage_count', 1) - 1
            new_rate = (old_rate * old_count + (1 if success else 0)) / (old_count + 1)
            skill_data['success_rate'] = new_rate
            
            # Update patterns
            if success:
                patterns = json.loads(skill_data.get('success_patterns', '{}'))
                for key, value in params.items():
                    if key not in patterns:
                        patterns[key] = {}
                    val_str = str(value)
                    patterns[key][val_str] = patterns[key].get(val_str, 0) + 1
                skill_data['success_patterns'] = json.dumps(patterns)
            
            self.store.update(MemoryStore.TABLE_SKILLS, skill_data['id'], skill_data)
            return skill_data['id']
        
        else:
            # Create new skill
            skill = SkillMemory(
                action=action,
                success_patterns=params if success else {},
                usage_count=1,
                success_rate=1.0 if success else 0.0
            )
            
            data = skill.to_dict()
            self.store.add(MemoryStore.TABLE_SKILLS, data)
            
            logger.debug(f"🎯 New skill tracked: {action}")
            return skill.id
    
    # =========================================================================
    # Recall Operations
    # =========================================================================
    
    def recall_similar(
        self, 
        query: str, 
        limit: int = 5,
        memory_type: str = 'all'
    ) -> List[Dict[str, Any]]:
        """
        Find memories similar to a query.
        
        Args:
            query: Search query
            limit: Maximum results
            memory_type: 'conversations', 'knowledge', 'skills', or 'all'
            
        Returns:
            List of matching memories with similarity scores
        """
        embedding = self.embedding.embed(query)
        results = []
        
        if memory_type in ['conversations', 'all']:
            conv_results = self.store.search_similar(
                MemoryStore.TABLE_CONVERSATIONS,
                embedding,
                limit=limit
            )
            for r in conv_results:
                r['memory_type'] = 'conversation'
                # Convert L2 distance to similarity: sim = 1 / (1 + distance)
                # L2 distance is not bounded 0-1, so we use this formula
                distance = r.get('_distance', 999)
                r['similarity'] = 1.0 / (1.0 + distance)
            results.extend(conv_results)
        
        if memory_type in ['knowledge', 'all']:
            know_results = self.store.search_similar(
                MemoryStore.TABLE_KNOWLEDGE,
                embedding,
                limit=limit
            )
            for r in know_results:
                r['memory_type'] = 'knowledge'
                # Convert L2 distance to similarity: sim = 1 / (1 + distance)
                distance = r.get('_distance', 999)
                r['similarity'] = 1.0 / (1.0 + distance)
            results.extend(know_results)
        
        if memory_type in ['emotional', 'all']:
            emo_results = self.store.search_similar(
                MemoryStore.TABLE_EMOTIONAL,
                embedding,
                limit=limit
            )
            for r in emo_results:
                r['memory_type'] = 'emotional'
                distance = r.get('_distance', 999)
                r['similarity'] = 1.0 / (1.0 + distance)
            results.extend(emo_results)
        
        # Sort by similarity
        results.sort(key=lambda x: x.get('similarity', 0), reverse=True)
        
        return results[:limit]
    
    def recall_knowledge_answer(self, query: str, limit: int = 3) -> Dict[str, Any]:
        """
        Recall knowledge to ANSWER a specific question.
        
        Unlike recall_similar (which returns raw data), this method:
        1. Prioritizes KNOWLEDGE facts over conversations
        2. Returns only highly relevant matches (similarity > 0.5)
        3. Provides a clean answer structure for natural responses
        4. Searches by category if query matches known categories
        
        Args:
            query: The user's question (e.g., "favorite color", "birthday")
            limit: Maximum knowledge facts to return
            
        Returns:
            Dict with:
                - 'found': bool - whether relevant knowledge was found
                - 'facts': List[str] - relevant knowledge facts
                - 'best_match': str or None - the most relevant fact
                - 'similarity': float - similarity score of best match
                - 'category': str or None - category of best match
        """
        query_lower = query.lower()
        
        # Try category-based search first for known query types
        category_keywords = {
            'preference': ['favorite', 'favourite', 'prefer', 'like'],
            'personal': ['birthday', 'born', 'age', 'name', 'nickname'],
            'relationships': ['friend', 'best friend', 'brother', 'sister', 'mother', 'father', 'family', 'wife', 'husband', 'relationship'],
            'work': ['job', 'work', 'company', 'career', 'profession'],
            'location': ['live', 'city', 'address', 'home', 'country'],
            'interest': ['hobby', 'hobbies', 'interest', 'enjoy'],
            'education': ['university', 'college', 'school', 'studied', 'degree'],
        }
        
        detected_category = None
        for category, keywords in category_keywords.items():
            if any(kw in query_lower for kw in keywords):
                detected_category = category
                break
        
        logger.info(f"🧠 Knowledge recall: query='{query}', detected_category={detected_category}")
        
        # Search by embedding
        embedding = self.embedding.embed(query)
        
        # Search ONLY knowledge (not conversations)
        results = self.store.search_similar(
            MemoryStore.TABLE_KNOWLEDGE,
            embedding,
            limit=limit * 2  # Get more results to filter
        )
        
        logger.info(f"🧠 Knowledge search returned {len(results)} results for '{query}'")
        
        # Filter by relevance threshold and optionally by category
        relevant_facts = []
        best_match = None
        best_similarity = 0.0
        best_category = None
        
        for r in results:
            # FIXED: LanceDB uses L2 (Euclidean) distance, not cosine
            # L2 distance can be > 1.0, so use: similarity = 1 / (1 + distance)
            # This maps any positive distance to 0-1 range (lower distance = higher similarity)
            distance = r.get('_distance', 999)
            similarity = 1.0 / (1.0 + distance)
            
            fact = r.get('fact', '')
            fact_category = r.get('category', 'general')
            
            # Boost similarity if category matches
            if detected_category and fact_category == detected_category:
                similarity = min(1.0, similarity + 0.1)
            
            # Threshold: 0.4 for L2-based similarity (1/(1+d) where d~1.0 gives ~0.5)
            if similarity > 0.4:  # Lower threshold for L2 distance
                relevant_facts.append(fact)
                logger.debug(f"🧠 Relevant fact: '{fact[:50]}...' (sim={similarity:.3f})")
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = fact
                    best_category = fact_category
        
        logger.info(f"🧠 Knowledge recall result: found={len(relevant_facts)} facts, best_sim={best_similarity:.3f}")
        
        return {
            'found': len(relevant_facts) > 0,
            'facts': relevant_facts[:limit],
            'best_match': best_match,
            'similarity': best_similarity,
            'category': best_category
        }
    
    def recall_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get most recent conversation memories."""
        results = self.store.get_all(
            MemoryStore.TABLE_CONVERSATIONS,
            limit=limit
        )
        # Sort by timestamp descending
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        return results[:limit]
    
    def get_knowledge(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get all knowledge facts."""
        return self.store.get_all(MemoryStore.TABLE_KNOWLEDGE, limit=limit)
    
    # =========================================================================
    # Emotional Memory Operations (Phase 30 — Smart Memory Integration)
    # =========================================================================
    
    def store_emotional(
        self,
        content: str,
        category: str = 'event',
        emotion: str = 'neutral',
        importance: float = 0.5,
        tags: Optional[List[str]] = None,
        expires_at: str = '',
        metadata: str = '{}'
    ) -> str:
        """
        Store an emotional memory in LanceDB.
        
        Args:
            content: The emotional memory content (e.g., "User has exam tomorrow")
            category: event, mood, goal, preference, milestone, journal
            emotion: Associated mood at time of storage
            importance: Memory importance (0.0 - 1.0)
            tags: Optional topic tags
            expires_at: Optional expiry timestamp as ISO string
            metadata: Extra context as JSON string
            
        Returns:
            Memory ID
        """
        # Generate embedding for semantic search
        embedding = self.embedding.embed(content)
        
        # Create emotional memory object
        memory = EmotionalMemory(
            content=content,
            category=category,
            emotion=emotion,
            embedding=embedding,
            importance=importance,
            tags=tags or [],
            expires_at=expires_at,
            metadata=metadata
        )
        
        # Store in LanceDB
        data = memory.to_dict()
        data['vector'] = embedding.tolist()
        
        self.store.add(MemoryStore.TABLE_EMOTIONAL, data)
        
        logger.debug(f"💜 Stored emotional memory [{category}]: {memory.id[:8]}...")
        return memory.id
    
    def get_emotional(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all emotional memories from LanceDB.
        
        Args:
            limit: Maximum results to return
            
        Returns:
            List of emotional memory records
        """
        return self.store.get_all(MemoryStore.TABLE_EMOTIONAL, limit=limit)
    
    def get_emotional_by_category(self, category: str, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get emotional memories filtered by category.
        
        Args:
            category: event, mood, goal, preference, milestone, journal
            limit: Maximum results
            
        Returns:
            List of emotional memories in that category
        """
        try:
            return self.store.get_all(
                MemoryStore.TABLE_EMOTIONAL,
                filter_condition=f"category = '{category}'",
                limit=limit
            )
        except Exception as e:
            logger.warning(f"Emotional category query failed: {e}")
            return []
    
    def recall_emotional_similar(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Find emotional memories similar to a query using vector search.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching emotional memories with similarity scores
        """
        embedding = self.embedding.embed(query)
        results = self.store.search_similar(
            MemoryStore.TABLE_EMOTIONAL,
            embedding,
            limit=limit
        )
        
        for r in results:
            r['memory_type'] = 'emotional'
            distance = r.get('_distance', 999)
            r['similarity'] = 1.0 / (1.0 + distance)
        
        return results
    
    def get_skill_stats(self, action: str) -> Optional[Dict[str, Any]]:
        """Get usage statistics for a specific action."""
        results = self.store.get_all(
            MemoryStore.TABLE_SKILLS,
            filter_condition=f"action = '{action}'",
            limit=1
        )
        return results[0] if results else None
    
    # =========================================================================
    # Memory Management
    # =========================================================================
    
    def forget_memory(self, memory_id: str) -> bool:
        """
        Delete a specific memory by ID.
        
        Args:
            memory_id: ID of memory to delete
            
        Returns:
            True if deleted
        """
        # Try all tables
        for table in [MemoryStore.TABLE_CONVERSATIONS, 
                      MemoryStore.TABLE_KNOWLEDGE, 
                      MemoryStore.TABLE_SKILLS,
                      MemoryStore.TABLE_EMOTIONAL]:
            if self.store.delete(table, memory_id):
                logger.info(f"🗑️ Forgot memory: {memory_id[:8]}...")
                return True
        return False
    
    def forget_matching(self, query: str, limit: int = 10) -> int:
        """
        Delete memories matching a query.
        
        Args:
            query: Search query to find memories to delete
            limit: Maximum memories to delete
            
        Returns:
            Number of memories deleted
        """
        memories = self.recall_similar(query, limit=limit)
        deleted = 0
        
        for mem in memories:
            # Lower threshold to 0.35 for L2-based similarity (1/(1+distance) formula)
            if mem.get('similarity', 0) > 0.35:
                if self.forget_memory(mem['id']):
                    deleted += 1
        
        logger.info(f"🗑️ Forgot {deleted} memories matching '{query[:30]}...'")
        return deleted
    
    def mark_important(self, memory_id: str, importance: float = 0.9) -> bool:
        """
        Mark a memory as important (protects from pruning).
        
        Args:
            memory_id: Memory ID
            importance: Importance score (default 0.9)
            
        Returns:
            True if updated
        """
        return self.store.update(
            MemoryStore.TABLE_CONVERSATIONS,
            memory_id,
            {'importance': importance}
        )
    
    def prune_old_memories(self, days: int = 30, keep_important: bool = True) -> int:
        """
        Delete old, low-importance memories.
        
        Args:
            days: Delete memories older than this
            keep_important: If True, keep high-importance memories
            
        Returns:
            Number of memories deleted
        """
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        condition = f"timestamp < '{cutoff}'"
        if keep_important:
            condition += " AND importance < 0.7"
        
        deleted = self.store.delete_where(MemoryStore.TABLE_CONVERSATIONS, condition)
        logger.info(f"🧹 Pruned {deleted} old memories (older than {days} days)")
        return deleted
    
    def clear_all_memory(self, include_knowledge: bool = True) -> Dict[str, int]:
        """
        Clear ALL memories from the database.
        
        Args:
            include_knowledge: If True, also clear knowledge facts
            
        Returns:
            Dict with counts of deleted items per table
        """
        deleted = {
            'conversations': 0,
            'knowledge': 0,
            'skills': 0,
            'emotional': 0
        }
        
        try:
            # Clear conversations
            deleted['conversations'] = self.store.delete_all(MemoryStore.TABLE_CONVERSATIONS)
            
            # Clear knowledge if requested
            if include_knowledge:
                deleted['knowledge'] = self.store.delete_all(MemoryStore.TABLE_KNOWLEDGE)
            
            # Clear skills
            deleted['skills'] = self.store.delete_all(MemoryStore.TABLE_SKILLS)
            
            # Clear emotional memories
            deleted['emotional'] = self.store.delete_all(MemoryStore.TABLE_EMOTIONAL)
            
            total = sum(deleted.values())
            logger.info(f"🗑️ Cleared all memory: {total} items deleted")
            logger.info(f"   Conversations: {deleted['conversations']}, Knowledge: {deleted['knowledge']}, Skills: {deleted['skills']}, Emotional: {deleted['emotional']}")
            
        except Exception as e:
            logger.error(f"Error clearing all memory: {e}")
        
        return deleted
    
    # =========================================================================
    # Helper Methods
    # =========================================================================
    
    def _calculate_importance(
        self, 
        user_message: str, 
        nexa_response: str, 
        success: bool
    ) -> float:
        """Calculate importance score for a memory."""
        importance = 0.5  # Base importance
        
        # Longer messages are more important
        total_len = len(user_message) + len(nexa_response)
        if total_len > 200:
            importance += 0.1
        if total_len > 500:
            importance += 0.1
        
        # Successful interactions are more important
        if success:
            importance += 0.1
        else:
            importance -= 0.1
        
        # Keywords that indicate importance
        important_words = ['remember', 'important', 'always', 'prefer', 'favorite']
        if any(word in user_message.lower() for word in important_words):
            importance += 0.2
        
        return min(1.0, max(0.0, importance))
    
    def _extract_tags(self, text: str) -> List[str]:
        """Extract topic tags from text."""
        tags = []
        text_lower = text.lower()
        
        # Category detection
        categories = {
            'app': ['open', 'close', 'launch', 'start', 'application'],
            'volume': ['volume', 'sound', 'mute', 'audio'],
            'brightness': ['brightness', 'screen', 'display'],
            'music': ['music', 'song', 'play', 'spotify'],
            'game': ['game', 'steam', 'play'],
            'weather': ['weather', 'temperature', 'rain'],
            'time': ['time', 'date', 'clock'],
            'system': ['shutdown', 'restart', 'sleep', 'battery'],
        }
        
        for tag, keywords in categories.items():
            if any(kw in text_lower for kw in keywords):
                tags.append(tag)
        
        return tags[:3]  # Max 3 tags
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return self.store.get_stats()
