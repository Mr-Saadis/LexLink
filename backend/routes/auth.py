from typing import Optional
from fastapi import APIRouter, Header
from models.auth import LoginRequest, SignupRequest
from services.auth_service import signup_user, login_user, get_current_user_profile

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/signup")
async def signup(req: SignupRequest):
    """
    Registers a public user (Layman / Lawyer) in Supabase auth.users & creates public.profiles.
    """
    return signup_user(req)


@router.post("/login")
async def login(req: LoginRequest):
    """
    Authenticates user/admin with Supabase Auth and returns JWT token & user profile.
    """
    return login_user(req)


@router.get("/me")
async def get_current_user(authorization: Optional[str] = Header(None)):
    """
    Validates JWT Bearer token and returns current user info.
    """
    return get_current_user_profile(authorization)
