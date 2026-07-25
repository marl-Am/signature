# tests/test_signatures.py
"""
Tests for app/routes/signatures.py: create, edit, delete, preview, and
ownership enforcement (A01 - Broken Access Control), plus output escaping
(A03 - Injection / stored XSS regression coverage).
"""

from flask import Flask
from flask.testing import FlaskClient

from app import db
from app.models.signature import Signature
from app.services.signature_service import SignatureService
from tests.conftest import get_user_by_email, register_via_client


def _create_signature(
    client: FlaskClient,
    name: str = "Work Signature",
    full_name: str = "Jane Doe",
    website: str = "",
    **extra: str,
):
    data = {"name": name, "full_name": full_name, "website": website, **extra}
    return client.post("/signatures/create", data=data, follow_redirects=False)


# ---------------------------------------------------------------------------
# Create
# ---------------------------------------------------------------------------


def test_create_requires_login(client: FlaskClient) -> None:
    response = _create_signature(client)
    assert response.status_code == 302
    assert "login" in response.headers["Location"].lower()


def test_create_succeeds_for_logged_in_user(app: Flask, client: FlaskClient) -> None:
    register_via_client(client, email="sig1@example.com")

    response = _create_signature(client, name="My Sig", full_name="Jane Doe")

    assert response.status_code == 302
    assert "dashboard" in response.headers["Location"].lower()

    with app.app_context():
        signature = Signature.query.filter_by(name="My Sig").first()
        assert signature is not None
        assert signature.full_name == "Jane Doe"
        assert signature.tracking_code is not None


def test_create_requires_name_and_full_name(client: FlaskClient) -> None:
    register_via_client(client, email="sig2@example.com")

    response = _create_signature(client, name="", full_name="")

    assert response.status_code == 200
    assert b"required" in response.data


def test_create_normalizes_bare_domain_to_https(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="sig3@example.com")

    _create_signature(
        client, name="URL Test", full_name="Jane Doe", website="google.com"
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="URL Test").first()
        assert signature is not None
        assert signature.website == "https://google.com"


def test_free_tier_blocks_second_signature(app: Flask, client: FlaskClient) -> None:
    register_via_client(client, email="freetier@example.com")

    first = _create_signature(client, name="First", full_name="Jane Doe")
    assert first.status_code == 302

    response = client.get("/signatures/create", follow_redirects=False)

    assert response.status_code == 302
    assert "pricing" in response.headers["Location"].lower()


def test_deleting_signature_frees_free_tier_slot(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="freeslot@example.com")
    _create_signature(client, name="First", full_name="Jane Doe")

    with app.app_context():
        signature = Signature.query.filter_by(name="First").first()
        assert signature is not None
        signature_id = signature.id

    client.post(f"/signatures/{signature_id}/delete", follow_redirects=False)

    # Should now be allowed to create again
    response = client.get("/signatures/create")
    assert response.status_code == 200  # form renders, no redirect to pricing


# ---------------------------------------------------------------------------
# Ownership (A01)
# ---------------------------------------------------------------------------


def _create_signature_for_user(
    app: Flask, client: FlaskClient, email: str, sig_name: str = "Owned Sig"
) -> int:
    register_via_client(client, email=email)
    _create_signature(client, name=sig_name, full_name="Owner Name")
    with app.app_context():
        signature = Signature.query.filter_by(name=sig_name).first()
        assert signature is not None
        return signature.id


def test_user_cannot_edit_another_users_signature(
    app: Flask, client: FlaskClient
) -> None:
    owner_client = client
    signature_id = _create_signature_for_user(app, owner_client, "owner@example.com")
    owner_client.get("/auth/logout")

    register_via_client(owner_client, email="intruder@example.com")

    response = owner_client.get(f"/signatures/{signature_id}/edit")

    assert response.status_code == 404


def test_user_cannot_preview_another_users_signature(
    app: Flask, client: FlaskClient
) -> None:
    signature_id = _create_signature_for_user(app, client, "owner2@example.com")
    client.get("/auth/logout")
    register_via_client(client, email="intruder2@example.com")

    response = client.get(f"/signatures/{signature_id}/preview")

    assert response.status_code == 404


