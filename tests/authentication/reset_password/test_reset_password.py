import pytest
from fastapi import status
from app.models.user import User
from app.core.security import get_password_hash, verify_password
from tests.authentication.reset_password.mock_data import mock_user


def create_test_user(db_session, email="test@example.com", password="old_password"):
    """Helper function to create a test user"""
    user = mock_user()
    user.email = email
    user.passwordhash = get_password_hash(password)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestResetPasswordEndpoint:
    """Test cases for POST /api/v1/auth/reset-password endpoint"""

    def test_reset_password_success(self, client, db_session):
        """Test successful password reset"""
        user = create_test_user(db_session)

        response = client.post(
            "/api/v1/auth/reset-password",
            params={"email": user.email},
            json={"new_password": "new_secure_password"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Password reset successful"

        # Verify that the password was updated in the database
        updated_user = db_session.query(User).filter_by(email=user.email).first()
        assert verify_password("new_secure_password", updated_user.passwordhash)
        assert updated_user.reset_code is None
        assert updated_user.reset_code_expiration is None

    def test_reset_password_nonexistent_user(self, client):
        """Test when the user does not exist"""
        response = client.post(
            "/api/v1/auth/reset-password",
            params={"email": "nonexistent@example.com"},
            json={"new_password": "any_password"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "User not found"

    def test_reset_password_missing_email_query(self, client):
        """Test when the email query parameter is missing"""
        response = client.post(
            "/api/v1/auth/reset-password",
            json={"new_password": "some_password"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_reset_password_missing_new_password(self, client, db_session):
        """Test when the new password field is missing in the request body"""
        user = create_test_user(db_session)

        response = client.post(
            "/api/v1/auth/reset-password",
            params={"email": user.email},
            json={},  # Missing new_password
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
