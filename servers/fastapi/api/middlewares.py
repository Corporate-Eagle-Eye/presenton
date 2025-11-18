from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response, JSONResponse
import httpx
import os
import hmac
import logging

from utils.get_env import get_can_change_keys_env
from utils.user_config import update_env_with_user_config

logger = logging.getLogger(__name__)


class UserConfigEnvUpdateMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if get_can_change_keys_env() != "false":
            update_env_with_user_config()
        return await call_next(request)


class ComposeAIAuthMiddleware(BaseHTTPMiddleware):
    """
    Validates user authentication via API key hash comparison.
    ComposeAI passes user_id, tenant_id, and hashed API key.
    Presenton validates with ComposeAI and compares hashes.
    """
    
    def __init__(self, app):
        super().__init__(app)
        self.composeai_url = os.getenv("COMPOSEAI_BACKEND_URL")
        self.enabled = os.getenv("ENABLE_COMPOSEAI_AUTH", "true").lower() == "true"
        self.show_docs = os.getenv("SHOW_API_DOCS", "false").lower() == "true"
    
    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip if authentication is disabled
        if not self.enabled:
            return await call_next(request)
        
        # Check if endpoint requires authentication
        if self._requires_auth(request.url.path):
            error_response = await self._validate_user(request)
            if error_response:
                return error_response
        
        return await call_next(request)
    
    def _requires_auth(self, path: str) -> bool:
        """Check if endpoint needs authentication."""
        # Public system endpoints
        if path.startswith(("/health", "/favicon.ico")):
            return False
        
        # Documentation endpoints - controlled by env variable
        if path.startswith(("/docs", "/openapi.json", "/redoc")):
            return not self.show_docs
        
        # All Next.js API routes (internal communication between FastAPI and Next.js)
        if path.startswith("/api/"):
            return False
        
        # FastAPI direct endpoints require authentication
        if path.startswith("/api/v1/"):
            return True
        
        # Static files and app data
        if path.startswith(("/static/", "/app_data/")):
            return False
        
        return False
    
    async def _validate_user(self, request: Request) -> Response | None:
        """
        Validate user via API key hash comparison.
        Supports both headers and query parameters for flexible authentication.
        Returns error response if validation fails, None if successful.
        """
        try:
            # Try headers first (preferred method)
            user_id = request.headers.get("x-user-id")
            tenant_id = request.headers.get("x-tenant-id")
            provided_hash = request.headers.get("x-tenant-api-key-hash")
            
            # Fallback to query parameters (for token-based authentication)
            if not user_id or not tenant_id or not provided_hash:
                user_id = request.query_params.get("user_id") or request.query_params.get("X-User-ID")
                tenant_id = request.query_params.get("tenant_id") or request.query_params.get("X-Tenant-ID") 
                provided_hash = (
                    request.query_params.get("hash") or 
                    request.query_params.get("X-Tenant-API-Key-Hash")
                )
            
            if not user_id or not tenant_id or not provided_hash:
                logger.warning(f"Missing auth credentials for {request.url.path}")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required. Provide X-User-ID, X-Tenant-ID, and X-Tenant-API-Key-Hash headers or query params."}
                )
            
            # Validate with ComposeAI backend
            tenant_hash = await self._get_tenant_hash(user_id, tenant_id)
            
            if not tenant_hash:
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid credentials"}
                )
            
            # Compare hashes (constant-time comparison to prevent timing attacks)
            if not hmac.compare_digest(provided_hash, tenant_hash):
                logger.warning(f"Hash mismatch for user {user_id}, tenant {tenant_id}")
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Invalid API key hash"}
                )
            
            # Store user context in request state
            request.state.user_id = user_id
            request.state.tenant_id = tenant_id
            return None
            
        except Exception as e:
            logger.error(f"Auth validation error: {str(e)}")
            return JSONResponse(
                status_code=500,
                content={"detail": "Authentication service error"}
            )
    
    async def _get_tenant_hash(self, user_id: str, tenant_id: str) -> str | None:
        """
        Validate user exists and belongs to tenant.
        Returns tenant's hashed API key from ComposeAI backend.
        Returns None on error.
        """
        if not self.composeai_url:
            logger.error("COMPOSEAI_BACKEND_URL not configured")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{self.composeai_url}/api/v1/auth/verify",
                    json={
                        "user_id": user_id,
                        "tenant_id": tenant_id
                    }
                )
                
                if response.status_code == 401:
                    logger.warning(f"User {user_id} not found or doesn't belong to tenant {tenant_id}")
                    return None
                
                if response.status_code == 403:
                    logger.warning(f"User {user_id} or tenant {tenant_id} is inactive")
                    return None
                
                if response.status_code != 200:
                    logger.error(f"ComposeAI auth service returned {response.status_code}")
                    return None
                
                data = response.json()
                return data.get("tenant_api_key_hash")
                
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to ComposeAI auth service: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in _get_tenant_hash: {str(e)}")
            return None


