### Role
Bạn là một Product Owner, chuyên gia lập trình backend kiêm devops. Skillset chính:
- Docker: Dockerfiles, Docker Compose
- Bảo mật, secure coding
- Ngôn ngữ: Python, FastAPI
- Database: PostgreSQL, SQLAlchemy

### CONTEXT
- Thực hiện build endpoint "/api/v1/auth/register" và endpoint "/api/v1/auth/change-password" với bảng user và token được mô tả trong file @user_schema.md
- Mô tả register thì cần request body giống với schema user
- Request body của endpoint "/api/v1/auth/change-password":
{
    old_password
    new_password
}

### SCOPE
- @bacopilot-be/

### INSTRUCTION
Bước 1: Thực hiện đọc và nghiên cứu **<CONTEXT>** và **<SCOPE>**
Bước 2: Thực hiện triển khai file template.md để mô tả cấu trúc thư mục để triển khai bộ API cho authentication biết service build với mô hình monolith framework sử dụng là FASTAPI và database là POSTGRESQL với các folder như: app, configs, data, docs, logs, tests
Bước 3: Thực hiện đọc và phân tích cấu trúc thư mục @bacopilot-be/template.md đảm bảo có file .env, .env.example và .gitignore
Bước 4: Thực hiện tạo cấu trúc dữ liệu giống với mô tả user table và token table trong file @bacopilot-be/user_schema.md
Bước 5: Thực hiện triển khai 2 endpoint register và change-password user thêm vào folder **<SCOPE>** với response trả về tất cả các trường như mô tả trong file @user_schema.md
Bước 6: Thực hiện bổ sung vào các file Dockerfile, docker-compose.yml để deploy bộ endpoint "register" và "change-password" lên port 8010
Bước 7: Sử dụng các lệnh curl để test toàn bộ endpoint authentication

### NOTE
1. Đảm bảo có file .env chứa những giá trị sensitive info và file .env.example chứa các placeholder về các sensitive info và file .env phải được ignore khi push lên github
2. Không được tạo thêm các file "fixed*", "test*", "*old" hoặc tạo xong phải thực hiện đổi tên ngay và xóa file cũ không đảm bảo optimize code và không dư resource
3. Đảm bảo bảng case được triển khai đúng với mô tả và case service được deploy lên port 8010
4. Đảm bảo tất cả các response trả về từ các request đều chính xác với triển khai của endpoint đó trong phần "authentication"
5. Giải thích những thay đổi đã thực hiện