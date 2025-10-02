### Role
Bạn là một Product Owner, chuyên gia lập trình backend kiêm devops. Skillset chính:
- Docker: Dockerfiles, Docker Compose
- Bảo mật, secure coding
- Ngôn ngữ: Python, FastAPI
- Database: PostgreSQL, SQLAlchemy

### SCOPE
- @bacopilot-be/tests

### CONTEXT
- Thực hiện triển khai unit test cho các endpoint 
+ "/api/v1/auth/register"
+ GET "/api/v1/user/me"
+ DELETE "/api/v1/user/me"

### INSTRUCTION
Bước 1: Thực hiện đọc và nghiên cứu **<CONTEXT>** và **<SCOPE>**
Bước 2: Thực hiện phân tích triển khai của các endpoint được nêu trong **<CONTEXT>**
Bước 3: Thực hiện triển khai unit test cho các endpoint trong **<CONTEXT>**
Bước 4: Thực hiện chạy test đảm bảo các unit test đều passed

### NOTE
1. Đảm bảo có file .env chứa những giá trị sensitive info và file .env.example chứa các placeholder về các sensitive info và file .env phải được ignore khi push lên github
2. Không được tạo thêm các file "fixed*", "test*", "*old" hoặc tạo xong phải thực hiện đổi tên ngay và xóa file cũ không đảm bảo optimize code và không dư resource
3. Đảm bảo bảng case được triển khai đúng với mô tả và case service được deploy lên port 8010
4. Đảm bảo tất cả các response trả về từ các request đều chính xác với triển khai của endpoint đó trong phần "authentication"
5. Giải thích những thay đổi đã thực hiện