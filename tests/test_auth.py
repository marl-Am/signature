# tests/test_auth.py
"""
Tests for app/routes/auth.py: registration, login, account lockout,
email verification, and password reset.
"""

from datetime import datetime, timedelta, timezone

from flask import Flask
from flask.testing import FlaskClient

from app.models.user import User
from tests.conftest import (
    STRONG_PASSWORD,
    get_user_by_email,
    login_via_client,
    register_via_client,
)

# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def test_register_creates_user_and_logs_in(app: Flask, client: FlaskClient) -> None:
    response = register_via_client(client, email="new@example.com")

    assert response.status_code == 302
    assert "dashboard" in response.headers["Location"].lower()

    user = get_user_by_email(app, "new@example.com")
    assert user.email == "new@example.com"
    assert user.subscription_tier == "free"
    assert user.subscription_status == "trial"
    # A04: password must never be stored in plain text
    assert user.password_hash != STRONG_PASSWORD


def test_register_rejects_duplicate_email(client: FlaskClient) -> None:
    register_via_client(client, email="dupe@example.com")
    client.get("/auth/logout")

    response = register_via_client(client, email="dupe@example.com")

    assert response.status_code == 200  # re-renders form with error, no redirect
    assert b"already exists" in response.data


def test_register_rejects_weak_password(client: FlaskClient) -> None:
    response = client.post(
        "/auth/register",
        data={"email": "weak@example.com", "password": "short1!", "name": "Weak"},
    )

    assert response.status_code == 200
    assert b"Registration failed" in response.data


def test_register_redirects_if_already_authenticated(client: FlaskClient) -> None:
    register_via_client(client, email="already@example.com")

    response = client.get("/auth/register")

    assert response.status_code == 302
    assert "dashboard" in response.headers["Location"].lower()


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------


def test_login_success(client: FlaskClient) -> None:
    register_via_client(client, email="login@example.com")
    client.get("/auth/logout")

    response = login_via_client(client, email="login@example.com")

    assert response.status_code == 302
    assert "dashboard" in response.headers["Location"].lower()


def test_login_wrong_password_shows_generic_message(client: FlaskClient) -> None:
    register_via_client(client, email="generic@example.com")
    client.get("/auth/logout")

    response = login_via_client(
        client, email="generic@example.com", password="WrongPass1!"
    )

    assert response.status_code == 200
    # A07: message must not reveal whether the account exists
    assert b"Invalid email or password" in response.data


def test_login_unknown_email_shows_same_generic_message(client: FlaskClient) -> None:
    response = login_via_client(
        client, email="nobody@example.com", password="WrongPass1!"
    )

    assert response.status_code == 200
    assert b"Invalid email or password" in response.data


def test_account_locks_after_five_failed_attempts(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="lockout@example.com")
    client.get("/auth/logout")

    for _ in range(5):
        login_via_client(client, email="lockout@example.com", password="WrongPass1!")

    user = get_user_by_email(app, "lockout@example.com")
    assert user.failed_login_attempts == 5
    assert user.locked_until is not None

    # Even the CORRECT password must now be rejected while locked
    response = login_via_client(client, email="lockout@example.com")
    assert response.status_code == 200
    assert b"locked" in response.data.lower()


def test_open_redirect_is_blocked(client: FlaskClient) -> None:
    """A10: `next` pointing to an external host must be ignored."""
    register_via_client(client, email="redirect@example.com")
    client.get("/auth/logout")

    response = client.post(
        "/auth/login?next=https://evil-example.com/steal",
        data={"email": "redirect@example.com", "password": STRONG_PASSWORD},
        follow_redirects=False,
    )

    assert response.status_code == 302
    location = response.headers["Location"]
    assert "evil-example.com" not in location
    assert "dashboard" in location.lower()


# ---------------------------------------------------------------------------
# Logout
# ---------------------------------------------------------------------------


def test_logout_requires_login(client: FlaskClient) -> None:
    response = client.get("/auth/logout")
    assert response.status_code == 302
    assert "login" in response.headers["Location"].lower()


def test_logout_clears_session(client: FlaskClient) -> None:
    register_via_client(client, email="logout@example.com")

    response = client.get("/auth/logout", follow_redirects=False)

    assert response.status_code == 302
    # Protected route should now bounce back to login
    dashboard_response = client.get("/signatures/create", follow_redirects=False)
    assert "login" in dashboard_response.headers["Location"].lower()


