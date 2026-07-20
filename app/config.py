# app/config.py
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Base configuration"""

    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-this-later")
    SQLALCHEMY_TRACK_MODIFICATIONS: bool = False

    # A07: Remember-me cookie settings
    REMEMBER_COOKIE_DURATION: timedelta = timedelta(days=30)
    REMEMBER_COOKIE_HTTPONLY: bool = True
    REMEMBER_COOKIE_SAMESITE: str = "Lax"

    # Email — Brevo (A02: loaded from env, never hardcoded)
    BREVO_API_KEY: str = os.getenv("BREVO_API_KEY", "")
    BREVO_FROM_EMAIL: str = os.getenv("BREVO_FROM_EMAIL", "no-reply@example.com")

    # Stripe (A02: loaded from env, never hardcoded)
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
    REMEMBER_COOKIE_SECURE: bool = True
    SESSION_COOKIE_SECURE: bool = True
    SESSION_COOKIE_HTTPONLY: bool = True
    SESSION_COOKIE_SAMESITE: str = "Lax"


class TestingConfig(Config):
    """Testing configuration"""

    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///test.db"
    REMEMBER_COOKIE_SECURE: bool = False
