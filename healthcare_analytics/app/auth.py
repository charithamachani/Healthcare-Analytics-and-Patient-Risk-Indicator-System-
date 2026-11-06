"""Very small API-key access control with two roles (FastAPI dependency).

analyst = read-only,  admin = read + write.
Fails closed: if no keys are configured, every protected endpoint returns 401.
The key box ("Authorize" button) also appears in the interactive docs at /docs.
"""
import hmac

from fastapi import HTTPException, Request, Security
from fastapi.security import APIKeyHeader

ROLE_RANK = {"analyst": 1, "admin": 2}
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def _role_for_key(keys: dict, provided: str):
    role = None
    for key, key_role in keys.items():
        # constant-time comparison avoids leaking key contents through timing
        if hmac.compare_digest(provided.encode(), key.encode()):
            role = key_role
    return role


def require_role(minimum: str):
    def dependency(request: Request, provided: str = Security(api_key_header)):
        role = _role_for_key(request.app.state.api_keys, provided) if provided else None
        if role is None:
            raise HTTPException(401, "Missing or invalid API key")
        if ROLE_RANK[role] < ROLE_RANK[minimum]:
            raise HTTPException(403, "Insufficient permissions for this action")
        return role
    return dependency
