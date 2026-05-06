import logging
import secrets
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from pydantic_settings import BaseSettings

from .models import SignupRequest, LoginRequest, CNICLoginRequest, AuthResponse, ForgotPasswordRequest, ResetPasswordRequest
from .utils import hash_password, verify_password, create_access_token, get_current_user, TokenData
from .config import get_auth_settings
from .email import send_password_reset_email
from ..database import supabase

logger = logging.getLogger("auth")
router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


# ── Google OAuth settings ─────────────────────────────────────────────────────

class GoogleOAuthSettings(BaseSettings):
    client_id: str = ""
    client_secret: str = ""
    redirect_uri: str = "http://localhost:8000/api/v1/auth/google/callback"
    frontend_redirect: str = "http://localhost:5173"

    model_config = {
        "env_prefix": "GOOGLE_",
        "env_file": ".env",
        "extra": "ignore",
    }


@lru_cache
def get_google_settings() -> GoogleOAuthSettings:
    return GoogleOAuthSettings()


# ── Email / password endpoints ────────────────────────────────────────────────

@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest):
    try:
        existing = supabase.table("users").select("id").eq("email", req.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = hash_password(req.password)
        insert_data = {
            "email": req.email,
            "password_hash": hashed,
            "full_name": req.full_name,
        }
        if req.cnic:
            insert_data["cnic"] = req.cnic

        result = supabase.table("users").insert(insert_data).execute()

        user = result.data[0]
        token = create_access_token({"user_id": user["id"], "email": user["email"]})
        return AuthResponse(user_id=user["id"], email=user["email"], full_name=user["full_name"], token=token)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Signup failed")
        raise HTTPException(status_code=500, detail="Signup failed")


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    try:
        result = supabase.table("users").select("*").eq("email", req.email).execute()
        if not result.data:
            raise HTTPException(status_code=401, detail="Invalid email or password")

        user = result.data[0]
        if not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid email or password")

        token = create_access_token({"user_id": user["id"], "email": user["email"]})
        return AuthResponse(user_id=user["id"], email=user["email"], full_name=user["full_name"], token=token)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Login failed")
        raise HTTPException(status_code=500, detail="Login failed")


@router.post("/cnic-login", response_model=AuthResponse)
async def cnic_login(req: CNICLoginRequest):
    try:
        result = supabase.table("users").select("*").eq("cnic", req.cnic).execute()
        if not result.data:
            raise HTTPException(status_code=401, detail="Invalid CNIC or password")

        user = result.data[0]
        if not verify_password(req.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid CNIC or password")

        token = create_access_token({"user_id": user["id"], "email": user["email"]})
        return AuthResponse(user_id=user["id"], email=user["email"], full_name=user["full_name"], token=token)
    except HTTPException:
        raise
    except Exception:
        logger.exception("CNIC login failed")
        raise HTTPException(status_code=500, detail="CNIC login failed")


@router.get("/me")
async def get_me(current_user: TokenData = Depends(get_current_user)):
    try:
        result = (
            supabase.table("users")
            .select("id,email,full_name,phone,cnic,ntn,city,province,tax_year,created_at")
            .eq("id", current_user.user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        return result.data[0]
    except HTTPException:
        raise
    except Exception:
        logger.exception("Get me failed")
        raise HTTPException(status_code=500, detail="Failed to fetch user")


# ── Google OAuth endpoints ────────────────────────────────────────────────────

@router.get("/google/login")
async def google_login():
    gs = get_google_settings()
    params = urlencode({
        "client_id": gs.client_id,
        "redirect_uri": gs.redirect_uri,
        "scope": "openid email profile",
        "response_type": "code",
        "access_type": "offline",
    })
    return RedirectResponse(url=f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


@router.get("/google/callback")
async def google_callback(code: str):
    gs = get_google_settings()
    try:
        async with httpx.AsyncClient() as client:
            # Exchange code for tokens
            token_resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": gs.client_id,
                    "client_secret": gs.client_secret,
                    "redirect_uri": gs.redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            token_resp.raise_for_status()
            access_token = token_resp.json()["access_token"]

            # Fetch user info
            userinfo_resp = await client.get(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            userinfo_resp.raise_for_status()
            userinfo = userinfo_resp.json()

        email: str = userinfo.get("email", "")
        full_name: str = userinfo.get("name", "")

        # Upsert user — track whether this is a brand-new account
        existing = supabase.table("users").select("*").eq("email", email).execute()
        if existing.data:
            user = existing.data[0]
            is_new_user = False
        else:
            result = supabase.table("users").insert({
                "email": email,
                "full_name": full_name,
                "password_hash": "",
                "auth_provider": "google",
            }).execute()
            user = result.data[0]
            is_new_user = True

        jwt = create_access_token({"user_id": user["id"], "email": user["email"]})
        redirect_url = f"{gs.frontend_redirect}?token={jwt}"
        if is_new_user:
            redirect_url += "&is_new=1"
        return RedirectResponse(url=redirect_url)

    except Exception:
        logger.exception("Google OAuth callback failed")
        raise HTTPException(status_code=500, detail="Google authentication failed")


# ── Password reset endpoints ─────────────────────────────────────────────────

@router.post("/forgot-password")
async def forgot_password(req: ForgotPasswordRequest):
    settings = get_auth_settings()
    try:
        result = supabase.table("users").select("id, email").eq("email", req.email).execute()
        if result.data:
            user = result.data[0]
            token = secrets.token_urlsafe(32)
            expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.reset_token_expire_minutes)
            supabase.table("password_reset_tokens").insert({
                "user_id": user["id"],
                "token": token,
                "expires_at": expires_at.isoformat(),
                "used": False,
            }).execute()
            reset_link = f"{settings.frontend_base_url}?reset_token={token}"
            await send_password_reset_email(user["email"], reset_link)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Forgot password failed")
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(req: ResetPasswordRequest):
    result = supabase.table("password_reset_tokens").select("*").eq("token", req.token).eq("used", False).execute()
    if not result.data:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token")

    record = result.data[0]
    expires_at_str = record["expires_at"]
    if expires_at_str.endswith("Z"):
        expires_at_str = expires_at_str[:-1] + "+00:00"
    expires_at = datetime.fromisoformat(expires_at_str)
    if not expires_at.tzinfo:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Reset token has expired. Please request a new one.")

    new_hash = hash_password(req.new_password)
    supabase.table("users").update({"password_hash": new_hash}).eq("id", record["user_id"]).execute()
    supabase.table("password_reset_tokens").update({"used": True}).eq("token", req.token).execute()
    return {"message": "Password updated successfully. You can now log in."}
