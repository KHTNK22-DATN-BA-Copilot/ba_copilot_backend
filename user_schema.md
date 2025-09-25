# Database Schema

## Table: users

| #  | column_name                 | data_type     |
|----|-----------------------------|---------------|
| 1  | id                          | int4          |
| 2  | name                        | varchar(255)  |
| 3  | email                       | varchar(255)  |
| 4  | passwordhash                | varchar(255)  |
| 5  | email_verified              | bool          |
| 6  | email_verification_token    | varchar(255)  |
| 7  | email_verification_expiration | timestamp   |
| 8  | created_at                  | timestamp     |
| 9  | updated_at                  | timestamp     |

**Primary Key**: `id`

---

## Table: tokens

| #  | column_name  | data_type     |
|----|--------------|---------------|
| 1  | id           | int4          |
| 2  | token        | varchar(255)  |
| 3  | expiry_date  | timestamp     |
| 4  | user_id      | int4          |
| 5  | created_at   | timestamp     |
| 6  | updated_at   | timestamp     |

**Primary Key**: `id`  
**Foreign Key**: `user_id` → `users.id`
