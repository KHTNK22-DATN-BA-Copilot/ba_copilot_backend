import pytest
from fastapi import status
from app.models.user import User
from app.models.token import Token
from datetime import datetime, timedelta


class TestGetUserMeEndpoint:
    """Test cases cho GET /api/v1/user/me endpoint"""

    def test_get_user_profile_success(self, authenticated_client):
        """Test lấy thông tin profile thành công với token hợp lệ"""
        client, user = authenticated_client

        response = client.get("/api/v1/user/me")

        # Kiểm tra status code
        assert response.status_code == status.HTTP_200_OK

        # Kiểm tra response data
        data = response.json()
        assert data["id"] == user.id
        assert data["email"] == user.email
        assert data["name"] == user.name
        assert data["email_verified"] == user.email_verified
        assert "created_at" in data
        assert "updated_at" in data

    def test_get_user_profile_without_token(self, client):
        """Test lấy profile không có Authorization header"""
        response = client.get("/api/v1/user/me")

        # Kiểm tra trả về 401 Unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Authorization header required"

    def test_get_user_profile_invalid_token_format(self, client):
        """Test với token format không hợp lệ"""
        # Token không có 'Bearer' prefix
        client.headers = {"Authorization": "InvalidTokenFormat"}
        response = client.get("/api/v1/user/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Invalid" in response.json()["detail"]

    def test_get_user_profile_invalid_bearer_scheme(self, client):
        """Test với scheme không phải Bearer"""
        client.headers = {"Authorization": "Basic abc123def456"}
        response = client.get("/api/v1/user/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Invalid authentication scheme"

    def test_get_user_profile_malformed_token(self, client):
        """Test với token bị malformed (không thể decode)"""
        client.headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.get("/api/v1/user/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Could not validate credentials"

    def test_get_user_profile_expired_token(self, client, create_test_user, db_session):
        """Test với token đã hết hạn"""
        from app.core.security import create_access_token

        # Tạo user
        user = create_test_user()

        # Tạo token đã expired
        expired_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(minutes=-10)  # Token đã hết hạn 10 phút trước
        )

        # Lưu token vào database với expiry_date đã qua
        token_record = Token(
            token=expired_token,
            expiry_date=datetime.utcnow() - timedelta(minutes=10),
            user_id=user.id
        )
        db_session.add(token_record)
        db_session.commit()

        client.headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.get("/api/v1/user/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user_profile_token_not_in_database(self, client, create_test_user):
        """Test với token hợp lệ nhưng không có trong database (đã logout)"""
        from app.core.security import create_access_token

        # Tạo user
        user = create_test_user()

        # Tạo token nhưng không lưu vào database (giả lập đã logout)
        valid_token = create_access_token(data={"sub": user.email})

        client.headers = {"Authorization": f"Bearer {valid_token}"}
        response = client.get("/api/v1/user/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Token has been invalidated or expired"

    def test_get_user_profile_user_not_found(self, client, db_session):
        """Test với token hợp lệ nhưng user không tồn tại"""
        from app.core.security import create_access_token

        # Tạo token cho user không tồn tại
        fake_token = create_access_token(data={"sub": "nonexistent@example.com"})

        # Lưu token vào database (giả lập)
        token_record = Token(
            token=fake_token,
            expiry_date=datetime.utcnow() + timedelta(minutes=15),
            user_id=9999  # ID không tồn tại
        )
        db_session.add(token_record)
        db_session.commit()

        client.headers = {"Authorization": f"Bearer {fake_token}"}
        response = client.get("/api/v1/user/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "User not found"

    def test_get_user_profile_empty_authorization_header(self, client):
        """Test với Authorization header trống"""
        client.headers = {"Authorization": ""}
        response = client.get("/api/v1/user/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user_profile_only_bearer_no_token(self, client):
        """Test với chỉ có 'Bearer' mà không có token"""
        client.headers = {"Authorization": "Bearer"}
        response = client.get("/api/v1/user/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_user_profile_multiple_users(self, client, create_test_user, db_session):
        """Test lấy profile với nhiều users, đảm bảo trả về đúng user"""
        from app.core.security import create_access_token

        # Tạo nhiều users
        user1 = create_test_user(email="user1@example.com", name="User 1")
        user2 = create_test_user(email="user2@example.com", name="User 2")

        # Tạo token cho user2
        token = create_access_token(data={"sub": user2.email})
        token_record = Token(
            token=token,
            expiry_date=datetime.utcnow() + timedelta(minutes=15),
            user_id=user2.id
        )
        db_session.add(token_record)
        db_session.commit()

        # Test với token của user2
        client.headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/user/me")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == user2.email
        assert data["name"] == "User 2"
        assert data["id"] == user2.id

    def test_get_user_profile_case_sensitivity(self, client, create_test_user, db_session):
        """Test header Authorization có case-sensitive không"""
        from app.core.security import create_access_token

        user = create_test_user()
        token = create_access_token(data={"sub": user.email})
        token_record = Token(
            token=token,
            expiry_date=datetime.utcnow() + timedelta(minutes=15),
            user_id=user.id
        )
        db_session.add(token_record)
        db_session.commit()

        # Test với lowercase 'bearer'
        client.headers = {"Authorization": f"bearer {token}"}
        response = client.get("/api/v1/user/me")

        # Code có .lower() nên sẽ accept
        assert response.status_code == status.HTTP_200_OK
