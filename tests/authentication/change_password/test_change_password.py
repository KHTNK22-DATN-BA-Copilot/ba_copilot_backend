import pytest
from fastapi import status
from app.models.user import User
from app.core.security import verify_password


class TestChangePasswordEndpoint:
    """Test cases for POST /api/v1/auth/change-password endpoint"""

    def test_change_password_success(self, authenticated_client, db_session):
        """Test successful password change"""
        client, user = authenticated_client

        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "old_password": "TestPassword123!",
                "new_password": "new_secure_password",
            },
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Password changed successfully"

        # Verify the password has been updated in the database
        updated_user = db_session.query(User).filter_by(email=user.email).first()
        assert verify_password("new_secure_password", updated_user.passwordhash)

    def test_change_password_incorrect_old_password(self, authenticated_client):
        """Test when the old password is incorrect"""
        client, _ = authenticated_client

        response = client.post(
            "/api/v1/auth/change-password",
            json={
                "old_password": "wrong_password",
                "new_password": "new_secure_password",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Incorrect old password"

    def test_change_password_missing_old_password(self, authenticated_client):
        """Test when old_password field is missing"""
        client, _ = authenticated_client

        response = client.post(
            "/api/v1/auth/change-password",
            json={"new_password": "new_secure_password"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_change_password_missing_new_password(self, authenticated_client):
        """Test when new_password field is missing"""
        client, _ = authenticated_client

        response = client.post(
            "/api/v1/auth/change-password",
            json={"old_password": "old_password"},
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
