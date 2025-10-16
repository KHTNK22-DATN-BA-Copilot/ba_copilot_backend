"""
Integration test configuration for backend tests.

This configuration is specifically for integration tests that run against
the full Docker stack (backend, AI service, and database).
"""

import pytest
import asyncio
import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.core.config import settings

# Test database URL - use the actual Docker database
# For integration tests, we use the real database from docker-compose
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://postgres:postgres123@localhost:5432/bacopilot_db"
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def test_db_engine():
    """Create database engine for integration testing."""
    engine = create_engine(DATABASE_URL)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def cleanup_test_database(test_db_engine):
    """
    Clean up test data before and after each test.
    
    This ensures a clean state for integration tests by removing
    test users and their associated data.
    """
    def _cleanup():
        with test_db_engine.connect() as conn:
            # Delete test users and cascading relations
            conn.execute(text("DELETE FROM users WHERE email LIKE '%integration_test%'"))
            conn.execute(text("DELETE FROM users WHERE email LIKE '%fullstack_test%'"))
            conn.execute(text("DELETE FROM users WHERE email LIKE '%test@example.com%'"))
            conn.commit()
    
    # Cleanup before test
    _cleanup()
    
    yield
    
    # Cleanup after test
    _cleanup()


@pytest.fixture(scope="session")
def test_client():
    """
    Create test client for API testing.
    
    For integration tests, we connect to the real backend service
    which in turn connects to the real AI service and database.
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture
def test_user_data():
    """
    Test user data for registration.
    
    Note: For unique users per test, use unique_test_user_data fixture
    from the test file instead.
    """
    timestamp = int(time.time() * 1000)
    return {
        "name": f"Integration Test User {timestamp}",
        "email": f"integration.test.{timestamp}@example.com",
        "passwordhash": "IntegrationTestPassword123!"
    }


@pytest.fixture
def test_project_data():
    """
    Test project data for creation.
    
    Note: For unique projects per test, use unique_test_project_data fixture
    from the test file instead.
    """
    timestamp = int(time.time() * 1000)
    return {
        "name": f"Integration Test Project {timestamp}",
        "description": "A comprehensive e-commerce platform for selling books online with user authentication, shopping cart, payment processing, and inventory management."
    }