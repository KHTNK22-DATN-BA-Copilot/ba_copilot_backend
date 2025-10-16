"""
Integration test configuration for backend tests.
"""

import pytest
import asyncio
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from app.main import app
from app.core.database import get_db
from app.core.config import settings

# Test database URL - use a separate test database
TEST_DATABASE_URL = "postgresql://postgres:postgres123@localhost:5432/bacopilot_db_test"

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(scope="session")
def test_db():
    """Create test database session."""
    engine = create_engine(TEST_DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

@pytest.fixture(scope="session")
def test_client():
    """Create test client for API testing."""
    
    def override_get_db():
        # For integration tests, we'll use the real database
        # but we should ensure clean state between tests
        pass
    
    # Override database dependency for integration tests
    # app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as client:
        yield client

@pytest.fixture
def test_user_data():
    """Test user data for registration."""
    return {
        "name": "Integration Test User",
        "email": "integration.test@example.com",
        "passwordhash": "IntegrationTestPassword123!"
    }

@pytest.fixture
def test_project_data():
    """Test project data for creation."""
    return {
        "name": "Integration Test Project",
        "description": "A comprehensive e-commerce platform for selling books online with user authentication, shopping cart, payment processing, and inventory management."
    }