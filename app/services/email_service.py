# app/services/email_service.py
"""
Email service - Brevo (formerly Sendinblue) integration for transactional emails.

Security:
- A02: API key loaded from environment, never hardcoded
- A09: All send failures are logged with context
"""

import os
import logging
from typing import Optional, Tuple, Any

import requests

logger = logging.getLogger(__name__)

BREVO_API_URL: str = "https://api.brevo.com/v3/smtp/email"
_REQUEST_TIMEOUT_SECONDS: int = 10


def _get_api_key() -> Optional[str]:
    """
    Read the Brevo API key from the environment.

    Returns None (and logs an error) if the key is missing so that the
    application can degrade gracefully instead of crashing.
    """
    api_key: Optional[str] = os.getenv("BREVO_API_KEY")
    if not api_key:
        logger.error("BREVO_API_KEY is not set — email will not be sent.")
        return None
    return api_key


def _get_from_email() -> str:
    """Return the verified sender address from env, with a safe fallback."""
    return os.getenv("BREVO_FROM_EMAIL", "no-reply@example.com")


def _send(
    to_email: str,
    to_name: str,
    subject: str,
    html_content: str,
) -> Tuple[bool, Optional[str]]:
    """
    Shared send path for all transactional emails via Brevo's REST API.

    Args:
        to_email:     Recipient email address.
        to_name:      Recipient display name.
        subject:      Email subject line.
        html_content: Rendered HTML body.

    Returns:
        Tuple of (success, error_message).
    """
    api_key: Optional[str] = _get_api_key()
    if api_key is None:
        return False, "Email service is not configured."

    payload: dict[str, Any] = {
        "sender": {"name": "Signature", "email": _get_from_email()},
        "to": [{"email": to_email, "name": to_name}],
        "subject": subject,
        "htmlContent": html_content,
    }
    headers: dict[str, str] = {
        "api-key": api_key,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        response = requests.post(
            BREVO_API_URL,
            json=payload,
            headers=headers,
            timeout=_REQUEST_TIMEOUT_SECONDS,
        )
        if response.status_code == 201:
            logger.info(
                "Email sent to %s (status %s, subject: %s)",
                to_email,
                response.status_code,
                subject,
            )
            return True, None
        else:
            logger.error(
                "Brevo returned status %s for email to %s: %s",
                response.status_code,
                to_email,
                response.text,
            )
            return False, f"Email service returned status {response.status_code}"
    except requests.RequestException as exc:
        logger.exception("Failed to send email to %s: %s", to_email, exc)
        return False, str(exc)


def send_welcome_email(to_email: str, to_name: str) -> Tuple[bool, Optional[str]]:
    """
    Send a welcome email to a newly registered user.

    Args:
        to_email: Recipient email address.
        to_name:  Recipient display name.

    Returns:
        Tuple of (success, error_message).
    """
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
    return _send(to_email, to_name, subject, html_content)


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
    return _send(to_email, to_name, subject, html_content)


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
    return _send(to_email, to_name, subject, html_content)