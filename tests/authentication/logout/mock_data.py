from datetime import datetime, timedelta
from app.models.user import User
from app.models.token import Token
from app.core.security import get_password_hash, create_access_token

def mock_user():
    return User(
        name="Test User",
        email="test@example.com",
        passwordhash=get_password_hash("123456"),
        email_verified=True
    )

def mock_token(user):
    # Tạo JWT token thật từ hàm của hệ thống
    access_token = create_access_token(data={"sub": user.email})

    return Token(
        token=access_token,
        expiry_date=datetime.utcnow() + timedelta(minutes=15),
        user_id=user.id
    )
