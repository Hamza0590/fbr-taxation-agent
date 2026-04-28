from pydantic import BaseModel
from typing import Optional


class ProfileResponse(BaseModel):
    full_name: str
    email: str
    phone: Optional[str] = None
    cnic: Optional[str] = None
    ntn: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    tax_year: Optional[str] = None
    created_at: Optional[str] = None


class ProfileUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    phone: Optional[str] = None
    cnic: Optional[str] = None
    ntn: Optional[str] = None
    city: Optional[str] = None
    province: Optional[str] = None
    tax_year: Optional[str] = None
