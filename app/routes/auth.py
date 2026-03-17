# app/routes/auth.py
"""
Authentication routes blueprint
Handles user registration, login, logout, and password reset
"""

from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.wrappers import Response
from typing import Union

# Import your UserService
from app.services.user_service import UserService # Assuming 'app' is the base of your project

# Create blueprint
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/register", methods=["GET", "POST"])
def register() -> Union[str, Response]:
    """
    User registration page

    POST: Process registration using UserService and handle errors/success.
    """
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        # A07: Extract and validate form data (simple presence check here)
        email: str = request.form.get("email", "").strip()
        password: str = request.form.get("password", "")
        name: str = request.form.get("name", "").strip()

        # Call the secure registration service method
        user, error_message = UserService.register_user(
            email=email,
            password=password,
            name=name
        )

        if user:
            # Registration successful
            # TODO: Consider not logging the user in immediately; require email verification first (A07)
            login_user(user)
            flash("Registration successful! You are now logged in. Please check your email for verification.", "success")
            return redirect(url_for("index"))
        else:
            # Registration failed due to validation or duplicate email
            flash(f"Registration failed: {error_message}", "danger")
            # Redirect back to registration form to try again (preserving form values is a nice UX feature)
            return render_template("auth/register.html", email=email, name=name)

    # GET request: show registration form
    return render_template("auth/register.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login() -> Union[str, Response]:
    """
    User login page

    POST: Authenticate user using UserService and create session.
    """
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        # A07: Extract credentials
        email: str = request.form.get("email", "").strip()
        password: str = request.form.get("password", "")
        remember: bool = bool(request.form.get("remember")) # Optional: for 'Remember Me' functionality

        # Call the secure authentication service method
        user, error_message = UserService.authenticate_user(
            email=email,
            password=password
        )

        if user:
            # Login successful (A07: The service layer handles success logging and failed attempt reset)
            login_user(user, remember=remember)
            flash("Login successful!", "success")
            # Redirect to the page the user tried to access, or dashboard
            next_page: str = request.args.get("next")
            return redirect(next_page or url_for("index"))
        else:
            # Login failed (A07/A09: The service layer handles failed attempts, lockout, and logging)
            # Use generic message to prevent user enumeration (A07)
            flash("Invalid email or password.", "danger")
            # Redirect back to login form (Do not expose whether email exists)
            return render_template("auth/login.html", email=email)

    # GET request: show login form
    return render_template("auth/login.html")


@auth_bp.route("/logout")
@login_required
def logout() -> Response:
    """
    Log out the current user
    """
    logout_user()
    flash("You have been logged out successfully.", "success")
    return redirect(url_for("index"))


@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password() -> Union[str, Response]:
    """
    Password reset request page

    POST: Initiate password reset using UserService.
    """
    # If user is already logged in, redirect to dashboard
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email: str = request.form.get("email", "").strip()

        # Call the password reset initiation service method
        success, message = UserService.initiate_password_reset(email=email)

        # A07: Always flash the same generic message to prevent user enumeration (security through obscurity)
        flash(message, "info")
        return redirect(url_for("auth.login"))

    # GET request: show password reset form
    return render_template("auth/forgot_password.html")

# Note: The following routes still need implementation:
# - /reset-password/<token> - Use UserService.reset_password
# - /verify-email/<token> - Use UserService.verify_email
# - /resend-verification - Use a new UserService method to resend verification email
