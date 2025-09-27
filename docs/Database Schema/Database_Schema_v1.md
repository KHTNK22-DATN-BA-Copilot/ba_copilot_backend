# Database Schema & Data Dictionary

## Purpose
This document outlines the tables, columns, data types, constraints, and relationships between tables in the database.  
The data dictionary explains the meaning of each column, data conventions, enum values (if any), and default values.  
It aims to help developers (backend, frontend) and QA understand the database structure for development and testing.

## Schema Description

### Table: users
This table stores user information in the system.

| Column                       | Data Type         | Constraints                            | Description                                                                |
|------------------------------|-------------------|----------------------------------------|---------------------------------------------------------------------------|
| id                           | Integer           | Primary Key, Index                     | Primary key, unique identifier for each user.                             |
| name                         | String(255)       | Not Null                               | User's name (max 255 characters).                                         |
| email                        | String(255)       | Unique, Index, Not Null                | User's email address, unique across the system.                           |
| passwordhash                 | String(255)       | Not Null                               | Hashed password of the user.                                              |
| email_verified               | Boolean           | Default: False                         | Email verification status (True: verified, False: not verified).          |
| email_verification_token     | String(255)       | Nullable                               | Token for email verification, can be null if no token exists.             |
| email_verification_expiration| DateTime          | Nullable                               | Expiration time of the email verification token, can be null.             |
| reset_code                   | String(255)       | Nullable                               | Code for password reset, can be null if no reset request exists.          |
| reset_code_expiration        | DateTime          | Nullable                               | Expiration time of the password reset code, can be null.                  |
| created_at                   | DateTime          | Server Default: CURRENT_TIMESTAMP      | Record creation time, automatically set by the server.                    |
| updated_at                   | DateTime          | Server Default: CURRENT_TIMESTAMP, On Update: CURRENT_TIMESTAMP | Record update time, automatically updated on changes.                     |

**Relationships**:
- The `users` table has a **one-to-many** relationship with the `tokens` table via the `id` (primary key) and `user_id` (foreign key in the `tokens` table).

### Table: tokens
This table stores token information related to users (e.g., authentication tokens, refresh tokens).

| Column                       | Data Type         | Constraints                            | Description                                                                |
|------------------------------|-------------------|----------------------------------------|---------------------------------------------------------------------------|
| id                           | Integer           | Primary Key, Index                     | Primary key, unique identifier for each token.                            |
| token                        | String(255)       | Not Null                               | Token value (max 255 characters).                                         |
| expiry_date                  | DateTime          | Not Null                               | Token expiration time.                                                    |
| user_id                      | Integer           | Foreign Key (users.id), Not Null       | Foreign key referencing the `id` column of the `users` table.             |
| created_at                   | DateTime          | Server Default: CURRENT_TIMESTAMP      | Record creation time, automatically set by the server.                    |
| updated_at                   | DateTime          | Server Default: CURRENT_TIMESTAMP, On Update: CURRENT_TIMESTAMP | Record update time, automatically updated on changes.                     |

**Relationships**:
- The `tokens` table has a **many-to-one** relationship with the `users` table via the `user_id` (foreign key) referencing the `id` column of the `users` table.

## Data Dictionary

### Data Conventions
- **String(255)**: Character string with a maximum length of 255, using UTF-8 encoding.
- **Integer**: Integer value, typically used for primary or foreign keys.
- **Boolean**: Logical value (`True` or `False`).
- **DateTime**: Timestamp in ISO 8601 format, may include timezone if needed.
- **Nullable**: Column can contain `null` if not required.
- **Server Default**: Value automatically set by the server when a record is created.
- **On Update**: Value automatically updated when the record is modified.

### Enum Values
- Currently, no columns use enum values.

### Notes
- When adding new tables or columns, update this document to ensure consistency.
- The `created_at` and `updated_at` columns are automatically managed by the server and do not require manual input.
- The `email_verification_token`, `email_verification_expiration`, `reset_code`, and `reset_code_expiration` columns can be null when no email verification or password reset is in progress.