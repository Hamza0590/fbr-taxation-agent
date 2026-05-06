import re
from pydantic import BaseModel, field_validator
from typing import Optional


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str
    cnic: Optional[str] = None


class LoginRequest(BaseModel):
    email: str
    password: str


class CNICLoginRequest(BaseModel):
    cnic: str
    password: str

    @field_validator("cnic")
    @classmethod
    def validate_cnic(cls, v: str) -> str:
        if not re.match(r"^\d{5}-\d{7}-\d$", v):
            raise ValueError("CNIC must be in format XXXXX-XXXXXXX-X")
        return v


class AuthResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    token: str


class TokenData(BaseModel):
    user_id: str
    email: str


class ForgotPasswordRequest(BaseModel):
    email: str


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        return v
