import json
import pytest

from services.query_extractor import extract_query_parameters


@pytest.mark.asyncio
async def test_multi_country_extraction(monkeypatch):
    """Ensure extraction works when multiple countries are mentioned."""

    def mock_generate(*args, **kwargs):
        return {
            "response": json.dumps({
                "origin": "Pakistan",
                "destination": "Germany",
                "product_description": "cotton shirts",
                "quantity": 5,
            })
        }

    monkeypatch.setattr("services.query_extractor.client.generate", mock_generate)

    result = await extract_query_parameters(
        "Ship 5 cotton shirts from Pakistan to Germany via France"
    )

    assert result["origin"] == "Pakistan"
    assert result["destination"] == "Germany"
    assert result["product_description"] == "cotton shirts"
    assert result["quantity"] == 5


@pytest.mark.asyncio
async def test_unit_based_quantity(monkeypatch):
    """Extract numeric quantity from unit-based phrasing."""

    def mock_generate(*args, **kwargs):
        return {
            "response": json.dumps({
                "origin": "US",
                "destination": "UK",
                "product_description": "steel rods",
                "quantity": "10 tons",
            })
        }

    monkeypatch.setattr("services.query_extractor.client.generate", mock_generate)

    result = await extract_query_parameters(
        "Export 10 tons of steel rods from the US to the UK"
    )

    assert result["quantity"] == 10
    assert result["origin"] == "US"
    assert result["destination"] == "UK"
    assert result["product_description"] == "steel rods"
