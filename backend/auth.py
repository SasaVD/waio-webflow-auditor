"""
Authentication core — password hashing, JWT tokens, FastAPI dependencies.
"""
import os
import uuid
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

import bcrypt
from jose import jwt, JWTError, ExpiredSignatureError
from fastapi import Request, HTTPException, Depends

logger = logging.getLogger(__name__)

JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_DAYS = 7
COOKIE_NAME = "waio_token"


# --------------- Password hashing ---------------

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt(rounds=12)).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


# --------------- JWT tokens ---------------

def create_access_token(user_id: str, email: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "email": email,
        "role": role,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRY_DAYS),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Decode and validate a JWT. Raises on invalid/expired."""
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


# --------------- FastAPI dependencies ---------------

def _extract_token(request: Request) -> Optional[str]:
    """Extract JWT from cookie or Authorization header."""
    token = request.cookies.get(COOKIE_NAME)
    if token:
        return token
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:]
    return None


async def get_current_user(request: Request) -> Dict[str, Any]:
    """FastAPI dependency — returns the authenticated user dict or raises 401."""
    token = _extract_token(request)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(token)
    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Fetch user from DB to ensure they still exist and are active
    from db_router import get_user_by_id
    user = await get_user_by_id(payload["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account deactivated")
    return user


async def get_current_user_optional(request: Request) -> Optional[Dict[str, Any]]:
    """Like get_current_user but returns None instead of raising 401."""
    token = _extract_token(request)
    if not token:
        return None
    try:
        payload = decode_token(token)
    except (ExpiredSignatureError, JWTError):
        return None
    from db_router import get_user_by_id
    user = await get_user_by_id(payload["sub"])
    if not user or not user.get("is_active", True):
        return None
    return user


async def require_admin(user: Dict[str, Any] = Depends(get_current_user)) -> Dict[str, Any]:
    """FastAPI dependency — ensures the current user has admin role."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user


# --------------- Rate limiting (simple in-memory) ---------------

_login_attempts: Dict[str, list] = {}


def check_rate_limit(ip: str, max_attempts: int = 5, window_seconds: int = 60) -> bool:
    """Returns True if the IP is within rate limits, False if exceeded."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=window_seconds)
    attempts = _login_attempts.get(ip, [])
    # Prune old attempts
    attempts = [t for t in attempts if t > cutoff]
    _login_attempts[ip] = attempts
    return len(attempts) < max_attempts


def record_login_attempt(ip: str):
    """Record a login attempt for rate limiting."""
    now = datetime.now(timezone.utc)
    _login_attempts.setdefault(ip, []).append(now)
