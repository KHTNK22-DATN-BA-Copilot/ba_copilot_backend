import pytest
from fastapi import status
from app.models.user import User
from app.models.token import Token
from datetime import datetime, timedelta


class TestDeleteUserMeEndpoint:
    """Test cases cho DELETE /api/v1/user/me endpoint"""

    def test_delete_user_account_success(self, authenticated_client, db_session):
        """Test xóa tài khoản thành công"""
        client, user = authenticated_client
        user_id = user.id
        user_email = user.email

        response = client.delete("/api/v1/user/me")

        # Kiểm tra status code
        assert response.status_code == status.HTTP_200_OK

        # Kiểm tra response message
        data = response.json()
        assert data["message"] == "User account deleted successfully"

        # Kiểm tra user đã bị xóa khỏi database
        deleted_user = db_session.query(User).filter(User.id == user_id).first()
        assert deleted_user is None

        # Kiểm tra tất cả tokens của user đã bị xóa
        user_tokens = db_session.query(Token).filter(Token.user_id == user_id).all()
        assert len(user_tokens) == 0

    def test_delete_user_account_without_token(self, client):
        """Test xóa tài khoản không có Authorization header"""
        response = client.delete("/api/v1/user/me")

        # Kiểm tra trả về 401 Unauthorized
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Authorization header required"

    def test_delete_user_account_invalid_token(self, client):
        """Test xóa tài khoản với token không hợp lệ"""
        client.headers = {"Authorization": "Bearer invalid.token.here"}
        response = client.delete("/api/v1/user/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Could not validate credentials"

    def test_delete_user_account_expired_token(self, client, create_test_user, db_session):
        """Test xóa tài khoản với token đã hết hạn"""
        from app.core.security import create_access_token

        user = create_test_user()

        # Tạo token đã expired
        expired_token = create_access_token(
            data={"sub": user.email},
            expires_delta=timedelta(minutes=-10)
        )

        # Lưu token với expiry_date đã qua
        token_record = Token(
            token=expired_token,
            expiry_date=datetime.utcnow() - timedelta(minutes=10),
            user_id=user.id
        )
        db_session.add(token_record)
        db_session.commit()

        client.headers = {"Authorization": f"Bearer {expired_token}"}
        response = client.delete("/api/v1/user/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_user_removes_all_tokens(self, client, create_test_user, db_session):
        """Test xóa user cũng xóa tất cả tokens của user đó"""
        from app.core.security import create_access_token

        user = create_test_user()

        # Tạo nhiều tokens cho user
        tokens = []
        for i in range(3):
            token = create_access_token(data={"sub": user.email})
            token_record = Token(
                token=token,
                expiry_date=datetime.utcnow() + timedelta(minutes=15),
                user_id=user.id
            )
            db_session.add(token_record)
            tokens.append(token)

        db_session.commit()

        # Verify có 3 tokens
        user_tokens = db_session.query(Token).filter(Token.user_id == user.id).all()
        assert len(user_tokens) == 3

        # Xóa user bằng token đầu tiên
        client.headers = {"Authorization": f"Bearer {tokens[0]}"}
        response = client.delete("/api/v1/user/me")

        assert response.status_code == status.HTTP_200_OK

        # Verify tất cả tokens đã bị xóa
        user_tokens = db_session.query(Token).filter(Token.user_id == user.id).all()
        assert len(user_tokens) == 0

    def test_delete_user_cannot_use_deleted_account(self, authenticated_client, db_session):
        """Test không thể dùng token sau khi đã xóa account"""
        client, user = authenticated_client
        token = client.headers["Authorization"].split()[1]

        # Xóa account
        response = client.delete("/api/v1/user/me")
        assert response.status_code == status.HTTP_200_OK

        # Thử dùng lại token để get profile
        client.headers = {"Authorization": f"Bearer {token}"}
        response = client.get("/api/v1/user/me")

        # Phải trả về 401 vì user đã bị xóa
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_user_with_multiple_users(self, client, create_test_user, db_session):
        """Test xóa 1 user không ảnh hưởng đến users khác"""
        from app.core.security import create_access_token

        # Tạo 2 users
        user1 = create_test_user(email="user1@example.com", name="User 1")
        user2 = create_test_user(email="user2@example.com", name="User 2")

        # Tạo token cho user1
        token1 = create_access_token(data={"sub": user1.email})
        token_record1 = Token(
            token=token1,
            expiry_date=datetime.utcnow() + timedelta(minutes=15),
            user_id=user1.id
        )
        db_session.add(token_record1)
        db_session.commit()

        # Xóa user1
        client.headers = {"Authorization": f"Bearer {token1}"}
        response = client.delete("/api/v1/user/me")
        assert response.status_code == status.HTTP_200_OK

        # Verify user1 đã bị xóa
        deleted_user = db_session.query(User).filter(User.id == user1.id).first()
        assert deleted_user is None

        # Verify user2 vẫn còn
        existing_user = db_session.query(User).filter(User.id == user2.id).first()
        assert existing_user is not None
        assert existing_user.email == user2.email

    def test_delete_user_token_not_in_database(self, client, create_test_user):
        """Test xóa user với token không có trong database"""
        from app.core.security import create_access_token

        user = create_test_user()

        # Tạo token nhưng không lưu vào database
        valid_token = create_access_token(data={"sub": user.email})

        client.headers = {"Authorization": f"Bearer {valid_token}"}
        response = client.delete("/api/v1/user/me")

        # Phải fail vì token không có trong database
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_user_invalid_authorization_format(self, client):
        """Test xóa user với Authorization header format không đúng"""
        client.headers = {"Authorization": "InvalidFormat"}
        response = client.delete("/api/v1/user/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_user_empty_bearer_token(self, client):
        """Test xóa user với Bearer token trống"""
        client.headers = {"Authorization": "Bearer "}
        response = client.delete("/api/v1/user/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_user_wrong_scheme(self, client):
        """Test xóa user với scheme không phải Bearer"""
        client.headers = {"Authorization": "Basic sometoken123"}
        response = client.delete("/api/v1/user/me")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Invalid authentication scheme"

    def test_delete_user_idempotency(self, authenticated_client, db_session):
        """Test xóa user 2 lần liên tiếp"""
        client, user = authenticated_client
        token = client.headers["Authorization"].split()[1]

        # Xóa lần 1
        response = client.delete("/api/v1/user/me")
        assert response.status_code == status.HTTP_200_OK

        # Thử xóa lần 2 với cùng token
        client.headers = {"Authorization": f"Bearer {token}"}
        response = client.delete("/api/v1/user/me")

        # Phải fail vì user và token đã bị xóa
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_delete_user_cascade_tokens(self, client, create_test_user, db_session):
        """Test xóa user cascade xóa luôn tokens (kiểm tra database integrity)"""
        from app.core.security import create_access_token

        user = create_test_user()
        user_id = user.id

        # Tạo token
        token = create_access_token(data={"sub": user.email})
        token_record = Token(
            token=token,
            expiry_date=datetime.utcnow() + timedelta(minutes=15),
            user_id=user.id
        )
        db_session.add(token_record)
        db_session.commit()

        # Verify token tồn tại
        tokens_before = db_session.query(Token).filter(Token.user_id == user_id).count()
        assert tokens_before == 1

        # Xóa user
        client.headers = {"Authorization": f"Bearer {token}"}
        response = client.delete("/api/v1/user/me")
        assert response.status_code == status.HTTP_200_OK

        # Verify tokens cũng bị xóa
        tokens_after = db_session.query(Token).filter(Token.user_id == user_id).count()
        assert tokens_after == 0
