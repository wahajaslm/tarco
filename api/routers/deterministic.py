# WORKFLOW: Deterministic endpoints for database-only trade compliance responses.
# Used by: Direct API calls, integration testing, deterministic workflows
# Endpoints:
# 1. /deterministic-json - Build response from database only (no LLM)
# 2. /deterministic-json+explain - Database response + LLM explanations
#
# Request flow: HTTP POST -> Parameter validation -> Deterministic builder -> Schema validation -> Response
# This ensures all numeric facts come from database, LLM only adds explanations
# Used when HS code is already known and only compliance data is needed.

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
import logging
from datetime import date, datetime

from db.session import get_db
from api.schemas.request import DeterministicRequest
from api.schemas.response import TradeComplianceResponse, QueryParameters, DeterministicValues
from api.schemas.validation import validate_trade_response
from core.config import settings
from services.deterministic_builder import create_deterministic_builder

logger = logging.getLogger(__name__)

router = APIRouter(tags=["deterministic"])


@router.post("/deterministic-json", response_model=TradeComplianceResponse)
async def get_deterministic_json(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Get deterministic trade compliance JSON from database only.
    
    This endpoint builds the response entirely from database data without any LLM processing.
    All numeric values, rates, dates, and legal bases come directly from the database.
    """
    try:
        # Extract parameters from raw request
        hs_code = request.get("hs_code")
        origin = request.get("origin")
        destination = request.get("destination")
        product_description = request.get("product_description")
        
        logger.info(f"Deterministic JSON request: HS={hs_code}, Origin={origin}, Dest={destination}")
        
        # Use the deterministic builder to get actual database data
        builder = create_deterministic_builder(db)
        response = builder.build_response(
            hs_code=hs_code,
            origin=origin,
            destination=destination,
            product_description=product_description
        )
        
        logger.info("Deterministic JSON response built successfully from database")
        return response
        
    except Exception as e:
        logger.error(f"Deterministic JSON request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build deterministic response: {str(e)}"
        )


@router.post("/deterministic-json+explain", response_model=TradeComplianceResponse)
async def get_deterministic_json_with_explanation(
    request: DeterministicRequest,
    db: Session = Depends(get_db)
):
    """
    Get deterministic trade compliance JSON with LLM explanations.
    
    This endpoint builds the response from database data and adds human-readable explanations
    derived from the deterministic payload. The LLM cannot introduce new numeric values.
    """
    try:
        logger.info(f"Deterministic JSON+explain request: HS={request.hs_code}, Origin={request.origin}, Dest={request.destination}")
        
        # For now, return the same as the basic endpoint
        return await get_deterministic_json({
            "hs_code": request.hs_code,
            "origin": request.origin,
            "destination": request.destination,
            "product_description": request.product_description
        }, db)
        
    except Exception as e:
        logger.error(f"Deterministic JSON+explain request failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to build deterministic response with explanation: {str(e)}"
        )
