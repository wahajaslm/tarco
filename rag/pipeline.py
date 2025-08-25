# WORKFLOW: Complete HS classification pipeline: retrieve → rerank → calibrate → classify.
# Used by: Chat endpoints, HS classification, clarification generation
# Pipeline steps:
# 1. retrieve() - Get candidates using vector search
# 2. rerank() - Rerank candidates using cross-encoder
# 3. calibrate() - Predict confidence and decide on abstention
# 4. classify() - Return HS code or clarification request
# 5. get_clarifying_question() - Generate clarification options
# 6. classify_with_clarification() - Process user clarification
#
# Classification flow: Product description -> RAG pipeline -> HS code or clarification
# This is the core ML pipeline that enables intelligent HS classification
# with confidence calibration and abstention when uncertain.

from typing import List, Dict, Any, Optional, Tuple
import logging
from rag.retrieval import vector_retriever
from rag.reranker import get_reranker
from rag.calibrator import calibrator
from api.schemas.response import ClassificationMethod

logger = logging.getLogger(__name__)


class HSClassificationPipeline:
    """Complete HS classification pipeline: retrieve → rerank → calibrate → classify."""
    
    def __init__(self):
        self.retriever = vector_retriever
        self.reranker = get_reranker()
        self.calibrator = calibrator
    
    def classify(self, query: str, filter_conditions: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Classify product description to HS code.
        
        Args:
            query: Product description
            filter_conditions: Optional filter conditions for retrieval
            
        Returns:
            Classification result with confidence and metadata
        """
        try:
            logger.info(f"Starting HS classification for query: {query[:100]}...")
            
            # Step 1: Retrieve candidates
            candidates = self.retriever.search(query, filter_conditions=filter_conditions)
            
            if not candidates:
                logger.warning("No candidates retrieved")
                return self._create_abstain_result("no_candidates_retrieved")
            
            # Step 2: Rerank candidates
            reranked_candidates = self.reranker.rerank_with_metadata(query, candidates)
            
            if not reranked_candidates:
                logger.warning("No candidates after reranking")
                return self._create_abstain_result("no_candidates_after_reranking")
            
            # Step 3: Extract confidence features
            confidence_features = self.reranker.get_confidence_features(query, reranked_candidates)
            
            if not confidence_features or len(confidence_features) < 5:
                logger.warning("Insufficient confidence features")
                return self._create_abstain_result("insufficient_confidence_features")
            
            # Step 4: Calculate margin
            margin = 0.0
            if len(reranked_candidates) > 1:
                margin = reranked_candidates[0]['rerank_score'] - reranked_candidates[1]['rerank_score']
            
            # Step 5: Get confidence and abstention decision
            confidence, should_abstain = self.calibrator.get_confidence_and_abstain(
                confidence_features, margin
            )
            
            # Step 6: Make classification decision
            if should_abstain:
                logger.info(f"Abstaining from classification. Confidence: {confidence:.3f}, Margin: {margin:.3f}")
                return self._create_abstain_result("low_confidence", confidence, margin)
            
            # Step 7: Return confident classification
            top_result = reranked_candidates[0]
            hs_code = top_result.get('metadata', {}).get('goods_code')
            
            if not hs_code:
                logger.warning("No HS code found in top result")
                return self._create_abstain_result("no_hs_code_in_result")
            
            logger.info(f"Confident classification: {hs_code} (confidence: {confidence:.3f})")
            
            return {
                'hs_code': hs_code,
                'confidence': confidence,
                'margin': margin,
                'method': ClassificationMethod.RETRIEVAL_RERANK_CALIBRATE,
                'abstained': False,
                'top_candidates': reranked_candidates[:3],  # Top 3 for debugging
                'metadata': top_result.get('metadata', {})
            }
            
        except Exception as e:
            logger.error(f"HS classification failed: {e}")
            return self._create_abstain_result("classification_error")
    
    def _create_abstain_result(self, reason: str, confidence: float = 0.0, margin: float = 0.0) -> Dict[str, Any]:
        """Create abstention result."""
        return {
            'hs_code': None,
            'confidence': confidence,
            'margin': margin,
            'method': ClassificationMethod.RETRIEVAL_RERANK_CALIBRATE,
            'abstained': True,
            'abstention_reason': reason,
            'top_candidates': [],
            'metadata': {}
        }
    
    def get_clarifying_question(self, query: str, top_candidates: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Generate clarifying question when classification is uncertain.
        
        Args:
            query: Original query
            top_candidates: Top classification candidates
            
        Returns:
            Clarifying question or None
        """
        try:
            if len(top_candidates) < 2:
                return None
            
            # Extract HS codes and descriptions
            candidates_info = []
            for i, candidate in enumerate(top_candidates[:3]):  # Top 3 candidates
                metadata = candidate.get('metadata', {})
                hs_code = metadata.get('goods_code')
                description = metadata.get('description', '')
                
                if hs_code:
                    candidates_info.append({
                        'id': chr(ord('a') + i),
                        'hs_code': hs_code,
                        'description': description,
                        'score': candidate.get('rerank_score', 0.0)
                    })
            
            if len(candidates_info) < 2:
                return None
            
            # Create clarifying question
            question = {
                'id': f"cq_{hash(query) % 10000}",
                'question': f"Which of the following best describes your product?",
                'options': candidates_info
            }
            
            return question
            
        except Exception as e:
            logger.error(f"Failed to generate clarifying question: {e}")
            return None
    
    def classify_with_clarification(self, query: str, selected_option: str, top_candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Classify with user clarification.
        
        Args:
            query: Original query
            selected_option: User's selected option (a, b, c, etc.)
            top_candidates: Top candidates from previous classification
            
        Returns:
            Classification result
        """
        try:
            # Find the selected candidate
            option_index = ord(selected_option.lower()) - ord('a')
            
            if option_index < 0 or option_index >= len(top_candidates):
                logger.error(f"Invalid option selected: {selected_option}")
                return self._create_abstain_result("invalid_option_selected")
            
            selected_candidate = top_candidates[option_index]
            metadata = selected_candidate.get('metadata', {})
            hs_code = metadata.get('goods_code')
            
            if not hs_code:
                logger.error("No HS code found in selected candidate")
                return self._create_abstain_result("no_hs_code_in_selected")
            
            logger.info(f"Classification with clarification: {hs_code}")
            
            return {
                'hs_code': hs_code,
                'confidence': 1.0,  # High confidence due to user clarification
                'margin': 0.0,
                'method': ClassificationMethod.RETRIEVAL_RERANK_CALIBRATE,
                'abstained': False,
                'clarification_used': True,
                'selected_option': selected_option,
                'metadata': metadata
            }
            
        except Exception as e:
            logger.error(f"Classification with clarification failed: {e}")
            return self._create_abstain_result("clarification_error")


# Global pipeline instance
hs_pipeline = HSClassificationPipeline()
