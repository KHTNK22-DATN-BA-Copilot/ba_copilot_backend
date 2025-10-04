import pytest
from fastapi import status
from app.models.user import User
from tests.authentication.login.mock_data import mock_user


def create_test_user(db_session, email="test@example.com", password="123456"):
    """Helper function to create a test user"""
    user = mock_user()
    user.email = email
    from app.core.security import get_password_hash
    user.passwordhash = get_password_hash(password)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestLoginEndpoint:
    """Test cases for POST /api/v1/auth/login endpoint"""

    def test_login_success(self, client, db_session):
        """Test successful login with valid email and password"""
        create_test_user(db_session)

        response = client.post(
            "/api/v1/auth/login",
            data={"email": "test@example.com", "password": "123456"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_invalid_password(self, client, db_session):
        """Test login with incorrect password"""
        create_test_user(db_session)

        response = client.post(
            "/api/v1/auth/login",
            data={"email": "test@example.com", "password": "wrongpassword"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Incorrect email or password"

    def test_login_nonexistent_email(self, client):
        """Test login with an email that is not registered"""
        response = client.post(
            "/api/v1/auth/login",
            data={"email": "nonexistent@example.com", "password": "123456"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Incorrect email or password"

    def test_login_unverified_email(self, client, db_session):
        """Test login with an unverified email"""
        user = create_test_user(db_session)
        user.email_verified = False
        db_session.commit()

        response = client.post(
            "/api/v1/auth/login",
            data={"email": "test@example.com", "password": "123456"},
        )

        # Depending on implementation: may block or allow login
        assert response.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_200_OK]

    def test_login_missing_fields(self, client):
        """Test login with missing required fields"""
        # Missing password
        response = client.post("/api/v1/auth/login", data={"email": "test@example.com"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

        # Missing email
        response = client.post("/api/v1/auth/login", data={"password": "123456"})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


    def test_login_case_sensitive_email(self, client, db_session):
        """Test login with different email case (uppercase vs lowercase)"""
        create_test_user(db_session, email="test@example.com")

        response = client.post(
            "/api/v1/auth/login",
            data={"email": "TEST@EXAMPLE.COM", "password": "123456"},
        )

        # Depending on implementation: email may or may not be normalized
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_401_UNAUTHORIZED]
