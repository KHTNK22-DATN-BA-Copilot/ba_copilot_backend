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

### Table: projects
This table stores project information in the system.

| Column                       | Data Type         | Constraints                            | Description                                                                |
|------------------------------|-------------------|----------------------------------------|---------------------------------------------------------------------------|
| id                           | Integer           | Primary Key, Index                     | Primary key, unique identifier for each project.                          |
| user_id                      | Integer           | Foreign Key (users.id), Not Null       | Foreign key referencing the `id` column of the `users` table.             |
| name                         | String(255)       | Not Null                               | Project name (max 255 characters).                                        |
| description                  | Text              | Nullable                               | Project description, can be null if no description exists.                |
| status                       | String(32)        | Not Null                               | Project status (e.g., active, archived).                                  |
| settings                     | JSONB             | Nullable                               | Project settings in JSON format, can be null.                             |
| created_at                   | timestamptz       | Server Default: CURRENT_TIMESTAMP      | Record creation time, automatically set by the server.                    |
| updated_at                   | timestamptz       | Server Default: CURRENT_TIMESTAMP, On Update: CURRENT_TIMESTAMP | Record update time, automatically updated on changes.                     |

**Relationships**:
- The `projects` table has a **many-to-one** relationship with the `users` table via the `user_id` (foreign key) referencing the `id` column of the `users` table.
- The `projects` table has a **one-to-many** relationship with the `documents` table via the `id` (primary key) and `project_id` (foreign key in the `documents` table).

### Table: documents
This table stores document information related to projects.

| Column                       | Data Type         | Constraints                            | Description                                                                |
|------------------------------|-------------------|----------------------------------------|---------------------------------------------------------------------------|
| document_id                  | uuid              | Primary Key, Index                     | Primary key, unique identifier for each document.                         |
| project_id                   | Integer           | Foreign Key (projects.id), Not Null    | Foreign key referencing the `id` column of the `projects` table.          |
| project_name                 | String(255)       | Not Null                               | Name of the project (max 255 characters).                                 |
| content_markdown             | Text              | Not Null                               | Document content in markdown format.                                      |
| status                       | String(32)        | Not Null                               | Document status (e.g., draft, published).                                 |
| document_metadata            | jsonb             | Nullable                               | Metadata of the document in JSON format, can be null.                     |
| version                      | Integer           | Not Null                               | Version number of the document.                                           |
| created_at                   | timestamptz       | Server Default: CURRENT_TIMESTAMP      | Record creation time, automatically set by the server.                    |
| updated_at                   | timestamptz       | Server Default: CURRENT_TIMESTAMP, On Update: CURRENT_TIMESTAMP | Record update time, automatically updated on changes.                     |

**Relationships**:
- The `documents` table has a **many-to-one** relationship with the `projects` table via the `project_id` (foreign key) referencing the `id` column of the `projects` table.

### Table: project_files
This table stores file information related to projects.

| Column                       | Data Type         | Constraints                            | Description                                                                |
|------------------------------|-------------------|----------------------------------------|---------------------------------------------------------------------------|
| id                           | Integer           | Primary Key, Index                     | Primary key, unique identifier for each file.                             |
| file_path                    | String(180)       | Not Null                               | Path to the file (max 180 characters).                                    |
| project_id                   | Integer           | Foreign Key (projects.id), Not Null    | Foreign key referencing the `id` column of the `projects` table.          |
| created_at                   | timestamptz       | Server Default: CURRENT_TIMESTAMP      | Record creation time, automatically set by the server.                    |
| updated_at                   | timestamptz       | Server Default: CURRENT_TIMESTAMP, On Update: CURRENT_TIMESTAMP | Record update time, automatically updated on changes.                     |

**Relationships**:
- The `project_files` table has a **many-to-one** relationship with the `projects` table via the `project_id` (foreign key) referencing the `id` column of the `projects` table.

## Data Dictionary

### Data Conventions
- **String(255)**: Character string with a maximum length of 255, using UTF-8 encoding.
- **String(32)**: Character string with a maximum length of 32, using UTF-8 encoding.
- **String(180)**: Character string with a maximum length of 180, using UTF-8 encoding.
- **Integer**: Integer value, typically used for primary or foreign keys.
- **Boolean**: Logical value (`True` or `False`).
- **DateTime**: Timestamp in ISO 8601 format, may include timezone if needed.
- **timestamptz**: Timestamp with timezone.
- **Text**: Large text field for storing longer content.
- **uuid**: Universally unique identifier.
- **JSONB**: JSON data type for storing structured data.
- **Nullable**: Column can contain `null` if not required.
- **Server Default**: Value automatically set by the server when a record is created.
- **On Update**: Value automatically updated when the record is modified.

### Enum Values
- Currently, no columns use enum values.

### Notes
- When adding new tables or columns, update this document to ensure consistency.
- The `created_at` and `updated_at` columns are automatically managed by the server and do not require manual input.
- The `email_verification_token`, `email_verification_expiration`, `reset_code`, and `reset_code_expiration` columns can be null when no email verification or password reset is in progress.
- The `description` and `settings` columns in the `projects` table can be null if no description or settings are provided.
- The `document_metadata` column in the `documents` table can be null if no metadata is provided.