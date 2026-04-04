"""
Authentication API routes — login, Google OAuth, admin user management.
"""
import os
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel

from auth import (
    hash_password, verify_password, create_access_token,
    get_current_user, require_admin,
    check_rate_limit, record_login_attempt,
    COOKIE_NAME, JWT_EXPIRY_DAYS,
    HAS_BCRYPT, HAS_JOSE,
)
from db_router import (
    get_user_by_email, get_user_by_google_id, create_user,
    update_user_last_login, update_user_password,
    list_users, update_user_active, get_user_by_id,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["auth"])

IS_PROD = os.environ.get("RAILWAY_ENVIRONMENT") or os.environ.get("APP_BASE_URL", "").startswith("https")


# --------------- Request models ---------------

class LoginRequest(BaseModel):
    email: str
    password: str

class GoogleLoginRequest(BaseModel):
    credential: str  # Google ID token from GSI

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str

class CreateUserRequest(BaseModel):
    email: str
    name: str
    role: str = "user"
    temporary_password: str


# --------------- Cookie helper ---------------

def _set_auth_cookie(response: Response, token: str):
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=bool(IS_PROD),
        samesite="lax",
        max_age=JWT_EXPIRY_DAYS * 24 * 60 * 60,
        path="/",
    )


def _clear_auth_cookie(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")


# --------------- Endpoints ---------------

@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response):
    """Email + password login. Returns user object and sets httpOnly JWT cookie."""
    client_ip = request.client.host if request.client else "unknown"
    email = body.email.strip().lower()
    logger.info(f"Login attempt for email: {email}")

    if not check_rate_limit(client_ip):
        raise HTTPException(status_code=429, detail="Too many login attempts. Try again in a minute.")

    record_login_attempt(client_ip)

    user = await get_user_by_email(email)
    logger.info(f"User found: {user is not None}")
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    logger.info(f"User has password_hash: {user.get('password_hash') is not None}")
    logger.info(f"Password hash length: {len(user.get('password_hash', ''))}")
    logger.info(f"Password hash prefix: {(user.get('password_hash') or '')[:7]}")
    logger.info(f"bcrypt available: {HAS_BCRYPT}, jose available: {HAS_JOSE}")

    if not user.get("password_hash"):
        raise HTTPException(status_code=401, detail="This account uses Google sign-in. Please use the Google button.")

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account deactivated")

    if not verify_password(body.password, user["password_hash"]):
        logger.warning(f"Password verification failed for {email}")
        raise HTTPException(status_code=401, detail="Invalid email or password")

    logger.info(f"Login successful for {email}")
    token = create_access_token(user["id"], user["email"], user["role"])
    _set_auth_cookie(response, token)
    await update_user_last_login(user["id"])

    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "avatar_url": user.get("avatar_url"),
        }
    }


@router.post("/google")
async def google_login(body: GoogleLoginRequest, response: Response):
    """Google OAuth token verification. Only works for pre-created users (invite-only)."""
    # Verify the Google ID token with Google's API
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"https://oauth2.googleapis.com/tokeninfo?id_token={body.credential}"
            )
            if resp.status_code != 200:
                raise HTTPException(status_code=401, detail="Invalid Google token")
            google_data = resp.json()
    except httpx.RequestError:
        raise HTTPException(status_code=502, detail="Failed to verify Google token")

    google_email = google_data.get("email", "").lower()
    google_id = google_data.get("sub")
    google_name = google_data.get("name", "")
    google_avatar = google_data.get("picture", "")

    if not google_email or not google_id:
        raise HTTPException(status_code=401, detail="Invalid Google token data")

    # Check if user exists by google_id first, then by email
    user = await get_user_by_google_id(google_id)
    if not user:
        user = await get_user_by_email(google_email)

    if not user:
        raise HTTPException(
            status_code=403,
            detail="No account found for this email. Contact your administrator."
        )

    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Account deactivated")

    # Update google_id and avatar if not yet set
    if not user.get("google_id") or not user.get("avatar_url"):
        from db_router import update_user_google_info
        await update_user_google_info(user["id"], google_id, google_avatar, google_name)

    token = create_access_token(user["id"], user["email"], user["role"])
    _set_auth_cookie(response, token)
    await update_user_last_login(user["id"])

    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user.get("name") or google_name,
            "role": user["role"],
            "avatar_url": user.get("avatar_url") or google_avatar,
        }
    }


@router.post("/logout")
async def logout(response: Response):
    """Clear the auth cookie."""
    _clear_auth_cookie(response)
    return {"status": "ok"}


@router.get("/me")
async def get_me(user=Depends(get_current_user)):
    """Return the currently authenticated user."""
    return {
        "user": {
            "id": user["id"],
            "email": user["email"],
            "name": user["name"],
            "role": user["role"],
            "avatar_url": user.get("avatar_url"),
        }
    }


@router.post("/change-password")
async def change_password(body: ChangePasswordRequest, user=Depends(get_current_user)):
    """Authenticated user changes their own password."""
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Verify current password if they have one
    if user.get("password_hash"):
        if not verify_password(body.current_password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Current password is incorrect")

    new_hash = hash_password(body.new_password)
    await update_user_password(user["id"], new_hash)
    return {"status": "ok"}


# --------------- Admin endpoints ---------------

@router.post("/admin/create-user")
async def admin_create_user(body: CreateUserRequest, admin=Depends(require_admin)):
    """Admin-only: create a new user account."""
    if body.role not in ("admin", "user"):
        raise HTTPException(status_code=400, detail="Role must be 'admin' or 'user'")
    if len(body.temporary_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    existing = await get_user_by_email(body.email.strip().lower())
    if existing:
        raise HTTPException(status_code=409, detail="A user with this email already exists")

    password_hash = hash_password(body.temporary_password)
    user_id = await create_user(
        email=body.email.strip().lower(),
        password_hash=password_hash,
        name=body.name.strip(),
        role=body.role,
        auth_provider="email",
    )
    return {"id": user_id, "email": body.email.strip().lower(), "status": "created"}


@router.get("/admin/users")
async def admin_list_users(admin=Depends(require_admin)):
    """Admin-only: list all user accounts."""
    users = await list_users()
    return {"users": users}


@router.put("/admin/users/{user_id}/active")
async def admin_toggle_user(user_id: str, active: bool = True, admin=Depends(require_admin)):
    """Admin-only: activate or deactivate a user."""
    target = await get_user_by_id(user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target["id"] == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    await update_user_active(user_id, active)
    return {"id": user_id, "is_active": active}


# --------------- Diagnostic endpoint (temporary) ---------------

@router.get("/debug")
async def auth_debug():
    """Temporary diagnostic endpoint for production debugging."""
    admin_email = os.environ.get("ADMIN_EMAIL", "")
    users = await list_users()
    admin_user = next((u for u in users if u["email"] == admin_email.lower()), None)

    return {
        "bcrypt_available": HAS_BCRYPT,
        "jose_available": HAS_JOSE,
        "total_users": len(users),
        "admin_email": admin_email,
        "admin_found_in_db": admin_user is not None,
        "admin_has_password_hash": bool(admin_user.get("password_hash")) if admin_user else None,
        "admin_hash_length": len(admin_user.get("password_hash", "")) if admin_user else None,
        "admin_hash_prefix": (admin_user.get("password_hash") or "")[:7] if admin_user else None,
        "admin_is_active": admin_user.get("is_active") if admin_user else None,
        "jwt_secret_set": os.environ.get("JWT_SECRET", "") != "dev-secret-change-in-production",
    }
