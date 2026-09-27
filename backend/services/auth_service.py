from typing import Optional
from fastapi import HTTPException, status
from models.auth import LoginRequest, SignupRequest
from supabase_client import (
    authenticate_user,
    register_user,
    get_user_from_token,
)


def signup_user(req: SignupRequest):
    """
    Registers a public user (Layman / Lawyer) in Supabase auth.users & creates public.profiles.
    """
    auth_data = register_user(
        email=req.email,
        password=req.password,
        name=req.name,
        role=req.role,
        license_no=req.license_no,
        cnic=req.cnic,
    )
    if not auth_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration failed. Email may already be in use or invalid credentials.",
        )
    return auth_data


def login_user(req: LoginRequest):
    """
    Authenticates user/admin with Supabase Auth and returns JWT token & user profile.
    """
    auth_data = authenticate_user(req.email, req.password)
    if not auth_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    return auth_data


def get_current_user_profile(authorization: Optional[str]):
    """
    Validates JWT Bearer token and returns current user info.
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header missing",
        )
    user = get_user_from_token(authorization)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired JWT token",
        )
    return {"user": user}
