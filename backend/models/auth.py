from typing import Optional
from pydantic import BaseModel


class LoginRequest(BaseModel):
    email: str
    password: str


class SignupRequest(BaseModel):
    email: str
    password: str
    name: str
    role: str = "layman"  # 'layman' | 'lawyer'
    license_no: Optional[str] = None
    cnic: Optional[str] = None
