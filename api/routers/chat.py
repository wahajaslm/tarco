# WORKFLOW: Chat endpoints for natural language HS classification and clarification.
# Used by: Interactive chat interfaces, natural language queries, clarification flows
# Endpoints:
# 1. /chat/resolve - Extract parameters, classify HS code, return response or clarification
# 2. /chat/answer - Process clarification answers and return final response
#
# Chat flow: Natural language -> Parameter extraction -> HS classification -> Response/Clarification
# Clarification flow: Clarification question -> User answer -> Reclassification -> Response
# This enables conversational interfaces with confidence-based clarification when uncertain.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional, Dict, Any
import logging

from db.session import get_db
from api.schemas.request import ChatResolveRequest, ChatAnswerRequest, NeedsClarificationResponse
from api.schemas.response import TradeComplianceResponse
from api.schemas.validation import validate_trade_response
from rag.pipeline import hs_pipeline
from services.deterministic_builder import create_deterministic_builder
from services.explainer import create_explainer

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory storage for clarification sessions (in production, use Redis)
clarification_sessions = {}


@router.post("/resolve")
async def resolve_chat_message(
    request: ChatResolveRequest,
    db: Session = Depends(get_db)
):
    """
    Resolve chat message with HS classification and deterministic response.
    
    This endpoint extracts query parameters, classifies the product to HS code,
    and returns either a deterministic response or clarification request.
    """
    try:
        logger.info(f"Chat resolve request: {request.message[:100]}...")
        
        # Extract query parameters using LLM
        extracted_params = await _extract_query_parameters(request.message)
        
        if not extracted_params.get('product_description'):
            return NeedsClarificationResponse(
                query_parameters=extracted_params,
                reason="no_product_description",
                clarifying_question={
                    "id": "cq_product",
                    "question": "Please provide a description of the product you want to import/export.",
                    "options": []
                },
                flags=["missing_product_description"]
            )
        
        # Classify product to HS code
        classification_result = hs_pipeline.classify(extracted_params['product_description'])
        
        if classification_result['abstained']:
            # Generate clarifying question
            clarifying_question = hs_pipeline.get_clarifying_question(
                extracted_params['product_description'],
                classification_result.get('top_candidates', [])
            )
            
            # Store session for later use
            session_id = f"session_{hash(request.message) % 10000}"
            clarification_sessions[session_id] = {
                'extracted_params': extracted_params,
                'classification_result': classification_result,
                'message': request.message
            }
            
            return NeedsClarificationResponse(
                query_parameters=extracted_params,
                reason=classification_result.get('abstention_reason', 'low_confidence_hs'),
                clarifying_question=clarifying_question,
                flags=["classification_pending"]
            )
        
        # Build deterministic response
        hs_code = classification_result['hs_code']
        builder = create_deterministic_builder(db)
        
        response = builder.build_response(
            hs_code=hs_code,
            origin=extracted_params.get('origin', ''),
            destination=extracted_params.get('destination', ''),
            product_description=extracted_params.get('product_description', '')
        )
        
        # Add classification metadata
        response.classification_meta = {
            'method': classification_result['method'],
            'confidence': classification_result['confidence'],
            'abstained': False
        }
        
        # Validate response
        validate_trade_response(response)
        
        logger.info(f"Chat resolve successful: HS={hs_code}")
        return response
        
    except Exception as e:
        logger.error(f"Chat resolve failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resolve chat message: {str(e)}"
        )


@router.post("/answer")
async def answer_clarification(
    request: ChatAnswerRequest,
    db: Session = Depends(get_db)
):
    """
    Answer clarification question and get deterministic response.
    
    This endpoint processes the user's answer to a clarification question
    and returns the final deterministic response.
    """
    try:
        logger.info(f"Chat answer request: question_id={request.question_id}, option={request.selected_option}")
        
        # Find the clarification session
        session = None
        session_id = None
        
        for sid, sess in clarification_sessions.items():
            if sess.get('clarifying_question', {}).get('id') == request.question_id:
                session = sess
                session_id = sid
                break
        
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clarification session not found"
            )
        
        # Classify with clarification
        classification_result = hs_pipeline.classify_with_clarification(
            session['extracted_params']['product_description'],
            request.selected_option,
            session['classification_result'].get('top_candidates', [])
        )
        
        if classification_result['abstained']:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid clarification answer"
            )
        
        # Build deterministic response
        hs_code = classification_result['hs_code']
        builder = create_deterministic_builder(db)
        
        response = builder.build_response(
            hs_code=hs_code,
            origin=session['extracted_params'].get('origin', ''),
            destination=session['extracted_params'].get('destination', ''),
            product_description=session['extracted_params'].get('product_description', '')
        )
        
        # Add classification metadata
        response.classification_meta = {
            'method': classification_result['method'],
            'confidence': classification_result['confidence'],
            'abstained': False
        }
        
        # Clean up session
        if session_id:
            del clarification_sessions[session_id]
        
        # Validate response
        validate_trade_response(response)
        
        logger.info(f"Chat answer successful: HS={hs_code}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat answer failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process clarification answer: {str(e)}"
        )


async def _extract_query_parameters(message: str) -> Dict[str, Any]:
    """
    Extract query parameters from user message using LLM.
    
    Args:
        message: User message
        
    Returns:
        Dictionary with extracted parameters
    """
    try:
        # Simple extraction logic (in production, use LLM)
        # This is a placeholder - implement proper LLM extraction
        extracted = {
            'origin': '',
            'destination': '',
            'product_description': '',
            'quantity': None
        }
        
        # Basic keyword extraction
        message_lower = message.lower()
        
        # Extract origin/destination from common patterns
        if 'from' in message_lower and 'to' in message_lower:
            parts = message_lower.split('from')
            if len(parts) > 1:
                to_parts = parts[1].split('to')
                if len(to_parts) > 1:
                    extracted['origin'] = to_parts[0].strip()
                    extracted['destination'] = to_parts[1].strip()
        
        # Extract product description (everything between import/export and from/to)
        if 'import' in message_lower:
            import_part = message_lower.split('import')[1]
            if 'from' in import_part:
                product_part = import_part.split('from')[0]
                extracted['product_description'] = product_part.strip()
        
        # Extract quantity
        import re
        quantity_match = re.search(r'(\d+)\s+', message)
        if quantity_match:
            extracted['quantity'] = int(quantity_match.group(1))
        
        return extracted
        
    except Exception as e:
        logger.error(f"Query parameter extraction failed: {e}")
        return {
            'origin': '',
            'destination': '',
            'product_description': '',
            'quantity': None
        }
