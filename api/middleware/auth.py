# WORKFLOW: Authentication middleware for JWT and API key validation.
# Used by: All protected API endpoints, security enforcement
# Functions:
# 1. _extract_token() - Extract JWT or API key from request headers
# 2. _validate_token() - Validate JWT token and extract payload
# 3. _is_public_endpoint() - Check if endpoint requires authentication
#
# Auth flow: Request -> Extract token -> Validate token -> Set user context -> Continue
# Security flow: Protected endpoint -> Auth check -> Allow/Deny
# Ensures all sensitive endpoints are properly authenticated
# Public endpoints (health, docs) bypass authentication.

from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import jwt
import logging
from typing import Optional
from core.config import settings

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for JWT and API key validation."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next):
        """Process request with authentication."""
        # Skip auth for health checks and public endpoints
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)
        
        # Extract and validate token
        token = await self._extract_token(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Validate token
        try:
            payload = self._validate_token(token)
            request.state.user = payload
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return await call_next(request)
    
    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (no auth required)."""
        public_paths = [
            "/healthz",
            "/readyz", 
            "/livez",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/",
            "/api/v1/deterministic-json",
            "/api/v1/deterministic-json+explain",
            "/api/v1/chat/resolve",
            "/api/v1/chat/answer",
            "/test-",
            "/test-deterministic",
            "/test-deterministic-dep",
            "/test-request-validation",
            "/test-raw-request",
            "/test-simple-",
            "/test-dep-raw",
            "/test-minimal"
        ]
        
        return any(path.startswith(public_path) for public_path in public_paths)
    
    async def _extract_token(self, request: Request) -> Optional[str]:
        """Extract token from request headers."""
        try:
            # Try Bearer token first
            credentials: HTTPAuthorizationCredentials = await security(request)
            if credentials:
                return credentials.credentials
            
            # Try API key header
            api_key = request.headers.get("X-API-Key")
            if api_key:
                return api_key
            
            return None
            
        except Exception as e:
            logger.error(f"Token extraction failed: {e}")
            return None
    
    def _validate_token(self, token: str) -> dict:
        """Validate JWT token."""
        try:
            payload = jwt.decode(
                token,
                settings.secret_key,
                algorithms=[settings.algorithm]
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.JWTError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid token: {str(e)}"
            )
