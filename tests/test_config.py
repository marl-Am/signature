"""Tests for startup configuration behavior."""

import pytest

from app.config import get_secret_key_for_config


def test_production_requires_secret_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Production mode must fail loudly when SECRET_KEY is unset."""
    monkeypatch.delenv("SECRET_KEY", raising=False)

    with pytest.raises(RuntimeError, match="SECRET_KEY must be set in production"):
        get_secret_key_for_config("production")


def test_dev_allows_local_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    """Development mode may keep a local-only fallback for easier local startup."""
    monkeypatch.delenv("SECRET_KEY", raising=False)

    assert (
        get_secret_key_for_config("development") == "dev-secret-key-change-this-later"
    )
