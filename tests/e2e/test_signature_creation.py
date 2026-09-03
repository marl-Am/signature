# tests/e2e/test_signature_creation.py
"""
Create a signature and confirm it appears.

Uses the real form from app/templates/signatures/create.html:
  - "Signature Label" -> id="label", name="name"
  - "Full Name"        -> id="full_name", name="full_name"
Submitting POSTs to url_for('signatures.create').
"""

from playwright.sync_api import Page, expect

from tests.e2e.conftest import CREATE_URL, Account, login


def test_create_signature_and_confirm_it_appears(page: Page, user_a: Account) -> None:
    login(page, user_a)
    page.goto(CREATE_URL)

    signature_label = "My E2E Test Signature"
    page.get_by_label("Signature Label").fill(signature_label)
    page.get_by_label("Full Name").fill("E2E Test User")
    page.get_by_role("button", name="Save Signature").click()

    # signatures.create() redirects to dashboard.index on success (confirmed
    # in app/routes/signatures.py), which lists the user's signatures.
    # The name legitimately appears more than once (flash message + the
    # dashboard's own listing), so .first() rather than a strict single match.
    expect(page.get_by_text(signature_label).first).to_be_visible()
