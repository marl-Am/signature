# tests/test_billing.py
"""
Tests for app/routes/billing.py: Stripe Checkout initiation and webhook
event handling.

All calls to the real Stripe API are mocked — these tests verify our own
routing, signature-verification gate, and database updates, not Stripe's
behavior itself.
"""

from types import SimpleNamespace
from unittest.mock import patch

import stripe
from flask import Flask
from flask.testing import FlaskClient

from app import db
from app.models.signature import Signature
from app.models.user import User
from tests.conftest import register_via_client

def _configure_stripe(app: Flask) -> None:
    app.config.update(
        STRIPE_SECRET_KEY="sk_test_dummy",
        STRIPE_WEBHOOK_SECRET="whsec_dummy",
        STRIPE_PRO_PRICE_ID="price_monthly_dummy",
        STRIPE_PRO_PRICE_ID_YEARLY="price_yearly_dummy",
    )


def _login_pro_candidate(
    app: Flask, client: FlaskClient, email: str = "billing@example.com"
) -> User:
    _configure_stripe(app)
    register_via_client(client, email=email)
    user = User.query.filter_by(email=email).first()
    assert user is not None
    return user


# ---------------------------------------------------------------------------
# /billing/upgrade
# ---------------------------------------------------------------------------


def test_upgrade_requires_login(app: Flask, client: FlaskClient) -> None:
    _configure_stripe(app)
    response = client.get("/billing/upgrade")
    assert response.status_code == 302
    assert "login" in response.headers["Location"].lower()


def test_upgrade_redirects_to_stripe_checkout(app: Flask, client: FlaskClient) -> None:
    _login_pro_candidate(app, client)

    fake_session = SimpleNamespace(url="https://checkout.stripe.com/fake-session")
    with patch(
        "app.routes.billing.stripe.checkout.Session.create", return_value=fake_session
    ):
        response = client.get("/billing/upgrade", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["Location"] == "https://checkout.stripe.com/fake-session"


def test_upgrade_already_pro_shows_info(app: Flask, client: FlaskClient) -> None:
    user = _login_pro_candidate(app, client, email="alreadypro@example.com")

    db_user = db.session.get(User, user.id)
    assert db_user is not None
    db_user.subscription_tier = "pro"

    db.session.commit()


def test_upgrade_missing_price_id_shows_error(app: Flask, client: FlaskClient) -> None:
    register_via_client(client, email="nopricecfg@example.com")
    app.config.update(STRIPE_PRO_PRICE_ID="", STRIPE_PRO_PRICE_ID_YEARLY="")

    response = client.get("/billing/upgrade", follow_redirects=True)

    assert b"not configured yet" in response.data


def test_upgrade_stripe_error_shows_friendly_message(
    app: Flask, client: FlaskClient
) -> None:
    _login_pro_candidate(app, client, email="stripefail@example.com")

    with patch(
        "app.routes.billing.stripe.checkout.Session.create",
        side_effect=stripe.StripeError("simulated failure"),
    ):
        response = client.get("/billing/upgrade", follow_redirects=True)

    assert b"Could not connect to payment provider" in response.data


# ---------------------------------------------------------------------------
# /billing/webhook
# ---------------------------------------------------------------------------


def test_webhook_rejects_invalid_signature(app: Flask, client: FlaskClient) -> None:
    _configure_stripe(app)

    with patch(
        "app.routes.billing.stripe.Webhook.construct_event",
        side_effect=stripe.SignatureVerificationError("bad sig", "sig_header"),
    ):
        response = client.post(
            "/billing/webhook",
            data=b"{}",
            headers={"Stripe-Signature": "invalid"},
        )

    assert response.status_code == 400


def test_webhook_rejects_missing_webhook_secret(
    app: Flask, client: FlaskClient
) -> None:
    app.config.update(STRIPE_WEBHOOK_SECRET="")

    response = client.post(
        "/billing/webhook", data=b"{}", headers={"Stripe-Signature": "whatever"}
    )

    assert response.status_code == 500


def test_webhook_checkout_completed_upgrades_user_and_unlocks_signatures(
    app: Flask, client: FlaskClient
) -> None:
    user = _login_pro_candidate(app, client, email="upgrademe@example.com")

    sig = Signature(
        user_id=user.id,
        name="Locked Sig",
        full_name="Jane Doe",
        tracking_code="tc_locked_1",
        html_content="<div>sig</div>",
        locked=True,
    )
    db.session.add(sig)
    db.session.commit()
    sig_id = sig.id

    fake_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": SimpleNamespace(
                client_reference_id=str(user.id),
                customer="cus_test123",
                subscription="sub_test123",
            )
        },
    }

    with patch(
        "app.routes.billing.stripe.Webhook.construct_event", return_value=fake_event
    ):
        response = client.post(
            "/billing/webhook",
            data=b"{}",
            headers={"Stripe-Signature": "valid"},
        )

    assert response.status_code == 200

    updated_user = db.session.get(User, user.id)
    assert updated_user is not None
    assert updated_user.subscription_tier == "pro"
    assert updated_user.stripe_customer_id == "cus_test123"

    updated_sig = db.session.get(Signature, sig_id)
    assert updated_sig is not None
    assert updated_sig.locked is False


