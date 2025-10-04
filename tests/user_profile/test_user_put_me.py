import pytest
from fastapi import status
from datetime import datetime, timedelta
from app.models.user import User
from app.models.token import Token


class TestUpdateUserProfileEndpoint:
    """Test cases cho PUT /api/v1/user/me endpoint"""

    def test_update_profile_success_name_only(self, authenticated_client, db_session):
        """Test cập nhật tên thành công"""
        client, user = authenticated_client

        payload = {"name": "Updated Name"}
        response = client.put("/api/v1/user/me", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Updated Name"
        assert data["email"] == user.email
        assert "updated_at" in data

        # Kiểm tra DB cập nhật thật
        db_user = db_session.query(User).filter(User.id == user.id).first()
        assert db_user.name == "Updated Name"

    def test_update_profile_success_email_and_name(
        self, authenticated_client, db_session
    ):
        """Test cập nhật cả email và name"""
        client, user = authenticated_client

        new_email = "new_email@example.com"
        payload = {"name": "New Name", "email": new_email}
        response = client.put("/api/v1/user/me", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == new_email
        assert data["name"] == "New Name"

        # Kiểm tra DB
        db_user = db_session.query(User).filter(User.id == user.id).first()
        assert db_user.email == new_email
        assert db_user.name == "New Name"

    def test_update_profile_email_already_registered(
        self, authenticated_client, create_test_user, db_session
    ):
        """Test cập nhật email trùng với user khác -> 400"""
        client, user = authenticated_client

        # Tạo user khác với email target
        existing_user = create_test_user(email="existing@example.com")

        payload = {"email": "existing@example.com"}
        response = client.put("/api/v1/user/me", json=payload)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Email already registered"

        # Đảm bảo email user hiện tại chưa bị thay đổi
        db_user = db_session.query(User).filter(User.id == user.id).first()
        assert db_user.email != "existing@example.com"

    def test_update_profile_same_email_should_pass(
        self, authenticated_client, db_session
    ):
        """Test cập nhật lại đúng email hiện tại (không đổi gì) -> 200"""
        client, user = authenticated_client

        payload = {"email": user.email}
        response = client.put("/api/v1/user/me", json=payload)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["email"] == user.email

    def test_update_profile_without_token(self, client):
        """Test cập nhật mà không có Authorization header -> 401"""
        payload = {"name": "No Token User"}
        response = client.put("/api/v1/user/me", json=payload)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Authorization header required"

    def test_update_profile_invalid_token(self, client):
        """Test với token sai định dạng -> 401"""
        headers = {"Authorization": "Bearer invalid.token.value"}
        payload = {"name": "Invalid Token User"}
        response = client.put("/api/v1/user/me", json=payload, headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert "Could not validate credentials" in response.json()["detail"]

    def test_update_profile_expired_token(self, client, create_test_user, db_session):
        """Test với token đã hết hạn -> 401"""
        from app.core.security import create_access_token

        user = create_test_user()
        expired_token = create_access_token(
            data={"sub": user.email}, expires_delta=timedelta(minutes=-5)
        )

        token_record = Token(
            token=expired_token,
            expiry_date=datetime.utcnow() - timedelta(minutes=5),
            user_id=user.id,
        )
        db_session.add(token_record)
        db_session.commit()

        headers = {"Authorization": f"Bearer {expired_token}"}
        payload = {"name": "Expired User"}
        response = client.put("/api/v1/user/me", json=payload, headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_update_profile_token_not_in_database(self, client, create_test_user):
        """Test token hợp lệ nhưng không tồn tại trong DB (đã logout)"""
        from app.core.security import create_access_token

        user = create_test_user()
        valid_token = create_access_token(data={"sub": user.email})

        headers = {"Authorization": f"Bearer {valid_token}"}
        payload = {"name": "Ghost User"}
        response = client.put("/api/v1/user/me", json=payload, headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "Token has been invalidated or expired"

    def test_update_profile_user_not_found(self, client, db_session):
        """Test token hợp lệ nhưng user không tồn tại trong DB"""
        from app.core.security import create_access_token

        fake_token = create_access_token(data={"sub": "nonexistent@example.com"})
        token_record = Token(
            token=fake_token,
            expiry_date=datetime.utcnow() + timedelta(minutes=15),
            user_id=9999,
        )
        db_session.add(token_record)
        db_session.commit()

        headers = {"Authorization": f"Bearer {fake_token}"}
        payload = {"name": "Fake User"}
        response = client.put("/api/v1/user/me", json=payload, headers=headers)

        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        assert response.json()["detail"] == "User not found"

    def test_update_profile_case_insensitive_bearer(
        self, client, create_test_user, db_session
    ):
        """Test header 'bearer' thường thay vì 'Bearer' vẫn hoạt động"""
        from app.core.security import create_access_token

        user = create_test_user()
        token = create_access_token(data={"sub": user.email})
        token_record = Token(
            token=token,
            expiry_date=datetime.utcnow() + timedelta(minutes=15),
            user_id=user.id,
        )
        db_session.add(token_record)
        db_session.commit()

        headers = {"Authorization": f"bearer {token}"}
        payload = {"name": "Lowercase Bearer"}
        response = client.put("/api/v1/user/me", json=payload, headers=headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["name"] == "Lowercase Bearer"
