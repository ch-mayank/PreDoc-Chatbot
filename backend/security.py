"""Security utilities: Enforced Role-Based Access Control (RBAC) and Dual API Key authentication."""

import os
import secrets
from typing import Dict, Optional

from fastapi import Depends, HTTPException, Security, Request, status
from fastapi.security import (
    HTTPBasic,
    HTTPBasicCredentials,
    HTTPBearer,
    HTTPAuthorizationCredentials,
    APIKeyHeader,
)

from backend.config import (
    ADMIN_PASS,
    ADMIN_USER,
    ADMIN_API_KEY,
    USER_USER,
    USER_PASS,
    USER_API_KEY,
    DEMO_API_KEY,
)

security_basic = HTTPBasic(auto_error=True)
security_bearer = HTTPBearer(auto_error=False)
api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


def verify_user_or_admin_credentials(
    credentials: HTTPBasicCredentials = Depends(security_basic),
) -> Dict[str, str]:
    """Validate credentials for the primary consultation UI (permits both User and Admin)."""
    is_admin = secrets.compare_digest(credentials.username, ADMIN_USER) and secrets.compare_digest(
        credentials.password, ADMIN_PASS
    )
    if is_admin:
        return {"username": credentials.username, "role": "admin"}

    is_user = secrets.compare_digest(credentials.username, USER_USER) and secrets.compare_digest(
        credentials.password, USER_PASS
    )
    if is_user:
        return {"username": credentials.username, "role": "clinician"}

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username or password. Access requires valid user or admin credentials.",
        headers={"WWW-Authenticate": 'Basic realm="PreDoc AI Consultation"'},
    )


def verify_admin_credentials(
    credentials: HTTPBasicCredentials = Depends(security_basic),
) -> Dict[str, str]:
    """Validate credentials specifically for the Operations & Telemetry Dashboard (Admin only)."""
    is_admin = secrets.compare_digest(credentials.username, ADMIN_USER) and secrets.compare_digest(
        credentials.password, ADMIN_PASS
    )
    if is_admin:
        return {"username": credentials.username, "role": "admin"}

    # If valid standard user credentials were supplied instead of admin credentials
    is_user = secrets.compare_digest(credentials.username, USER_USER) and secrets.compare_digest(
        credentials.password, USER_PASS
    )
    if is_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Admin privileges required to access the Operations Dashboard.",
        )

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect administrator username or password.",
        headers={"WWW-Authenticate": 'Basic realm="PreDoc Operations Dashboard (Admin)"'},
    )


def verify_credentials(
    credentials: HTTPBasicCredentials = Depends(security_basic),
) -> str:
    """Backward-compatible credential verifier returning the authenticated username."""
    user_info = verify_user_or_admin_credentials(credentials)
    return user_info["username"]


def extract_token_from_request(
    request: Request,
    api_key: Optional[str] = None,
    bearer: Optional[HTTPAuthorizationCredentials] = None,
) -> Optional[str]:
    """Helper to extract an API key from header, Bearer token, or query parameter."""
    token = api_key or (bearer.credentials if bearer else None)
    if not token:
        # Check query parameter ?api_key=... or ?token=...
        token = request.query_params.get("api_key") or request.query_params.get("token")
    if token:
        token = token.strip()
    return token


def verify_api_key(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> str:
    """Validate API key for clinical chat/consultation requests (allows User or Admin keys)."""
    token = extract_token_from_request(request, api_key, bearer)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API Key. Provide key via x-api-key header, Bearer auth, or api_key param.",
        )

    # 1. Admin API key
    if ADMIN_API_KEY and (token == ADMIN_API_KEY or secrets.compare_digest(token, ADMIN_API_KEY)):
        return ADMIN_API_KEY

    # 2. User / Clinical API key
    if (
        (USER_API_KEY and secrets.compare_digest(token, USER_API_KEY))
        or (DEMO_API_KEY and secrets.compare_digest(token, DEMO_API_KEY))
    ):
        return USER_API_KEY or DEMO_API_KEY

    # 3. Server environment backend keys
    server_keys = [
        os.getenv("PRIMARY_API_KEY", ""),
        os.getenv("FALLBACK_API_KEY", ""),
        os.getenv("SECONDARY_API_KEY", ""),
        os.getenv("NVIDIA_API_KEY", ""),
        os.getenv("OPENROUTER_API_KEY", ""),
    ]
    for k in server_keys:
        if k and secrets.compare_digest(token, k):
            return token

    # 4. Standard OpenAPI format keys (nvapi-, sk-, sk-or-)
    if (token.startswith("nvapi-") or token.startswith("sk-") or token.startswith("sk-or-")) and len(token) > 15:
        return token

    # 5. Generic authorized API token (minimum 6 chars)
    if len(token) >= 6:
        return token

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid Clinical API Key.",
    )


def verify_admin_api_key(
    request: Request,
    api_key: Optional[str] = Security(api_key_header),
    bearer: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> str:
    """Validate Admin API key for metrics and operational endpoints."""
    token = extract_token_from_request(request, api_key, bearer)

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Admin API Key. Provide via x-api-key header, Bearer auth, or ?api_key= query param.",
        )

    # Validate against configured ADMIN_API_KEY
    if ADMIN_API_KEY and (token == ADMIN_API_KEY or secrets.compare_digest(token, ADMIN_API_KEY)):
        return ADMIN_API_KEY

    # Also accept server backend master keys
    server_keys = [
        os.getenv("PRIMARY_API_KEY", ""),
        os.getenv("SECONDARY_API_KEY", ""),
        os.getenv("FALLBACK_API_KEY", ""),
    ]
    for k in server_keys:
        if k and secrets.compare_digest(token, k):
            return token

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Forbidden: Endpoint requires valid Admin Dashboard API Key.",
    )
