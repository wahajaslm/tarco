#!/usr/bin/env python3
"""
Trade Compliance API - Working version with health router.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

# Add core configuration and routers
from core.config import settings
from api.routers import health

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

# Expose health checks both at root and versioned paths
app.include_router(health.router, prefix=settings.api_v1_prefix)
logger.info("Health router included with API prefix")

@app.get("/healthz")
async def root_health_check():
    """Root-level health endpoint for external monitors."""
    return await health.health_check()

# Include deterministic and chat routers
try:
    from api.routers import deterministic, chat
    app.include_router(deterministic.router, prefix=settings.api_v1_prefix)
    app.include_router(chat.router, prefix=f"{settings.api_v1_prefix}/chat")
    logger.info("Deterministic and chat routers included")
except Exception as e:
    logger.warning(f"Failed to include routers: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
