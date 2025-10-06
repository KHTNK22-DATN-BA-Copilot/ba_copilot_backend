# Unit Tests Documentation

## Tổng quan

Thư mục này chứa các unit tests cho backend API của BACopilot. Tests được viết bằng pytest và sử dụng SQLite in-memory database để testing.

## Cấu trúc Tests

```
tests/
├── __init__.py
├── conftest.py                 # Test fixtures và setup
├── test_auth_register.py       # Tests cho POST /api/v1/auth/register
├── test_user_get_me.py        # Tests cho GET /api/v1/user/me
└── test_user_delete_me.py     # Tests cho DELETE /api/v1/user/me
```

## Các Endpoint được Test

### 1. POST /api/v1/auth/register
- ✅ Đăng ký user thành công
- ✅ Email đã tồn tại
- ✅ Email format không hợp lệ
- ✅ Thiếu required fields
- ✅ Name/password trống
- ✅ Đăng ký nhiều users
- ✅ Tên có ký tự đặc biệt
- ✅ Tên quá dài
- ✅ Email case sensitivity

### 2. GET /api/v1/user/me
- ✅ Lấy profile thành công với token hợp lệ
- ✅ Không có Authorization header
- ✅ Token format không hợp lệ
- ✅ Bearer scheme không đúng
- ✅ Token bị malformed
- ✅ Token đã hết hạn
- ✅ Token không có trong database
- ✅ User không tồn tại
- ✅ Authorization header trống
- ✅ Chỉ có Bearer không có token
- ✅ Multiple users test
- ✅ Case sensitivity test

### 3. DELETE /api/v1/user/me
- ✅ Xóa account thành công
- ✅ Không có token
- ✅ Token không hợp lệ
- ✅ Token đã hết hạn
- ✅ Xóa user cascade xóa tất cả tokens
- ✅ Không thể dùng lại account đã xóa
- ✅ Xóa 1 user không ảnh hưởng users khác
- ✅ Token không có trong database
- ✅ Authorization format không đúng
- ✅ Bearer token trống
- ✅ Scheme không phải Bearer
- ✅ Idempotency test
- ✅ Database integrity test

## Cài đặt Dependencies

### Cách 1: Sử dụng pip (Local)
```bash
pip install -r requirements.txt
```

### Cách 2: Sử dụng Docker (Khuyến nghị)
Dependencies đã được cài trong Docker image khi build.

## Chạy Tests

### Cách 1: Chạy trong Docker Container (Khuyến nghị)

1. Start Docker containers:
```bash
docker-compose up -d
```

2. Chạy tất cả tests:
```bash
docker-compose exec app pytest tests/ -v
```

3. Hoặc sử dụng script đã tạo sẵn:
```bash
./run_tests.sh
```

4. Chạy test cho từng endpoint cụ thể:
```bash
# Test register endpoint
docker-compose exec app pytest tests/test_auth_register.py -v

# Test GET user/me endpoint
docker-compose exec app pytest tests/test_user_get_me.py -v

# Test DELETE user/me endpoint
docker-compose exec app pytest tests/test_user_delete_me.py -v
```

5. Chạy test với coverage:
```bash
docker-compose exec app pytest tests/ --cov=app --cov-report=html
```

### Cách 2: Chạy Local (Nếu có Python environment)

```bash
# Chạy tất cả tests
pytest tests/ -v

# Chạy test cụ thể
pytest tests/test_auth_register.py -v

# Chạy test với coverage
pytest tests/ --cov=app --cov-report=html
```

## Test Fixtures

### db_session
Tạo SQLite in-memory database session mới cho mỗi test. Database được tạo và xóa tự động sau mỗi test.

### client
TestClient của FastAPI với database session override.

### test_user_data
Dữ liệu user mẫu để testing:
```python
{
    "name": "Test User",
    "email": "testuser@example.com",
    "passwordhash": "TestPassword123!"
}
```

### create_test_user
Factory fixture để tạo user trong database với các parameters tùy chỉnh.

### authenticated_client
Test client đã được authenticated với Bearer token hợp lệ, trả về tuple (client, user).

## Lưu ý

1. **Test Isolation**: Mỗi test chạy trong database session riêng biệt, đảm bảo không có side effects giữa các tests.

2. **In-Memory Database**: Tests sử dụng SQLite in-memory nên rất nhanh và không ảnh hưởng đến PostgreSQL production database.

3. **Mocking Email**: Tests không thực sự gửi email. Email sending functions được mock hoặc bỏ qua trong test environment.

4. **Token Management**: Tests kiểm tra cả việc tạo, validate và xóa tokens trong database.

5. **Error Cases**: Tests cover cả happy path và error cases để đảm bảo API hoạt động đúng trong mọi tình huống.

## Kết quả Expected

Tất cả tests phải PASS:
```
tests/test_auth_register.py::TestRegisterEndpoint::test_register_success PASSED
tests/test_auth_register.py::TestRegisterEndpoint::test_register_duplicate_email PASSED
...
tests/test_user_delete_me.py::TestDeleteUserMeEndpoint::test_delete_user_cascade_tokens PASSED

========================= XX passed in X.XXs =========================
```

## Troubleshooting

### Lỗi: ModuleNotFoundError
- Đảm bảo đã cài đặt tất cả dependencies trong requirements.txt
- Chạy: `pip install -r requirements.txt`

### Lỗi: Database connection
- Nếu chạy local, đảm bảo không cần connect PostgreSQL (tests dùng SQLite)
- Nếu chạy trong Docker, đảm bảo containers đang chạy: `docker-compose ps`

### Lỗi: Import errors
- Đảm bảo PYTHONPATH đã được set đúng
- Trong Docker, điều này đã được handle tự động
