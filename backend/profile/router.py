import logging
from fastapi import APIRouter, HTTPException, Depends
from .models import ProfileResponse, ProfileUpdateRequest
from ..auth.utils import get_current_user, TokenData
from ..database import supabase

logger = logging.getLogger("profile")
router = APIRouter(prefix="/api/v1/profile", tags=["Profile"])


@router.get("/", response_model=ProfileResponse)
async def get_profile(current_user: TokenData = Depends(get_current_user)):
    try:
        result = (
            supabase.table("users")
            .select("full_name,email,phone,cnic,ntn,city,province,tax_year,created_at")
            .eq("id", current_user.user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        row = result.data[0]
        return ProfileResponse(
            full_name=row.get("full_name", ""),
            email=row.get("email", ""),
            phone=row.get("phone"),
            cnic=row.get("cnic"),
            ntn=row.get("ntn"),
            city=row.get("city"),
            province=row.get("province"),
            tax_year=row.get("tax_year"),
            created_at=str(row["created_at"]) if row.get("created_at") else None,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Get profile failed")
        raise HTTPException(status_code=500, detail="Failed to fetch profile")


@router.put("/", response_model=ProfileResponse)
async def update_profile(
    req: ProfileUpdateRequest,
    current_user: TokenData = Depends(get_current_user),
):
    try:
        update_data = req.model_dump(exclude_none=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update")

        result = (
            supabase.table("users")
            .update(update_data)
            .eq("id", current_user.user_id)
            .execute()
        )
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        row = result.data[0]
        return ProfileResponse(
            full_name=row.get("full_name", ""),
            email=row.get("email", ""),
            phone=row.get("phone"),
            cnic=row.get("cnic"),
            ntn=row.get("ntn"),
            city=row.get("city"),
            province=row.get("province"),
            tax_year=row.get("tax_year"),
            created_at=str(row["created_at"]) if row.get("created_at") else None,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Update profile failed")
        raise HTTPException(status_code=500, detail="Failed to update profile")
