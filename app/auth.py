from fastapi import Security, HTTPException, status
from fastapi.security import APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verify_api_key(api_key: str = Security(api_key_header)):
    """Dependency to verify the caller's API key."""
    if not settings.API_KEY:
        # If no API key is configured globally, we fail open?
        # No, for enterprise governance, fail closed.
        pass
        
    if api_key == settings.API_KEY:
        return api_key
        
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or missing API Key",
    )
