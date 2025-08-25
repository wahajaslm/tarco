# WORKFLOW: Qdrant vector database for similarity search and retrieval.
# Used by: RAG pipeline, HS classification, vector indexing
# Functions:
# 1. search() - Find similar documents using cosine similarity
# 2. add_documents() - Index documents with embeddings
# 3. _build_filter() - Apply metadata filters to searches
# 4. get_collection_info() - Monitor collection status
#
# Retrieval flow: Query embedding -> Vector search -> Top-k candidates -> Metadata
# This is the second step in RAG: query -> similar documents
# Returns candidates for reranking and classification.

import logging
import uuid
from typing import Any, Dict, List, Optional

from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue, PointStruct, Distance, VectorParams

from core.config import settings
from rag.embeddings import get_embedding_model

logger = logging.getLogger(__name__)


class VectorRetriever:
    """Vector retrieval using Qdrant and embedding model."""

    def __init__(self, collection_name: str = "nomenclature_chunks"):
        self.collection_name = collection_name
        self.embedding_model = None

        qdrant_url = settings.qdrant_url
        if qdrant_url in {":memory:", "memory", "memory://"}:
            self.client = QdrantClient(":memory:")
        else:
            parsed = qdrant_url.replace("http://", "").replace("https://", "")
            if ":" in parsed:
                host, port = parsed.split(":")
                port = int(port)
            else:
                host = parsed
                port = 6333
            self.client = QdrantClient(host, port=port)

        self._ensure_collection_exists()

    def _ensure_collection_exists(self):
        """Ensure the collection exists with proper configuration."""
        collections = self.client.get_collections()
        collection_names = [c.name for c in collections.collections]

        if self.collection_name not in collection_names:
            logger.info(f"Creating collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=settings.vector_dimension,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Collection {self.collection_name} created successfully")
        else:
            logger.info(f"Collection {self.collection_name} already exists")
    
    def add_documents(self, documents: List[Dict[str, Any]]) -> None:
        """
        Add documents to the vector store.
        
        Args:
            documents: List of documents with 'content' and 'metadata' fields
        """
        try:
            if not documents:
                return
            
            # Extract texts and metadata
            texts = [doc['content'] for doc in documents]
            metadatas = [doc.get('metadata', {}) for doc in documents]
            
            # Generate embeddings
            model = self._get_embedding_model()
            embeddings = model.encode_batch(texts)
            
            # Prepare points for Qdrant
            points = []
            for embedding, metadata in zip(embeddings, metadatas):
                points.append(
                    PointStruct(id=uuid.uuid4(), vector=embedding.tolist(), payload=metadata)
                )
            
            # Upload to Qdrant
            self.client.upsert(
                collection_name=self.collection_name,
                points=points
            )
            
            logger.info(f"Added {len(documents)} documents to vector store")
            
        except Exception as e:
            logger.error(f"Failed to add documents: {e}")
            raise
    
    def search(self, query: str, top_k: int = None, filter_conditions: Optional[Dict] = None) -> List[Dict[str, Any]]:
        """
        Search for similar documents.
        
        Args:
            query: Search query
            top_k: Number of results to return
            filter_conditions: Optional filter conditions
            
        Returns:
            List of search results with scores and metadata
        """
        try:
            top_k = top_k or settings.top_k_retrieval
            
            # Generate query embedding
            model = self._get_embedding_model()
            query_embedding = model.encode(query)
            
            # Perform search
            search_results = self.client.search(
                collection_name=self.collection_name,
                query_vector=query_embedding.tolist(),
                limit=top_k,
                with_payload=True,
                query_filter=self._build_filter(filter_conditions) if filter_conditions else None,
            )
            
            # Format results
            results = []
            for result in search_results:
                results.append({
                    'score': result.score,
                    'metadata': result.payload,
                    'id': result.id
                })
            
            logger.info(f"Retrieved {len(results)} results for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise
    
    def _build_filter(self, conditions: Dict[str, Any]) -> Filter:
        """Build Qdrant filter from conditions."""
        filter_conditions = []
        
        for field, value in conditions.items():
            if isinstance(value, (str, int, float, bool)):
                filter_conditions.append(
                    FieldCondition(
                        key=field,
                        match=MatchValue(value=value)
                    )
                )
            elif isinstance(value, list):
                # Handle list conditions (e.g., "in" operations)
                for val in value:
                    filter_conditions.append(
                        FieldCondition(
                            key=field,
                            match=MatchValue(value=val)
                        )
                    )
        
        return Filter(must=filter_conditions)
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information."""
        try:
            info = self.client.get_collection(self.collection_name)
            return {
                'name': info.name,
                'vectors_count': info.vectors_count,
                'points_count': info.points_count,
                'status': info.status
            }
        except Exception as e:
            logger.error(f"Failed to get collection info: {e}")
            raise
    
    def delete_collection(self) -> None:
        """Delete the collection."""
        try:
            self.client.delete_collection(self.collection_name)
            logger.info(f"Collection {self.collection_name} deleted")
        except Exception as e:
            logger.error(f"Failed to delete collection: {e}")
            raise

    def _get_embedding_model(self):
        if self.embedding_model is None:
            self.embedding_model = get_embedding_model()
        return self.embedding_model


# Global retriever instance
vector_retriever = VectorRetriever()
