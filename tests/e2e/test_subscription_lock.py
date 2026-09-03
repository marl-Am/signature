# tests/e2e/test_subscription_lock.py
"""
Downgrading locks the paid feature in the UI.

app/templates/signatures/create.html gates non-classic layouts and
non-default fonts behind {% if current_user.subscription_tier == 'pro' %}:
free-tier users see a disabled radio input plus a "Pro" badge instead of
the option. This test creates a Pro user, confirms the option is unlocked,
then simulates a downgrade (as a Stripe webhook would perform) and
confirms the same option becomes locked without anything else changing.
"""

from flask import Flask
from playwright.sync_api import Page, expect

from tests.e2e.conftest import CREATE_URL, Account, login, set_subscription_tier


def test_downgrade_locks_pro_layout_option(
    page: Page, app: Flask, pro_user: Account
) -> None:
    login(page, pro_user)
    page.goto(CREATE_URL)

    # As Pro: the "Ruled" layout radio is enabled, no "Pro" upsell badge.
    ruled_radio = page.locator('input[name="layout"][value="ruled"]')
    expect(ruled_radio).to_be_enabled()

    set_subscription_tier(app, pro_user, "free")
    page.reload()

    # As Free (post-downgrade): same radio is now disabled, badge shown.
    # Playwright locators resolve at assertion time, so the one above stays
    # valid across the reload and does not need rebuilding.
    expect(ruled_radio).to_be_disabled()
    expect(page.get_by_text("Pro", exact=True).first).to_be_visible()
