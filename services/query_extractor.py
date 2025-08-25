# WORKFLOW: LLM service for extracting query parameters from natural language messages.
# Used by: Chat endpoints for parameter extraction.
# Functions:
# 1. extract_query_parameters() - Parse user message to origin, destination, product description, quantity.
#
# Extraction flow: User message -> LLM prompt -> JSON response -> Validation -> Parameter dict

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any, Dict

import ollama

from core.config import settings

logger = logging.getLogger(__name__)

client = ollama.Client(host=settings.ollama_url)

PROMPT_TEMPLATE = """
Extract the origin country, destination country, product description, and quantity from the following message.
Return ONLY a JSON object with keys: origin, destination, product_description, quantity (number or null).

Message: {message}
JSON:
"""


async def extract_query_parameters(message: str) -> Dict[str, Any]:
    """Extract query parameters from a user message using LLM."""
    prompt = PROMPT_TEMPLATE.format(message=message)

    def _call_llm() -> Dict[str, Any]:
        return client.generate(model=settings.llm_model, prompt=prompt)

    try:
        response = await asyncio.to_thread(_call_llm)
        data = json.loads(response.get("response", "{}"))

        origin = data.get("origin", "")
        destination = data.get("destination", "")
        product_description = data.get("product_description", "")
        quantity_raw = data.get("quantity")

        quantity = None
        if isinstance(quantity_raw, str):
            match = re.search(r"\d+", quantity_raw)
            if match:
                quantity = int(match.group())
        elif isinstance(quantity_raw, (int, float)):
            quantity = int(quantity_raw)

        if not isinstance(origin, str) or not isinstance(destination, str) or not isinstance(product_description, str):
            raise ValueError("Invalid field types")

        return {
            "origin": origin,
            "destination": destination,
            "product_description": product_description,
            "quantity": quantity,
        }
    except Exception as e:
        logger.error(f"Failed to extract query parameters: {e}")
        return {"origin": "", "destination": "", "product_description": "", "quantity": None}
