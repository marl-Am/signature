# tests/test_tracking.py
"""
Tests for app/routes/tracking.py: the open pixel and click redirect
endpoints, and the scanner/proxy filtering that guards both.

These routes are intentionally public (no login required) — see the
module docstring in tracking.py for the security rationale (A01, A09,
A10). Tests here exercise the real routes end to end against the test
database, rather than unit-testing _is_scanner_request() in isolation,
since the thing that actually matters is what gets written to
total_opens/total_clicks for a real request.
"""

from unittest.mock import patch

from flask import Flask
from flask.testing import FlaskClient

from app import db
from app.models.analytics import SignatureClick, SignatureOpen
from app.models.signature import Signature
from app.models.user import User
from tests.conftest import register_via_client, get_user_by_email


def _create_signature(app: Flask, email: str, tracking_code: str) -> int:
    """
    Create a Signature with all four trackable platform URLs set, owned by
    a freshly registered user. Returns the signature's id.
    """
    register_via_client(app.test_client(), email=email)
    user: User = get_user_by_email(app, email)

    sig = Signature(
        user_id=user.id,
        name="Test Sig",
        full_name="Jane Doe",
        tracking_code=tracking_code,
        html_content="<div>sig</div>",
        linkedin_url="https://linkedin.com/in/janedoe",
        twitter_url="https://x.com/janedoe",
        facebook_url="https://facebook.com/janedoe",
        instagram_url="https://instagram.com/janedoe",
        website="https://example.com",
    )
    db.session.add(sig)
    db.session.commit()
    return sig.id


# ---------------------------------------------------------------------------
# /track/pixel/<code>.gif
# ---------------------------------------------------------------------------


def test_pixel_unknown_code_still_returns_gif(client: FlaskClient) -> None:
    """
    Silent-fail requirement from the module docstring: an invalid tracking
    code must not reveal that fact via a different response.
    """
    response = client.get("/track/pixel/not-a-real-code.gif")

    assert response.status_code == 200
    assert response.content_type == "image/gif"


def test_pixel_valid_code_increments_opens(app: Flask, client: FlaskClient) -> None:
    sig_id = _create_signature(app, "pixelopen@example.com", "tc_pixel_open")

    response = client.get(
        "/track/pixel/tc_pixel_open.gif",
        headers={"User-Agent": "Mozilla/5.0 (real browser)"},
    )

    assert response.status_code == 200
    updated = db.session.get(Signature, sig_id)
    assert updated is not None
    assert updated.total_opens == 1
    assert updated.last_opened_at is not None

    opens = SignatureOpen.query.filter_by(signature_id=sig_id).all()
    assert len(opens) == 1


def test_pixel_known_proxy_user_agent_does_not_increment(
    app: Flask, client: FlaskClient
) -> None:
    """Proofpoint's scanner UA is on the allow-list of things to ignore."""
    sig_id = _create_signature(app, "pixelproofpoint@example.com", "tc_pixel_pp")

    client.get(
        "/track/pixel/tc_pixel_pp.gif",
        headers={"User-Agent": "Proofpoint-Scanner/1.0"},
    )

    updated = db.session.get(Signature, sig_id)
    assert updated is not None
    assert updated.total_opens == 0
    assert SignatureOpen.query.filter_by(signature_id=sig_id).count() == 0


def test_pixel_google_image_proxy_user_agent_is_now_counted(
    app: Flask, client: FlaskClient
) -> None:
    """
    Regression test for the 2026-08-06 Gmail-opens bug: a genuine Gmail
    open comes through with a User-Agent ending in
    "(via ggpht.com GoogleImageProxy)" — confirmed directly from production
    logs. This string used to be on _PROXY_SIGNATURES and silently
    zeroed-out every real Gmail open. It must now be counted.
    """
    sig_id = _create_signature(app, "pixelgmail@example.com", "tc_pixel_gmail")

    client.get(
        "/track/pixel/tc_pixel_gmail.gif",
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 5.1; rv:11.0) Gecko Firefox/11.0 "
                "(via ggpht.com GoogleImageProxy)"
            )
        },
    )

    updated = db.session.get(Signature, sig_id)
    assert updated is not None
    assert updated.total_opens == 1


# ---------------------------------------------------------------------------
# /track/click/<code>/<platform>
# ---------------------------------------------------------------------------


