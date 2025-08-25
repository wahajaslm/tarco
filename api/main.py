#!/usr/bin/env python3
"""
Trade Compliance API - Working version with health router.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import time

# Add core configuration
from core.config import settings

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level))
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.project_name,
    version=settings.version,
    description="Production-grade Trade Compliance API with deterministic JSON responses"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=settings.allowed_methods,
    allow_headers=settings.allowed_headers,
)

# Include health router
from api.routers import health
app.include_router(health.router, prefix=settings.api_v1_prefix)
logger.info("Health router included")

# Include deterministic router
try:
    from api.routers import deterministic
    app.include_router(deterministic.router, prefix=settings.api_v1_prefix)
    logger.info("Deterministic router included")
except Exception as e:
    logger.warning(f"Failed to include deterministic router: {e}")

@app.get("/health")
async def health():
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/test")
async def test(request: dict):
    logger.info("Test endpoint called")
    return {"status": "success", "data": request}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
