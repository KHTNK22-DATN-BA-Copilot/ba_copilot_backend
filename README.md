# Project README

## How to Run the Program

### Prerequisites
- Ensure you have [Docker](https://www.docker.com/) installed on your system.
- Git is required to clone the repository.

### Steps to Run
1. **Clone the Repository**  
   Clone the code from the repository using the following command:  
   ```bash
   git clone <repository-link>
   ```

2. **Navigate to the Project Directory**  
   Change to the project directory:  
   ```bash
   cd <project-directory>
   ```

3. **Run with Docker Compose**  
   Start the application using Docker Compose:  
   ```bash
   docker compose up -d
   ```

4. **Access the Application**  
   The application will be available at:  
   ```
   http://localhost:8010
   ```

## Available Endpoints
The application currently supports the following 6 endpoints:

1. **Register**  
   - **Endpoint**: `POST http://localhost:8010/api/v1/auth/register`  
   - **Request Body**:  
     ```json
     {
       "name": "yourName",
       "email": "youremail@gmail.com",
       "passwordhash": "your password"
     }
     ```

2. **Login**  
   - **Endpoint**: `POST http://localhost:8010/api/v1/auth/login`  
   - **Request Body**:  
     ```json
     {
       "email": "youremail@gmail.com",
       "password": "your password"
     }
     ```

3. **Change Password**  
   - **Endpoint**: `POST http://localhost:8010/api/v1/auth/change-password`  
   - **Request Body**:  
     ```json
     {
       "old_password": "12345678",
       "new_password": "23456789"
     }
     ```

4. **Forgot Password**  
   - **Endpoint**: `POST http://localhost:8010/api/v1/auth/forgot-password`  
   - **Request Body**:  
     ```json
     {
       "email": "thuongquanquanhy@gmail.com"
     }
     ```

5. **Verify OTP**  
   - **Endpoint**: `POST http://localhost:8010/api/v1/auth/verify-otp?email=thuongquanquanhy@gmail.com`  
   - **Request Body**:  
     ```json
     {
       "code": "123456"
     }
     ```

6. **Reset Password**  
   - **Endpoint**: `POST http://localhost:8010/api/v1/auth/reset-password?email=thuongquanquanhy@gmail.com`  
   - **Request Body**:  
     ```json
     {
       "new_password": "12345678"
     }
     ```

7. **Verify register email**  
   - **Endpoint**: `POST http://localhost:8010/api/v1/auth/verify-email?email=thuongquanquanhy@gmail.com`  
   - **Request Body**:  
     ```json
     {
       "code": "123456",
     }
     ```