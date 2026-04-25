"""
Root conftest — shared fixtures for all tests.

Provides:
  - Mocked Firebase auth dependency
  - Mocked DB session
  - Test FastAPI client
  - Common data factories
"""

import uuid
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from api.utils.auth import FirebaseUser


# ── Reusable test data ────────────────────────────────────────────
TEST_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")
TEST_FIREBASE_UID = "firebase_test_uid_123"
TEST_EMAIL = "testuser@example.com"
TEST_DISPLAY_NAME = "Test User"


@pytest.fixture
def firebase_user() -> FirebaseUser:
    """A fake FirebaseUser for dependency injection."""
    return FirebaseUser(uid=TEST_FIREBASE_UID, email=TEST_EMAIL, name=TEST_DISPLAY_NAME, picture=None)


@pytest.fixture
def mock_db():
    """Async mock for SQLAlchemy session."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.close = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def mock_user():
    """A mock User ORM object."""
    user = MagicMock()
    user.id = TEST_USER_ID
    user.firebase_uid = TEST_FIREBASE_UID
    user.email = TEST_EMAIL
    user.display_name = TEST_DISPLAY_NAME
    user.avatar_url = None
    user.created_at = datetime(2025, 1, 1)
    user.updated_at = datetime(2025, 1, 1)
    return user


@pytest.fixture
def mock_progress():
    """A mock UserProgress ORM object."""
    progress = MagicMock()
    progress.user_id = TEST_USER_ID
    progress.total_xp = 500
    progress.level = 3
    progress.streak_days = 5
    progress.longest_streak = 10
    progress.last_active_date = date.today()
    progress.sessions_completed = 10
    progress.quiz_correct_total = 25
    progress.topics_explored = 4
    return progress


@pytest.fixture
def mock_mastery():
    """A mock TopicMastery ORM object."""
    mastery = MagicMock()
    mastery.user_id = TEST_USER_ID
    mastery.topic = "Python"
    mastery.mastery_score = 75.0
    mastery.questions_answered = 20
    mastery.correct_answers = 15
    return mastery


def override_auth(firebase_user: FirebaseUser):
    """Create auth dependency override returning the given user."""
    async def _override():
        return firebase_user
    return _override


def override_db(mock_db):
    """Create DB dependency override returning the mock session."""
    async def _override():
        yield mock_db
    return _override


@pytest.fixture
def test_client(firebase_user, mock_db):
    """Synchronous TestClient with mocked auth and DB."""
    from api.main import app
    from api.utils.auth import get_current_user
    from api.db.session import get_db

    app.dependency_overrides[get_current_user] = override_auth(firebase_user)
    app.dependency_overrides[get_db] = override_db(mock_db)

    client = TestClient(app)
    yield client

    app.dependency_overrides.clear()


@pytest.fixture
async def async_client(firebase_user, mock_db):
    """Async HTTPX client with mocked auth and DB."""
    from api.main import app
    from api.utils.auth import get_current_user
    from api.db.session import get_db

    app.dependency_overrides[get_current_user] = override_auth(firebase_user)
    app.dependency_overrides[get_db] = override_db(mock_db)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
