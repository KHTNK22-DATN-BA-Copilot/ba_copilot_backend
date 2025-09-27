# BE API Specification - BA Copilot Authentication Services

This document specifies the REST API endpoints provided by the BA Copilot Authentication Service backend. This is one of three repositories in the BA Copilot ecosystem, specifically handling user authentication and account management.

**Repository Context**: This is the **Backend Repository** - one of three repositories:

1. **Frontend Repository**: NextJS + ReactJS + TailwindCSS
2. **Backend Repository** : Core business logic, authentication, and database operations
3. **AI Services Repository**: AI-powered generation services

**Base URL**: `http://localhost:8010/api/auth/v1` (Development)  
**API Version**: 1.0  
**Content-Type**: `application/json`

### Headers

```http
Authorization: Bearer
Content-Type: application/json
Accept: application/json
```

### Authentication Endpoints

#### POST /api/v1/auth/register

Register a new user account.

**Request Body:**

```json
{
  "name": "John Doe",
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200 Successful Response):**

```json
{
  "user": {
    "name": "string",
    "email": "user@example.com",
    "id": 0,
    "email_verified": false,
    "email_verification_token": "string",
    "email_verification_expiration": "2019-08-24T14:15:22Z",
    "created_at": "2019-08-24T14:15:22Z",
    "updated_at": "2019-08-24T14:15:22Z"
  },
  "message": "Register successfully, please check your mail to verify email"
}
```

**Error Responses:**

- **400 Bad Request**:
  ```json
  {
    "error": {
      "code": "BAD_REQUEST",
      "message": "Email already registered",
      "details": {
        "field": "email",
        "issue": "Email already registered"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **422 Unprocessable Entity**:
  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid input provided",
      "details": {
        "field": "email",
        "issue": "Invalid email format"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **500 Internal Server Error**:
  ```json
  {
    "error": {
      "code": "INTERNAL_SERVER_ERROR",
      "message": "An unexpected error occurred",
      "details": {},
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

#### POST /api/v1/auth/verify-email

Verify user email using OTP.

**Query Parameters:**

- `email` (string, required): User’s email address

**Request Body:**

```json
{
  "code": "123456"
}
```

**Response (200 OK):**

```json
{
  "message": "Email verified successfully"
}
```

**Error Responses:**

- **400 Bad Request**:
  ```json
  {
    "error": {
      "code": "BAD_REQUEST",
      "message": "Invalid or expired OTP",
      "details": {
        "field": "code",
        "issue": "OTP code is incorrect or expired"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **422 Unprocessable Entity**:
  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid input provided",
      "details": {
        "field": "email",
        "issue": "Invalid email format"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **500 Internal Server Error**:
  ```json
  {
    "error": {
      "code": "INTERNAL_SERVER_ERROR",
      "message": "An unexpected error occurred",
      "details": {},
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

#### POST /api/v1/auth/change-password

Change user password.

**Headers:**

```http
Authorization: Bearer <jwt_token>
```

**Request Body:**

```json
{
  "old_password": "OldPassword123!",
  "new_password": "NewPassword456!"
}
```

**Response (200 OK):**

```json
{
  "message": "Password changed successfully"
}
```

**Error Responses:**

- **400 Bad Request**:
  ```json
  {
    "error": {
      "code": "BAD_REQUEST",
      "message": "Incorrect old password",
      "details": {
        "field": "old_password",
        "issue": "Incorrect old password"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **401 Unauthorized**:
  ```json
  {
    "error": {
      "code": "UNAUTHORIZED",
      "message": "Authorization header required",
      "details": {
        "field": "authorization",
        "issue": "Invalid or missing JWT token"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **422 Unprocessable Entity**:
  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid input provided",
      "details": {
        "field": "new_password",
        "issue": "Password does not meet requirements"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **500 Internal Server Error**:
  ```json
  {
    "error": {
      "code": "INTERNAL_SERVER_ERROR",
      "message": "An unexpected error occurred",
      "details": {},
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

#### POST /api/v1/auth/forgot-password

Initiate password reset process.

**Request Body:**

```json
{
  "email": "user@example.com"
}
```

**Response (200 OK):**

```json
{
  "message": "Reset code has been sent to your email"
}
```

**Error Responses:**

- **400 Bad Request**:
  ```json
  {
    "error": {
      "code": "BAD_REQUEST",
      "message": "Email not found",
      "details": {
        "field": "email",
        "issue": "No user associated with this email"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **422 Unprocessable Entity**:
  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid input provided",
      "details": {
        "field": "email",
        "issue": "Invalid email format"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **500 Internal Server Error**:
  ```json
  {
    "error": {
      "code": "INTERNAL_SERVER_ERROR",
      "message": "An unexpected error occurred",
      "details": {},
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

#### POST /api/v1/auth/verify-otp

Verify OTP for password reset.

**Query Parameters:**

- `email` (string, required): User’s email address

**Request Body:**

```json
{
  "code": "123456"
}
```

**Response (200 OK):**

```json
{
  "message": "OTP verified successfully"
}
```

**Error Responses:**

- **400 Bad Request**:
  ```json
  {
    "error": {
      "code": "BAD_REQUEST",
      "message": "Invalid or expired OTP",
      "details": {
        "field": "code",
        "issue": "OTP code is incorrect or expired"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **422 Unprocessable Entity**:
  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid input provided",
      "details": {
        "field": "email",
        "issue": "Invalid email format"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **500 Internal Server Error**:
  ```json
  {
    "error": {
      "code": "INTERNAL_SERVER_ERROR",
      "message": "An unexpected error occurred",
      "details": {},
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

#### POST /api/v1/auth/reset-password

Reset user password using OTP.

**Query Parameters:**

- `email` (string, required): User’s email address

**Request Body:**

```json
{
  "new_password": "NewPassword456!"
}
```

**Response (200 OK):**

```json
{
  "message": "Password reset successfully"
}
```

**Error Responses:**

- **400 Bad Request**:
  ```json
  {
    "error": {
      "code": "BAD_REQUEST",
      "message": "User not found",
      "details": {
        "field": "email",
        "issue": "No user found"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **422 Unprocessable Entity**:
  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid input provided",
      "details": {
        "field": "new_password",
        "issue": "Password does not meet requirements"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **500 Internal Server Error**:
  ```json
  {
    "error": {
      "code": "INTERNAL_SERVER_ERROR",
      "message": "An unexpected error occurred",
      "details": {},
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

#### POST /api/v1/auth/login

Authenticate user and receive access token.

**Request Body:**

```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Response (200 OK):**

```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses:**

- **401 Unauthorized**:
  ```json
  {
    "error": {
      "code": "UNAUTHORIZED",
      "message": "Incorrect email or password",
      "details": {
        "field": "email",
        "issue": "Incorrect email or password"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **422 Unprocessable Entity**:
  ```json
  {
    "error": {
      "code": "VALIDATION_ERROR",
      "message": "Invalid input provided",
      "details": {
        "field": "email",
        "issue": "Invalid email format"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **500 Internal Server Error**:
  ```json
  {
    "error": {
      "code": "INTERNAL_SERVER_ERROR",
      "message": "An unexpected error occurred",
      "details": {},
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

## Health Check

### GET /health

Get service health status.

**Response (200 OK):**

```json
{
  "status": "healthy",
  "timestamp": "2025-09-20T14:30:00Z",
  "version": "1.0.0",
  "services": {
    "database": "healthy",
    "llm_providers": {
      "openai": "healthy",
      "claude": "healthy"
    },
    "file_storage": "healthy",
    "diagram_renderer": "healthy"
  },
  "uptime_seconds": 86400
}
```

**Error Responses:**

- **500 Internal Server Error**:
  ```json
  {
    "error": {
      "code": "INTERNAL_SERVER_ERROR",
      "message": "Service health check failed",
      "details": {
        "service": "database",
        "issue": "Database connection error"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **503 Service Unavailable**:
  ```json
  {
    "error": {
      "code": "SERVICE_UNAVAILABLE",
      "message": "Service temporarily unavailable",
      "details": {
        "service": "api",
        "issue": "Server maintenance in progress"
      },
      "timestamp": "2025-09-27T12:49:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

## Error Handling

### Standard Error Response Format

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input provided",
    "details": {
      "field": "email",
      "issue": "Invalid email format"
    },
    "timestamp": "2025-09-27T12:49:00Z",
    "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Common HTTP Status Codes

- **200 OK**: Request successful
- **201 Created**: Resource created successfully
- **204 No Content**: Request successful, no content returned
- **400 Bad Request**: Invalid request parameters
- **401 Unauthorized**: Authentication required or invalid
- **403 Forbidden**: Access denied to resource
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Request valid but cannot be processed
- **500 Internal Server Error**: Server error
- **503 Service Unavailable**: Service temporarily unavailable

## Development Setup

### Running the API Locally

1. **Start the development server:**

   ```bash
   docker compose up -d
   ```

2. **Access API documentation:**

   - Swagger UI: http://localhost:8010/docs
   - ReDoc: http://localhost:8010/redoc

### Environment Variables

Required environment variables for local development: env.example
