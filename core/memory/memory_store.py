"""
Memory Store - LanceDB Vector Database Operations

Handles all database operations for Nexa's Smart Memory system:
- Creating/managing tables for different memory types
- CRUD operations (Create, Read, Update, Delete)
- Vector similarity search
- Hybrid search (vector + filters)
"""

import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class MemoryStore:
    """
    LanceDB wrapper for vector storage and retrieval.
    
    Tables:
    - conversations: ConversationMemory records
    - knowledge: KnowledgeMemory records  
    - skills: SkillMemory records
    """
    
    # Table names
    TABLE_CONVERSATIONS = "conversations"
    TABLE_KNOWLEDGE = "knowledge"
    TABLE_SKILLS = "skills"
    TABLE_EMOTIONAL = "emotional"
    
    # Embedding dimension
    VECTOR_DIM = 384
    
    def __init__(self, db_path: Union[str, Path]):
        """
        Initialize connection to LanceDB.
        
        Args:
            db_path: Path to database directory
        """
        self.db_path = Path(db_path)
        self.db_path.mkdir(parents=True, exist_ok=True)
        
        self._db = None
        self._connect()
    
    def _connect(self) -> None:
        """Establish connection to LanceDB."""
        try:
            import lancedb
            
            self._db = lancedb.connect(str(self.db_path))
            logger.info(f"✅ Connected to LanceDB at {self.db_path}")
            
            # Ensure tables exist and are up to date
            self._ensure_tables()
            self._migrate_tables()
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to LanceDB: {e}")
            raise RuntimeError(f"Could not connect to LanceDB: {e}") from e
    
    def _migrate_tables(self) -> None:
        """Migrate tables to add missing columns."""
        import pyarrow as pa
        
        try:
            # Check if conversations table needs migration (session_id column)
            if self.TABLE_CONVERSATIONS in self._db.table_names():
                table = self._db.open_table(self.TABLE_CONVERSATIONS)
                schema = table.schema
                field_names = [field.name for field in schema]
                
                if 'session_id' not in field_names:
                    logger.info("🔄 Migrating conversations table: adding session_id column...")
                    # Drop and recreate the table (data will be lost but it's okay for fresh start)
                    self._db.drop_table(self.TABLE_CONVERSATIONS)
                    new_schema = pa.schema([
                        pa.field("id", pa.string()),
                        pa.field("user_message", pa.string()),
                        pa.field("nexa_response", pa.string()),
                        pa.field("vector", pa.list_(pa.float32(), self.VECTOR_DIM)),
                        pa.field("timestamp", pa.string()),
                        pa.field("success", pa.bool_()),
                        pa.field("importance", pa.float32()),
                        pa.field("tags", pa.string()),
                        pa.field("session_id", pa.string()),
                    ])
                    self._db.create_table(self.TABLE_CONVERSATIONS, schema=new_schema)
                    logger.info("✅ Conversations table migrated with session_id column")
            
            # Check if knowledge table needs migration (category column)
            if self.TABLE_KNOWLEDGE in self._db.table_names():
                table = self._db.open_table(self.TABLE_KNOWLEDGE)
                schema = table.schema
                field_names = [field.name for field in schema]
                
                if 'category' not in field_names:
                    logger.info("🔄 Migrating knowledge table: adding category column...")
                    # Drop and recreate the table
                    self._db.drop_table(self.TABLE_KNOWLEDGE)
                    new_schema = pa.schema([
                        pa.field("id", pa.string()),
                        pa.field("fact", pa.string()),
                        pa.field("category", pa.string()),
                        pa.field("vector", pa.list_(pa.float32(), self.VECTOR_DIM)),
                        pa.field("source", pa.string()),
                        pa.field("confidence", pa.float32()),
                        pa.field("created_at", pa.string()),
                        pa.field("last_accessed", pa.string()),
                        pa.field("access_count", pa.int32()),
                    ])
                    self._db.create_table(self.TABLE_KNOWLEDGE, schema=new_schema)
                    logger.info("✅ Knowledge table migrated with category column")
                    
        except Exception as e:
            logger.warning(f"⚠️ Table migration warning: {e}")
    
    def _ensure_tables(self) -> None:
        """Create tables if they don't exist."""
        import pyarrow as pa
        
        existing_tables = self._db.table_names()
        
        # Conversations table schema
        if self.TABLE_CONVERSATIONS not in existing_tables:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("user_message", pa.string()),
                pa.field("nexa_response", pa.string()),
                pa.field("vector", pa.list_(pa.float32(), self.VECTOR_DIM)),
                pa.field("timestamp", pa.string()),
                pa.field("success", pa.bool_()),
                pa.field("importance", pa.float32()),
                pa.field("tags", pa.string()),
                pa.field("session_id", pa.string()),  # Session tracking
            ])
            self._db.create_table(self.TABLE_CONVERSATIONS, schema=schema)
            logger.info(f"📋 Created table: {self.TABLE_CONVERSATIONS}")
        
        # Knowledge table schema
        if self.TABLE_KNOWLEDGE not in existing_tables:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("fact", pa.string()),
                pa.field("category", pa.string()),  # preference, personal, relationship, etc.
                pa.field("vector", pa.list_(pa.float32(), self.VECTOR_DIM)),
                pa.field("source", pa.string()),
                pa.field("confidence", pa.float32()),
                pa.field("created_at", pa.string()),
                pa.field("last_accessed", pa.string()),
                pa.field("access_count", pa.int32()),
            ])
            self._db.create_table(self.TABLE_KNOWLEDGE, schema=schema)
            logger.info(f"📋 Created table: {self.TABLE_KNOWLEDGE}")
        
        # Skills table schema
        if self.TABLE_SKILLS not in existing_tables:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("action", pa.string()),
                pa.field("success_patterns", pa.string()),  # JSON string
                pa.field("failure_patterns", pa.string()),  # JSON string
                pa.field("usage_count", pa.int32()),
                pa.field("success_rate", pa.float32()),
                pa.field("last_used", pa.string()),
                pa.field("preferred_value", pa.string()),  # JSON string
            ])
            self._db.create_table(self.TABLE_SKILLS, schema=schema)
            logger.info(f"📋 Created table: {self.TABLE_SKILLS}")
        
        # Emotional table schema (Phase 30 — Smart Memory integration)
        if self.TABLE_EMOTIONAL not in existing_tables:
            schema = pa.schema([
                pa.field("id", pa.string()),
                pa.field("content", pa.string()),
                pa.field("category", pa.string()),       # event, mood, goal, preference, milestone, journal
                pa.field("emotion", pa.string()),         # Associated mood at time of storage
                pa.field("vector", pa.list_(pa.float32(), self.VECTOR_DIM)),
                pa.field("importance", pa.float32()),
                pa.field("created_at", pa.string()),
                pa.field("expires_at", pa.string()),
                pa.field("tags", pa.string()),            # Comma-separated tags
                pa.field("metadata", pa.string()),        # JSON string
            ])
            self._db.create_table(self.TABLE_EMOTIONAL, schema=schema)
            logger.info(f"📋 Created table: {self.TABLE_EMOTIONAL}")
    
    def _get_table(self, table_name: str):
        """Get a table by name."""
        return self._db.open_table(table_name)
    
    # =========================================================================
    # CRUD Operations
    # =========================================================================
    
    def add(self, table_name: str, data: Dict[str, Any]) -> str:
        """
        Add a record to a table.
        
        Args:
            table_name: Name of the table
            data: Record data (must include 'id' and 'vector')
            
        Returns:
            ID of the inserted record
        """
        try:
            table = self._get_table(table_name)
            table.add([data])
            record_id = data.get('id', 'unknown')
            logger.debug(f"➕ Added record {record_id} to {table_name}")
            return record_id
            
        except Exception as e:
            logger.error(f"❌ Error adding to {table_name}: {e}")
            raise
    
    def add_batch(self, table_name: str, records: List[Dict[str, Any]]) -> int:
        """
        Add multiple records to a table.
        
        Args:
            table_name: Name of the table
            records: List of record dicts
            
        Returns:
            Number of records added
        """
        if not records:
            return 0
        
        try:
            table = self._get_table(table_name)
            table.add(records)
            logger.debug(f"➕ Added {len(records)} records to {table_name}")
            return len(records)
            
        except Exception as e:
            logger.error(f"❌ Error batch adding to {table_name}: {e}")
            raise
    
    def get(self, table_name: str, record_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a record by ID.
        
        Args:
            table_name: Name of the table
            record_id: Record ID to retrieve
            
        Returns:
            Record dict or None if not found
        """
        try:
            table = self._get_table(table_name)
            results = table.search().where(f"id = '{record_id}'", prefilter=True).limit(1).to_list()
            
            if results:
                return results[0]
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting {record_id} from {table_name}: {e}")
            return None
    
    def update(self, table_name: str, record_id: str, updates: Dict[str, Any]) -> bool:
        """
        Update a record by ID.
        
        Args:
            table_name: Name of the table
            record_id: Record ID to update
            updates: Dict of field -> new value
            
        Returns:
            True if updated, False otherwise
        """
        try:
            table = self._get_table(table_name)
            
            # LanceDB update: delete + re-add approach
            existing = self.get(table_name, record_id)
            if not existing:
                logger.warning(f"⚠️ Record {record_id} not found for update")
                return False
            
            # Merge updates
            existing.update(updates)
            
            # Delete old and add new
            self.delete(table_name, record_id)
            self.add(table_name, existing)
            
            logger.debug(f"✏️ Updated record {record_id} in {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error updating {record_id} in {table_name}: {e}")
            return False
    
    def delete(self, table_name: str, record_id: str) -> bool:
        """
        Delete a record by ID.
        
        Args:
            table_name: Name of the table
            record_id: Record ID to delete
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            table = self._get_table(table_name)
            table.delete(f"id = '{record_id}'")
            logger.debug(f"🗑️ Deleted record {record_id} from {table_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error deleting {record_id} from {table_name}: {e}")
            return False
    
    def delete_where(self, table_name: str, condition: str) -> int:
        """
        Delete records matching a condition.
        
        Args:
            table_name: Name of the table
            condition: SQL-like WHERE condition
            
        Returns:
            Number of records deleted (approximate)
        """
        try:
            table = self._get_table(table_name)
            # Get count before
            before_count = table.count_rows()
            table.delete(condition)
            after_count = table.count_rows()
            
            deleted = before_count - after_count
            logger.info(f"🗑️ Deleted {deleted} records from {table_name} where {condition}")
            return deleted
            
        except Exception as e:
            logger.error(f"❌ Error deleting from {table_name}: {e}")
            return 0
    
    def delete_all(self, table_name: str) -> int:
        """
        Delete ALL records from a table.
        
        Args:
            table_name: Name of the table to clear
            
        Returns:
            Number of records deleted
        """
        try:
            table = self._get_table(table_name)
            count = table.count_rows()
            if count > 0:
                # Delete all by using a condition that matches everything
                table.delete("id IS NOT NULL")
                logger.info(f"🗑️ Cleared all {count} records from {table_name}")
            return count
            
        except Exception as e:
            logger.error(f"❌ Error clearing {table_name}: {e}")
            return 0
    
    # =========================================================================
    # Search Operations
    # =========================================================================
    
    def search_similar(
        self, 
        table_name: str, 
        query_vector: np.ndarray, 
        limit: int = 10,
        min_similarity: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search for similar records using vector similarity.
        
        Args:
            table_name: Name of the table
            query_vector: Query embedding vector
            limit: Maximum results to return
            min_similarity: Minimum similarity threshold (0.0 - 1.0)
            
        Returns:
            List of matching records with '_distance' field
        """
        try:
            table = self._get_table(table_name)
            
            results = (
                table
                .search(query_vector.tolist())
                .limit(limit)
                .to_list()
            )
            
            # Filter by similarity if needed (LanceDB returns L2 distance, lower = more similar)
            # Convert L2 distance to similarity: sim = 1 / (1 + distance)
            if min_similarity > 0:
                results = [
                    r for r in results 
                    if (1.0 / (1.0 + r.get('_distance', 999))) >= min_similarity
                ]
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error searching {table_name}: {e}")
            return []
    
    def search_hybrid(
        self,
        table_name: str,
        query_vector: np.ndarray,
        filter_condition: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search: vector similarity + filter conditions.
        
        Args:
            table_name: Name of the table
            query_vector: Query embedding vector
            filter_condition: SQL-like WHERE condition
            limit: Maximum results to return
            
        Returns:
            List of matching records
        """
        try:
            table = self._get_table(table_name)
            
            results = (
                table
                .search(query_vector.tolist())
                .where(filter_condition, prefilter=True)
                .limit(limit)
                .to_list()
            )
            
            return results
            
        except Exception as e:
            logger.error(f"❌ Error hybrid searching {table_name}: {e}")
            return []
    
    def get_all(
        self, 
        table_name: str, 
        filter_condition: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get all records from a table (with optional filter).
        
        Args:
            table_name: Name of the table
            filter_condition: Optional SQL-like WHERE condition
            limit: Maximum results to return
            
        Returns:
            List of records
        """
        try:
            table = self._get_table(table_name)
            
            # Use a dummy search to get all records
            query = table.search()
            
            if filter_condition:
                query = query.where(filter_condition, prefilter=True)
            
            results = query.limit(limit).to_list()
            return results
            
        except Exception as e:
            logger.error(f"❌ Error getting all from {table_name}: {e}")
            return []
    
    def count(self, table_name: str) -> int:
        """Get number of records in a table."""
        try:
            table = self._get_table(table_name)
            return table.count_rows()
        except Exception as e:
            logger.error(f"❌ Error counting {table_name}: {e}")
            return 0
    
    # =========================================================================
    # Utility Methods
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the database."""
        return {
            'conversations': self.count(self.TABLE_CONVERSATIONS),
            'knowledge': self.count(self.TABLE_KNOWLEDGE),
            'skills': self.count(self.TABLE_SKILLS),
            'emotional': self.count(self.TABLE_EMOTIONAL),
            'path': str(self.db_path),
        }
    
    def clear_table(self, table_name: str) -> int:
        """
        Clear all records from a table.
        
        Args:
            table_name: Name of the table to clear
            
        Returns:
            Number of records deleted
        """
        count = self.count(table_name)
        if count > 0:
            try:
                # Delete all by using a always-true condition
                table = self._get_table(table_name)
                table.delete("id IS NOT NULL")
                logger.info(f"🗑️ Cleared {count} records from {table_name}")
            except Exception as e:
                logger.error(f"❌ Error clearing {table_name}: {e}")
                return 0
        return count
    
    def close(self) -> None:
        """Close database connection."""
        self._db = None
        logger.info("🔒 LanceDB connection closed")
