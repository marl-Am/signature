# app/models/user.py
"""
User model with OWASP Top 10:2025 security measures.

Security Features Implemented:
- A01: Access Control - user_id relationships on all resources
- A04: Cryptographic Failures - Argon2id password hashing
- A07: Authentication Failures - account lockout, session management
- A09: Logging - track login attempts and suspicious activity

Datetime note: All datetimes are written as timezone-aware UTC via
datetime.now(timezone.utc). PostgreSQL (Supabase, production) stores these as
TIMESTAMPTZ and returns them aware, so comparisons work directly.

SQLite (local dev and test) does NOT preserve timezone info on TIMESTAMP
columns — a value written as aware UTC comes back naive on read. Comparing
a naive value against an aware datetime.now(timezone.utc) raises:
    TypeError: can't compare offset-naive and offset-aware datetimes
_ensure_aware_utc() normalizes any value read back as naive (assumed to be
UTC, since that's the only thing ever written) before every such comparison,
so behavior is correct on both SQLite and PostgreSQL without touching the
storage layer or requiring a schema/migration change.
"""

from app import db
from flask_login import UserMixin
from argon2 import PasswordHasher, Type
from argon2.exceptions import VerifyMismatchError, InvalidHashError
from datetime import datetime, timedelta, timezone
from typing import Optional
import secrets

# OWASP Recommended minimum configuration for Argon2id:
# Memory: 19 MiB -> 19456 KiB (argon2-cffi uses KiB)
# Iterations (time_cost): 2
# Parallelism: 1
ARGON2_MEMORY_COST_KIB: int = 19456
ARGON2_TIME_COST: int = 2
ARGON2_PARALLELISM: int = 1

ph = PasswordHasher(
    time_cost=ARGON2_TIME_COST,
    memory_cost=ARGON2_MEMORY_COST_KIB,
    parallelism=ARGON2_PARALLELISM,
    type=Type.ID,  # Explicitly use Argon2id
)


