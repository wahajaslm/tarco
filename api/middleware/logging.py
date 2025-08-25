# WORKFLOW: Structured logging middleware for request/response monitoring.
# Used by: All API endpoints, operational monitoring, debugging
# Functions:
# 1. _log_request() - Log incoming request details (method, path, headers, body)
# 2. _log_response() - Log response details (status, timing, content type)
# 3. _log_error() - Log error details with context
#
# Logging flow: Request -> Log request -> Process -> Log response/error
# Provides comprehensive request tracing and performance monitoring
# Enables debugging, performance analysis, and operational insights.

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import time
import structlog
from typing import Callable
import json

logger = structlog.get_logger()


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured request/response logging."""
    
    def __init__(self, app: ASGIApp):
        super().__init__(app)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and log details."""
        start_time = time.time()
        
        # Log request
        await self._log_request(request)
        
        # Process request
        try:
            response = await call_next(request)
            process_time = time.time() - start_time
            
            # Log response
            await self._log_response(request, response, process_time)
            
            return response
            
        except Exception as e:
            process_time = time.time() - start_time
            
            # Log error
            await self._log_error(request, e, process_time)
            raise
    
    async def _log_request(self, request: Request):
        """Log incoming request details."""
        try:
            # Get request body if available
            body = None
            if request.method in ["POST", "PUT", "PATCH"]:
                try:
                    body = await request.body()
                    if body:
                        # Try to parse as JSON
                        try:
                            body = json.loads(body.decode())
                        except:
                            body = body.decode()[:1000]  # Truncate if not JSON
                except:
                    pass
            
            logger.info(
                "Incoming request",
                method=request.method,
                url=str(request.url),
                path=request.url.path,
                query_params=dict(request.query_params),
                headers=dict(request.headers),
                body=body,
                client_ip=request.client.host if request.client else None,
                user_agent=request.headers.get("user-agent")
            )
            
        except Exception as e:
            logger.error(f"Failed to log request: {e}")
    
    async def _log_response(self, request: Request, response: Response, process_time: float):
        """Log response details."""
        try:
            logger.info(
                "Response sent",
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                process_time_ms=round(process_time * 1000, 2),
                content_length=response.headers.get("content-length"),
                content_type=response.headers.get("content-type")
            )
            
        except Exception as e:
            logger.error(f"Failed to log response: {e}")
    
    async def _log_error(self, request: Request, error: Exception, process_time: float):
        """Log error details."""
        try:
            logger.error(
                "Request failed",
                method=request.method,
                path=request.url.path,
                error_type=type(error).__name__,
                error_message=str(error),
                process_time_ms=round(process_time * 1000, 2)
            )
            
        except Exception as e:
            logger.error(f"Failed to log error: {e}")
