# WORKFLOW: BAAI/bge-reranker-base cross-encoder for reranking search results.
# Used by: RAG pipeline, HS classification, confidence calibration
# Functions:
# 1. rerank() - Rerank candidates using cross-encoder scores
# 2. rerank_with_metadata() - Enhanced reranking with metadata handling
# 3. get_confidence_features() - Extract features for confidence calibration
#
# Reranking flow: Candidates -> Cross-encoder scoring -> Reranked results -> Top-k
# This is the third step in RAG: candidates -> relevance scoring
# Provides more accurate ranking than vector similarity alone.
# Features extracted here are used for confidence calibration.

"""Cross-encoder based reranker for the RAG pipeline.

Similar to the embedding utilities, we avoid importing heavy ML dependencies at
module import time. The actual cross-encoder model is loaded lazily when
instantiating :class:`Reranker`.
"""

from typing import List, Dict, Any
import numpy as np
import logging
from core.config import settings

logger = logging.getLogger(__name__)


class Reranker:
    """BAAI/bge-reranker-base cross-encoder for reranking search results."""
    
    def __init__(self, model_name: str = None):
        self.model_name = model_name or settings.reranker_model
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Load the reranker model."""
        try:
            logger.info(f"Loading reranker model: {self.model_name}")
            from sentence_transformers import CrossEncoder

            self.model = CrossEncoder(self.model_name)
            logger.info("Reranker model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load reranker model: {e}")
            raise
    
    def rerank(self, query: str, documents: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]:
        """
        Rerank documents based on query relevance.
        
        Args:
            query: Search query
            documents: List of documents with 'content' and other metadata
            top_k: Number of top results to return
            
        Returns:
            Reranked list of documents with updated scores
        """
        try:
            if not documents:
                return []
            
            top_k = top_k or settings.top_k_rerank
            
            # Prepare pairs for cross-encoder
            pairs = []
            for doc in documents:
                content = doc.get('content', '')
                pairs.append([query, content])
            
            # Get cross-encoder scores
            scores = self.model.predict(pairs)
            
            # Update documents with new scores
            for doc, score in zip(documents, scores):
                doc['rerank_score'] = float(score)
            
            # Sort by rerank score (descending)
            reranked_docs = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)
            
            # Return top_k results
            top_results = reranked_docs[:top_k]
            
            logger.info(f"Reranked {len(documents)} documents, returning top {len(top_results)}")
            return top_results
            
        except Exception as e:
            logger.error(f"Reranking failed: {e}")
            raise
    
    def rerank_with_metadata(self, query: str, documents: List[Dict[str, Any]], top_k: int = None) -> List[Dict[str, Any]]:
        """
        Rerank documents with enhanced metadata handling.
        
        Args:
            query: Search query
            documents: List of documents with metadata
            top_k: Number of top results to return
            
        Returns:
            Reranked list of documents with scores and metadata
        """
        try:
            if not documents:
                return []
            
            top_k = top_k or settings.top_k_rerank
            
            # Extract content for reranking
            contents = []
            for doc in documents:
                content = doc.get('content', '')
                if not content and 'metadata' in doc:
                    # Try to construct content from metadata
                    metadata = doc['metadata']
                    content = f"{metadata.get('goods_code', '')} {metadata.get('description', '')}"
                contents.append(content)
            
            # Prepare pairs for cross-encoder
            pairs = [[query, content] for content in contents]
            
            # Get cross-encoder scores
            scores = self.model.predict(pairs)
            
            # Update documents with new scores
            for doc, score in zip(documents, scores):
                doc['rerank_score'] = float(score)
                doc['original_score'] = doc.get('score', 0.0)  # Preserve original score
            
            # Sort by rerank score (descending)
            reranked_docs = sorted(documents, key=lambda x: x['rerank_score'], reverse=True)
            
            # Return top_k results
            top_results = reranked_docs[:top_k]
            
            logger.info(f"Reranked {len(documents)} documents with metadata, returning top {len(top_results)}")
            return top_results
            
        except Exception as e:
            logger.error(f"Reranking with metadata failed: {e}")
            raise
    
    def get_confidence_features(self, query: str, top_results: List[Dict[str, Any]]) -> List[float]:
        """
        Extract features for confidence calibration.
        
        Args:
            query: Search query
            top_results: Top reranked results
            
        Returns:
            List of confidence features
        """
        try:
            if not top_results:
                return []
            
            features = []
            
            # Top1 score
            if len(top_results) > 0:
                features.append(top_results[0]['rerank_score'])
            else:
                features.append(0.0)
            
            # Top2 score
            if len(top_results) > 1:
                features.append(top_results[1]['rerank_score'])
            else:
                features.append(0.0)
            
            # Gap between top1 and top2
            if len(top_results) > 1:
                gap = top_results[0]['rerank_score'] - top_results[1]['rerank_score']
                features.append(gap)
            else:
                features.append(0.0)
            
            # Mean score of top results
            scores = [doc['rerank_score'] for doc in top_results]
            features.append(np.mean(scores))
            
            # Standard deviation of scores
            features.append(np.std(scores))
            
            return features
            
        except Exception as e:
            logger.error(f"Feature extraction failed: {e}")
            raise


# Global reranker instance (lazy-loaded)
_reranker = None

def get_reranker():
    """Get the global reranker instance (lazy-loaded)."""
    global _reranker
    if _reranker is None:
        _reranker = Reranker()
    return _reranker
