# FastAPI Authentication Service - Project Structure

## Overview
Monolithic FastAPI application with PostgreSQL database for authentication services.

## Directory Structure

```
bacopilot-be/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI application entry point
│   ├── models/
│   │   ├── __init__.py
│   │   ├── user.py               # User model
│   │   └── token.py              # Token model
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── user.py               # User Pydantic schemas
│   │   └── auth.py               # Authentication schemas
│   ├── api/
│   │   ├── __init__.py
│   │   └── v1/
│   │       ├── __init__.py
│   │       └── auth.py           # Authentication endpoints
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py             # Application configuration
│   │   ├── security.py           # Password hashing, JWT utilities
│   │   └── database.py           # Database connection
│   └── utils/
│       ├── __init__.py
│       └── helpers.py            # Utility functions
├── configs/
│   └── database.conf             # Database configuration
├── data/
│   └── migrations/               # Database migration files
├── docs/
│   └── api.md                    # API documentation
├── logs/
│   └── app.log                   # Application logs
├── tests/
│   ├── __init__.py
│   ├── test_auth.py              # Authentication tests
│   └── conftest.py               # Test configuration
├── .env                          # Environment variables (sensitive)
├── .env.example                  # Environment variables template
├── .gitignore                    # Git ignore rules
├── Dockerfile                    # Docker container definition
├── docker-compose.yml            # Docker compose configuration
├── requirements.txt              # Python dependencies
└── README.md                     # Project documentation
```

## Key Components

### Application Layer (`app/`)
- **main.py**: FastAPI application factory and route registration
- **models/**: SQLAlchemy database models
- **schemas/**: Pydantic models for request/response validation
- **api/**: REST API endpoints organized by version
- **core/**: Core application utilities (config, security, database)
- **utils/**: Helper functions and utilities

### Configuration (`configs/`)
- Database and application configuration files

### Data Layer (`data/`)
- Database migrations and data-related scripts

### Documentation (`docs/`)
- API documentation and project documentation

### Logging (`logs/`)
- Application log files

### Testing (`tests/`)
- Unit and integration tests

## Environment Files
- **.env**: Contains sensitive environment variables (database credentials, secret keys)
- **.env.example**: Template with placeholder values for environment variables
- **.gitignore**: Ensures .env and other sensitive files are not committed

## Deployment
- **Dockerfile**: Container definition for the FastAPI application
- **docker-compose.yml**: Multi-container setup with PostgreSQL database
- **Port**: Application runs on port 8010

## Authentication Endpoints
- `POST /api/v1/auth/register`: User registration
- `POST /api/v1/auth/change-password`: Password change for authenticated users