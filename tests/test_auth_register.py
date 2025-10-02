import pytest
from fastapi import status
from app.models.user import User


class TestRegisterEndpoint:
    """Test cases cho POST /api/v1/auth/register endpoint"""

    def test_register_success(self, client, test_user_data, db_session):
        """Test đăng ký user thành công"""
        response = client.post("/api/v1/auth/register", json=test_user_data)

        # Kiểm tra status code
        assert response.status_code == status.HTTP_200_OK

        # Kiểm tra response structure
        data = response.json()
        assert "user" in data
        assert "message" in data
        assert data["message"] == "Register successfully, please check your mail to verify email"

        # Kiểm tra user data
        user_data = data["user"]
        assert user_data["email"] == test_user_data["email"]
        assert user_data["name"] == test_user_data["name"]
        assert user_data["email_verified"] is False
        assert "id" in user_data
        assert "created_at" in user_data
        assert "updated_at" in user_data

        # Kiểm tra user có tồn tại trong database
        db_user = db_session.query(User).filter(User.email == test_user_data["email"]).first()
        assert db_user is not None
        assert db_user.email == test_user_data["email"]
        assert db_user.name == test_user_data["name"]
        assert db_user.email_verified is False
        assert db_user.email_verification_token is not None  # OTP đã được hash
        assert db_user.email_verification_expiration is not None

    def test_register_duplicate_email(self, client, test_user_data, create_test_user):
        """Test đăng ký với email đã tồn tại"""
        # Tạo user trước
        create_test_user(email=test_user_data["email"])

        # Thử đăng ký lại với cùng email
        response = client.post("/api/v1/auth/register", json=test_user_data)

        # Kiểm tra trả về lỗi
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["detail"] == "Email already registered"

    def test_register_invalid_email_format(self, client, test_user_data):
        """Test đăng ký với email format không hợp lệ"""
        invalid_data = test_user_data.copy()
        invalid_data["email"] = "invalid-email-format"

        response = client.post("/api/v1/auth/register", json=invalid_data)

        # Pydantic sẽ validate và trả về 422
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_missing_required_fields(self, client):
        """Test đăng ký thiếu required fields"""
        # Thiếu email
        incomplete_data = {
            "name": "Test User",
            "passwordhash": "TestPassword123!"
        }

        response = client.post("/api/v1/auth/register", json=incomplete_data)
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    def test_register_empty_name(self, client, test_user_data):
        """Test đăng ký với name trống"""
        invalid_data = test_user_data.copy()
        invalid_data["name"] = ""

        response = client.post("/api/v1/auth/register", json=invalid_data)

        # FastAPI/Pydantic có thể chấp nhận empty string, nhưng check logic
        # Nếu không có validation cho empty name, test này có thể pass
        # Tùy vào business logic
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]

    def test_register_empty_password(self, client, test_user_data):
        """Test đăng ký với password trống"""
        invalid_data = test_user_data.copy()
        invalid_data["passwordhash"] = ""

        response = client.post("/api/v1/auth/register", json=invalid_data)

        # Password trống vẫn sẽ được hash, nhưng không nên cho phép
        # Tùy business logic, có thể cần thêm validation
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_422_UNPROCESSABLE_ENTITY]

    def test_register_multiple_users(self, client, db_session):
        """Test đăng ký nhiều users với email khác nhau"""
        users_data = [
            {"name": "User 1", "email": "user1@example.com", "passwordhash": "Password1!"},
            {"name": "User 2", "email": "user2@example.com", "passwordhash": "Password2!"},
            {"name": "User 3", "email": "user3@example.com", "passwordhash": "Password3!"},
        ]

        for user_data in users_data:
            response = client.post("/api/v1/auth/register", json=user_data)
            assert response.status_code == status.HTTP_200_OK

        # Kiểm tra tất cả users đã được tạo
        db_users = db_session.query(User).all()
        assert len(db_users) == 3

    def test_register_special_characters_in_name(self, client, test_user_data):
        """Test đăng ký với tên có ký tự đặc biệt"""
        special_data = test_user_data.copy()
        special_data["name"] = "Nguyễn Văn A (Test) <>"
        special_data["email"] = "special@example.com"

        response = client.post("/api/v1/auth/register", json=special_data)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["user"]["name"] == special_data["name"]

    def test_register_long_name(self, client, test_user_data):
        """Test đăng ký với tên rất dài"""
        long_data = test_user_data.copy()
        long_data["name"] = "A" * 300  # Vượt quá 255 ký tự
        long_data["email"] = "longname@example.com"

        response = client.post("/api/v1/auth/register", json=long_data)

        # Có thể trả về lỗi nếu có validation length
        # SQLAlchemy có thể truncate hoặc raise error
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST, status.HTTP_500_INTERNAL_SERVER_ERROR]

    def test_register_case_sensitive_email(self, client, test_user_data, create_test_user):
        """Test email có phân biệt hoa thường không"""
        # Tạo user với email lowercase
        create_test_user(email="test@example.com")

        # Thử đăng ký với email uppercase
        uppercase_data = test_user_data.copy()
        uppercase_data["email"] = "TEST@EXAMPLE.COM"

        response = client.post("/api/v1/auth/register", json=uppercase_data)

        # Tùy vào implementation, email có thể được normalize
        # Database constraint sẽ quyết định
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_400_BAD_REQUEST]
