# BA Copilot Backend

Backend service for the BA Copilot application, providing REST API endpoints for authentication, project management, and SRS document generation.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start with Docker](#quick-start-with-docker)
- [Running Integration Tests](#running-integration-tests)
- [Architecture](#architecture)
- [Available Endpoints](#available-endpoints)
- [Development](#development)

## Prerequisites

- [Docker](https://www.docker.com/) and Docker Compose
- Git

## Quick Start with Docker

The BA Copilot stack includes three main services:

- **PostgreSQL**: Database
- **Backend**: This service (FastAPI)
- **AI Service**: AI-powered SRS generation

### 1. Clone the Repository

```bash
git clone <repository-link>
cd <project-directory>
```

### 2. Start the Complete Stack

From the **root project directory**, run:

```powershell
# Stop and remove existing containers (if any)
docker-compose down -v

# Build and start all services
docker-compose up -d --build
```

This will start:

- **PostgreSQL** on `localhost:5432`
- **Backend** on `localhost:8010`
- **AI Service** on `localhost:8000`

### 3. Verify Services are Healthy

```powershell
# Check service status
docker-compose ps

# All services should show "healthy" status
# Wait 30-60 seconds for all health checks to pass
```

### 4. Access the Application

- **Backend API**: http://localhost:8010
- **API Documentation**: http://localhost:8010/docs
- **Health Check**: http://localhost:8010/health

## Running Integration Tests

The project includes comprehensive integration tests that verify the complete workflow from user registration to AI-powered SRS document generation.

### Prerequisites for Testing

1. **Ensure Docker Stack is Running**:

   ```powershell
   docker-compose ps
   # All services should be "healthy"
   ```

2. **Install Python Dependencies** (if running tests from host):
   ```powershell
   cd ba_copilot_backend
   pip install -r requirements.txt
   pip install requests  # For integration tests
   ```

### Running the Integration Test Suite

```powershell
cd ba_copilot_backend
.\.venv\Scripts\Activate.ps1
python tests/integration/test_full_stack.py
```

This test script verifies:

- ✅ Backend and AI services are healthy
- ✅ User registration and login
- ✅ Project creation
- ✅ SRS document generation via AI service
- ✅ AI service returns non-fallback responses (real OpenRouter AI)
- ✅ Data persistence in database

**Expected Output:**

```
[INFO] ================================================================================
[INFO] ✅ FULL STACK INTEGRATION TEST PASSED!
[INFO] ================================================================================
[INFO] Summary:
[INFO]   - User Registration: ✅
[INFO]   - User Login: ✅
[INFO]   - User Profile: ✅
[INFO]   - Project Creation: ✅
[INFO]   - SRS Generation: ✅
[INFO]   - AI Service (Non-Fallback): ✅ (Provider: ...)
[INFO]   - Document Structure: ✅
[INFO] ================================================================================

[INFO]
The SRS documents received:
{...}
```

### Test AI Service Directly

To verify the AI service is working independently:

```powershell
cd ba_copilot_ai
./.venv/Scripts/Activate.ps1
python tests/test_srs_ai_direct.py
```

This should return a properly formatted SRS document with OpenRouter as the provider.

## Architecture

### Service Communication

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│   Client    │────────▶│   Backend    │────────▶│ AI Service  │
│             │         │   (FastAPI)  │         │  (FastAPI)  │
└─────────────┘         └──────────────┘         └─────────────┘
                               │                        │
                               │                        │
                               ▼                        ▼
                        ┌──────────────┐        ┌─────────────┐
                        │  PostgreSQL  │        │  OpenRouter │
                        │   Database   │        │     API     │
                        └──────────────┘        └─────────────┘
```

### Docker Networking

Services communicate via Docker's internal network:

- Backend → AI: `http://ai:8000`
- Backend → Database: `postgres:5432`
- AI → Database: `postgres:5432`

### Health Checks

All services implement health checks:

- **PostgreSQL**: `pg_isready` check every 5s
- **Backend**: HTTP check at `/health` every 10s
- **AI Service**: HTTP check at `/v1/health/` every 10s

Services wait for dependencies to be healthy before starting.

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
       "code": "123456"
     }
     ```

## Development

### Environment Variables

Required environment variables for the backend service:

```env
# Database Configuration
DATABASE_URL=postgresql://user:password@postgres:5432/dbname

# JWT Configuration
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# AI Service Configuration
AI_SERVICE_URL=http://ai:8000

# CORS Configuration
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:8010
```

### Local Development (without Docker)

1. **Set up Python Virtual Environment**:

   ```powershell
   cd ba_copilot_backend
   python -m venv venv
   .\venv\Scripts\activate
   ```

2. **Install Dependencies**:

   ```powershell
   pip install -r requirements.txt
   ```

3. **Run PostgreSQL** (via Docker or local installation)

4. **Start the Backend**:
   ```powershell
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8010
   ```

### Running Tests

```powershell
# Unit tests
pytest tests/unit -v

# Integration tests (requires running Docker stack)
pytest tests/integration -v

# With coverage
pytest --cov=app --cov-report=html
```

### Viewing Logs

```powershell
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f ai
docker-compose logs -f postgres
```

---

**Built with ❤️ by the BA Backend Team**
