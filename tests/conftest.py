# tests/conftest.py
"""
Shared pytest fixtures for the Signature test suite.

Key decisions:
- Uses an in-memory SQLite database (sqlite://) per test function, not the
  file-based TestingConfig URI, so tests never touch dev.db and each test
  starts from a clean, isolated schema.
- Requires app/__init__.py's create_app() to accept a config_class parameter
  (see handoff notes) so TestingConfig can be selected without touching
  DevelopmentConfig behavior.
- Mocks all outbound email sends (SendGrid) so the test suite never makes
  real network calls and never depends on SENDGRID_API_KEY being set.
"""

from typing import Generator
from unittest.mock import patch

import pytest
from flask import Flask
from flask.testing import FlaskClient
from sqlalchemy.pool import StaticPool

from app import create_app, db as _db
from app.config import TestingConfig
from app.models.user import User

from app.services import ip_range_service

@pytest.fixture()
def app() -> Generator[Flask, None, None]:
    """Create a Flask app configured for testing, backed by in-memory SQLite."""
    test_app: Flask = create_app(TestingConfig)
    test_app.config.update(
        SQLALCHEMY_DATABASE_URI="sqlite://",  # in-memory, fresh per test
        # sqlite:// opens a NEW, empty, isolated database per physical
        # connection. Without pinning to a single shared connection, the
        # default pool can hand out different connections to the test
        # client's requests vs. direct `User.query...` calls inside the
        # test body — each seeing a different, disconnected database, so
        # writes made one way are invisible the other way. StaticPool
        # forces one connection for the whole engine so every access
        # (test client request or direct ORM call) shares the same data.
        SQLALCHEMY_ENGINE_OPTIONS={
            "poolclass": StaticPool,
            "connect_args": {"check_same_thread": False},
        },
        WTF_CSRF_ENABLED=False,
        SERVER_NAME="localhost.test",
    )

    with test_app.app_context():
        _db.create_all()
        yield test_app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture(autouse=True)
def mock_email_sends() -> Generator[None, None, None]:
    """
    Prevent any test from hitting the real SendGrid API.

    Patched at the source module (app.services.email_service) so both the
    direct imports in auth.py and the deferred imports in user_service.py
    pick up the mock, since both resolve the function from this module at
    call time.
    """
    with patch(
        "app.services.email_service.send_welcome_email",
        return_value=(True, None),
    ), patch(
        "app.services.email_service.send_verification_email",
        return_value=(True, None),
    ), patch(
        "app.services.email_service.send_password_reset_email",
        return_value=(True, None),
    ):
        yield


# ---------------------------------------------------------------------------
# Test data helpers
# ---------------------------------------------------------------------------

STRONG_PASSWORD = (
    "StrongPass1!"  # 12 chars, upper/lower/digit/special — passes validate_password
)


def register_via_client(
    client: FlaskClient,
    email: str = "user@example.com",
    password: str = STRONG_PASSWORD,
    name: str = "Test User",
):
    """Register a user through the real /auth/register route."""
    return client.post(
        "/auth/register",
        data={"email": email, "password": password, "name": name},
        follow_redirects=False,
    )


def login_via_client(
    client: FlaskClient,
    email: str = "user@example.com",
    password: str = STRONG_PASSWORD,
):
    """Log a user in through the real /auth/login route."""
    return client.post(
        "/auth/login",
        data={"email": email, "password": password},
        follow_redirects=False,
    )


def get_user_by_email(app: Flask, email: str) -> User:
    """
    Look up a user by email.

    Assumes an app context is already active — the `app` fixture keeps one
    pushed for the full duration of each test via its `yield`, so this must
    NOT push a second nested context here; doing so would tear down the
    scoped session on exit and detach the returned instance before the
    caller can use it.
    """
    user = User.query.filter_by(email=email.lower()).first()
    assert user is not None, f"expected user {email} to exist"
    return user

# ---------------------------------------------------------------------------
# Test microsoft endpoints
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _no_office365_ip_fetch(monkeypatch):
    """
    Keep tests from making a real network call to endpoints.office.com.
    is_office365_ip() will return False for every IP unless a specific
    test overrides this with its own monkeypatch.
    """
    monkeypatch.setattr(ip_range_service, "_cached_networks", [])
    monkeypatch.setattr(ip_range_service, "_cache_fetched_at", 0.0)
    monkeypatch.setattr(ip_range_service, "_fetch_networks", lambda: [])
