from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.user import User
from app.models.token import Token
from app.schemas.user import UserResponse, UserUpdate, UserDeleteResponse
from app.api.v1.auth import get_current_user
from datetime import datetime

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_user_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Lấy thông tin profile của người dùng đang đăng nhập
    """
    return current_user


@router.put("/me", response_model=UserResponse)
def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Cập nhật thông tin profile của người dùng đang đăng nhập
    """
    # Kiểm tra nếu email mới đã tồn tại (trừ email hiện tại)
    if user_update.email and user_update.email != current_user.email:
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        current_user.email = user_update.email

    # Cập nhật name nếu có
    if user_update.name:
        current_user.name = user_update.name

    # Cập nhật thời gian
    current_user.updated_at = datetime.utcnow()

    db.commit()
    db.refresh(current_user)

    return current_user


@router.delete("/me", response_model=UserDeleteResponse)
def delete_user_account(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Xóa tài khoản của người dùng đang đăng nhập
    """
    # Xóa tất cả tokens của user trước
    db.query(Token).filter(Token.user_id == current_user.id).delete()

    # Xóa user
    db.delete(current_user)
    db.commit()

    return {"message": "User account deleted successfully"}
