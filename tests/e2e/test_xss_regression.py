# tests/e2e/test_xss_regression.py
"""
Regression test for the stored-XSS fix in
SignatureService._sanitize_accent_color (app/services/signature_service.py).

Before the fix, accent_color was interpolated directly into style=""
attributes with no escaping or format check — a value containing a
double-quote could break out of the attribute and inject arbitrary HTML/JS
into every rendered signature. The fix requires a strict #RRGGBB match and
silently falls back to DEFAULT_ACCENT_COLOR otherwise.

Posts the payload directly rather than through the UI, since the real
<input type="color"> control in create.html wouldn't let a browser user
type this in the first place — the actual attack surface is a raw HTTP
request, which is what a browser's native input restrictions don't
protect against.
"""

from flask import Flask
from playwright.sync_api import Dialog, Page

from app.models.signature import Signature
from app.services.signature_service import SignatureService
from tests.e2e.conftest import BASE_URL, CREATE_URL, Account, login

# Breaks out of style="..." if unescaped, then adds an event-handler
# attribute that would fire arbitrary JS in any client that renders the
# HTML (a real email client, or this app's own preview page).
_XSS_PAYLOAD: str = '#0c2788" onmouseover="alert(1)'


def test_malicious_accent_color_does_not_break_out_of_style_attribute(
    page: Page, app: Flask, pro_user: Account
) -> None:
    login(page, pro_user)

    # Grab a valid CSRF token from the real page, then post the payload
    # directly — accent_color customization only applies to Pro accounts,
    # so pro_user is required to even reach the vulnerable code path.
    page.goto(CREATE_URL)
    csrf_token = page.locator('input[name="csrf_token"]').first.input_value()

    response = page.request.post(
        CREATE_URL,
        form={
            "csrf_token": csrf_token,
            "name": "XSS Regression Signature",
            "full_name": "XSS Test",
            "accent_color": _XSS_PAYLOAD,
        },
    )
    assert response.ok

    with app.app_context():
        sig = (
            Signature.query.filter_by(user_id=pro_user.id)
            .order_by(Signature.created_at.desc())
            .first()
        )
        assert sig is not None, "signature was not created"
        signature_id: int = sig.id
        stored_html: str = sig.html_content

    # The payload must never appear verbatim in stored HTML — it should
    # have been rejected by the #RRGGBB check and silently replaced with
    # the default, not escaped-and-kept.
    assert _XSS_PAYLOAD not in stored_html
    assert "onmouseover" not in stored_html
    assert SignatureService.DEFAULT_ACCENT_COLOR in stored_html

    # Belt-and-suspenders: load the real preview page and confirm no
    # script ever executes, in case some other path let it through.
    dialog_fired = False

    def _on_dialog(dialog: Dialog) -> None:
        nonlocal dialog_fired
        dialog_fired = True
        dialog.dismiss()

    page.on("dialog", _on_dialog)
    page.goto(f"{BASE_URL}/signatures/{signature_id}/preview")
    page.wait_for_timeout(500)
    assert not dialog_fired
