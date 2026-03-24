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
    REMEMBER_COOKIE_HTTPONLY: bool = True  # JS cannot read the cookie
    REMEMBER_COOKIE_SAMESITE: str = "Lax"  # CSRF mitigation

    # Email — SendGrid (A02: loaded from env, never hardcoded)
    SENDGRID_API_KEY: str = os.getenv("SENDGRID_API_KEY", "")
    SENDGRID_FROM_EMAIL: str = os.getenv("SENDGRID_FROM_EMAIL", "no-reply@example.com")


class DevelopmentConfig(Config):
    """Development configuration"""

    DEBUG: bool = True
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", "sqlite:///dev.db")
    SQLALCHEMY_ECHO: bool = True  # Log SQL queries
    REMEMBER_COOKIE_SECURE: bool = False  # HTTP is fine in dev


class ProductionConfig(Config):
    """Production configuration"""

    DEBUG: bool = False
    SQLALCHEMY_DATABASE_URI: str = os.getenv("DATABASE_URL", "")
    REMEMBER_COOKIE_SECURE: bool = True  # HTTPS only in prod


class TestingConfig(Config):
    """Testing configuration"""

    TESTING: bool = True
    SQLALCHEMY_DATABASE_URI: str = "sqlite:///test.db"
    REMEMBER_COOKIE_SECURE: bool = False
