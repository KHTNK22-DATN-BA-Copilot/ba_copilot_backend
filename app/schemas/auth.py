from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    passwordhash: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str

class ForgetPasswordRequest(BaseModel):
    email: str

class VerifyOTPRequest(BaseModel):
    code:str

class ResetPasswordRequest(BaseModel):
    new_password: str
    
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class LogoutResponse(BaseModel):
    message: str