import pytest
import sys
import types

# Provide a lightweight stub for 'mailersend' used by app.core.mailer so tests
# can import app without installing external dependency.
mailersend_stub = types.ModuleType("mailersend")
mailersend_stub.MailerSendClient = lambda *a, **k: None
mailersend_stub.EmailBuilder = lambda *a, **k: None
exceptions_mod = types.ModuleType("mailersend.exceptions")
class MailerSendError(Exception):
    pass
exceptions_mod.MailerSendError = MailerSendError
mailersend_stub.exceptions = exceptions_mod
sys.modules["mailersend"] = mailersend_stub
sys.modules["mailersend.exceptions"] = exceptions_mod

# Provide a minimal 'celery' stub so importing app doesn't require celery installed.
celery_mod = types.ModuleType("celery")

class DummyCeleryApp:
    def __init__(self, *a, **k):
        self.conf = {}

    def task(self, *args, **kwargs):
        def _decorator(f):
            return f

        return _decorator


def _chain_stub(*args, **kwargs):
    class _Canvas:
        def apply_async(self, *a, **k):
            return None

    return _Canvas()


celery_mod.Celery = DummyCeleryApp
celery_mod.chain = _chain_stub
sys.modules["celery"] = celery_mod
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.models.user import User
from app.models.token import Token

# Sử dụng SQLite in-memory database cho testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Tạo database session mới cho mỗi test"""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """Tạo test client với database session override"""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    # Mock email sending functions để tránh lỗi khi test
    with patch('app.api.v1.auth.send_verify_email_otp') as mock_send_verify:
        with patch('app.api.v1.auth.send_reset_email') as mock_send_reset:
            mock_send_verify.return_value = None
            mock_send_reset.return_value = None

            with TestClient(app) as test_client:
                yield test_client

    app.dependency_overrides.clear()


@pytest.fixture
def test_user_data():
    """Dữ liệu user mẫu để testing"""
    return {
        "name": "Test User",
        "email": "testuser@example.com",
        "passwordhash": "TestPassword123!"
    }


@pytest.fixture
def create_test_user(db_session):
    """Factory fixture để tạo test user"""
    from app.core.security import get_password_hash
    from datetime import datetime

    def _create_user(email="testuser@example.com", name="Test User", password="TestPassword123!"):
        hashed_password = get_password_hash(password)
        user = User(
            name=name,
            email=email,
            passwordhash=hashed_password,
            email_verified=True,
            email_verification_token=None,
            email_verification_expiration=None
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _create_user


@pytest.fixture
def authenticated_client(client, create_test_user, db_session):
    """Tạo authenticated client với access token"""
    from app.core.security import create_access_token
    from datetime import datetime, timedelta

    # Tạo user
    user = create_test_user()

    # Tạo access token
    access_token = create_access_token(data={"sub": user.email})

    # Lưu token vào database
    token_record = Token(
        token=access_token,
        expiry_date=datetime.utcnow() + timedelta(minutes=15),
        user_id=user.id
    )
    db_session.add(token_record)
    db_session.commit()

    # Set authorization header
    client.headers = {
        **client.headers,
        "Authorization": f"Bearer {access_token}"
    }

    return client, user
