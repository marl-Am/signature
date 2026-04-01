# app/routes/billing.py
"""
Billing routes — Stripe Checkout integration.

Flow:
  1. User clicks Upgrade → GET /billing/upgrade
       Creates a Stripe Checkout Session (server-side) and redirects the
       browser to Stripe's hosted payment page.

  2. Payment succeeds → Stripe redirects to GET /billing/success
       Shows a confirmation flash. The account is NOT upgraded here —
       that happens in the webhook (step 4), which is the authoritative source.

  3. User cancels on Stripe → GET /billing/cancel
       Shows a cancellation flash, returns to pricing.

  4. Stripe POSTs to /billing/webhook
       Verifies the Stripe signature (A08: integrity), then upgrades or
       downgrades the account based on the event type.

Security notes:
  - A02: Secret key and webhook secret loaded from env, never hardcoded.
  - A08: Every webhook payload is verified with stripe.Webhook.construct_event
         before any database write occurs.
  - A01: Upgrade only modifies the user identified by client_reference_id
         (set to current_user.id when creating the session), never a
         user-supplied value from the webhook payload.
  - SSRF (A10): No outbound URL is constructed from user input.
"""

import logging
from typing import Union

import stripe
from flask import (
    Blueprint,
    current_app,
    flash,
    redirect,
    request,
    url_for,
    Response,
    make_response,
)
from flask_login import login_required, current_user
from datetime import datetime

from app import db
from app.models.user import User

logger = logging.getLogger(__name__)

billing_bp = Blueprint("billing", __name__, url_prefix="/billing")


def _stripe_client() -> None:
    """Return a configured Stripe client using the secret key from config."""
    stripe.api_key = current_app.config["STRIPE_SECRET_KEY"]
    return stripe


# ---------------------------------------------------------------------------
# 1. Initiate checkout
# ---------------------------------------------------------------------------


@billing_bp.route("/upgrade")
@login_required
def upgrade() -> Response:
    """
    Create a Stripe Checkout Session and redirect the user to Stripe.

    If the user is already on Pro, send them to the dashboard instead.
    """
    if current_user.subscription_tier == "pro":
        flash("You are already on the Pro plan.", "info")
        return redirect(url_for("dashboard.index"))

    price_id: str = current_app.config["STRIPE_PRO_PRICE_ID"]
    if not price_id:
        logger.error("STRIPE_PRO_PRICE_ID is not configured.")
        flash("Billing is not configured yet. Please try again later.", "danger")
        return redirect(url_for("pricing"))

    _stripe_client()

    # Build the session params
    session_params: dict = {
        "mode": "subscription",
        "line_items": [{"price": price_id, "quantity": 1}],
        # client_reference_id lets us identify the user in the webhook (A01)
        "client_reference_id": str(current_user.id),
        "success_url": url_for("billing.success", _external=True)
        + "?session_id={CHECKOUT_SESSION_ID}",
        "cancel_url": url_for("billing.cancel", _external=True),
        "allow_promotion_codes": True,
    }

    # Re-use an existing Stripe customer if we have one, so the user's
    # billing history is consolidated in one Stripe record.
    if current_user.stripe_customer_id:
        session_params["customer"] = current_user.stripe_customer_id
    else:
        session_params["customer_email"] = current_user.email

    try:
        checkout_session = stripe.checkout.Session.create(**session_params)
    except stripe.StripeError as exc:
        logger.exception("Stripe Checkout Session creation failed: %s", exc)
        flash("Could not connect to payment provider. Please try again.", "danger")
        return redirect(url_for("pricing"))

    return redirect(checkout_session.url, code=303)


# ---------------------------------------------------------------------------
# 2. Success landing
# ---------------------------------------------------------------------------


@billing_bp.route("/success")
@login_required
def success() -> Response:
    """
    Landing page after the user completes the Stripe Checkout form.

    The account upgrade is handled by the webhook — this route only shows
    a confirmation message. A short delay before the webhook fires means
    the dashboard may still show 'Free' briefly, which is expected.
    """
    flash(
        "Payment received! Your account will be upgraded to Pro within a few seconds.",
        "success",
    )
    return redirect(url_for("dashboard.index"))


# ---------------------------------------------------------------------------
# 3. Cancel landing
# ---------------------------------------------------------------------------


@billing_bp.route("/cancel")
@login_required
def cancel() -> Response:
    """Landing page when the user clicks 'Back' on the Stripe Checkout page."""
    flash("Upgrade cancelled. You can upgrade any time from the pricing page.", "info")
    return redirect(url_for("pricing"))


