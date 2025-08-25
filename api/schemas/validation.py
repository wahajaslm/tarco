# WORKFLOW: JSON Schema validation module (hard gate for all responses).
# Used by: API endpoints, deterministic builder, testing
# Functions:
# 1. validate_trade_response() - Validate Pydantic model against JSON schema
# 2. validate_response_dict() - Validate dictionary against JSON schema
# 3. get_validation_errors() - Get detailed validation errors without raising
#
# Validation flow: Response generation -> Schema validation -> Pass/Fail
# This is the final gate ensuring all responses meet the strict schema requirements.
# No response can be returned without passing this validation.

import json
import jsonschema
from pathlib import Path
from typing import Dict, Any, Optional
from api.schemas.response import TradeComplianceResponse
import logging

logger = logging.getLogger(__name__)


class SchemaValidator:
    """JSON Schema validator for trade compliance responses."""
    
    def __init__(self):
        self.schema_path = Path(__file__).parent.parent.parent / "schema" / "trade_response.schema.json"
        self.schema = self._load_schema()
    
    def _load_schema(self) -> Dict[str, Any]:
        """Load the JSON schema from file."""
        try:
            with open(self.schema_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON schema: {e}")
            raise
    
    def validate_response(self, response_data: Dict[str, Any]) -> bool:
        """
        Validate response against JSON schema.
        
        Args:
            response_data: Response data to validate
            
        Returns:
            True if valid, raises ValidationError if invalid
        """
        try:
            jsonschema.validate(instance=response_data, schema=self.schema)
            logger.info("Response validated successfully against JSON schema")
            return True
        except jsonschema.ValidationError as e:
            logger.error(f"Schema validation failed: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error during schema validation: {e}")
            raise
    
    def validate_pydantic_model(self, model: TradeComplianceResponse) -> bool:
        """
        Validate Pydantic model by converting to dict and validating against JSON schema.
        
        Args:
            model: Pydantic model to validate
            
        Returns:
            True if valid, raises ValidationError if invalid
        """
        try:
            # Convert Pydantic model to dict
            response_dict = model.model_dump(mode='json')
            
            # Validate against JSON schema
            return self.validate_response(response_dict)
        except Exception as e:
            logger.error(f"Pydantic model validation failed: {e}")
            raise
    
    def get_validation_errors(self, response_data: Dict[str, Any]) -> Optional[str]:
        """
        Get detailed validation errors without raising exception.
        
        Args:
            response_data: Response data to validate
            
        Returns:
            Error message if invalid, None if valid
        """
        try:
            jsonschema.validate(instance=response_data, schema=self.schema)
            return None
        except jsonschema.ValidationError as e:
            return f"Schema validation error: {e.message} at path: {'/'.join(str(p) for p in e.path)}"
        except Exception as e:
            return f"Unexpected validation error: {e}"


# Global validator instance
schema_validator = SchemaValidator()


def validate_trade_response(response: TradeComplianceResponse) -> bool:
    """
    Convenience function to validate trade compliance response.
    
    Args:
        response: TradeComplianceResponse model
        
    Returns:
        True if valid, raises ValidationError if invalid
    """
    return schema_validator.validate_pydantic_model(response)


def validate_response_dict(response_dict: Dict[str, Any]) -> bool:
    """
    Convenience function to validate response dictionary.
    
    Args:
        response_dict: Response dictionary
        
    Returns:
        True if valid, raises ValidationError if invalid
    """
    return schema_validator.validate_response(response_dict)
