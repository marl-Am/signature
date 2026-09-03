# tests/e2e/conftest.py
"""
Shared fixtures and helpers for Playwright end-to-end tests.

Runs against the Neon `dev` Postgres branch (see WORKFLOW.md — same engine
as production, not SQLite), so fixtures create and tear down real rows
rather than relying on an in-memory DB.

This module also owns the shared base URLs and the `login` helper. Test
modules import them from here instead of each declaring a private copy.
"""

import os
import secrets
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from flask import Flask
from playwright.sync_api import Page, expect

from app import create_app, db
from app.models.signature import Signature
from app.models.user import User

BASE_URL: str = os.getenv("BASE_URL", "http://localhost:5000")
LOGIN_URL: str = f"{BASE_URL}/auth/login"
CREATE_URL: str = f"{BASE_URL}/signatures/create"


@dataclass
class Account:
    email: str
    password: str
    id: int


@pytest.fixture(scope="session")
def app() -> Iterator[Flask]:
    flask_app = create_app()
    flask_app.config.update(TESTING=True)
    with flask_app.app_context():
        yield flask_app


def login(page: Page, account: Account) -> None:
    """
    Sign `account` in through the real login form and wait until the app
    has navigated away from the login page.
    """
    page.goto(LOGIN_URL)
    page.get_by_label("Email").fill(account.email)
    page.get_by_label("Password").fill(account.password)
    page.get_by_role("button", name="Sign In").click()
    expect(page).not_to_have_url(LOGIN_URL)


def _make_user(
    app: Flask,
    email: str,
    password: str,
    name: str = "E2E Test User",
    subscription_tier: str = "free",
) -> Account:
    with app.app_context():
        user = User(email=email, name=name, subscription_tier=subscription_tier)
        # set_password raises ValueError if password < MIN_PASSWORD_LENGTH
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        return Account(email=email, password=password, id=user.id)


def _delete_user(app: Flask, account: Account) -> None:
    with app.app_context():
        user = db.session.get(User, account.id)
        if user is not None:
            db.session.delete(user)  # cascades to signatures (ondelete="CASCADE")
            db.session.commit()


def set_subscription_tier(app: Flask, account: Account, tier: str) -> None:
    """
    Directly flip a user's subscription_tier, simulating what a Stripe
    webhook would do on upgrade/downgrade — used by tests that check the
    UI reacts to a tier change without needing a real Stripe round-trip.
    """
    with app.app_context():
        user = db.session.get(User, account.id)
        if user is None:
            raise ValueError(f"No user found for id={account.id}")
        user.subscription_tier = tier
        db.session.commit()


@pytest.fixture
def user_a(app: Flask) -> Iterator[Account]:
    account = _make_user(app, "e2e-user-a@example.com", "TestPass123!")
    yield account
    _delete_user(app, account)


@pytest.fixture
def user_b(app: Flask) -> Iterator[Account]:
    account = _make_user(app, "e2e-user-b@example.com", "TestPass123!")
    yield account
    _delete_user(app, account)


@pytest.fixture
def pro_user(app: Flask) -> Iterator[Account]:
    """A user starting on the Pro tier, for tests that then downgrade it."""
    account = _make_user(
        app, "e2e-pro-user@example.com", "TestPass123!", subscription_tier="pro"
    )
    yield account
    _delete_user(app, account)


@pytest.fixture
def signature_b(app: Flask, user_b: Account) -> int:
    """
    A minimal signature owned by user_b, for the cross-account access
    test. tracking_code and html_content are NOT NULL on the model but
    their actual values don't matter for an ownership check.
    """
    with app.app_context():
        sig = Signature(
            user_id=user_b.id,
            name="User B's Signature",
            full_name="User B",
            html_content="<div>placeholder</div>",
            tracking_code=secrets.token_hex(16),
        )
        db.session.add(sig)
        db.session.commit()
        return sig.id
