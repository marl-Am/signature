# app/routes/profile.py
"""
Profile routes blueprint.
Handles change email, change password, and delete account.

Security:
- A01: All routes require login; actions operate only on current_user
- A07: Email change and account deletion require password re-confirmation
"""

import logging

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, logout_user, current_user
from werkzeug.wrappers import Response

from app.services.user_service import UserService

logger = logging.getLogger(__name__)

profile_bp = Blueprint("profile", __name__, url_prefix="/profile")


@profile_bp.route("/")
@login_required
def index() -> str:
    """Render the profile page."""
    return render_template("profile/index.html")


@profile_bp.route("/change-email", methods=["POST"])
@login_required
def change_email() -> Response:
    """
    Change the current user's email address.

    Requires current password confirmation. On success the new address is
    unverified and a fresh verification email is dispatched.
    """
    current_password: str = request.form.get("current_password", "")
    new_email: str = request.form.get("new_email", "").strip()

    success, token_or_error = UserService.change_email(
        user=current_user._get_current_object(),
        current_password=current_password,
        new_email=new_email,
    )

    if not success:
        flash(f"Email change failed: {token_or_error}", "danger")
        return redirect(url_for("profile.index"))

    # token_or_error is the verification token on success
    verify_url: str = url_for(
        "auth.verify_email", token=token_or_error, _external=True
    )
    try:
        from app.services.email_service import send_verification_email

        sent, err = send_verification_email(
            to_email=current_user.email,
            to_name=current_user.name,
            verify_url=verify_url,
        )
        if not sent:
            logger.warning(
                "Verification email failed after email change for user %s: %s",
                current_user.id,
                err,
            )
    except Exception as exc:  # noqa: BLE001
        logger.exception(
            "Unexpected error sending verification email after email change for user %s: %s",
            current_user.id,
            exc,
        )

    flash(
        "Email address updated. Please check your inbox to verify the new address.",
        "success",
    )
    return redirect(url_for("profile.index"))


@profile_bp.route("/change-password", methods=["POST"])
@login_required
def change_password() -> Response:
    """Change the current user's password."""
    current_password: str = request.form.get("current_password", "")
    new_password: str = request.form.get("new_password", "")
    confirm_password: str = request.form.get("confirm_password", "")

    if new_password != confirm_password:
        flash("New passwords do not match.", "danger")
        return redirect(url_for("profile.index"))

    success, error = UserService.change_password(
        user=current_user._get_current_object(),
        current_password=current_password,
        new_password=new_password,
    )

    if not success:
        flash(f"Password change failed: {error}", "danger")
        return redirect(url_for("profile.index"))

    flash("Password updated successfully.", "success")
    return redirect(url_for("profile.index"))


@profile_bp.route("/delete-account", methods=["POST"])
@login_required
def delete_account() -> Response:
    """
    Permanently delete the current user's account.

    Logs the user out before deletion so Flask-Login does not hold a
    reference to a now-deleted user object.
    """
    current_password: str = request.form.get("current_password", "")

    # Grab the real object before logout clears the proxy
    user = current_user._get_current_object()

    success, error = UserService.delete_account(
        user=user,
        current_password=current_password,
    )

    if not success:
        flash(f"Account deletion failed: {error}", "danger")
        return redirect(url_for("profile.index"))

    logout_user()
    logger.info("User account deleted (id=%s)", user.id)
    flash("Your account has been permanently deleted.", "info")
    return redirect(url_for("index"))