def test_user_cannot_delete_another_users_signature(
    app: Flask, client: FlaskClient
) -> None:
    signature_id = _create_signature_for_user(app, client, "owner3@example.com")
    client.get("/auth/logout")
    register_via_client(client, email="intruder3@example.com")

    response = client.post(f"/signatures/{signature_id}/delete")

    assert response.status_code == 404

    with app.app_context():
        # Signature must still exist — the delete must not have gone through
        assert db.session.get(Signature, signature_id) is not None


# ---------------------------------------------------------------------------
# Edit
# ---------------------------------------------------------------------------


def test_owner_can_edit_own_signature(app: Flask, client: FlaskClient) -> None:
    signature_id = _create_signature_for_user(app, client, "editor@example.com")

    response = client.post(
        f"/signatures/{signature_id}/edit",
        data={
            "name": "Renamed Signature",
            "full_name": "Jane Updated",
            "website": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    with app.app_context():
        signature = db.session.get(Signature, signature_id)
        assert signature is not None
        assert signature.name == "Renamed Signature"
        assert signature.full_name == "Jane Updated"


def test_edit_requires_name_and_full_name(app: Flask, client: FlaskClient) -> None:
    signature_id = _create_signature_for_user(app, client, "editor2@example.com")

    response = client.post(
        f"/signatures/{signature_id}/edit",
        data={"name": "", "full_name": "", "website": ""},
    )

    assert response.status_code == 200
    assert b"required" in response.data


# ---------------------------------------------------------------------------
# XSS / Output Escaping (A03) — regression coverage for the stored XSS bug
# fixed in session 19. A signature saved with HTML-special or quote
# characters in free-text fields, or a dangerous URL scheme in any URL
# field, must produce escaped/rejected output in html_content — never live
# tags or a clickable dangerous href.
# ---------------------------------------------------------------------------


# --- Unit tests: SignatureService._escape() ---------------------------------


def test_escape_helper_escapes_angle_brackets_and_quotes() -> None:
    result = SignatureService._escape('<script>"test"</script>')
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    assert "&quot;" in result


def test_escape_helper_handles_none_and_empty_string() -> None:
    assert SignatureService._escape(None) == ""
    assert SignatureService._escape("") == ""


# --- Unit tests: SignatureService._sanitize_href() --------------------------


def test_sanitize_href_rejects_javascript_scheme() -> None:
    assert SignatureService._sanitize_href("javascript:alert(1)") is None


def test_sanitize_href_rejects_data_scheme() -> None:
    assert (
        SignatureService._sanitize_href("data:text/html,<script>alert(1)</script>")
        is None
    )


def test_sanitize_href_rejects_vbscript_scheme() -> None:
    assert SignatureService._sanitize_href("vbscript:msgbox(1)") is None


def test_sanitize_href_rejects_malformed_url_without_netloc() -> None:
    assert SignatureService._sanitize_href("not a url") is None


def test_sanitize_href_accepts_well_formed_https_url() -> None:
    assert (
        SignatureService._sanitize_href("https://example.com") == "https://example.com"
    )


def test_sanitize_href_returns_none_for_empty_or_none() -> None:
    assert SignatureService._sanitize_href(None) is None
    assert SignatureService._sanitize_href("") is None


# --- End-to-end: create/edit through the route, checking stored html_content -


def test_full_name_with_script_tag_is_escaped_in_stored_html(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="xss1@example.com")

    _create_signature(
        client,
        name="XSS Full Name",
        full_name="<script>alert(1)</script>",
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="XSS Full Name").first()
        assert signature is not None
        assert "<script>" not in signature.html_content
        assert "&lt;script&gt;" in signature.html_content


def test_quote_and_angle_brackets_in_full_name_cannot_inject_a_live_tag(
    app: Flask, client: FlaskClient
) -> None:
    """
    full_name is rendered as text content inside a <div>...</div>. If
    angle brackets and quotes were not escaped, a value like this could
    inject a live, executable <img onerror=...> tag into the page. Once
    escaped, the dangerous characters become harmless entities and the
    raw tag can never appear verbatim, even though the escaped text still
    visibly contains words like "onerror" and "alert" -- that's expected
    and harmless once it's inert text rather than a live tag.
    """
    register_via_client(client, email="xss2@example.com")

    live_tag = "<img src=x onerror=alert(1)>"
    _create_signature(client, name="XSS Quote Name", full_name=f'Jane">{live_tag}')

    with app.app_context():
        signature = Signature.query.filter_by(name="XSS Quote Name").first()
        assert signature is not None
        # The raw, executable tag must never appear unescaped
        assert live_tag not in signature.html_content
        # The dangerous characters must appear as harmless entities instead
        assert "&quot;" in signature.html_content
        assert "&lt;img" in signature.html_content
        assert "&gt;" in signature.html_content


def test_company_field_with_html_is_escaped(app: Flask, client: FlaskClient) -> None:
    register_via_client(client, email="xss3@example.com")

    _create_signature(
        client,
        name="XSS Company",
        full_name="Jane Doe",
        company="Acme<script>alert(1)</script>",
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="XSS Company").first()
        assert signature is not None
        assert "<script>" not in signature.html_content
        assert "&lt;script&gt;" in signature.html_content


def test_department_field_with_html_is_escaped(app: Flask, client: FlaskClient) -> None:
    register_via_client(client, email="xss4@example.com")

    live_tag = "<img src=x onerror=alert(1)>"
    _create_signature(
        client,
        name="XSS Department",
        full_name="Jane Doe",
        department=live_tag,
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="XSS Department").first()
        assert signature is not None
        assert live_tag not in signature.html_content
        assert "&lt;img" in signature.html_content
        assert "&gt;" in signature.html_content


def test_website_url_with_empty_host_produces_no_link(
    app: Flask, client: FlaskClient
) -> None:
    """
    The website contact link's href is always the app's own
    /track/click/... redirect URL, never the user's raw website value --
    the raw value only ever appears as escaped display text. So the
    meaningful thing to test here is that _sanitize_href's netloc check
    still gates whether the link is shown at all: a URL with a valid
    scheme but no host must not produce a rendered link.
    """
    register_via_client(client, email="xss5@example.com")

    _create_signature(
        client,
        name="XSS Empty Host",
        full_name="Jane Doe",
        website="https:///",
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="XSS Empty Host").first()
        assert signature is not None
        assert "track/click" not in signature.html_content


def test_logo_url_with_quote_cannot_break_out_of_src_attribute(
    app: Flask, client: FlaskClient
) -> None:
    """
    logo_url is the one field whose raw value lands directly in an
    src="..." attribute. _normalize_url leaves values that already start
    with https:// unchanged, so a URL crafted with an embedded double
    quote must still be safely escaped by _sanitize_href before reaching
    that attribute -- otherwise it could break out and inject a new one
    (e.g. onerror=alert(1)).
    """
    register_via_client(client, email="xss6@example.com")

    malicious = 'https://evil.example.com/logo.png" onerror="alert(1)'
    _create_signature(
        client, name="XSS Logo Attr Breakout", full_name="Jane Doe", logo_url=malicious
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="XSS Logo Attr Breakout").first()
        assert signature is not None
        assert 'onerror="alert(1)"' not in signature.html_content
        assert "&quot;" in signature.html_content


def test_logo_url_with_embedded_script_tag_is_html_escaped(
    app: Flask, client: FlaskClient
) -> None:
    """
    _normalize_url prepends https:// to any value that doesn't already
    start with http(s), so a raw dangerous-scheme value like a data: URL
    actually passes _sanitize_href's scheme check once normalized (its
    scheme is now "https"). The thing that actually keeps this safe is
    that the whole value, including any embedded markup, still goes
    through html.escape -- so it can only ever render as an inert, broken
    image src, never as executable markup.
    """
    register_via_client(client, email="xss7@example.com")

    malicious = "data:text/html,<script>alert(1)</script>"
    _create_signature(
        client,
        name="XSS Logo Data Scheme",
        full_name="Jane Doe",
        logo_url=malicious,
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="XSS Logo Data Scheme").first()
        assert signature is not None
        assert "<script>" not in signature.html_content
        assert "&lt;script&gt;" in signature.html_content


def test_edit_reescapes_full_name_since_html_is_fully_regenerated(
    app: Flask, client: FlaskClient
) -> None:
    """
    html_content is fully regenerated on every edit (see
    SignatureService.update_signature), so a malicious value introduced
    through an edit must be escaped exactly like one introduced at
    creation time.
    """
    signature_id = _create_signature_for_user(app, client, "xss7@example.com")

    client.post(
        f"/signatures/{signature_id}/edit",
        data={
            "name": "Owned Sig",
            "full_name": "<script>alert(1)</script>",
            "website": "",
        },
        follow_redirects=False,
    )

    with app.app_context():
        signature = db.session.get(Signature, signature_id)
        assert signature is not None
        assert "<script>" not in signature.html_content
        assert "&lt;script&gt;" in signature.html_content


# ---------------------------------------------------------------------------
# Free-tier watermark
# ---------------------------------------------------------------------------

WATERMARK_MARKER = "Sent with"


def _set_subscription_tier(app: Flask, email: str, tier: str) -> None:
    """
    Directly set a user's subscription_tier for test setup (no Stripe call).

    Deliberately does NOT open its own `with app.app_context():` block.
    The `app` fixture already keeps one app context (and one SQLAlchemy
    session) active for the whole test. Opening a second one here would
    create a separate session that never touches the User object already
    cached in the first session's identity map from registration/login --
    committing a tier change through that second session would leave the
    original session (the one every later client.post(...) call reuses)
    still holding the stale, pre-upgrade value.
    """
    user = get_user_by_email(app, email)
    user.subscription_tier = tier
    db.session.commit()


def test_free_tier_signature_includes_watermark(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="watermark1@example.com")

    _create_signature(client, name="Free Sig", full_name="Jane Doe")

    with app.app_context():
        signature = Signature.query.filter_by(name="Free Sig").first()
        assert signature is not None
        assert WATERMARK_MARKER in signature.html_content


def test_pro_tier_signature_does_not_include_watermark(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="watermark2@example.com")
    _set_subscription_tier(app, "watermark2@example.com", "pro")

    _create_signature(client, name="Pro Sig", full_name="Jane Doe")

    with app.app_context():
        signature = Signature.query.filter_by(name="Pro Sig").first()
        assert signature is not None
        assert WATERMARK_MARKER not in signature.html_content


def test_watermark_removed_after_edit_following_upgrade_to_pro(
    app: Flask, client: FlaskClient
) -> None:
    """
    The watermark is only re-evaluated when html_content is regenerated
    (create/edit) -- not automatically the instant a subscription changes.
    Confirms that upgrading, then editing, removes it.
    """
    signature_id = _create_signature_for_user(app, client, "watermark3@example.com")

    with app.app_context():
        signature = db.session.get(Signature, signature_id)
        assert signature is not None
        assert WATERMARK_MARKER in signature.html_content  # free by default

    _set_subscription_tier(app, "watermark3@example.com", "pro")

    client.post(
        f"/signatures/{signature_id}/edit",
        data={"name": "Owned Sig", "full_name": "Owner Name", "website": ""},
        follow_redirects=False,
    )

    with app.app_context():
        signature = db.session.get(Signature, signature_id)
        assert signature is not None
        assert WATERMARK_MARKER not in signature.html_content


def test_watermark_reappears_after_edit_following_downgrade(
    app: Flask, client: FlaskClient
) -> None:
    """
    Symmetric case: downgrading from pro back to free, then editing, must
    bring the watermark back.
    """
    register_via_client(client, email="watermark4@example.com")
    _set_subscription_tier(app, "watermark4@example.com", "pro")

    _create_signature(client, name="Downgrade Sig", full_name="Jane Doe")

    with app.app_context():
        signature = Signature.query.filter_by(name="Downgrade Sig").first()
        assert signature is not None
        assert WATERMARK_MARKER not in signature.html_content
        signature_id = signature.id

    _set_subscription_tier(app, "watermark4@example.com", "free")

    client.post(
        f"/signatures/{signature_id}/edit",
        data={"name": "Downgrade Sig", "full_name": "Jane Doe", "website": ""},
        follow_redirects=False,
    )

    with app.app_context():
        signature = db.session.get(Signature, signature_id)
        assert signature is not None
        assert WATERMARK_MARKER in signature.html_content


def test_watermark_survives_tracking_pixel_stripping_for_preview(
    app: Flask, client: FlaskClient
) -> None:
    """
    strip_tracking_pixel() targets only the pixel <img> tag via a narrow
    regex. Confirm it doesn't accidentally also strip the watermark, since
    the preview page relies on this function for its on-screen render.
    """
    register_via_client(client, email="watermark5@example.com")
    _create_signature(client, name="Preview Sig", full_name="Jane Doe")

    with app.app_context():
        signature = Signature.query.filter_by(name="Preview Sig").first()
        assert signature is not None
        signature_id = signature.id

    response = client.get(f"/signatures/{signature_id}/preview")

    assert response.status_code == 200
    assert WATERMARK_MARKER.encode() in response.data


# ---------------------------------------------------------------------------
# Pro-tier accent color (A01 tier gating + A03 output escaping)
#
# accent_color is interpolated directly into style="" attributes across
# every layout. Free-tier submissions must be silently ignored, and any
# submitted value -- from any tier -- must be rejected unless it is a
# strict #RRGGBB hex string, since that is what actually prevents a value
# from breaking out of the surrounding attribute (see
# SignatureService._sanitize_accent_color).
# ---------------------------------------------------------------------------


def test_free_tier_accent_color_submission_is_ignored(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="accent1@example.com")

    _create_signature(
        client, name="Free Accent Sig", full_name="Jane Doe", accent_color="#ff0000"
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="Free Accent Sig").first()
        assert signature is not None
        assert signature.accent_color == SignatureService.DEFAULT_ACCENT_COLOR
        assert "#ff0000" not in signature.html_content


def test_pro_tier_valid_accent_color_is_applied(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="accent2@example.com")
    _set_subscription_tier(app, "accent2@example.com", "pro")

    _create_signature(
        client, name="Pro Accent Sig", full_name="Jane Doe", accent_color="#ff0000"
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="Pro Accent Sig").first()
        assert signature is not None
        assert signature.accent_color == "#ff0000"
        assert "#ff0000" in signature.html_content


def test_pro_tier_malformed_accent_color_falls_back_and_cannot_break_out_of_attribute(
    app: Flask, client: FlaskClient
) -> None:
    """
    A value like this, if interpolated unescaped into
    style="color:{accent_color};...", would close the style attribute
    early and inject a new one. The strict #RRGGBB format check is what
    actually prevents this, for every tier -- not just the tier gate.
    """
    register_via_client(client, email="accent3@example.com")
    _set_subscription_tier(app, "accent3@example.com", "pro")

    malicious = 'red" onmouseover="alert(1)'
    _create_signature(
        client,
        name="Malicious Accent Sig",
        full_name="Jane Doe",
        accent_color=malicious,
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="Malicious Accent Sig").first()
        assert signature is not None
        assert signature.accent_color == SignatureService.DEFAULT_ACCENT_COLOR
        assert "onmouseover" not in signature.html_content


def test_pro_tier_accent_color_persists_correctly_through_edit(
    app: Flask, client: FlaskClient
) -> None:
    """
    html_content is fully regenerated on every edit, so a Pro user's
    accent color choice must still be honored (not silently reset to
    default) when a signature is saved again.
    """
    signature_id = _create_signature_for_user(app, client, "accent4@example.com")
    _set_subscription_tier(app, "accent4@example.com", "pro")

    client.post(
        f"/signatures/{signature_id}/edit",
        data={
            "name": "Owned Sig",
            "full_name": "Owner Name",
            "website": "",
            "accent_color": "#00ff00",
        },
        follow_redirects=False,
    )

    with app.app_context():
        signature = db.session.get(Signature, signature_id)
        assert signature is not None
        assert signature.accent_color == "#00ff00"
        assert "#00ff00" in signature.html_content


# ---------------------------------------------------------------------------
# Free vs. Pro font family (A01 tier gating + A03 output escaping)
#
# font_family is interpolated directly into style="" attributes across
# every layout. The UI only ever offers a fixed <select>, but that's a
# client-side constraint only -- a request built outside the form could
# submit anything. A positive allow-list match (not just a format check)
# is what actually prevents this, since the permitted values are fixed
# strings this file defines itself.
# ---------------------------------------------------------------------------

PRO_ONLY_FONT = "'Courier New', Courier, monospace"
FREE_ALLOWED_FONT = "Calibri, Candara, sans-serif"


def test_free_tier_can_use_a_free_font(app: Flask, client: FlaskClient) -> None:
    register_via_client(client, email="font1@example.com")

    _create_signature(
        client,
        name="Free Font Sig",
        full_name="Jane Doe",
        font_family=FREE_ALLOWED_FONT,
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="Free Font Sig").first()
        assert signature is not None
        assert signature.font_family == FREE_ALLOWED_FONT


def test_free_tier_pro_only_font_submission_falls_back_to_default(
    app: Flask, client: FlaskClient
) -> None:
    register_via_client(client, email="font2@example.com")

    _create_signature(
        client,
        name="Free Pro Font Sig",
        full_name="Jane Doe",
        font_family=PRO_ONLY_FONT,
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="Free Pro Font Sig").first()
        assert signature is not None
        assert signature.font_family == SignatureService.DEFAULT_FONT_FAMILY
        assert PRO_ONLY_FONT not in signature.html_content


def test_pro_tier_can_use_a_pro_only_font(app: Flask, client: FlaskClient) -> None:
    register_via_client(client, email="font3@example.com")
    _set_subscription_tier(app, "font3@example.com", "pro")

    _create_signature(
        client, name="Pro Font Sig", full_name="Jane Doe", font_family=PRO_ONLY_FONT
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="Pro Font Sig").first()
        assert signature is not None
        assert signature.font_family == PRO_ONLY_FONT
        assert PRO_ONLY_FONT in signature.html_content


def test_pro_tier_malformed_font_family_falls_back_and_cannot_break_out_of_attribute(
    app: Flask, client: FlaskClient
) -> None:
    """
    A value like this, if interpolated unescaped into
    style="font-family:{font_family};...", would close the style
    attribute early and inject a new one. The allow-list match is what
    actually prevents this, for every tier -- not just the tier gate --
    since a Pro account has no legitimate way to submit anything outside
    the fixed set of values this file defines.
    """
    register_via_client(client, email="font4@example.com")
    _set_subscription_tier(app, "font4@example.com", "pro")

    malicious = 'Arial" onmouseover="alert(1)'
    _create_signature(
        client, name="Malicious Font Sig", full_name="Jane Doe", font_family=malicious
    )

    with app.app_context():
        signature = Signature.query.filter_by(name="Malicious Font Sig").first()
        assert signature is not None
        assert signature.font_family == SignatureService.DEFAULT_FONT_FAMILY
        assert "onmouseover" not in signature.html_content


def test_pro_tier_font_family_persists_correctly_through_edit(
    app: Flask, client: FlaskClient
) -> None:
    """
    html_content is fully regenerated on every edit, so a Pro user's font
    choice must still be honored (not silently reset to default) when a
    signature is saved again.
    """
    signature_id = _create_signature_for_user(app, client, "font5@example.com")
    _set_subscription_tier(app, "font5@example.com", "pro")

    client.post(
        f"/signatures/{signature_id}/edit",
        data={
            "name": "Owned Sig",
            "full_name": "Owner Name",
            "website": "",
            "font_family": PRO_ONLY_FONT,
        },
        follow_redirects=False,
    )

    with app.app_context():
        signature = db.session.get(Signature, signature_id)
        assert signature is not None
        assert signature.font_family == PRO_ONLY_FONT
        assert PRO_ONLY_FONT in signature.html_content


def test_downgraded_user_editing_signature_with_pro_only_font_falls_back(
    app: Flask, client: FlaskClient
) -> None:
    """
    Symmetric case to the watermark's downgrade test: a signature saved
    while Pro (with a Pro-only font) that is later edited after a
    downgrade to free must have that font replaced with the default, not
    silently retain a font the account is no longer entitled to.
    """
    signature_id = _create_signature_for_user(app, client, "font6@example.com")
    _set_subscription_tier(app, "font6@example.com", "pro")

    client.post(
        f"/signatures/{signature_id}/edit",
        data={
            "name": "Owned Sig",
            "full_name": "Owner Name",
            "website": "",
            "font_family": PRO_ONLY_FONT,
        },
        follow_redirects=False,
    )

    _set_subscription_tier(app, "font6@example.com", "free")

    client.post(
        f"/signatures/{signature_id}/edit",
        data={
            "name": "Owned Sig",
            "full_name": "Owner Name",
            "website": "",
            "font_family": PRO_ONLY_FONT,
        },
        follow_redirects=False,
    )

    with app.app_context():
        signature = db.session.get(Signature, signature_id)
        assert signature is not None
        assert signature.font_family == SignatureService.DEFAULT_FONT_FAMILY
        assert PRO_ONLY_FONT not in signature.html_content
