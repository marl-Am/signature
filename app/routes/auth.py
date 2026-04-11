# app/routes/auth.py
"""
Authentication routes blueprint.
Handles user registration, login, logout, and password reset.
"""

import logging
from urllib.parse import urlparse, urljoin
from typing import Union

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.wrappers import Response

from app.services.user_service import UserService

logger = logging.getLogger(__name__)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def _is_safe_redirect_url(target: str) -> bool:
    """
    A10/A01: Validate that a redirect target is a local URL.
    Prevents open-redirect attacks by rejecting any URL pointing to a
    different host.
    """
    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))
    return test_url.scheme in ("http", "https") and ref_url.netloc == test_url.netloc


@auth_bp.route("/register", methods=["GET", "POST"])
def register() -> Union[str, Response]:
    """User registration page."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email: str = request.form.get("email", "").strip()
        password: str = request.form.get("password", "")
        name: str = request.form.get("name", "").strip()

        user, error_message = UserService.register_user(
            email=email,
            password=password,
            name=name,
        )

        if user:
            login_user(user)

            # Generate token and send verification email
            token: str = user.generate_verification_token()
            verify_url: str = url_for("auth.verify_email", token=token, _external=True)
            try:
                from app.services.email_service import send_verification_email

                success, err = send_verification_email(
                    to_email=user.email,
                    to_name=user.name,
                    verify_url=verify_url,
                )
                if not success:
                    logger.warning(
                        "Verification email failed for %s: %s", user.email, err
                    )
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Unexpected error sending verification email for %s: %s",
                    user.email,
                    exc,
                )

            flash(
                "Registration successful! Please check your email to verify your address.",
                "success",
            )
            return redirect(url_for("dashboard.index"))
        else:
            flash(f"Registration failed: {error_message}", "danger")
            return render_template("auth/register.html", email=email, name=name)

    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> Union[str, Response]:
    """User login page."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email: str = request.form.get("email", "").strip()
        password: str = request.form.get("password", "")
        remember: bool = request.form.get("remember") == "on"

        user, error_message = UserService.authenticate_user(
            email=email,
            password=password,
        )

        if user:
            login_user(user, remember=remember)
            flash("Login successful!", "success")

            # A10: Only redirect to `next` if it is a safe local URL
            next_page: str | None = request.args.get("next")
            if next_page and _is_safe_redirect_url(next_page):
                return redirect(next_page)
            return redirect(url_for("dashboard.index"))
        else:
            # A07: Generic message — do not reveal whether the email exists
            flash("Invalid email or password.", "danger")
            return render_template("auth/login.html", email=email)

    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout() -> Response:
    """Log out the current user and clear the session."""
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("index"))


@auth_bp.route("/verify-email/<string:token>")
def verify_email(token: str) -> Response:
    """
    Email verification endpoint — reached via the link emailed after registration.

    A07: Token is single-use; it is cleared from the DB on successful verification.
    A01: Any authenticated user can verify their own email via this link.
         Mismatched tokens simply find no user and show an error.
    """
    from app.models.user import User

    user: User | None = User.query.filter_by(email_verification_token=token).first()

    if user is None:
        # Token not found — already used, expired, or tampered with
        flash(
            "This verification link is invalid or has already been used. "
            "Please request a new one.",
            "danger",
        )
        return redirect(url_for("auth.login"))

    user.verify_email(token)
    logger.info("Email verified for user %s", user.email)

    # If already logged in, stay on dashboard; otherwise go to login
    if current_user.is_authenticated:
        flash("Your email address has been verified.", "success")
        return redirect(url_for("dashboard.index"))

    flash(
        "Your email address has been verified. You can now log in.",
        "success",
    )
    return redirect(url_for("auth.login"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password() -> Union[str, Response]:
    """Password reset request page."""
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email: str = request.form.get("email", "").strip()

        # Returns (success, message, token_or_none)
        _, message, token = UserService.initiate_password_reset(email=email)

        # Only send the email when a real user was found (token is not None)
        if token is not None:
            reset_url: str = url_for("auth.reset_password", token=token, _external=True)
            try:
                from app.services.email_service import send_password_reset_email

                # Look up the user solely to get their name for the email greeting
                user = UserService.get_user_by_email(email)
                to_name: str = user.name if user else "there"

                success, err = send_password_reset_email(
                    to_email=email,
                    to_name=to_name,
                    reset_url=reset_url,
                )
                if not success:
                    logger.warning("Password reset email failed for %s: %s", email, err)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Unexpected error sending reset email for %s: %s", email, exc
                )

        # A07: Always show the same flash message regardless of outcome
        flash(message, "info")
        return redirect(url_for("auth.login"))

    return render_template("auth/forgot_password.html")


@auth_bp.route("/reset-password/<string:token>", methods=["GET", "POST"])
def reset_password(token: str) -> Union[str, Response]:
    """
    Password reset form — reached via the link emailed to the user.

    GET:  Render the form (token is validated on POST, not GET, to avoid
          consuming the token on simple page loads).
    POST: Validate the token, set the new password, log the user in.
    """
    if current_user.is_authenticated:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        new_password: str = request.form.get("password", "")
        confirm_password: str = request.form.get("confirm_password", "")

        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
            return render_template("auth/reset_password.html", token=token)

        success, error_message = UserService.reset_password(
            token=token,
            new_password=new_password,
        )

        if success:
            flash(
                "Your password has been reset. You can now log in with your new password.",
                "success",
            )
            return redirect(url_for("auth.login"))
        else:
            # Token expired or invalid
            flash(f"Password reset failed: {error_message}", "danger")
            return render_template("auth/reset_password.html", token=token)

    return render_template("auth/reset_password.html", token=token)


@auth_bp.route("/resend-verification")
@login_required
def resend_verification() -> Response:
    """
    Resend the verification email to the current user.
    Only useful if the user is logged in but not yet verified.
    """
    if current_user.email_verified:
        flash("Your email address is already verified.", "info")
        return redirect(url_for("dashboard.index"))

    token: str = current_user.generate_verification_token()
    verify_url: str = url_for("auth.verify_email", token=token, _external=True)

    try:
        from app.services.email_service import send_verification_email

        success, err = send_verification_email(
            to_email=current_user.email,
            to_name=current_user.name,
            verify_url=verify_url,
        )
        if success:
            flash("Verification email sent. Please check your inbox.", "success")
        else:
            logger.warning(
                "Resend verification failed for %s: %s", current_user.email, err
            )
            flash("Could not send the email. Please try again later.", "danger")
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Unexpected error resending verification for %s: %s",
            current_user.email,
            exc,
        )
        flash("An unexpected error occurred. Please try again later.", "danger")

    return redirect(url_for("dashboard.index"))
