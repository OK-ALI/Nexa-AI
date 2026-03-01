"""
Embedding Engine - Text to Vector Conversion for Smart Memory

Uses sentence-transformers to convert text into 384-dimensional vectors
for semantic similarity search in LanceDB.

Model: all-MiniLM-L6-v2 (22MB, fast, good quality)
"""

import logging
from typing import List, Optional, Union
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """
    Converts text into embedding vectors for semantic search.
    
    Uses all-MiniLM-L6-v2 model:
    - 384 dimensions
    - 22MB model size
    - Fast CPU inference (~10ms per text)
    - Good semantic quality
    """
    
    # Model configuration
    MODEL_NAME = "all-MiniLM-L6-v2"
    EMBEDDING_DIM = 384
    
    def __init__(self, lazy_load: bool = True):
        """
        Initialize embedding engine.
        
        Args:
            lazy_load: If True, model loads on first use. If False, load immediately.
        """
        self._model = None
        self._lazy_load = lazy_load
        self._load_failed = False  # Track if loading already failed
        
        if not lazy_load:
            self._load_model()
    
    def _load_model(self) -> None:
        """Load the sentence-transformer model."""
        if self._model is not None or self._load_failed:
            return
        
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"🧠 Loading embedding model: {self.MODEL_NAME}...")
            self._model = SentenceTransformer(self.MODEL_NAME)
            logger.info(f"✅ Embedding model loaded ({self.EMBEDDING_DIM}-dim vectors)")
            
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            self._load_failed = True
            # DON'T raise - gracefully degrade to zero vectors
    
    @property
    def model(self):
        """Get model, loading if necessary (lazy load). Returns None if failed."""
        if self._model is None and not self._load_failed:
            self._load_model()
        return self._model
    
    def embed(self, text: str) -> np.ndarray:
        """
        Convert a single text to embedding vector.
        
        Args:
            text: Text to embed
            
        Returns:
            384-dimensional numpy array
        """
        if not text or not text.strip():
            logger.warning("⚠️ Empty text provided for embedding, returning zero vector")
            return np.zeros(self.EMBEDDING_DIM, dtype=np.float32)
        
        # Check if model is available
        if self.model is None:
            # Model failed to load - return zero vector (graceful degradation)
            return np.zeros(self.EMBEDDING_DIM, dtype=np.float32)
        
        try:
            embedding = self.model.encode(
                text,
                convert_to_numpy=True,
                normalize_embeddings=True  # Unit vectors for cosine similarity
            )
            return embedding.astype(np.float32)
            
        except Exception as e:
            logger.error(f"❌ Error embedding text: {e}")
            return np.zeros(self.EMBEDDING_DIM, dtype=np.float32)
    
    def embed_batch(self, texts: List[str]) -> np.ndarray:
        """
        Convert multiple texts to embedding vectors (batch processing).
        
        Args:
            texts: List of texts to embed
            
        Returns:
            Numpy array of shape (len(texts), 384)
        """
        if not texts:
            return np.zeros((0, self.EMBEDDING_DIM), dtype=np.float32)
        
        # Check if model is available
        if self.model is None:
            return np.zeros((len(texts), self.EMBEDDING_DIM), dtype=np.float32)
        
        # Filter empty texts
        valid_texts = [t if t and t.strip() else " " for t in texts]
        
        try:
            embeddings = self.model.encode(
                valid_texts,
                convert_to_numpy=True,
                normalize_embeddings=True,
                batch_size=32,
                show_progress_bar=False
            )
            return embeddings.astype(np.float32)
            
        except Exception as e:
            logger.error(f"❌ Error batch embedding: {e}")
            return np.zeros((len(texts), self.EMBEDDING_DIM), dtype=np.float32)
    
    def similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """
        Calculate cosine similarity between two vectors.
        
        Args:
            vec1: First embedding vector
            vec2: Second embedding vector
            
        Returns:
            Similarity score between -1.0 and 1.0 (higher = more similar)
        """
        # Both vectors are normalized, so cosine similarity = dot product
        return float(np.dot(vec1, vec2))
    
    def find_most_similar(
        self, 
        query_vec: np.ndarray, 
        candidates: List[np.ndarray],
        top_k: int = 5
    ) -> List[tuple]:
        """
        Find most similar vectors from a list of candidates.
        
        Args:
            query_vec: Query embedding
            candidates: List of candidate embeddings
            top_k: Number of top results to return
            
        Returns:
            List of (index, similarity_score) tuples, sorted by similarity descending
        """
        if not candidates:
            return []
        
        similarities = [
            (i, self.similarity(query_vec, cand)) 
            for i, cand in enumerate(candidates)
        ]
        
        # Sort by similarity descending
        similarities.sort(key=lambda x: x[1], reverse=True)
        
        return similarities[:top_k]
    
    def is_loaded(self) -> bool:
        """Check if model is currently loaded."""
        return self._model is not None
    
    def unload(self) -> None:
        """Unload model to free memory."""
        if self._model is not None:
            del self._model
            self._model = None
            logger.info("🗑️ Embedding model unloaded")


# Singleton instance for global use
_embedding_engine: Optional[EmbeddingEngine] = None


def get_embedding_engine() -> EmbeddingEngine:
    """Get or create the global embedding engine instance."""
    global _embedding_engine
    if _embedding_engine is None:
        _embedding_engine = EmbeddingEngine(lazy_load=True)
    return _embedding_engine
