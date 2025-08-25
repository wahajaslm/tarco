"""Tests for :func:`extract_query_parameters`.

The Ollama client is patched to return deterministic JSON payloads so tests run
offline and never invoke the real model. A helper, ``set_mock_response``,
replaces ``client.generate`` with a stub that returns the supplied dictionary
encoded as a JSON string.
"""

from __future__ import annotations

import json
import sys
from types import SimpleNamespace

import pytest


# Stub external dependencies so the service imports without real packages.
class _DummyClient:
    def __init__(self, *args, **kwargs) -> None:  # pragma: no cover - simple stub
        pass

    def generate(self, *args, **kwargs):  # pragma: no cover - simple stub
        raise NotImplementedError


class _DummyBaseSettings:
    def __init__(self, **kwargs) -> None:  # pragma: no cover - simple stub
        for key, value in kwargs.items():
            setattr(self, key, value)


sys.modules.setdefault("ollama", SimpleNamespace(Client=_DummyClient))
sys.modules.setdefault(
    "pydantic_settings", SimpleNamespace(BaseSettings=_DummyBaseSettings)
)

from services.query_extractor import extract_query_parameters  # noqa: E402


def set_mock_response(monkeypatch: pytest.MonkeyPatch, payload: dict) -> None:
    """Patch the LLM call to return ``payload`` encoded as JSON."""

    def mock_generate(*args, **kwargs):
        return {"response": json.dumps(payload)}

    monkeypatch.setattr("services.query_extractor.client.generate", mock_generate)


@pytest.mark.asyncio
async def test_multiple_origins_destinations(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure extraction works when several countries are mentioned."""

    set_mock_response(
        monkeypatch,
        {
            "origin": "Pakistan",
            "destination": "Germany",
            "product_description": "cotton shirts",
            "quantity": 5,
        },
    )

    result = await extract_query_parameters(
        "Ship 5 cotton shirts from Pakistan and India to Germany and France"
    )

    assert result["origin"] == "Pakistan"
    assert result["destination"] == "Germany"
    assert result["product_description"] == "cotton shirts"
    assert result["quantity"] == 5


@pytest.mark.asyncio
async def test_unit_based_quantity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Extract numeric quantity from unit-based phrasing."""

    set_mock_response(
        monkeypatch,
        {
            "origin": "US",
            "destination": "UK",
            "product_description": "steel rods",
            "quantity": "10 tons",
        },
    )

    result = await extract_query_parameters(
        "Export 10 tons of steel rods from the US to the UK"
    )

    assert result["quantity"] == 10
    assert result["origin"] == "US"
    assert result["destination"] == "UK"
    assert result["product_description"] == "steel rods"