def test_click_valid_platform_increments_and_redirects(
    app: Flask, client: FlaskClient
) -> None:
    sig_id = _create_signature(app, "clicklinkedin@example.com", "tc_click_li")

    response = client.get(
        "/track/click/tc_click_li/linkedin",
        headers={"User-Agent": "Mozilla/5.0 (real browser)"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"] == "https://linkedin.com/in/janedoe"

    updated = db.session.get(Signature, sig_id)
    assert updated is not None
    assert updated.total_clicks == 1

    clicks = SignatureClick.query.filter_by(signature_id=sig_id).all()
    assert len(clicks) == 1
    assert clicks[0].platform == "linkedin"


def test_click_unknown_platform_redirects_home_without_touching_db(
    app: Flask, client: FlaskClient
) -> None:
    """A10: platform is validated against a fixed allow-list before any DB lookup."""
    sig_id = _create_signature(app, "clickunknown@example.com", "tc_click_unknown")

    response = client.get(
        "/track/click/tc_click_unknown/myspace", follow_redirects=False
    )

    assert response.status_code == 302
    updated = db.session.get(Signature, sig_id)
    assert updated is not None
    assert updated.total_clicks == 0


def test_click_unknown_tracking_code_redirects_home(client: FlaskClient) -> None:
    response = client.get(
        "/track/click/not-a-real-code/linkedin", follow_redirects=False
    )
    assert response.status_code == 302


def test_click_blank_destination_redirects_home_without_incrementing(
    app: Flask, client: FlaskClient
) -> None:
    """
    A signature that never set a linkedin_url should redirect home rather
    than error, and must not count as a click.
    """
    register_via_client(client, email="clickblank@example.com")
    user = get_user_by_email(app, "clickblank@example.com")
    sig = Signature(
        user_id=user.id,
        name="No Socials",
        full_name="Jane Doe",
        tracking_code="tc_click_blank",
        html_content="<div>sig</div>",
    )
    db.session.add(sig)
    db.session.commit()
    sig_id = sig.id

    response = client.get(
        "/track/click/tc_click_blank/linkedin", follow_redirects=False
    )

    assert response.status_code == 302
    updated = db.session.get(Signature, sig_id)
    assert updated is not None
    assert updated.total_clicks == 0


def test_click_known_proxy_user_agent_does_not_increment(
    app: Flask, client: FlaskClient
) -> None:
    sig_id = _create_signature(app, "clickbarracuda@example.com", "tc_click_bc")

    client.get(
        "/track/click/tc_click_bc/linkedin",
        headers={"User-Agent": "Barracuda-Scanner/2.0"},
        follow_redirects=False,
    )

    updated = db.session.get(Signature, sig_id)
    assert updated is not None
    assert updated.total_clicks == 0


# ---------------------------------------------------------------------------
# Office 365 Safe Links IP-range filtering (2026-08-06 fix)
# ---------------------------------------------------------------------------


def test_click_from_office365_ip_does_not_increment(
    app: Flask, client: FlaskClient
) -> None:
    """
    A Safe Links pre-scan uses a browser-like User-Agent by design, so it
    can only be caught by source IP. is_office365_ip is patched at its
    import site in tracking.py, matching how the route actually calls it.
    """
    sig_id = _create_signature(app, "clicksafelinks@example.com", "tc_click_o365")

    with patch("app.routes.tracking.is_office365_ip", return_value=True):
        client.get(
            "/track/click/tc_click_o365/linkedin",
            headers={"User-Agent": "Mozilla/5.0 (looks like a real browser)"},
            follow_redirects=False,
        )

    updated = db.session.get(Signature, sig_id)
    assert updated is not None
    assert updated.total_clicks == 0


def test_click_from_non_office365_ip_increments_normally(
    app: Flask, client: FlaskClient
) -> None:
    sig_id = _create_signature(app, "clicknormal@example.com", "tc_click_normal")

    with patch("app.routes.tracking.is_office365_ip", return_value=False):
        client.get(
            "/track/click/tc_click_normal/linkedin",
            headers={"User-Agent": "Mozilla/5.0 (looks like a real browser)"},
            follow_redirects=False,
        )

    updated = db.session.get(Signature, sig_id)
    assert updated is not None
    assert updated.total_clicks == 1
