# WORKFLOW: Vector index building for RAG operations using goods nomenclature data.
# Used by: ETL pipeline, bootstrap script, vector index maintenance
# Functions:
# 1. build_nomenclature_index() - Build vector index from goods nomenclature
# 2. build_evidence_index() - Build vector index from legal evidence
# 3. update_vector_index() - Update existing vector index with new data
# 4. validate_vector_index() - Validate vector index integrity
# 5. rebuild_vector_index() - Complete rebuild of vector index
#
# Indexing flow: Database data -> Text preparation -> Embedding generation -> Vector storage -> Validation
# This creates the vector search capabilities needed for HS classification and RAG operations.

"""
Vector index building for RAG operations.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from db.models import GoodsNomenclature, LegalBases, MeasuresImport, MeasuresExport
from rag.retrieval import vector_retriever
from rag.embeddings import get_embedding_model
from core.config import settings

logger = logging.getLogger(__name__)


def prepare_nomenclature_documents(db: Session) -> List[Dict[str, Any]]:
    """
    Prepare goods nomenclature documents for vector indexing.
    
    Args:
        db: Database session
        
    Returns:
        List of document dictionaries
    """
    try:
        # Get all goods nomenclature items
        nomenclature_items = db.query(GoodsNomenclature).all()
        
        documents = []
        for item in nomenclature_items:
            # Create content for vector search
            content = f"{item.goods_code} {item.description}"
            
            # Create metadata
            metadata = {
                'goods_code': item.goods_code,
                'description': item.description,
                'level': item.level,
                'is_leaf': item.is_leaf,
                'valid_from': item.valid_from.isoformat() if item.valid_from else None,
                'valid_to': item.valid_to.isoformat() if item.valid_to else None,
                'type': 'nomenclature'
            }
            
            documents.append({
                'content': content,
                'metadata': metadata
            })
        
        logger.info(f"Prepared {len(documents)} nomenclature documents for indexing")
        return documents
        
    except Exception as e:
        logger.error(f"Failed to prepare nomenclature documents: {e}")
        raise


def prepare_evidence_documents(db: Session) -> List[Dict[str, Any]]:
    """
    Prepare legal evidence documents for vector indexing.
    
    Args:
        db: Database session
        
    Returns:
        List of document dictionaries
    """
    try:
        documents = []
        
        # Get legal bases
        legal_bases = db.query(LegalBases).all()
        for legal_base in legal_bases:
            content = f"{legal_base.id} {legal_base.title}"
            metadata = {
                'legal_base_id': legal_base.id,
                'title': legal_base.title,
                'type': 'legal_base'
            }
            documents.append({
                'content': content,
                'metadata': metadata
            })
        
        # Get measures with legal context
        import_measures = db.query(MeasuresImport).all()
        for measure in import_measures:
            content = f"{measure.goods_code} {measure.measure_type} {measure.legal_base_title}"
            metadata = {
                'goods_code': measure.goods_code,
                'measure_type': measure.measure_type,
                'origin_group': measure.origin_group,
                'legal_base_id': measure.legal_base_id,
                'legal_base_title': measure.legal_base_title,
                'type': 'import_measure'
            }
            documents.append({
                'content': content,
                'metadata': metadata
            })
        
        export_measures = db.query(MeasuresExport).all()
        for measure in export_measures:
            content = f"{measure.goods_code} {measure.measure_type} {measure.legal_base_title}"
            metadata = {
                'goods_code': measure.goods_code,
                'measure_type': measure.measure_type,
                'destination_group': measure.destination_group,
                'legal_base_id': measure.legal_base_id,
                'legal_base_title': measure.legal_base_title,
                'type': 'export_measure'
            }
            documents.append({
                'content': content,
                'metadata': metadata
            })
        
        logger.info(f"Prepared {len(documents)} evidence documents for indexing")
        return documents
        
    except Exception as e:
        logger.error(f"Failed to prepare evidence documents: {e}")
        raise


def build_nomenclature_index(db: Session) -> None:
    """
    Build vector index from goods nomenclature data.
    
    Args:
        db: Database session
    """
    try:
        logger.info("Building nomenclature vector index")
        
        # Prepare documents
        documents = prepare_nomenclature_documents(db)
        
        if not documents:
            logger.warning("No nomenclature documents to index")
            return
        
        # Add documents to vector store
        vector_retriever.add_documents(documents)
        
        logger.info(f"Successfully indexed {len(documents)} nomenclature documents")
        
    except Exception as e:
        logger.error(f"Failed to build nomenclature index: {e}")
        raise


def build_evidence_index(db: Session) -> None:
    """
    Build vector index from legal evidence data.
    
    Args:
        db: Database session
    """
    try:
        logger.info("Building evidence vector index")
        
        # Prepare documents
        documents = prepare_evidence_documents(db)
        
        if not documents:
            logger.warning("No evidence documents to index")
            return
        
        # Add documents to evidence collection
        evidence_retriever = vector_retriever
        evidence_retriever.collection_name = "evidence_chunks"
        evidence_retriever._ensure_collection_exists()
        evidence_retriever.add_documents(documents)
        
        logger.info(f"Successfully indexed {len(documents)} evidence documents")
        
    except Exception as e:
        logger.error(f"Failed to build evidence index: {e}")
        raise


def update_vector_index(db: Session, force_rebuild: bool = False) -> None:
    """
    Update vector index with new or changed data.
    
    Args:
        db: Database session
        force_rebuild: Force complete rebuild of index
    """
    try:
        logger.info("Updating vector index")
        
        if force_rebuild:
            logger.info("Force rebuild requested, rebuilding complete index")
            rebuild_vector_index(db)
            return
        
        # Check if index exists and has data
        try:
            collections = vector_retriever.client.get_collections()
            nomenclature_exists = any(c.name == "nomenclature_chunks" for c in collections.collections)
            
            if nomenclature_exists:
                # Get collection info to check if it has data
                collection_info = vector_retriever.client.get_collection("nomenclature_chunks")
                if collection_info.points_count > 0:
                    logger.info("Vector index exists and has data, skipping rebuild")
                    return
        except Exception as e:
            logger.warning(f"Could not check existing index: {e}")
        
        # Build index
        build_nomenclature_index(db)
        build_evidence_index(db)
        
        logger.info("Vector index update completed")
        
    except Exception as e:
        logger.error(f"Failed to update vector index: {e}")
        raise


def validate_vector_index() -> bool:
    """
    Validate vector index integrity.
    
    Returns:
        True if validation passes, False otherwise
    """
    try:
        logger.info("Validating vector index")
        
        # Check if collections exist
        collections = vector_retriever.client.get_collections()
        collection_names = [c.name for c in collections.collections]
        
        if "nomenclature_chunks" not in collection_names:
            logger.error("Nomenclature collection not found")
            return False
        
        # Check collection info
        nomenclature_info = vector_retriever.client.get_collection("nomenclature_chunks")
        logger.info(f"Nomenclature collection has {nomenclature_info.points_count} points")
        
        if nomenclature_info.points_count == 0:
            logger.warning("Nomenclature collection is empty")
            return False
        
        # Test search functionality
        test_query = "cotton hoodies"
        results = vector_retriever.search(test_query, top_k=5)
        
        if not results:
            logger.error("Vector search test failed")
            return False
        
        logger.info(f"Vector search test successful, found {len(results)} results")
        
        # Check evidence collection if it exists
        if "evidence_chunks" in collection_names:
            evidence_info = vector_retriever.client.get_collection("evidence_chunks")
            logger.info(f"Evidence collection has {evidence_info.points_count} points")
        
        logger.info("Vector index validation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Vector index validation failed: {e}")
        return False


def rebuild_vector_index(db: Session) -> None:
    """
    Complete rebuild of vector index.
    
    Args:
        db: Database session
    """
    try:
        logger.info("Starting complete vector index rebuild")
        
        # Delete existing collections
        try:
            collections = vector_retriever.client.get_collections()
            for collection in collections.collections:
                if collection.name in ["nomenclature_chunks", "evidence_chunks"]:
                    vector_retriever.client.delete_collection(collection.name)
                    logger.info(f"Deleted collection: {collection.name}")
        except Exception as e:
            logger.warning(f"Could not delete existing collections: {e}")
        
        # Rebuild collections
        build_nomenclature_index(db)
        build_evidence_index(db)
        
        # Validate rebuild
        if not validate_vector_index():
            raise Exception("Vector index validation failed after rebuild")
        
        logger.info("Vector index rebuild completed successfully")
        
    except Exception as e:
        logger.error(f"Failed to rebuild vector index: {e}")
        raise


def get_index_statistics() -> Dict[str, Any]:
    """
    Get vector index statistics.
    
    Returns:
        Dictionary with index statistics
    """
    try:
        stats = {
            'collections': {},
            'total_documents': 0
        }
        
        collections = vector_retriever.client.get_collections()
        
        for collection in collections.collections:
            collection_info = vector_retriever.client.get_collection(collection.name)
            stats['collections'][collection.name] = {
                'points_count': collection_info.points_count,
                'vectors_count': collection_info.vectors_count,
                'segments_count': collection_info.segments_count
            }
            stats['total_documents'] += collection_info.points_count
        
        return stats
        
    except Exception as e:
        logger.error(f"Failed to get index statistics: {e}")
        return {}


def main():
    """
    Main function for vector index building.
    """
    try:
        from db.session import get_db
        
        with next(get_db()) as db:
            logger.info("Starting vector index building")
            
            # Build nomenclature index
            build_nomenclature_index(db)
            
            # Build evidence index
            build_evidence_index(db)
            
            # Validate index
            if validate_vector_index():
                logger.info("Vector index building completed successfully")
                
                # Print statistics
                stats = get_index_statistics()
                logger.info(f"Index statistics: {stats}")
            else:
                logger.error("Vector index validation failed")
                return 1
        
        return 0
        
    except Exception as e:
        logger.error(f"Vector index building failed: {e}")
        return 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