def _ensure_aware_utc(value: datetime) -> datetime:
    """
    Return `value` as timezone-aware UTC.

    If `value` is already aware (e.g. read back from PostgreSQL), it is
    returned unchanged. If it is naive (e.g. read back from SQLite, which
    drops tzinfo on round-trip), it is assumed to be UTC — the only
    timezone this codebase ever writes — and tagged accordingly.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


class User(UserMixin, db.Model):
    """
    User model for authentication and authorization.

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
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    email_verification_token = db.Column(db.String(100), unique=True, nullable=True)
    email_verification_expires = db.Column(db.DateTime, nullable=True)

    # Account lockout (prevents brute force attacks)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)

    # Password reset
    password_reset_token = db.Column(db.String(100), unique=True, nullable=True)
    password_reset_expires = db.Column(db.DateTime, nullable=True)

    # ========================================
    # A09: LOGGING & MONITORING
    # ========================================
    last_login_at = db.Column(db.DateTime, nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)  # IPv6 compatible

    created_at = db.Column(
        db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
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
    signatures = db.relationship(
        "Signature",
        back_populates="user",
        lazy="dynamic",
        cascade="all, delete-orphan",
    )

    # ========================================
    # PASSWORD MANAGEMENT (A04: Cryptographic Failures)
    # ========================================

    def set_password(self, password: str) -> None:
        """
        Hash and store password using OWASP-recommended Argon2id.

        Args:
            password: Plain text password to hash.
        """
        if not password or len(password) < 12:
            raise ValueError("Password must be at least 12 characters long")
        self.password_hash = ph.hash(password)

    def check_password(self, password: str) -> bool:
        """
        Verify password against stored hash.

        Also re-hashes if cost parameters have been updated.

        Args:
            password: Plain text password to verify.

        Returns:
            True if password matches, False otherwise.
        """
        try:
            ph.verify(self.password_hash, password)
            if ph.check_needs_rehash(self.password_hash):
                self.password_hash = ph.hash(password)
                db.session.add(self)
            return True
        except (VerifyMismatchError, InvalidHashError):
            return False
        except Exception:
            return False

    # ========================================
    # A07: ACCOUNT LOCKOUT
    # ========================================

    def is_locked(self) -> bool:
        """
        Check if account is currently locked due to failed login attempts.

        Returns:
            True if account is locked, False otherwise.
        """
        if self.locked_until is None:
            return False

        if datetime.now(timezone.utc) > _ensure_aware_utc(self.locked_until):
            self.locked_until = None
            self.failed_login_attempts = 0
            db.session.commit()
            return False

        return True

    def record_failed_login(self) -> None:
        """
        Record a failed login attempt and lock account if threshold exceeded.
        """
        self.failed_login_attempts += 1

        MAX_ATTEMPTS = 5
        LOCKOUT_DURATION_MINUTES = 15

        if self.failed_login_attempts >= MAX_ATTEMPTS:
            self.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=LOCKOUT_DURATION_MINUTES
            )

        db.session.commit()

    def record_successful_login(self, ip_address: Optional[str] = None) -> None:
        """
        Record successful login and reset failed attempts.

        Args:
            ip_address: IP address of the login (A09: Logging).
        """
        self.failed_login_attempts = 0
        self.locked_until = None
        self.last_login_at = datetime.now(timezone.utc)
        self.last_login_ip = ip_address
        db.session.commit()

    # ========================================
    # EMAIL VERIFICATION
    # ========================================

    def generate_verification_token(self) -> str:
        """
        Generate a secure email verification token that expires in 24 hours.

        Returns:
            URL-safe verification token.
        """
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_expires = datetime.now(timezone.utc) + timedelta(
            hours=24
        )
        db.session.commit()
        return self.email_verification_token

    def verify_email(self, token: str) -> bool:
        """
        Verify email with provided token.

        Returns:
            True if verification successful, False if token is wrong or expired.
        """
        if (
            self.email_verification_token != token
            or self.email_verification_expires is None
            or datetime.now(timezone.utc)
            > _ensure_aware_utc(self.email_verification_expires)
        ):
            return False

        self.email_verified = True
        self.email_verification_token = None
        self.email_verification_expires = None
        db.session.commit()
        return True

    # ========================================
    # PASSWORD RESET
    # ========================================

    def generate_password_reset_token(self) -> str:
        """
        Generate a secure password reset token that expires in 1 hour.

        Returns:
            URL-safe reset token.
        """
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        db.session.commit()
        return self.password_reset_token

    def reset_password(self, token: str, new_password: str) -> bool:
        """
        Reset password using a valid, unexpired token.

        Returns:
            True if reset successful, False otherwise.
        """
        if (
            self.password_reset_token != token
            or self.password_reset_expires is None
            or datetime.now(timezone.utc)
            > _ensure_aware_utc(self.password_reset_expires)
        ):
            return False

        self.set_password(new_password)
        self.password_reset_token = None
        self.password_reset_expires = None
        db.session.commit()
        return True

    # ========================================
    # SUBSCRIPTION CHECKS
    # ========================================

    def has_active_subscription(self) -> bool:
        """
        Check if user has an active paid subscription or valid trial.

        Returns:
            True if subscription is active, False otherwise.
        """
        if self.subscription_status == "active":
            return True
        if self.subscription_status == "trial" and self.trial_ends_at:
            return datetime.now(timezone.utc) < _ensure_aware_utc(self.trial_ends_at)
        return False

    def can_create_signature(self) -> bool:
        """
        Check if user can create a new signature based on subscription tier.

        Free tier: 1 unlocked signature. Pro tier: unlimited.
        Locked signatures (system-imposed on downgrade) do not count against
        the free tier limit — only unlocked signatures are considered.

        Returns:
            True if user can create a signature, False otherwise.
        """
        if self.subscription_tier == "pro":
            return True

        # Count only unlocked signatures — locked ones don't consume the free slot
        unlocked_count: int = self.signatures.filter_by(locked=False).count()
        return unlocked_count < 1

    # ========================================
    # UTILITY METHODS
    # ========================================

    def __repr__(self) -> str:
        return f"<User {self.email}>"

    def to_dict(self) -> dict:
        """
        Serialize user to a dictionary safe for API responses.

        Security: Never includes password_hash or reset/verification tokens.
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
