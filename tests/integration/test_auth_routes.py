"""
Integration tests for Auth routes.

Tests:
  - Registration success and duplicate-email conflict
  - Login with valid/invalid tokens
  - Password reset (always returns OK for security)
  - GET /auth/me with valid auth
  - Unauthenticated access → 401
  - Malformed request bodies → 422
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestHealthCheck:
    """Health endpoint requires no auth."""

    def test_health_returns_200(self, test_client):
        """GET /health returns 200 with service info."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "learnai"


class TestRegister:
    """POST /auth/register integration tests."""

    @patch("api.routers.auth.firebase_auth")
    @patch("api.routers.auth.get_firebase_app")
    @patch("api.routers.auth.log_auth_event")
    @patch("api.routers.auth.UserRepository")
    def test_register_success(self, MockUserRepo, mock_log, mock_fb_app, mock_fb_auth, test_client, mock_user):
        """Valid registration → 201 with user data."""
        firebase_user_mock = MagicMock()
        firebase_user_mock.uid = "new_firebase_uid"
        mock_fb_auth.create_user.return_value = firebase_user_mock
        MockUserRepo.return_value.upsert_from_firebase = AsyncMock(return_value=mock_user)

        response = test_client.post("/auth/register", json={
            "email": "new@example.com",
            "password": "SecureP@ss123",
            "display_name": "New User",
        })

        assert response.status_code == 201
        data = response.json()
        assert data["message"] == "Registration successful"
        assert data["user"]["email"] == mock_user.email

    @patch("api.routers.auth.firebase_auth")
    @patch("api.routers.auth.get_firebase_app")
    def test_register_duplicate_email(self, mock_fb_app, mock_fb_auth, test_client):
        """Duplicate email → 409 Conflict."""
        from firebase_admin import auth as fb_auth
        mock_fb_auth.create_user.side_effect = fb_auth.EmailAlreadyExistsError(
            message="Email exists", cause=None, http_response=None
        )

        response = test_client.post("/auth/register", json={
            "email": "existing@example.com",
            "password": "SecureP@ss123",
            "display_name": "Existing User",
        })

        assert response.status_code == 409

    def test_register_malformed_body(self, test_client):
        """Missing required fields → 422."""
        response = test_client.post("/auth/register", json={"email": "bad"})
        assert response.status_code == 422


class TestLogin:
    """POST /auth/login integration tests."""

    @patch("api.routers.auth.update_streak", new_callable=AsyncMock)
    @patch("api.routers.auth.firebase_auth")
    @patch("api.routers.auth.get_firebase_app")
    @patch("api.routers.auth.log_auth_event")
    @patch("api.routers.auth.UserRepository")
    @patch("api.routers.auth.GamificationRepository")
    def test_login_success(self, MockGamRepo, MockUserRepo, mock_log, mock_fb_app,
                           mock_fb_auth, mock_streak, test_client, mock_user, mock_progress):
        """Valid token → 200 with user + gamification data."""
        mock_fb_auth.verify_id_token.return_value = {
            "uid": "firebase_uid", "email": "test@example.com", "name": "Test",
        }
        MockUserRepo.return_value.upsert_from_firebase = AsyncMock(return_value=mock_user)
        MockGamRepo.return_value.get_progress = AsyncMock(return_value=mock_progress)

        response = test_client.post("/auth/login", json={"id_token": "valid_token"})

        assert response.status_code == 200
        data = response.json()
        assert data["user"]["email"] == mock_user.email
        assert data["user"]["total_xp"] == 500

    @patch("api.routers.auth.firebase_auth")
    @patch("api.routers.auth.get_firebase_app")
    def test_login_invalid_token(self, mock_fb_app, mock_fb_auth, test_client):
        """Invalid Firebase token → 401."""
        mock_fb_auth.verify_id_token.side_effect = Exception("Invalid token")

        response = test_client.post("/auth/login", json={"id_token": "bad_token"})

        assert response.status_code == 401

    def test_login_missing_token(self, test_client):
        """Missing id_token → 422."""
        response = test_client.post("/auth/login", json={})
        assert response.status_code == 422


class TestResetPassword:
    """POST /auth/reset-password integration tests."""

    @patch("api.routers.auth.firebase_auth")
    @patch("api.routers.auth.get_firebase_app")
    def test_reset_password_success(self, mock_fb_app, mock_fb_auth, test_client):
        """Valid email → 200 (never reveals if account exists)."""
        mock_fb_auth.generate_password_reset_link.return_value = "https://reset.link"

        response = test_client.post("/auth/reset-password", json={"email": "user@example.com"})

        assert response.status_code == 200
        assert "reset link" in response.json()["message"].lower()

    @patch("api.routers.auth.firebase_auth")
    @patch("api.routers.auth.get_firebase_app")
    def test_reset_password_nonexistent_email(self, mock_fb_app, mock_fb_auth, test_client):
        """Non-existent email → still 200 (security: don't reveal existence)."""
        mock_fb_auth.generate_password_reset_link.side_effect = Exception("User not found")

        response = test_client.post("/auth/reset-password", json={"email": "nobody@example.com"})

        assert response.status_code == 200


class TestGetMe:
    """GET /auth/me integration tests."""

    @patch("api.routers.auth.UserRepository")
    @patch("api.routers.auth.GamificationRepository")
    def test_get_me_authenticated(self, MockGamRepo, MockUserRepo, test_client, mock_user, mock_progress):
        """Authenticated user → 200 with profile data."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=mock_user)
        MockGamRepo.return_value.get_progress = AsyncMock(return_value=mock_progress)

        response = test_client.get("/auth/me")

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == mock_user.email
        assert data["total_xp"] == 500

    @patch("api.routers.auth.UserRepository")
    def test_get_me_user_not_found(self, MockUserRepo, test_client):
        """Auth valid but no DB record → 404."""
        MockUserRepo.return_value.get_by_firebase_uid = AsyncMock(return_value=None)

        response = test_client.get("/auth/me")

        assert response.status_code == 404
