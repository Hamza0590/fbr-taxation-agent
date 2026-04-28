from pydantic import BaseModel
from typing import Optional


class SignupRequest(BaseModel):
    email: str
    password: str
    full_name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    token: str


class TokenData(BaseModel):
    user_id: str
    email: str
