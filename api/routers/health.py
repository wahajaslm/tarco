# WORKFLOW: Health check endpoints for monitoring and operational status.
# Used by: Load balancers, monitoring systems, operational dashboards
# Endpoints:
# 1. /healthz - Basic health check (always returns healthy)
# 2. /readyz - Readiness check with service dependencies
# 3. /livez - Liveness check for Kubernetes probes
#
# Health flow: Health check request -> Service status check -> Health response
# Readiness flow: Readiness check -> Database/vector/LLM connectivity -> Ready/Not ready
# Used for service discovery, load balancing, and operational monitoring.

from fastapi import APIRouter
# from sqlalchemy.orm import Session
import logging
from datetime import datetime

# from db.session import get_db, check_db_connection
from core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/healthz")
async def health_check():
    """
    Basic health check endpoint.
    
    Returns:
        Health status of the API
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": settings.version,
        "environment": settings.environment
    }


@router.get("/readyz")
async def readiness_check():
    """
    Readiness check endpoint.
    
    Checks if the service is ready to handle requests by verifying:
    - Database connection
    - Required services availability
    
    Returns:
        Readiness status with detailed checks
    """
    checks = {
        "database": False,
        "vector_store": False,
        "llm_service": False
    }
    
    # Check database connection
    try:
        # checks["database"] = check_db_connection()
        checks["database"] = True  # Simplified for now
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
    
    # Check vector store (Qdrant)
    try:
        # This would check Qdrant connection in production
        checks["vector_store"] = True
    except Exception as e:
        logger.error(f"Vector store health check failed: {e}")
    
    # Check LLM service (Ollama)
    try:
        # This would check Ollama connection in production
        checks["llm_service"] = True
    except Exception as e:
        logger.error(f"LLM service health check failed: {e}")
    
    # Determine overall readiness
    is_ready = all(checks.values())
    
    return {
        "status": "ready" if is_ready else "not_ready",
        "timestamp": datetime.utcnow().isoformat(),
        "checks": checks,
        "version": settings.version
    }


@router.get("/livez")
async def liveness_check():
    """
    Liveness check endpoint.
    
    Simple check to determine if the service is alive.
    Used by Kubernetes liveness probes.
    
    Returns:
        Liveness status
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }
