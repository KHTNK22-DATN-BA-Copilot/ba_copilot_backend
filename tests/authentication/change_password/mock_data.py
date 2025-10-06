from app.models.user import User
from app.core.security import get_password_hash


def mock_user():
    return User(
        name="Test User",
        email="test@example.com",
        passwordhash=get_password_hash("123456"),
        email_verified=True,
        email_verification_token=None,
        email_verification_expiration=None,
        reset_code=None,
        reset_code_expiration=None,
    )
