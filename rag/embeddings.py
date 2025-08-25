# WORKFLOW: BAAI/bge-m3 embedding model for vector search operations.
# Used by: RAG pipeline, vector indexing, similarity search
# Functions:
# 1. encode() - Generate embeddings for single text or batch
# 2. encode_batch() - Process large batches efficiently
# 3. get_embedding_dimension() - Get model output dimension
#
# Embedding flow: Text input -> BAAI/bge-m3 model -> Normalized embeddings -> Vector store
# This is the first step in the RAG pipeline: text -> vector representation
# Used for both indexing nomenclature data and query encoding.

from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np
import logging
from core.config import settings

logger = logging.getLogger(__name__)


class EmbeddingModel:
    """BAAI/bge-m3 embedding model wrapper."""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.embedding_model
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the embedding model."""
        try:
            logger.info(f"Loading embedding model: {self.model_name}")
            self.model = SentenceTransformer(
                self.model_name,
                cache_folder=settings.model_cache_dir
            )
            logger.info("Embedding model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            raise
    
    def encode(self, texts: Union[str, List[str]], normalize: bool = True) -> np.ndarray:
        """
        Encode texts to embeddings.
        
        Args:
            texts: Single text or list of texts
            normalize: Whether to normalize embeddings (recommended for cosine similarity)
            
        Returns:
            Embeddings as numpy array
        """
        try:
            if isinstance(texts, str):
                texts = [texts]
            
            embeddings = self.model.encode(
                texts,
                normalize_embeddings=normalize,
                convert_to_numpy=True
            )
            
            return embeddings
        except Exception as e:
            logger.error(f"Embedding encoding failed: {e}")
            raise
    
    def encode_batch(self, texts: List[str], batch_size: int = 32, normalize: bool = True) -> np.ndarray:
        """
        Encode texts in batches for memory efficiency.
        
        Args:
            texts: List of texts to encode
            batch_size: Batch size for processing
            normalize: Whether to normalize embeddings
            
        Returns:
            Embeddings as numpy array
        """
        try:
            all_embeddings = []
            
            for i in range(0, len(texts), batch_size):
                batch = texts[i:i + batch_size]
                batch_embeddings = self.encode(batch, normalize=normalize)
                all_embeddings.append(batch_embeddings)
            
            return np.vstack(all_embeddings)
        except Exception as e:
            logger.error(f"Batch embedding encoding failed: {e}")
            raise
    
    def get_embedding_dimension(self) -> int:
        """Get the embedding dimension."""
        if self.model is None:
            raise ValueError("Model not loaded")
        return self.model.get_sentence_embedding_dimension()


# Global embedding model instance (lazy-loaded)
_embedding_model = None

def get_embedding_model():
    """Get the global embedding model instance (lazy-loaded)."""
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = EmbeddingModel()
    return _embedding_model