def test_webhook_checkout_completed_ignores_other_users(
    app: Flask, client: FlaskClient
) -> None:
    """A01: the webhook must only ever modify the user named in client_reference_id."""
    victim = _login_pro_candidate(app, client, email="victim@example.com")
    client.get("/auth/logout")
    attacker = _login_pro_candidate(app, client, email="attacker@example.com")

    fake_event = {
        "type": "checkout.session.completed",
        "data": {
            "object": SimpleNamespace(
                client_reference_id=str(victim.id),
                customer="cus_victim",
                subscription="sub_victim",
            )
        },
    }

    with patch(
        "app.routes.billing.stripe.Webhook.construct_event", return_value=fake_event
    ):
        client.post(
            "/billing/webhook", data=b"{}", headers={"Stripe-Signature": "valid"}
        )

    attacker_after = db.session.get(User, attacker.id)
    victim_after = db.session.get(User, victim.id)
    assert attacker_after is not None and victim_after is not None
    assert attacker_after.subscription_tier == "free"
    assert victim_after.subscription_tier == "pro"


def test_webhook_subscription_deleted_downgrades_and_locks_extra_signatures(
    app: Flask, client: FlaskClient
) -> None:
    user = _login_pro_candidate(app, client, email="downgrade@example.com")

    db_user = db.session.get(User, user.id)
    assert db_user is not None
    db_user.subscription_tier = "pro"
    db_user.stripe_customer_id = "cus_downgrade"

    sig1 = Signature(
        user_id=user.id,
        name="Oldest",
        full_name="Jane Doe",
        tracking_code="tc_old",
        html_content="<div>1</div>",
    )
    db.session.add(sig1)
    db.session.commit()

    sig2 = Signature(
        user_id=user.id,
        name="Newest",
        full_name="Jane Doe",
        tracking_code="tc_new",
        html_content="<div>2</div>",
    )
    db.session.add(sig2)
    db.session.commit()

    sig1_id, sig2_id = sig1.id, sig2.id

    fake_event = {
        "type": "customer.subscription.deleted",
        "data": {
            "object": SimpleNamespace(
                customer="cus_downgrade",
                current_period_end=None,
            )
        },
    }

    with patch(
        "app.routes.billing.stripe.Webhook.construct_event", return_value=fake_event
    ):
        response = client.post(
            "/billing/webhook", data=b"{}", headers={"Stripe-Signature": "valid"}
        )

    assert response.status_code == 200

    updated_user = db.session.get(User, user.id)
    assert updated_user is not None
    assert updated_user.subscription_tier == "free"
    assert updated_user.subscription_status == "cancelled"

    oldest = db.session.get(Signature, sig1_id)
    newest = db.session.get(Signature, sig2_id)
    assert oldest is not None and newest is not None
    assert oldest.locked is False
    assert newest.locked is True


def test_webhook_subscription_updated_maps_status(
    app: Flask, client: FlaskClient
) -> None:
    user = _login_pro_candidate(app, client, email="statusmap@example.com")

    db_user = db.session.get(User, user.id)
    assert db_user is not None
    db_user.stripe_customer_id = "cus_statusmap"
    db.session.commit()

    fake_event = {
        "type": "customer.subscription.updated",
        "data": {
            "object": SimpleNamespace(
                customer="cus_statusmap",
                status="past_due",
                cancel_at_period_end=False,
            )
        },
    }

    with patch(
        "app.routes.billing.stripe.Webhook.construct_event", return_value=fake_event
    ):
        client.post(
            "/billing/webhook", data=b"{}", headers={"Stripe-Signature": "valid"}
        )

    updated_user = db.session.get(User, user.id)
    assert updated_user is not None
    assert (
        updated_user.subscription_status == "active"
    )  # past_due maps to active per status_map
