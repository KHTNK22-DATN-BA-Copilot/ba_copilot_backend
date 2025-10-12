
**Base URL**: `http://localhost:8010/api/v1/projects`
**API Version**: 1.0  
**Content-Type**: `application/json`

## Headers

```http
Authorization: Bearer <jwt_token>
Content-Type: application/json
Accept: application/json
```

## Project Management Endpoints

### POST /api/v1/projects/

Create a new project for the authenticated user.

**Request Body:**

```json
{
  "name": "string",
  "description": "string",
  "status": "string", // Optional, defaults to "active"
  "settings": {} // Optional, defaults to {}
}
```

**Response (200 OK):**

```json
{
  "id": 0,
  "user_id": 0,
  "name": "string",
  "description": "string",
  "status": "string",
  "settings": {},
  "created_at": "2025-10-12T16:25:00Z",
  "updated_at": "2025-10-12T16:25:00Z"
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
      "timestamp": "2025-10-12T16:25:00Z",
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
        "field": "name",
        "issue": "Field is required"
      },
      "timestamp": "2025-10-12T16:25:00Z",
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
      "timestamp": "2025-10-12T16:25:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

### GET /api/v1/projects/

Retrieve a list of projects for the authenticated user (excludes deleted projects).

**Response (200 OK):**

```json
{
  "projects": [
    {
      "id": 0,
      "user_id": 0,
      "name": "string",
      "description": "string",
      "status": "string",
      "settings": {},
      "created_at": "2025-10-12T16:25:00Z",
      "updated_at": "2025-10-12T16:25:00Z"
    }
  ]
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
      "timestamp": "2025-10-12T16:25:00Z",
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
      "timestamp": "2025-10-12T16:25:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

### GET /api/v1/projects/{project_id}

Retrieve details of a specific project by ID for the authenticated user (excludes deleted projects).

**Path Parameters:**

- `project_id` (integer, required): The ID of the project

**Response (200 OK):**

```json
{
  "id": 0,
  "user_id": 0,
  "name": "string",
  "description": "string",
  "status": "string",
  "settings": {},
  "created_at": "2025-10-12T16:25:00Z",
  "updated_at": "2025-10-12T16:25:00Z"
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
      "timestamp": "2025-10-12T16:25:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **404 Not Found**:
  ```json
  {
    "error": {
      "code": "NOT_FOUND",
      "message": "Project not found",
      "details": {
        "field": "project_id",
        "issue": "Project not found"
      },
      "timestamp": "2025-10-12T16:25:00Z",
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
      "timestamp": "2025-10-12T16:25:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

### PUT /api/v1/projects/{project_id}

Update an existing project for the authenticated user.

**Path Parameters:**

- `project_id` (integer, required): The ID of the project

**Request Body:**

```json
{
  "name": "string",
  "description": "string",
  "status": "string",
  "settings": {}
}
```

**Response (200 OK):**

```json
{
  "id": 0,
  "message": "Project updated successfully"
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
      "timestamp": "2025-10-12T16:25:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **404 Not Found**:
  ```json
  {
    "error": {
      "code": "NOT_FOUND",
      "message": "Project not found",
      "details": {
        "field": "project_id",
        "issue": "Project not found"
      },
      "timestamp": "2025-10-12T16:25:00Z",
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
        "field": "name",
        "issue": "Field is required"
      },
      "timestamp": "2025-10-12T16:25:00Z",
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
      "timestamp": "2025-10-12T16:25:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

### DELETE /api/v1/projects/{project_id}

Soft delete a project for the authenticated user by setting its status to "deleted".

**Path Parameters:**

- `project_id` (integer, required): The ID of the project

**Response (200 OK):**

```json
{
  "message": "Project deleted successfully"
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
      "timestamp": "2025-10-12T16:25:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```
- **404 Not Found**:
  ```json
  {
    "error": {
      "code": "NOT_FOUND",
      "message": "Project not found",
      "details": {
        "field": "project_id",
        "issue": "Project not found"
      },
      "timestamp": "2025-10-12T16:25:00Z",
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
      "timestamp": "2025-10-12T16:25:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

## Error Handling

### Standard Error Response Format

```json
{
  "error": {
    "code": "string", // e.g., VALIDATION_ERROR, NOT_FOUND, UNAUTHORIZED
    "message": "string", // e.g., Invalid input provided
    "details": {
      "field": "string", // e.g., project_id
      "issue": "string" // e.g., Project not found
    },
    "timestamp": "2025-10-12T16:25:00Z",
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
- **404 Not Found**: Resource not found
- **422 Unprocessable Entity**: Request valid but cannot be processed
- **500 Internal Server Error**: Server error

