from fastapi import APIRouter, Depends, HTTPException, status, Header, Form
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_password_hash, verify_password, create_access_token, verify_token
from app.models.user import User
from app.models.token import Token
from app.schemas.auth import RegisterRequest, ChangePasswordRequest, TokenResponse, ForgetPasswordRequest
from app.schemas.user import UserResponse
from datetime import datetime, timedelta
import secrets
from typing import Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

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
    sender_email = "your_email@gmail.com"
    sender_password = "your_app_password"  
    smtp_server = "smtp.gmail.com"
    smtp_port = 587

    subject = "Your Password Reset Code"
    body = f"Here is your reset code: {reset_code}"

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())


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
    password_data: ForgetPasswordRequest,
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.email == password_data.email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Email not found"
        )

    reset_code = str(secrets.randbelow(1000000)).zfill(6)

    user.reset_code = reset_code
    user.reset_code_expiration = datetime.utcnow() + timedelta(minutes=15)

    db.commit()
    db.refresh(user)

    # TODO: gửi email thực tế (SMTP/SendGrid/Resend...)
    print(f"Reset code for {user.email}: {reset_code}")

    return {"message": "Reset code has been sent to your email"}

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