# BE API Specification - BA Copilot User Management Services

This document specifies the REST API endpoints provided by the BA Copilot User Management Service backend. This is part of the Backend Repository in the BA Copilot ecosystem, specifically handling user profile retrieval, updates, and account deletion.

**Repository Context**: This is the **Backend Repository** - one of three repositories:

1. **Frontend Repository**: NextJS + ReactJS + TailwindCSS
2. **Backend Repository** : Core business logic, authentication, and database operations
3. **AI Services Repository**: AI-powered generation services

**Base URL**: `http://localhost:8010/api/user/v1` (Development)  
**API Version**: 1.0  
**Content-Type**: `application/json`

### Headers

```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
Accept: application/json
```

### User Endpoints

#### GET /api/v1/user/me

Retrieve the profile of the currently authenticated user.

**Headers:**

```http
Authorization: Bearer <jwt_token>
```

**Response (200 OK):**

```json
{
  "name": "John Doe",
  "email": "user@example.com",
  "id": 0,
  "email_verified": false,
  "created_at": "2019-08-24T14:15:22Z",
  "updated_at": "2019-08-24T14:15:22Z"
}
```

**Error Responses:**

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

#### PUT /api/v1/user/me

Update the profile of the currently authenticated user.

**Headers:**

```http
Authorization: Bearer <jwt_token>
```

**Request Body:**

```json
{
  "name": "Jane Doe",
  "email": "newuser@example.com"
}
```

**Response (200 OK):**

```json
{
  "name": "Jane Doe",
  "email": "newuser@example.com",
  "id": 0,
  "email_verified": false,
  "created_at": "2019-08-24T14:15:22Z",
  "updated_at": "2025-09-27T12:49:00Z"
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

#### DELETE /api/v1/user/me

Delete the account of the currently authenticated user.

**Headers:**

```http
Authorization: Bearer <jwt_token>
```

**Response (200 OK):**

```json
{
  "message": "User account deleted successfully"
}
```

**Error Responses:**

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