# ---------------------------------------------------------------------------
# 4. Stripe webhook
# ---------------------------------------------------------------------------


@billing_bp.route("/webhook", methods=["POST"])
def webhook() -> Union[Response, tuple[Response, int]]:
    """
    Receive and process Stripe webhook events.

    A08 (Integrity): The payload signature is verified with
    stripe.Webhook.construct_event before any logic runs. An invalid
    signature returns 400 immediately.

    This endpoint intentionally does NOT require @login_required —
    it is called by Stripe's servers, not by a browser session.
    """
    payload: bytes = request.get_data()
    sig_header: str | None = request.headers.get("Stripe-Signature")
    webhook_secret: str = current_app.config["STRIPE_WEBHOOK_SECRET"]

    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET is not configured.")
        return make_response("Webhook secret not configured.", 500), 500

    # --- Verify signature (A08) ---
    try:
        _stripe_client()
        event = stripe.Webhook.construct_event(payload, sig_header, webhook_secret)
    except ValueError:
        # Payload could not be parsed
        logger.warning("Stripe webhook: invalid payload received.")
        return make_response("Invalid payload.", 400), 400
    except stripe.SignatureVerificationError:
        # Signature mismatch — reject immediately
        logger.warning("Stripe webhook: signature verification failed.")
        return make_response("Invalid signature.", 400), 400

    event_type: str = event["type"]
    logger.info("Stripe webhook received: %s", event_type)

    # --- Route events ---
    if event_type == "checkout.session.completed":
        _handle_checkout_completed(event["data"]["object"])

    elif event_type == "customer.subscription.deleted":
        _handle_subscription_deleted(event["data"]["object"])

    elif event_type == "customer.subscription.updated":
        _handle_subscription_updated(event["data"]["object"])

    # Return 200 for all unhandled events so Stripe does not retry them.
    return make_response("", 200)


# ---------------------------------------------------------------------------
# Webhook helpers
# ---------------------------------------------------------------------------


def _handle_checkout_completed(session) -> None:
    user_id_str: str | None = getattr(session, "client_reference_id", None)
    if not user_id_str or not str(user_id_str).isdigit():
        logger.error(
            "checkout.session.completed: missing or invalid client_reference_id."
        )
        return

    user: User | None = db.session.get(User, int(user_id_str))
    if user is None:
        logger.error("checkout.session.completed: no user found for id=%s", user_id_str)
        return

    user.stripe_customer_id = getattr(session, "customer", None)
    user.stripe_subscription_id = getattr(session, "subscription", None)
    user.subscription_status = "active"
    user.subscription_tier = "pro"
    user.subscription_ends_at = None

    db.session.commit()
    logger.info("User %s upgraded to Pro.", user.id)


def _handle_subscription_deleted(subscription) -> None:
    stripe_customer_id: str | None = getattr(subscription, "customer", None)
    if not stripe_customer_id:
        logger.error("customer.subscription.deleted: missing customer id.")
        return

    user: User | None = User.query.filter_by(
        stripe_customer_id=stripe_customer_id
    ).first()
    if user is None:
        logger.error(
            "customer.subscription.deleted: no user found for customer=%s",
            stripe_customer_id,
        )
        return

    user.subscription_status = "cancelled"
    user.subscription_tier = "free"
    user.stripe_subscription_id = None

    period_end: int | None = getattr(subscription, "current_period_end", None)
    if period_end:
        user.subscription_ends_at = datetime.utcfromtimestamp(period_end)

    db.session.commit()
    logger.info("User %s downgraded to Free.", user.id)


def _handle_subscription_updated(subscription) -> None:
    stripe_customer_id: str | None = getattr(subscription, "customer", None)
    stripe_status: str | None = getattr(subscription, "status", None)

    if not stripe_customer_id or not stripe_status:
        return

    user: User | None = User.query.filter_by(
        stripe_customer_id=stripe_customer_id
    ).first()
    if user is None:
        return

    status_map: dict[str, str] = {
        "active": "active",
        "trialing": "trial",
        "past_due": "active",
        "canceled": "cancelled",
        "unpaid": "expired",
    }
    user.subscription_status = status_map.get(stripe_status, user.subscription_status)

    db.session.commit()
    logger.info("User %s subscription updated to %s.", user.id, stripe_status)
