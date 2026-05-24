from pydantic import BaseModel, EmailStr
from datetime import datetime
from typing import Optional

from app.schemas.base_response import BaseResponseModel


class UserBase(BaseResponseModel):
    name: str
    email: EmailStr


class UserCreate(UserBase):
    passwordhash: str


class UserResponse(UserBase):
    id: int
    email_verified: bool
    email_verification_token: Optional[str] = None
    email_verification_expiration: Optional[datetime] = None
    onboard_dashboard: bool
    onboard_project: bool
    onboard_file: bool
    onboard_workflow: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RegisterResponse(BaseResponseModel):
    user: UserResponse
    message: str


class UserInDB(UserResponse):
    passwordhash: str


class UserUpdate(BaseResponseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    onboard_dashboard: Optional[bool] = None
    onboard_project: Optional[bool] = None
    onboard_file: Optional[bool] = None
    onboard_workflow: Optional[bool] = None

class UserDeleteResponse(BaseResponseModel):
    message: str
