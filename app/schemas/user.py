from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional


class UserBase(BaseModel):
    name: str
    email: EmailStr


class UserCreate(UserBase):
    passwordhash: str


class UserResponse(UserBase):
    id: int
    email_verified: bool
    email_verification_token: Optional[str] = None
    email_verification_expiration: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class RegisterResponse(BaseModel):
    user: UserResponse
    message: str
    
class UserInDB(UserResponse):
    passwordhash: str