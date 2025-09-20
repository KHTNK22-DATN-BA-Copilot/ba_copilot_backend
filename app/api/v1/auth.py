from fastapi import APIRouter, Depends, HTTPException, status, Header, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, verify_token
from app.models.user import User
from app.models.token import Token
from app.schemas.auth import RegisterRequest, ChangePasswordRequest, TokenResponse, ForgetPasswordRequest, VerifyOTPRequest, ResetPasswordRequest
from app.schemas.user import UserResponse
from datetime import datetime, timedelta
import secrets
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from fastapi import Query

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)


def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)):
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

    payload = verify_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
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



def send_reset_email(to_email: str, reset_code: str):
    subject = "Your Password Reset Code"

    body = f"""
    <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <p>We received a request to reset your password.</p>
            <p>Please use the following reset code:</p>
            <h2 style="color: #2c3e50; font-size: 28px; letter-spacing: 3px; text-align: center;">
                {reset_code}
            </h2>
            <p>This code will expire in <b>15 minutes</b>.</p>
            <br>
            <p>If you did not request a password reset, please ignore this email.</p>
        </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["From"] = settings.smtp_user
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "html"))

    with smtplib.SMTP(settings.smtp_server, settings.smtp_port) as server:
        server.starttls()
        server.login(settings.smtp_user, settings.smtp_password)
        server.sendmail(settings.smtp_user, to_email, msg.as_string())


@router.post("/register", response_model=UserResponse)
def register_user(user_data: RegisterRequest, db: Session = Depends(get_db)):
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == user_data.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Hash password and create user
    hashed_password = get_password_hash(user_data.passwordhash)
    verification_token = secrets.token_urlsafe(32)

    db_user = User(
        name=user_data.name,
        email=user_data.email,
        passwordhash=hashed_password,
        email_verified=False,
        email_verification_token=verification_token,
        email_verification_expiration=datetime.utcnow() + timedelta(hours=24)
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


@router.post("/change-password")
def change_password(
    password_data: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Verify old password
    if not verify_password(password_data.old_password, current_user.passwordhash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect old password"
        )

    # Hash and update new password
    hashed_new_password = get_password_hash(password_data.new_password)
    current_user.passwordhash = hashed_new_password
    current_user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(current_user)

    return {"message": "Password changed successfully"}


@router.post("/forgot-password")
def forgot_password(
    reset_data: ForgetPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == reset_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email not found"
        )

    reset_code = str(secrets.randbelow(1000000)).zfill(6)

    user.reset_code = reset_code
    user.reset_code_expiration = datetime.utcnow() + timedelta(minutes=15)

    db.commit()
    db.refresh(user)

    send_reset_email(reset_data.email,reset_code)

    return {"message": "Reset code has been sent to your email"}

@router.post("/verify-otp")
def verify_otp(
    verify_data: VerifyOTPRequest,
    email: str = Query(...), 
    db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user or user.reset_code != verify_data.code or user.reset_code_expiration < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset code"
        )

    return {"message": "OTP verified successfully"}

@router.post("/reset-password")
def reset_password(
    email: str = Query(...), 
    reset_data: ResetPasswordRequest = None,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
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
            detail="Incorrect email or password"
        )

    access_token = create_access_token(data={"sub": user.email})
    return {"access_token": access_token, "token_type": "bearer"}