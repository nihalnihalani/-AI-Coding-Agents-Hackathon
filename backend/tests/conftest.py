import pytest
import asyncio
import os
import tempfile
from typing import AsyncGenerator, Generator
from fastapi.testclient import TestClient
from httpx import AsyncClient
import redis

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["REDIS_URL"] = "redis://localhost:6379/1"  # Use DB 1 for tests
os.environ["JWT_SECRET_KEY"] = "test-secret-key-for-testing-only"

from app.core.config import settings
from app.core.auth import auth_service
from app.services.state_service import state_service
from app.services.notification_service import notification_service
from app.services.websocket_manager import websocket_manager

# Import main app after setting environment
from app import app


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def client() -> Generator[TestClient, None, None]:
    """Create a test client for the FastAPI app."""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


@pytest.fixture(scope="function")
async def clean_redis():
    """Clean Redis database before each test."""
    try:
        if state_service.is_available():
            # Clear test database
            test_keys = state_service.redis_client.keys("aura:*")
            if test_keys:
                state_service.redis_client.delete(*test_keys)
        yield
    finally:
        # Clean up after test
        if state_service.is_available():
            test_keys = state_service.redis_client.keys("aura:*")
            if test_keys:
                state_service.redis_client.delete(*test_keys)


@pytest.fixture
def auth_headers():
    """Create authentication headers for test requests."""
    # Get demo user token
    user = auth_service.authenticate_user("demo@aura.ai", "demo123")
    if user:
        token = auth_service.create_access_token(
            data={"sub": user["email"], "role": user["role"]}
        )
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.fixture
def admin_headers():
    """Create admin authentication headers for test requests."""
    # Get admin user token
    user = auth_service.authenticate_user("admin@aura.ai", "admin123")
    if user:
        token = auth_service.create_access_token(
            data={"sub": user["email"], "role": user["role"]}
        )
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.fixture
def manager_headers():
    """Create manager authentication headers for test requests."""
    # Get manager user token
    user = auth_service.authenticate_user("manager@aura.ai", "manager123")
    if user:
        token = auth_service.create_access_token(
            data={"sub": user["email"], "role": user["role"]}
        )
        return {"Authorization": f"Bearer {token}"}
    return {}


@pytest.fixture
def sample_resume_file():
    """Create a sample resume file for testing."""
    resume_content = """
    John Doe
    Software Engineer
    
    Experience:
    - 5 years Python development
    - FastAPI and React experience
    - Machine learning background
    
    Skills:
    - Python, JavaScript, TypeScript
    - FastAPI, React, Node.js
    - PostgreSQL, Redis
    - AWS, Docker, Kubernetes
    
    Education:
    - BS Computer Science, University of Technology
    """
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
        f.write(resume_content)
        return f.name


@pytest.fixture
def sample_session_data():
    """Create sample session data for testing."""
    return {
        "session_id": "test-session-123",
        "user_profile": {
            "user_id": "user_123",
            "full_name": "John Doe",
            "email": "john.doe@company.com",
            "job_role": "Software Engineer",
            "department": "Engineering",
            "start_date": "2024-01-15"
        },
        "conversation_history": [
            {
                "role": "user",
                "content": "Hello, I'm new here",
                "timestamp": "2024-01-15T10:00:00Z"
            }
        ],
        "onboarding_plan_steps": [],
        "completed_tasks": [],
        "current_step": None,
        "active_llm": "gemini",
        "contextual_memory": {},
        "created_at": "2024-01-15T10:00:00Z"
    }


@pytest.fixture
def sample_onboarding_plan():
    """Create sample onboarding plan for testing."""
    return {
        "user_profile": {
            "user_id": "user_123",
            "full_name": "John Doe",
            "job_role": "Software Engineer"
        },
        "plan_steps": [
            {
                "step_id": "welcome",
                "title": "Welcome to the Team",
                "description": "Complete initial welcome tasks",
                "estimated_duration": "1 hour",
                "priority": "high",
                "dependencies": [],
                "tools_needed": ["slack"],
                "status": "pending"
            },
            {
                "step_id": "setup_dev",
                "title": "Development Environment Setup",
                "description": "Set up your development environment",
                "estimated_duration": "2 hours",
                "priority": "high",
                "dependencies": ["welcome"],
                "tools_needed": ["github"],
                "status": "pending"
            }
        ],
        "created_at": "2024-01-15T10:00:00Z",
        "estimated_completion": "2024-01-20T17:00:00Z"
    }


@pytest.fixture(autouse=True)
async def cleanup_connections():
    """Clean up WebSocket connections after each test."""
    yield
    # Clean up any active connections
    for session_id in list(websocket_manager.active_connections.keys()):
        await websocket_manager.disconnect(session_id)
    
    # Clean up notification service connections
    notification_service.connections.clear()
    notification_service.connection_metadata.clear()
    notification_service.subscriptions.clear()


@pytest.fixture
def mock_llm_response():
    """Mock LLM response for testing."""
    return {
        "content": "Hello! I'm Aura, your onboarding assistant. I'm here to help you get started.",
        "role": "assistant",
        "llm_used": "gemini",
        "intent": "greeting",
        "suggestions": [
            "Upload your resume",
            "Tell me about your role",
            "What's the onboarding process?"
        ],
        "metadata": {
            "confidence": 0.95,
            "processing_time": 0.5
        }
    }


# Test configuration validation
@pytest.fixture(autouse=True)
def validate_test_config():
    """Validate test configuration before running tests."""
    assert settings.environment == "test", "Tests must run in test environment"
    assert "test" in settings.jwt_secret_key.lower(), "Test JWT secret should contain 'test'"
    assert settings.redis_url.endswith("/1"), "Tests should use Redis DB 1"