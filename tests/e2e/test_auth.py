# tests/e2e/test_auth.py
"""
Login success and failure paths against the real form at /auth/login.

The failure case reuses the `user_a` fixture with a deliberately wrong
password, so it exercises the password check itself rather than the
unknown-email path.
"""

from playwright.sync_api import Page, expect

from tests.e2e.conftest import BASE_URL, LOGIN_URL, Account, login


def test_login_rejects_bad_password(page: Page, user_a: Account) -> None:
    page.goto(LOGIN_URL)
    page.get_by_label("Email").fill(user_a.email)
    page.get_by_label("Password").fill("wrong-password")
    page.get_by_role("button", name="Sign In").click()

    expect(page.get_by_text("Invalid email or password")).to_be_visible()
    expect(page).to_have_url(LOGIN_URL)


def test_login_accepts_valid_password(page: Page, user_a: Account) -> None:
    login(page, user_a)
    expect(page).to_have_url(f"{BASE_URL}/dashboard/")
