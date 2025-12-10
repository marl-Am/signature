# app/services/user_service.py
"""
User service - Authentication and user management business logic

Security Features:
- A07: Authentication Failures - Account lockout, password validation
- A04: Cryptographic Failures - Secure password hashing
- A09: Logging - Track login attempts and suspicious activity
"""

from app import db
from app.models.user import User
from flask import request
from typing import Optional, Tuple
from datetime import datetime, timedelta
import re


class UserService:
    """
    Service layer for user operations

    Handles registration, login, password management with OWASP security
    """

    # Password requirements (A07: Authentication Failures)
    MIN_PASSWORD_LENGTH = 8
    PASSWORD_PATTERN = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&])[A-Za-z\d@$!%*?&]{8,}$"
    )

    @staticmethod
    def validate_password(password: str) -> Tuple[bool, Optional[str]]:
        """
        Validate password meets security requirements

        Requirements:
        - At least 8 characters
        - At least one uppercase letter
        - At least one lowercase letter
        - At least one digit
        - At least one special character

        Args:
            password: Password to validate

        Returns:
            Tuple of (is_valid, error_message)
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
        Validate email format

        Args:
            email: Email to validate

        Returns:
            Tuple of (is_valid, error_message)
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
        Register a new user

        Security:
        - A07: Validates password strength
        - A04: Hashes password securely
        - Checks for duplicate emails

        Args:
            email: User's email address
            password: User's password (plain text)
            name: User's full name

        Returns:
            Tuple of (User object or None, error_message or None)
        """
        # Validate email format
        is_valid_email, email_error = UserService.validate_email(email)
        if not is_valid_email:
            return None, email_error

        # Check if email already exists
        if User.query.filter_by(email=email.lower()).first():
            return None, "An account with this email already exists"

        # Validate password strength
        is_valid_password, password_error = UserService.validate_password(password)
        if not is_valid_password:
            return None, password_error

        # Create user
        user = User(
            email=email.lower(), name=name  # Store emails in lowercase for consistency
        )
        user.set_password(password)  # A04: Secure password hashing

        # Set trial period (14 days)
        user.trial_ends_at = datetime.utcnow() + timedelta(days=14)
        user.subscription_status = "trial"
        user.subscription_tier = "free"

        db.session.add(user)
        db.session.commit()

        # TODO: Send welcome email
        # TODO: Generate email verification token and send verification email

        return user, None

    @staticmethod
    def authenticate_user(
        email: str, password: str
    ) -> Tuple[Optional[User], Optional[str]]:
        """
        Authenticate user login

        Security:
        - A07: Account lockout after failed attempts
        - A09: Logs login attempts with IP

        Args:
            email: User's email
            password: User's password (plain text)

        Returns:
            Tuple of (User object or None, error_message or None)
        """
        # Find user by email
        user = User.query.filter_by(email=email.lower()).first()

        if not user:
            # A09: Log failed login attempt (no user found)
            # TODO: Log to security logging system
            return None, "Invalid email or password"

        # A07: Check if account is locked
        if user.is_locked():
            return (
                None,
                f"Account is locked due to too many failed login attempts. Try again later.",
            )

        # Check if account is active
        if not user.is_active:
            return None, "This account has been deactivated. Please contact support."

        # Verify password
        if not user.check_password(password):
            # A07: Record failed login attempt
            user.record_failed_login()

            # A09: Log failed login attempt
            # TODO: Log to security logging system with IP address

            return None, "Invalid email or password"

        # A07: Record successful login
        ip_address = request.remote_addr if request else None
        user.record_successful_login(ip_address)

        # A09: Log successful login
        # TODO: Log to security logging system

        return user, None

    @staticmethod
    def initiate_password_reset(email: str) -> Tuple[bool, str]:
        """
        Initiate password reset process

        Security:
        - Generates secure token with expiration
        - Doesn't reveal if email exists (security through obscurity)

        Args:
            email: User's email

        Returns:
            Tuple of (success, message)
        """
        user = User.query.filter_by(email=email.lower()).first()

        if user:
            # Generate reset token
            token = user.generate_password_reset_token()

            # TODO: Send password reset email with token
            # reset_url = f"https://yourdomain.com/reset-password/{token}"
            # send_email(user.email, "Password Reset", reset_url)

        # Always return same message (don't reveal if email exists)
        return (
            True,
            "If an account exists with this email, you will receive password reset instructions.",
        )

    @staticmethod
    def reset_password(token: str, new_password: str) -> Tuple[bool, Optional[str]]:
        """
        Reset user password with token

        Args:
            token: Reset token from email
            new_password: New password to set

        Returns:
            Tuple of (success, error_message)
        """
        # Validate new password
        is_valid, error = UserService.validate_password(new_password)
        if not is_valid:
            return False, error

        # Find user by reset token
        user = User.query.filter_by(password_reset_token=token).first()

        if not user:
            return False, "Invalid or expired reset token"

        # Attempt password reset
        if user.reset_password(token, new_password):
            return True, None
        else:
            return False, "Invalid or expired reset token"

    @staticmethod
    def change_password(
        user: User, current_password: str, new_password: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Change user password (requires current password)

        Args:
            user: User object
            current_password: Current password for verification
            new_password: New password to set

        Returns:
            Tuple of (success, error_message)
        """
        # Verify current password
        if not user.check_password(current_password):
            return False, "Current password is incorrect"

        # Validate new password
        is_valid, error = UserService.validate_password(new_password)
        if not is_valid:
            return False, error

        # Don't allow same password
        if user.check_password(new_password):
            return False, "New password must be different from current password"

        # Set new password
        user.set_password(new_password)
        db.session.commit()

        return True, None

    @staticmethod
    def verify_email(token: str) -> Tuple[bool, Optional[str]]:
        """
        Verify user email with token

        Args:
            token: Verification token from email

        Returns:
            Tuple of (success, error_message)
        """
        user = User.query.filter_by(email_verification_token=token).first()

        if not user:
            return False, "Invalid verification token"

        if user.verify_email(token):
            return True, None
        else:
            return False, "Invalid verification token"

    @staticmethod
    def get_user_by_id(user_id: int) -> Optional[User]:
        """
        Get user by ID

        Args:
            user_id: User ID

        Returns:
            User object or None
        """
        return User.query.get(user_id)

    @staticmethod
    def get_user_by_email(email: str) -> Optional[User]:
        """
        Get user by email

        Args:
            email: User's email

        Returns:
            User object or None
        """
        return User.query.filter_by(email=email.lower()).first()
