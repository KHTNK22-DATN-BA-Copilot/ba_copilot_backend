**Base URL**: `http://localhost:8010/api/v1/srs` (Development)  
**API Version**: 1.0  
**Content-Type**: `multipart/form-data`

## Headers

```http
Authorization: Bearer <jwt_token>
Content-Type: multipart/form-data
Accept: application/json
```

## SRS Generation Endpoint

### POST /api/v1/srs/generate

Generate an SRS document by uploading files to Supabase, calling the AI service, and storing the generated document in the database.

**Request Body (multipart/form-data):**

- `project_id` (integer, required): The ID of the project
- `project_name` (string, required): The name of the project
- `description` (string, required): Description of the project
- `files` (file, required): List of files to be uploaded and processed


**Response (200 OK):**

```json
{
  "document_id": "string",
  "user_id": "string",
  "generated_at": "2025-10-12T16:34:00Z",
  "input_description": "string",
  "document": {},
  "status": "generated"
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
      "timestamp": "2025-10-12T16:34:00Z",
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
        "field": "project_id",
        "issue": "Field is required"
      },
      "timestamp": "2025-10-12T16:34:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

- **500 Internal Server Error** (e.g., file upload failure):
  ```json
  {
    "error": {
      "code": "INTERNAL_SERVER_ERROR",
      "message": "Failed to upload file",
      "details": {
        "field": "files",
        "issue": "Failed to upload file example.pdf"
      },
      "timestamp": "2025-10-12T16:34:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

- **502 Bad Gateway** (e.g., AI service unavailable):
  ```json
  {
    "error": {
      "code": "BAD_GATEWAY",
      "message": "AI service unavailable after multiple retries",
      "details": {},
      "timestamp": "2025-10-12T16:34:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

- **500 Internal Server Error** (e.g., invalid AI response):
  ```json
  {
    "error": {
      "code": "INTERNAL_SERVER_ERROR",
      "message": "AI service returned invalid response: missing document",
      "details": {
        "field": "document",
        "issue": "Missing required field in AI response"
      },
      "timestamp": "2025-10-12T16:34:00Z",
      "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
    }
  }
  ```

## Error Handling

### Standard Error Response Format

```json
{
  "error": {
    "code": "string", // e.g., VALIDATION_ERROR, INTERNAL_SERVER_ERROR, BAD_GATEWAY
    "message": "string", // e.g., Invalid input provided
    "details": {
      "field": "string", // e.g., project_id
      "issue": "string" // e.g., Field is required
    },
    "timestamp": "2025-10-12T16:34:00Z",
    "request_id": "req_550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Common HTTP Status Codes

- **200 OK**: Request successful
- **401 Unauthorized**: Authentication required or invalid
- **422 Unprocessable Entity**: Request valid but cannot be processed
- **500 Internal Server Error**: Server error
- **502 Bad Gateway**: AI service unavailable

