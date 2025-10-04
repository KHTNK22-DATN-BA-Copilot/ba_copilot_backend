import pytest
from unittest.mock import patch
from fastapi import status
from datetime import datetime
from app.models.user import User
from tests.authentication.forget_password.mock_data import mock_user


def create_test_user(db_session, email="test@example.com", verified=True):
    """Helper function to create a test user"""
    user = mock_user()
    user.email = email
    user.email_verified = verified
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


class TestForgotPasswordEndpoint:
    """Test cases for POST /api/v1/auth/forgot-password endpoint"""

    def test_forgot_password_success(self, client, db_session):
        """Test successful password reset request"""
        user = create_test_user(db_session)

        with patch("app.api.v1.auth.send_reset_email") as mock_send_email:
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": user.email},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["message"] == "Reset code has been sent to your email"

            # Verify that the email function was called once
            mock_send_email.assert_called_once()
            args, kwargs = mock_send_email.call_args
            assert args[0] == user.email
            assert len(args[1]) == 6  # The reset code should be 6 digits

            # Verify that reset_code and expiration were saved to the database
            updated_user = db_session.query(User).filter_by(email=user.email).first()
            assert updated_user.reset_code is not None
            assert updated_user.reset_code_expiration > datetime.utcnow()

    def test_forgot_password_nonexistent_email(self, client):
        """Test when email does not exist in the database"""
        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": "nonexistent@example.com"},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Email not found"

    def test_forgot_password_unverified_email(self, client, db_session):
        """Test when email is not verified"""
        user = create_test_user(db_session, verified=False)

        response = client.post(
            "/api/v1/auth/forgot-password",
            json={"email": user.email},
        )

        # Depending on the implementation, the API may allow or block this request
        assert response.status_code in [
            status.HTTP_401_UNAUTHORIZED,
            status.HTTP_200_OK,
        ]

    def test_forgot_password_missing_email_field(self, client):
        """Test request without the email field"""
        response = client.post("/api/v1/auth/forgot-password", json={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
