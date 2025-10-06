import pytest
from fastapi import status
from app.models.token import Token
from tests.authentication.logout.mock_data import mock_user, mock_token


def create_test_user(db_session):
    """Helper function to create a mock user and valid JWT token in the test database."""
    user = mock_user()
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    token = mock_token(user)
    db_session.add(token)
    db_session.commit()
    db_session.refresh(token)

    return user, token


class TestLogoutEndpoint:
    """Test cases for POST /api/v1/auth/logout endpoint"""

    def test_logout_success(self, client, db_session):
        """Test successful logout with valid Bearer JWT token"""
        user, token = create_test_user(db_session)

        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {token.token}"},
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["message"] == "Successfully logged out"

        # Verify token was deleted from database
        deleted_token = (
            db_session.query(Token).filter(Token.token == token.token).first()
        )
        assert deleted_token is None

    def test_logout_missing_authorization_header(self, client):
        """Test logout without Authorization header"""
        response = client.post("/api/v1/auth/logout")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Authorization header required"

    def test_logout_invalid_scheme(self, client):
        """Test logout with invalid authentication scheme"""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Basic sometoken"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Invalid authentication scheme"

    def test_logout_invalid_format(self, client):
        """Test logout with malformed Authorization header"""
        response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": "Bearer"},
        )

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert data["detail"] == "Invalid authorization header format"
