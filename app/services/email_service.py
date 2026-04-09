# app/services/email_service.py
"""
Email service - SendGrid integration for transactional emails.

Security:
- A02: API key loaded from environment, never hardcoded
- A09: All send failures are logged with context
"""

import os
import logging
from typing import Optional, Tuple

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

logger = logging.getLogger(__name__)


def _get_client() -> Optional[SendGridAPIClient]:
    """
    Build a SendGrid client from the environment variable.

    Returns None (and logs an error) if the key is missing so that the
    application can degrade gracefully instead of crashing.
    """
    api_key: Optional[str] = os.getenv("SENDGRID_API_KEY")
    if not api_key:
        logger.error("SENDGRID_API_KEY is not set — email will not be sent.")
        return None
    return SendGridAPIClient(api_key)


def _get_from_email() -> str:
    """Return the verified sender address from env, with a safe fallback."""
    return os.getenv("SENDGRID_FROM_EMAIL", "no-reply@example.com")


def send_welcome_email(to_email: str, to_name: str) -> Tuple[bool, Optional[str]]:
    """
    Send a welcome email to a newly registered user.

    Args:
        to_email: Recipient email address.
        to_name:  Recipient display name.

    Returns:
        Tuple of (success, error_message).
    """
    client = _get_client()
    if client is None:
        return False, "Email service is not configured."

    subject = "Welcome to Signature — your account is ready"
    html_content = f"""
    <p>Hi {to_name},</p>
    <p>Welcome! Your Signature account has been created.</p>
    <p>
      You are on a <strong>14-day free trial</strong>. Head to your
      <a href="https://signature.example.com/dashboard">dashboard</a>
      to build your first email signature.
    </p>
    <p>If you have questions, just reply to this email.</p>
    <p>— The Signature Team</p>
    """

    message = Mail(
        from_email=Email(_get_from_email(), "Signature"),
        to_emails=To(to_email, to_name),
        subject=subject,
        html_content=Content("text/html", html_content),
    )

    try:
        response = client.send(message)  # type: ignore[union-attr]
        if response.status_code in (200, 202):
            logger.info(
                "Welcome email sent to %s (status %s)", to_email, response.status_code
            )
            return True, None
        else:
            logger.error(
                "SendGrid returned status %s for welcome email to %s",
                response.status_code,
                to_email,
            )
            return False, f"Email service returned status {response.status_code}"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send welcome email to %s: %s", to_email, exc)
        return False, str(exc)


def send_verification_email(
    to_email: str, to_name: str, verify_url: str
) -> Tuple[bool, Optional[str]]:
    """
    Send an email address verification email to a newly registered user.

    Args:
        to_email:   Recipient email address.
        to_name:    Recipient display name.
        verify_url: Fully-qualified verification URL (includes the secure token).

    Returns:
        Tuple of (success, error_message).
    """
    client = _get_client()
    if client is None:
        return False, "Email service is not configured."

    subject = "Signature — please verify your email address"
    html_content = f"""
    <p>Hi {to_name},</p>
    <p>Thanks for signing up! Click the link below to verify your email address:</p>
    <p><a href="{verify_url}">{verify_url}</a></p>
    <p>This link expires in <strong>24 hours</strong>.</p>
    <p>
      If you did not create a Signature account, you can safely ignore this email.
    </p>
    <p>— The Signature Team</p>
    """

    message = Mail(
        from_email=Email(_get_from_email(), "Signature"),
        to_emails=To(to_email, to_name),
        subject=subject,
        html_content=Content("text/html", html_content),
    )

    try:
        response = client.send(message)  # type: ignore[union-attr]
        if response.status_code in (200, 202):
            logger.info(
                "Verification email sent to %s (status %s)",
                to_email,
                response.status_code,
            )
            return True, None
        else:
            logger.error(
                "SendGrid returned status %s for verification email to %s",
                response.status_code,
                to_email,
            )
            return False, f"Email service returned status {response.status_code}"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send verification email to %s: %s", to_email, exc)
        return False, str(exc)


def send_password_reset_email(
    to_email: str, to_name: str, reset_url: str
) -> Tuple[bool, Optional[str]]:
    """
    Send a password-reset email containing a one-time link.

    Args:
        to_email:  Recipient email address.
        to_name:   Recipient display name.
        reset_url: Fully-qualified reset URL (includes the secure token).

    Returns:
        Tuple of (success, error_message).
    """
    client = _get_client()
    if client is None:
        return False, "Email service is not configured."

    subject = "Signature — password reset request"
    html_content = f"""
    <p>Hi {to_name},</p>
    <p>We received a request to reset your password. Click the link below to choose a new one:</p>
    <p><a href="{reset_url}">{reset_url}</a></p>
    <p>This link expires in <strong>1 hour</strong>.</p>
    <p>
      If you did not request a password reset, you can safely ignore this email —
      your account has not been changed.
    </p>
    <p>— The Signature Team</p>
    """

    message = Mail(
        from_email=Email(_get_from_email(), "Signature"),
        to_emails=To(to_email, to_name),
        subject=subject,
        html_content=Content("text/html", html_content),
    )

    try:
        response = client.send(message)  # type: ignore[union-attr]
        if response.status_code in (200, 202):
            logger.info(
                "Password reset email sent to %s (status %s)",
                to_email,
                response.status_code,
            )
            return True, None
        else:
            logger.error(
                "SendGrid returned status %s for reset email to %s",
                response.status_code,
                to_email,
            )
            return False, f"Email service returned status {response.status_code}"
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to send password reset email to %s: %s", to_email, exc)
        return False, str(exc)