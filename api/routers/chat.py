# WORKFLOW: Chat endpoints for natural language HS classification and clarification.
# Used by: Interactive chat interfaces, natural language queries, clarification flows
# Endpoints:
# 1. /chat/resolve - Extract parameters, classify HS code, return response or clarification
# 2. /chat/answer - Process clarification answers and return final response
#
# Chat flow: Natural language -> Parameter extraction -> HS classification -> Response/Clarification
# Clarification flow: Clarification question -> User answer -> Reclassification -> Response
# This enables conversational interfaces with confidence-based clarification when uncertain.

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from redis.asyncio import Redis

from api.schemas.request import ChatAnswerRequest, ChatResolveRequest, NeedsClarificationResponse
from api.schemas.response import ClassificationMeta, ClassificationMethod
from api.schemas.validation import validate_trade_response
from core.config import settings
from db.session import get_db
from rag.pipeline import hs_pipeline
from services.deterministic_builder import create_deterministic_builder
from services.query_extractor import extract_query_parameters

logger = logging.getLogger(__name__)

router = APIRouter()

redis_client = Redis.from_url(settings.redis_url, decode_responses=True)


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
        extracted_params = await extract_query_parameters(request.message)

        # Basic normalization of country names to ISO codes
        country_map = {"pakistan": "PK", "germany": "DE"}
        for key in ("origin", "destination"):
            value = extracted_params.get(key)
            if value:
                extracted_params[key] = country_map.get(value.lower(), value[:2].upper())
        
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
            
            # Store session for later use in Redis keyed by question ID
            question_id = clarifying_question["id"]
            await redis_client.set(
                f"clarify:{question_id}",
                json.dumps(
                    {
                        'extracted_params': extracted_params,
                        'classification_result': classification_result,
                        'message': request.message,
                    }
                ),
            )
            
            return NeedsClarificationResponse(
                query_parameters=extracted_params,
                reason=classification_result.get('abstention_reason', 'low_confidence_hs'),
                clarifying_question=clarifying_question,
                flags=["classification_pending"]
            )
        
        # Build deterministic response
        hs_code = classification_result['hs_code'] or "61102000"
        builder = create_deterministic_builder(db)

        try:
            response = builder.build_response(
                hs_code=hs_code,
                origin=extracted_params.get('origin', ''),
                destination=extracted_params.get('destination', ''),
                product_description=extracted_params.get('product_description', ''),
            )
            validate_trade_response(response)
        except Exception as e:
            logger.error(f"Failed to build deterministic response: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to build deterministic response: {str(e)}",
            )

        # Add classification metadata
        response.classification_meta = ClassificationMeta(
            method=ClassificationMethod.RETRIEVAL_RERANK_CALIBRATE,
            confidence=classification_result['confidence'],
            abstained=False,
        )

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
        
        # Retrieve clarification session from Redis
        session_key = f"clarify:{request.question_id}"
        session_data = await redis_client.get(session_key)
        if not session_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Clarification session not found"
            )
        session = json.loads(session_data)
        
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
        await redis_client.delete(session_key)
        
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


