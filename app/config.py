# app/config.py
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()


def get_secret_key_for_config(config_name: str) -> str:
    """Return the configured secret key for the given environment.

    Production must fail loudly when the environment variable is missing so
    misconfiguration is caught at startup rather than silently using a default.
    Development and testing intentionally allow a local fallback so tests and
    local runs do not require a manually configured secret.
    """
    secret_key = os.getenv("SECRET_KEY")
    if config_name == "production":
        if not secret_key:
            raise RuntimeError("SECRET_KEY must be set in production")
        return secret_key
    return secret_key or "dev-secret-key-change-this-later"


def get_brevo_from_email_for_config(config_name: str) -> str:
    """Return the configured Brevo sender address for the given environment.

    Production must fail loudly when the environment variable is missing so
    misconfiguration is caught at startup rather than silently sending from a
    placeholder address. Development and testing intentionally allow a local
    fallback so tests and local runs do not require a manually configured
    sender address.
    """
    from_email = os.getenv("BREVO_FROM_EMAIL")
    if config_name == "production":
        if not from_email:
            raise RuntimeError("BREVO_FROM_EMAIL must be set in production")
        return from_email
    return from_email or "no-reply@example.com"

class Config:
    """Base configuration"""

    SECRET_KEY: str = get_secret_key_for_config("development")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # verify pooled connections
    # are alive before reuse, and recycle them before Neon's idle-connection
    # timeout can silently close them out from under us. Without this, a
    # connection Neon closed while idle raises psycopg2.OperationalError
    # ("SSL connection has been closed unexpectedly") on the next request
    # that tries to reuse it.
    SQLALCHEMY_ENGINE_OPTIONS: dict = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }

    REMEMBER_COOKIE_DURATION: timedelta = timedelta(days=30)
    REMEMBER_COOKIE_HTTPONLY: bool = True
    REMEMBER_COOKIE_SAMESITE: str = "Lax"

    # Verification Email — Brevo
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    BREVO_FROM_EMAIL: str = get_brevo_from_email_for_config("development")

    # Payments - Stripe
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_PUBLISHABLE_KEY: str = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    STRIPE_PRO_PRICE_ID: str = os.getenv("STRIPE_PRO_PRICE_ID", "")
    STRIPE_PRO_PRICE_ID_YEARLY = os.environ.get("STRIPE_PRO_PRICE_ID_YEARLY")


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG: bool = True
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    SQLALCHEMY_ECHO: bool = True
    REMEMBER_COOKIE_SECURE: bool = False


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG: bool = False
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", "")
    SECRET_KEY: str = get_secret_key_for_config("production")
    BREVO_FROM_EMAIL: str = get_brevo_from_email_for_config("production")
    REMEMBER_COOKIE_SECURE: bool = True
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"


class TestingConfig(Config):
    """Testing configuration"""

    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///test.db"
    REMEMBER_COOKIE_SECURE: bool = False
    # Test client posts raw form dicts directly to routes without first
    # fetching a page to read csrf_token() out of, so CSRF checks are
    # disabled for this config. conftest.py's `app` fixture already forces
    # this at the fixture level; setting it here too means anything else
    # that runs under TestingConfig (outside pytest) gets the same behavior.
    WTF_CSRF_ENABLED: bool = False
