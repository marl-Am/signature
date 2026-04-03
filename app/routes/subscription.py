# app/routes/subscription.py
"""
Subscription management routes.

Routes:
  GET  /subscription/manage  — Show current plan details fetched live from Stripe.
  POST /subscription/cancel  — Cancel at period end; webhook handles the downgrade.

Security notes:
  - A01: @login_required on every route; cancellation verifies the subscription
         belongs to the current user via stripe_customer_id, not a user-supplied id.
  - A02: No secrets handled here — Stripe key loaded from config in _stripe_client().
  - A10: No outbound URL constructed from user input.
"""

import logging
from typing import Union

import stripe
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    render_template,
    request,
    url_for,
    Response,
)
from flask_login import login_required, current_user
from datetime import datetime

from app import db
from app.models.user import User

logger = logging.getLogger(__name__)

subscription_bp = Blueprint("subscription", __name__, url_prefix="/subscription")


def _init_stripe() -> None:
    """Configure Stripe with the secret key from app config."""
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]


# ---------------------------------------------------------------------------
# Manage page
# ---------------------------------------------------------------------------


@subscription_bp.route("/manage")
@login_required
def manage() -> str:
    """
    Render the subscription management page.

    Fetches live subscription data from Stripe when the user is on Pro
    so billing dates are always accurate.
    """
    _init_stripe()

    stripe_sub: dict | None = None
    stripe_error: bool = False

    if current_user.subscription_tier == "pro" and current_user.stripe_subscription_id:
        try:
            stripe_sub = stripe.Subscription.retrieve(
                current_user.stripe_subscription_id
            )
        except stripe.StripeError as exc:
            logger.exception(
                "Could not retrieve Stripe subscription for user %s: %s",
                current_user.id,
                exc,
            )
            stripe_error = True

    # Derive human-readable values for the template
    period_end: datetime | None = None
    cancel_at_period_end: bool = False

    if stripe_sub:
        raw_end: int | None = getattr(stripe_sub, "cancel_at", None)
        if raw_end:
            period_end = datetime.utcfromtimestamp(raw_end)
        cancel_at_period_end = bool(getattr(stripe_sub, "cancel_at_period_end", False))

    # Fallback to DB value if the live Stripe call returned nothing
    if period_end is None and current_user.subscription_ends_at:
        period_end = current_user.subscription_ends_at

    return render_template(
        "subscription/manage.html",
        period_end=period_end,
        cancel_at_period_end=cancel_at_period_end,
        stripe_error=stripe_error,
    )


# ---------------------------------------------------------------------------
# Cancel subscription
# ---------------------------------------------------------------------------


@subscription_bp.route("/cancel", methods=["POST"])
@login_required
def cancel() -> Response:
    """
    Cancel the current user's subscription at the end of the billing period.

    Sets cancel_at_period_end=True on the Stripe subscription so the user
    retains Pro access until their paid period expires.  The webhook
    customer.subscription.deleted fires at period end and downgrades the DB.

    A01: We only cancel the subscription stored on current_user — never a
         caller-supplied subscription id.
    """
    if current_user.subscription_tier != "pro":
        flash("You do not have an active Pro subscription to cancel.", "warning")
        return redirect(url_for("subscription.manage"))

    if not current_user.stripe_subscription_id:
        logger.error(
            "Cancel attempted for user %s but stripe_subscription_id is missing.",
            current_user.id,
        )
        flash("Could not locate your subscription. Please contact support.", "danger")
        return redirect(url_for("subscription.manage"))

    _init_stripe()

    try:
        stripe.Subscription.modify(
            current_user.stripe_subscription_id,
            cancel_at_period_end=True,
        )
    except stripe.StripeError as exc:
        logger.exception(
            "Failed to cancel subscription for user %s: %s", current_user.id, exc
        )
        flash("Could not cancel your subscription. Please try again.", "danger")
        return redirect(url_for("subscription.manage"))

    logger.info(
        "User %s set subscription %s to cancel at period end.",
        current_user.id,
        current_user.stripe_subscription_id,
    )
    flash(
        "Your subscription has been cancelled. "
        "You will retain Pro access until the end of your current billing period.",
        "success",
    )
    return redirect(url_for("subscription.manage"))
