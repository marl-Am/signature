# app/services/user_service.py
"""
User service - Authentication and user management business logic.

Security Features:
- A07: Authentication Failures - Account lockout, password validation
- A04: Cryptographic Failures - Secure password hashing
- A09: Logging - Track login attempts and suspicious activity
"""

import logging
import re
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, Tuple
from flask import request
from app import db
from app.models.user import User

logger = logging.getLogger(__name__)


class AuthFailureReason(Enum):
    ACCOUNT_NOT_FOUND = "account_not_found"
    ACCOUNT_LOCKED = "account_locked"
    ACCOUNT_DEACTIVATED = "account_deactivated"
    INVALID_CREDENTIALS = "invalid_credentials"


class UserService:
    """
    Service layer for user operations.

    Handles registration, login, and password management with OWASP security.
    """

    # Password requirements (A07: Authentication Failures)
    MIN_PASSWORD_LENGTH = 12
    PASSWORD_PATTERN = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    )

    @staticmethod
    def validate_password(password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password meets security requirements.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if len(password) < UserService.MIN_PASSWORD_LENGTH:
            return (
                False,
                f"Password must be at least {UserService.MIN_PASSWORD_LENGTH} characters",
            )
        if not re.search(r"[a-z]", password):
            return False, "Password must contain at least one lowercase letter"
        if not re.search(r"[A-Z]", password):
            return False, "Password must contain at least one uppercase letter"
        if not re.search(r"\d", password):
            return False, "Password must contain at least one digit"
        if not re.search(r"[@$!%*?&]", password):
            return (
                False,
                "Password must contain at least one special character (@$!%*?&)",
            )
        return True, None

    @staticmethod
    def validate_email(email: str) -> Tuple[bool, Optional[str]]:
        """
        Validate email format.

        Returns:
            Tuple of (is_valid, error_message).
        """
        email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
        if not email_pattern.match(email):
            return False, "Invalid email format"
        return True, None

    @staticmethod
    def register_user(
        email: str, password: str, name: str
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Register a new user and send a welcome email.

        Security:
        - A07: Validates password strength
        - A04: Hashes password securely
        - Checks for duplicate emails

        Returns:
            Tuple of (User object or None, error_message or None).
        """
        is_valid_email, email_error = UserService.validate_email(email)
        if not is_valid_email:
            return None, email_error

        if User.query.filter_by(email=email.lower()).first():
            return None, "An account with this email already exists"

        is_valid_password, password_error = UserService.validate_password(password)
        if not is_valid_password:
            return None, password_error

        user = User(email=email.lower(), name=name)
        user.set_password(password)  # A04: Secure password hashing

        user.trial_ends_at = datetime.now(timezone.utc) + timedelta(days=14)
        user.subscription_status = "trial"
        user.subscription_tier = "free"

        db.session.add(user)
        db.session.commit()

        # Send welcome email — import here to avoid circular imports
        try:
            from app.services.email_service import send_welcome_email

            success, err = send_welcome_email(to_email=user.email, to_name=user.name)
            if not success:
                # Non-fatal: registration succeeded, email failed
                logger.warning("Welcome email failed for user %s: %s", user.id, err)
        except Exception as exc:  # noqa: BLE001
            logger.exception(
                "Unexpected error sending welcome email for user %s: %s", user.id, exc
            )

        return user, None


    @staticmethod
    def authenticate_user(
        email: str, password: str
    ) -> Tuple[Optional[User], Optional[str], Optional["AuthFailureReason"]]:
        """
        Authenticate user login.

        Returns:
            Tuple of (User object or None, error_message or None, failure_reason or None).
        """
        user = User.query.filter_by(email=email.lower()).first()

        if not user:
            return None, "Invalid email or password", AuthFailureReason.ACCOUNT_NOT_FOUND

        if user.is_locked():
            return (
                None,
                "Account is locked due to too many failed login attempts. Try again later.",
                AuthFailureReason.ACCOUNT_LOCKED,
            )

        if not user.is_active:
            return (
                None,
                "This account has been deactivated. Please contact support.",
                AuthFailureReason.ACCOUNT_DEACTIVATED,
            )

        if not user.check_password(password):
            user.record_failed_login()
            return None, "Invalid email or password", AuthFailureReason.INVALID_CREDENTIALS

        ip_address: Optional[str] = request.remote_addr if request else None
        user.record_successful_login(ip_address)

        return user, None, None

    @staticmethod
    def initiate_password_reset(email: str) -> Tuple[bool, str, Optional[str]]:
        """
        Generate a password-reset token for the given email address.

        The caller is responsible for building the reset URL (using url_for
        inside a request context) and sending the email.  This keeps HTTP
        concerns out of the service layer.

        Security:
        - Generates a secure token with expiration via the User model
        - Does NOT reveal whether the email address exists (A07)

        Returns:
            Tuple of (success, user_facing_message, token_or_none).
            token_or_none is None when no matching user was found, so the
            caller must never branch on it in a way that leaks that fact to
            the user.
        """
        SAFE_MESSAGE = (
            "If an account exists with this email, "
            "you will receive password reset instructions shortly."
        )

        user = User.query.filter_by(email=email.lower()).first()
        if not user:
            # Return the same message; do not reveal the account does not exist
            return True, SAFE_MESSAGE, None

        token: str = user.generate_password_reset_token()
        return True, SAFE_MESSAGE, token

    @staticmethod
    def reset_password(token: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Reset user password with a valid token.

        Returns:
            Tuple of (success, error_message).
        """
        is_valid, error = UserService.validate_password(new_password)
        if not is_valid:
            return False, error

        user = User.query.filter_by(password_reset_token=token).first()
        if not user:
            return False, "Invalid or expired reset token"

        if user.reset_password(token, new_password):
            return True, None
        return False, "Invalid or expired reset token"

    @staticmethod
    def change_password(
        user: User, current_password: str, new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Change password (requires current password for verification).

        Returns:
            Tuple of (success, error_message).
        """
        if not user.check_password(current_password):
            return False, "Current password is incorrect"

        is_valid, error = UserService.validate_password(new_password)
        if not is_valid:
            return False, error

        if user.check_password(new_password):
            return False, "New password must be different from current password"

        user.set_password(new_password)
        db.session.commit()
        return True, None

    @staticmethod
    def verify_email(token: str) -> Tuple[bool, Optional[str]]:
        """
        Verify user email address with token.

        Returns:
            Tuple of (success, error_message).
        """
        user = User.query.filter_by(email_verification_token=token).first()
        if not user:
            return False, "Invalid verification token"

        if user.verify_email(token):
            return True, None
        return False, "Invalid verification token"

    @staticmethod
    def change_email(
        user: "User", current_password: str, new_email: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Change the user's email address.

        Requires current password re-confirmation (A07).
        Resets email_verified and generates a new verification token
        so the new address must be confirmed before it is trusted.

        Returns:
            Tuple of (success, token_or_error).
            On success the second element is the new verification token
            so the caller can send the verification email.
        """
        if not user.check_password(current_password):
            return False, "Current password is incorrect"

        is_valid, email_error = UserService.validate_email(new_email)
        if not is_valid:
            return False, email_error

        new_email = new_email.lower()

        if new_email == user.email:
            return False, "New email address must be different from your current one"

        if User.query.filter_by(email=new_email).first():
            return False, "An account with this email already exists"

        user.email = new_email
        user.email_verified = False
        db.session.commit()

        token: str = user.generate_verification_token()
        return True, token

    @staticmethod
    def delete_account(
        user: "User", current_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Permanently delete a user account and all associated data.

        Requires current password re-confirmation (A01/A07).
        Cascading deletes on the signatures relationship handle child rows.

        Returns:
            Tuple of (success, error_message).
        """
        if not user.check_password(current_password):
            return False, "Current password is incorrect"

        db.session.delete(user)
        db.session.commit()
        return True, None

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        return User.query.get(user_id)

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        return User.query.filter_by(email=email.lower()).first()
