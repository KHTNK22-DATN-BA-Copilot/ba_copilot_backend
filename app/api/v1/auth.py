from fastapi import APIRouter, Depends, HTTPException, status, Header, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import (
    get_password_hash,
    get_otp_hash,
    verify_password,
    create_access_token,
    verify_token,
    verify_email_otp,
)
from app.models.user import User
from app.models.token import Token
from app.schemas.auth import (
    RegisterRequest,
    ChangePasswordRequest,
    TokenResponse,
    ForgetPasswordRequest,
    VerifyOTPRequest,
    ResetPasswordRequest,
    LogoutResponse,
)
from app.schemas.refrest_token import (
    RefreshTokenRequest
)
from app.schemas.user import UserResponse, RegisterResponse
from datetime import datetime, timedelta, timezone
import secrets
import uuid
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from fastapi import Query
from app.core.mailer import send_reset_email, send_verify_email_otp



router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def get_current_user(
    authorization: Optional[str] = Header(None), db: Session = Depends(get_db)
):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload, error = verify_token(token)
    if error == "expired":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    elif error == "invalid":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email: str = payload.get("sub")
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload invalid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


@router.post("/register", response_model=RegisterResponse)
def register_user(user_data: RegisterRequest, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # Hash password and create user
    hashed_password = get_password_hash(user_data.passwordhash)
    otp = str(secrets.randbelow(1000000)).zfill(6)

    hashed_otp = get_otp_hash(otp)
    send_verify_email_otp(user_data.email, otp)

    db_user = User(
        name=user_data.name,
        email=user_data.email,
        passwordhash=hashed_password,
        email_verified=False,
        email_verification_token=hashed_otp,
        email_verification_expiration=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return {
        "user": db_user,
        "message": "Register successfully, please check your mail to verify email",
    }


@router.post("/verify-email")
def verify_email_by_otp(
    verify_data: VerifyOTPRequest,
    email: str = Query(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or user.email_verification_expiration < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    if not verify_email_otp(verify_data.code, user.email_verification_token):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    user.email_verification_token = None
    user.email_verification_expiration = None
    return {"message": "OTP verified successfully"}


@router.post("/change-password")
def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify old password
    if not verify_password(password_data.old_password, current_user.passwordhash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Incorrect old password"
        )

    # Hash and update new password
    hashed_new_password = get_password_hash(password_data.new_password)
    current_user.passwordhash = hashed_new_password
    current_user.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(current_user)

    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
def forgot_password(reset_data: ForgetPasswordRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == reset_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email not found"
        )

    reset_code = str(secrets.randbelow(1000000)).zfill(6)
    hashed_code = get_otp_hash(reset_code)

    user.reset_code = hashed_code
    user.reset_code_expiration = datetime.now(timezone.utc) + timedelta(minutes=15)

    db.commit()
    db.refresh(user)

    send_reset_email(reset_data.email, reset_code)

    return {"message": "Reset code has been sent to your email"}


@router.post("/verify-otp")
def verify_otp(
    verify_data: VerifyOTPRequest,
    email: str = Query(...),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or user.reset_code_expiration < datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Invalid or expired OTP")

    if not verify_email_otp(verify_data.code, user.reset_code):
        raise HTTPException(status_code=400, detail="Invalid OTP")

    return {"message": "OTP verified successfully"}


@router.post("/reset-password")
def reset_password(
    email: str = Query(...),
    reset_data: ResetPasswordRequest = None,
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="User not found"
        )

    user.passwordhash = get_password_hash(reset_data.new_password)
    user.reset_code = None
    user.reset_code_expiration = None

    db.commit()
    db.refresh(user)

    return {"message": "Password reset successful"}


@router.post("/login", response_model=TokenResponse)
def login(email: str = Form(), password: str = Form(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.passwordhash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    # create access_token
    access_token = create_access_token(data={"sub": user.email})

    # create refresh_token
    expired_at = datetime.now(timezone.utc) + timedelta(days=7)
    refresh_token = str(uuid.uuid4())

    # Store token in database for logout tracking
    token_record = Token(
        token=refresh_token,
        expiry_date=expired_at,  # Same as token expiry
        user_id=user.id,
    )
    db.add(token_record)
    db.commit()

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
    }


@router.post("/refresh")
def refresh_token(request: RefreshTokenRequest, db: Session = Depends(get_db)):

    if not request.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Refresh Token is required!"
        )

    # Tìm token trong database
    refresh_token = (
        db.query(Token)
        .filter(Token.token == request.refresh_token)
        .first()
    )

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Refresh token is not in database!",
        )

    # Kiểm tra token hết hạn
    if refresh_token.expiry_date < datetime.now(timezone.utc):
        db.delete(refresh_token)
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Refresh token was expired. Please make a new signin request.",
        )

    # Lấy user liên kết
    user = refresh_token.user
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found for this refresh token.",
        )

    # Tạo access token mới
    new_access_token = create_access_token(
        data={"sub": user.email},
        expires_delta=timedelta(hours=1),
    )

    return {"accessToken": new_access_token, "refreshToken": refresh_token.token}


@router.post("/logout", response_model=LogoutResponse)
def logout(
    current_user: User = Depends(get_current_user),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Find and delete the token from database to invalidate it
    token_record = db.query(Token).filter(Token.token == token).first()
    if token_record:
        db.delete(token_record)
        db.commit()

    return {"message": "Successfully logged out"}
