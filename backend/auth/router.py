import logging
from fastapi import APIRouter, HTTPException, Depends, status
from .models import SignupRequest, LoginRequest, AuthResponse
from .utils import hash_password, verify_password, create_access_token, get_current_user, TokenData
from ..database import supabase

logger = logging.getLogger("auth")
router = APIRouter(prefix="/api/v1/auth", tags=["Auth"])


@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest):
    try:
        existing = supabase.table("users").select("id").eq("email", req.email).execute()
        if existing.data:
            raise HTTPException(status_code=400, detail="Email already registered")

        hashed = hash_password(req.password)
        result = supabase.table("users").insert({
            "email": req.email,
            "password_hash": hashed,
            "full_name": req.full_name,
        }).execute()

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
