# WORKFLOW: Pydantic request schemas for API input validation.
# Used by: FastAPI endpoints for request validation and documentation
# Schemas include:
# 1. DeterministicRequest - For /deterministic-json endpoints
# 2. ChatResolveRequest - For /chat/resolve endpoint
# 3. ChatAnswerRequest - For /chat/answer endpoint
# 4. NeedsClarificationResponse - For clarification responses
# 5. ETLIngestRequest - For data ingestion endpoints
#
# Validation flow: HTTP request -> Pydantic validation -> Endpoint processing
# Ensures all inputs are properly formatted and validated before processing.

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Literal


class DeterministicRequest(BaseModel):
    """Request schema for deterministic JSON endpoints."""
    hs_code: str = Field(..., pattern=r"^[0-9]{4,10}$", description="HS code (4-10 digits)")
    origin: str = Field(..., min_length=2, max_length=3, description="Origin country code")
    destination: str = Field(..., min_length=2, max_length=3, description="Destination country code")
    product_description: Optional[str] = Field(None, description="Product description")
    incoterm: Optional[str] = Field(None, description="Incoterm")
    currency: Optional[str] = Field(None, min_length=3, max_length=3, description="Currency code")


class ChatResolveRequest(BaseModel):
    """Request schema for chat resolve endpoint."""
    message: str = Field(..., min_length=1, max_length=1000, description="User message")


class ChatAnswerRequest(BaseModel):
    """Request schema for chat answer endpoint."""
    question_id: str = Field(..., description="Question ID from clarification")
    selected_option: str = Field(..., description="Selected option (a, b, c, etc.)")


class ClarifyingQuestion(BaseModel):
    """Schema for clarifying questions."""
    id: str = Field(..., description="Question ID")
    question: str = Field(..., description="Question text")
    options: List[dict] = Field(..., description="Available options")


class NeedsClarificationResponse(BaseModel):
    """Response schema when clarification is needed."""
    status: Literal["needs_clarification"] = "needs_clarification"
    query_parameters: dict = Field(..., description="Extracted query parameters")
    reason: str = Field(..., description="Reason for clarification")
    clarifying_question: Optional[ClarifyingQuestion] = Field(None, description="Clarifying question")
    flags: List[str] = Field(default_factory=list, description="System flags")


class ETLIngestRequest(BaseModel):
    """Request schema for ETL ingestion."""
    zip_file_path: str = Field(..., description="Path to ZIP file containing XLSX files")
    source_name: str = Field(..., description="Source name for provenance tracking")
    
    @validator('zip_file_path')
    def validate_zip_path(cls, v):
        if not v.endswith('.zip'):
            raise ValueError('File must be a ZIP file')
        return v