# ---------------------------------------------------------------------------
# Email verification
# ---------------------------------------------------------------------------


def test_verify_email_with_valid_token(app: Flask, client: FlaskClient) -> None:
    register_via_client(client, email="verify@example.com")
    user = get_user_by_email(app, "verify@example.com")
    token = user.email_verification_token
    assert token is not None

    response = client.get(f"/auth/verify-email/{token}", follow_redirects=False)

    assert response.status_code == 302
    verified_user = get_user_by_email(app, "verify@example.com")
    assert verified_user.email_verified is True
    assert verified_user.email_verification_token is None


def test_verify_email_with_invalid_token(client: FlaskClient) -> None:
    response = client.get("/auth/verify-email/not-a-real-token", follow_redirects=False)

    assert response.status_code == 302
    assert "login" in response.headers["Location"].lower()


def test_verify_email_with_expired_token_redirects_to_login(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="expiredverify@example.com")
    with app.app_context():
        user = get_user_by_email(app, "expiredverify@example.com")
        user.email_verification_token = "expired-token"
        user.email_verification_expires = datetime.now(timezone.utc) - timedelta(
            hours=1
        )
        user.email_verified = False
        user.save() if hasattr(user, "save") else None
        from app import db

        db.session.commit()

    response = client.get(
        "/auth/verify-email/expired-token",
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "login" in response.headers["Location"].lower()

    with app.app_context():
        user = get_user_by_email(app, "expiredverify@example.com")
        assert user.email_verified is False
        assert user.email_verification_token == "expired-token"


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------


def test_forgot_password_gives_same_message_regardless_of_email_existing(
    client: FlaskClient,
) -> None:
    """A07: response must not leak whether the account exists."""
    register_via_client(client, email="known@example.com")
    client.get("/auth/logout")

    known_response = client.post(
        "/auth/forgot-password",
        data={"email": "known@example.com"},
        follow_redirects=True,
    )
    unknown_response = client.post(
        "/auth/forgot-password",
        data={"email": "ghost@example.com"},
        follow_redirects=True,
    )

    assert b"password reset instructions" in known_response.data
    assert b"password reset instructions" in unknown_response.data


def test_reset_password_with_valid_token(app: Flask, client: FlaskClient) -> None:
    register_via_client(client, email="reset@example.com")
    client.get("/auth/logout")

    with app.app_context():
        user: User = get_user_by_email(app, "reset@example.com")
        token = user.generate_password_reset_token()

    new_password = "NewStrongPass1!"
    response = client.post(
        f"/auth/reset-password/{token}",
        data={"password": new_password, "confirm_password": new_password},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "login" in response.headers["Location"].lower()

    login_response = login_via_client(
        client, email="reset@example.com", password=new_password
    )
    assert login_response.status_code == 302
    assert "dashboard" in login_response.headers["Location"].lower()


def test_reset_password_rejects_mismatched_confirmation(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="mismatch@example.com")
    client.get("/auth/logout")

    with app.app_context():
        user = get_user_by_email(app, "mismatch@example.com")
        token = user.generate_password_reset_token()

    response = client.post(
        f"/auth/reset-password/{token}",
        data={"password": "NewStrongPass1!", "confirm_password": "Different1!"},
    )

    assert response.status_code == 200
    assert b"do not match" in response.data


def test_reset_password_rejects_invalid_token(client: FlaskClient) -> None:
    response = client.post(
        "/auth/reset-password/not-a-real-token",
        data={"password": "NewStrongPass1!", "confirm_password": "NewStrongPass1!"},
    )

    assert response.status_code == 200
    assert b"Password reset failed" in response.data


# ---------------------------------------------------------------------------
# Resend verification
# ---------------------------------------------------------------------------


def test_resend_verification_requires_login(client: FlaskClient) -> None:
    response = client.get("/auth/resend-verification")
    assert response.status_code == 302
    assert "login" in response.headers["Location"].lower()


def test_resend_verification_when_already_verified(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="alreadyverified@example.com")
    user = get_user_by_email(app, "alreadyverified@example.com")
    token = user.email_verification_token
    assert token is not None
    client.get(f"/auth/verify-email/{token}")

    response = client.get("/auth/resend-verification", follow_redirects=True)

    assert b"already verified" in response.data
