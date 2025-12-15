# app/models/user.py
"""
User model with OWASP Top 10:2025 security measures

Security Features Implemented:
- A01: Access Control - user_id relationships on all resources
- A04: Cryptographic Failures - bcrypt password hashing
- A07: Authentication Failures - account lockout, session management
- A09: Logging - track login attempts and suspicious activity
"""

from app import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets


class User(UserMixin, db.Model):
    """
    User model for authentication and authorization

    Inherits from UserMixin (Flask-Login) which provides:
    - is_authenticated property
    - is_active property
    - is_anonymous property
    - get_id() method
    """

    __tablename__ = "users"

    # ========================================
    # PRIMARY FIELDS
    # ========================================
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    name = db.Column(db.String(100), nullable=False)

    # ========================================
    # A07: AUTHENTICATION SECURITY
    # ========================================
    # Account status
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verification_token = db.Column(db.String(100), unique=True, nullable=True)

    # Account lockout protection (prevents brute force attacks)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    # Password reset security
    password_reset_token = db.Column(db.String(100), unique=True, nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)

    # ========================================
    # A09: LOGGING & MONITORING
    # ========================================
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)  # IPv6 compatible
    created_at = db.Column(db.DateTime, default=datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime, default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc), nullable=False
    )

    # ========================================
    # SUBSCRIPTION & BUSINESS LOGIC
    # ========================================
    subscription_status = db.Column(
        db.String(20), default="trial", nullable=False
    )  # Values: 'trial', 'active', 'cancelled', 'expired'

    subscription_tier = db.Column(
        db.String(20), default="free", nullable=False
    )  # Values: 'free', 'pro', 'enterprise'

    stripe_customer_id = db.Column(db.String(100), unique=True, nullable=True)
    stripe_subscription_id = db.Column(db.String(100), unique=True, nullable=True)
    trial_ends_at = db.Column(db.DateTime, nullable=True)
    subscription_ends_at = db.Column(db.DateTime, nullable=True)

    # ========================================
    # A01: RELATIONSHIPS (for access control)
    # ========================================
    # One user has many signatures
    signatures = db.relationship(
        "Signature",
        back_populates="user",
        lazy="dynamic",  # Don't load all signatures by default
        cascade="all, delete-orphan",  # Delete signatures when user is deleted
    )

    # TODO: Add relationships as you create models
    # analytics = db.relationship('Analytics', back_populates='user', lazy='dynamic')
    # api_keys = db.relationship('APIKey', back_populates='user', lazy='dynamic')

    # ========================================
    # PASSWORD MANAGEMENT (A04: Cryptographic Failures)
    # ========================================

    def set_password(self, password: str) -> None:
        """
        Hash and store password using Werkzeug's bcrypt implementation

        Security: Uses bcrypt with automatic salt generation
        OWASP A04: Cryptographic Failures - Never store plaintext passwords

        Args:
            password: Plain text password to hash
        """
        if not password or len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        self.password_hash = generate_password_hash(password, method="scrypt")

    def check_password(self, password: str) -> bool:
        """
        Verify password against stored hash

        Args:
            password: Plain text password to verify

        Returns:
            True if password matches, False otherwise
        """
        return check_password_hash(self.password_hash, password)

    # ========================================
    # A07: ACCOUNT LOCKOUT (Authentication Failures)
    # ========================================

    def is_locked(self) -> bool:
        """
        Check if account is currently locked due to failed login attempts

        Returns:
            True if account is locked, False otherwise
        """
        if self.locked_until is None:
            return False

        # Check if lockout period has expired
        if datetime.now(timezone.utc)() > self.locked_until:
            # Auto-unlock account
            self.locked_until = None
            self.failed_login_attempts = 0
            db.session.commit()
            return False

        return True

    def record_failed_login(self) -> None:
        """
        Record a failed login attempt and lock account if threshold exceeded

        Security: Prevents brute force attacks
        OWASP A07: Authentication Failures
        """
        self.failed_login_attempts += 1

        # Lock account after 5 failed attempts for 15 minutes
        MAX_ATTEMPTS = 5
        LOCKOUT_DURATION_MINUTES = 15

        if self.failed_login_attempts >= MAX_ATTEMPTS:
            self.locked_until = datetime.now(timezone.utc)() + timedelta(
                minutes=LOCKOUT_DURATION_MINUTES
            )

        db.session.commit()

    def record_successful_login(self, ip_address: Optional[str] = None) -> None:
        """
        Record successful login and reset failed attempts

        Args:
            ip_address: IP address of the login (for A09: Logging)
        """
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = datetime.now(timezone.utc)()
        self.last_login_ip = ip_address
        db.session.commit()

    # ========================================
    # EMAIL VERIFICATION
    # ========================================

    def generate_verification_token(self) -> str:
        """
        Generate secure email verification token

        Returns:
            URL-safe verification token
        """
        self.email_verification_token = secrets.token_urlsafe(32)
        db.session.commit()
        return self.email_verification_token

    def verify_email(self, token: str) -> bool:
        """
        Verify email with provided token

        Args:
            token: Verification token from email link

        Returns:
            True if verification successful, False otherwise
        """
        if self.email_verification_token == token:
            self.email_verified = True
            self.email_verification_token = None
            db.session.commit()
            return True
        return False

    # ========================================
    # PASSWORD RESET
    # ========================================

    def generate_password_reset_token(self) -> str:
        """
        Generate secure password reset token with expiration

        Security: Token expires after 1 hour

        Returns:
            URL-safe reset token
        """
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_expires = datetime.now(timezone.utc)() + timedelta(hours=1)
        db.session.commit()
        return self.password_reset_token

    def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using valid token

        Args:
            token: Reset token from email link
            new_password: New password to set

        Returns:
            True if reset successful, False otherwise
        """
        # Verify token matches and hasn't expired
        if (
            self.password_reset_token != token
            or self.password_reset_expires is None
            or datetime.now(timezone.utc)() > self.password_reset_expires
        ):
            return False

        # Set new password and clear reset token
        self.set_password(new_password)
        self.password_reset_token = None
        self.password_reset_expires = None
        db.session.commit()
        return True

    # ========================================
    # SUBSCRIPTION CHECKS (Business Logic)
    # ========================================

    def has_active_subscription(self) -> bool:
        """
        Check if user has an active paid subscription

        Returns:
            True if subscription is active, False otherwise
        """
        if self.subscription_status == "active":
            return True

        # Check if trial is still valid
        if self.subscription_status == "trial" and self.trial_ends_at:
            return datetime.now(timezone.utc) < self.trial_ends_at

        return False

    def can_create_signature(self) -> bool:
        """
        Check if user can create a new signature based on subscription tier

        Free tier: 1 signature
        Pro tier: Unlimited signatures

        Returns:
            True if user can create signature, False otherwise
        """
        if self.subscription_tier == "pro":
            return True

        # Free tier limited to 1 signature
        signature_count = self.signatures.count()
        return signature_count < 1

    # ========================================
    # UTILITY METHODS
    # ========================================

    def __repr__(self) -> str:
        """String representation for debugging"""
        return f"<User {self.email}>"

    def to_dict(self) -> dict:
        """
        Convert user to dictionary (for API responses)

        Security: Never include password_hash or tokens in output

        Returns:
            Dictionary of safe user data
        """
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
            "email_verified": self.email_verified,
            "subscription_status": self.subscription_status,
            "subscription_tier": self.subscription_tier,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_login_at": (
                self.last_login_at.isoformat() if self.last_login_at else None
            ),
        }


# ========================================
# DATABASE INDEXES (Performance & Security)
# ========================================
# These are already defined with index=True on columns above:
# - email (unique + indexed for fast lookups during login)
# - stripe_customer_id (unique for Stripe integration)
# - email_verification_token (unique for secure verification)
# - password_reset_token (unique for secure password reset)
