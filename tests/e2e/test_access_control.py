# tests/e2e/test_access_control.py
"""
Ownership / access-control regression test.

Pairs with the user_id filter in AnalyticsService.get_signature_detail()
(app/services/analytics_service.py) — Signature.query.filter_by(id=...,
user_id=...).first_or_404() means a signature owned by another user
returns 404 rather than leaking data cross-account.
"""

from playwright.sync_api import Page

from tests.e2e.conftest import BASE_URL, Account, login


def test_user_cannot_open_another_users_signature_by_url(
    page: Page, user_a: Account, user_b: Account, signature_b: int
) -> None:
    login(page, user_a)
    response = page.goto(f"{BASE_URL}/analytics/signature/{signature_b}")

    assert response is not None
    assert response.status == 404
