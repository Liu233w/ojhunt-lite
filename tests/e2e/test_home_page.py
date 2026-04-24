import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import BASE_URL


@pytest.mark.playwright
def test_legacy_banner_visible_by_default(page: Page):
    page.goto(BASE_URL)
    banner = page.locator("#legacy-banner")
    expect(banner).to_be_visible()
    expect(banner).to_contain_text("acm-statistics")
    expect(banner.locator('a[href="/pdf/legacy"]')).to_be_visible()


@pytest.mark.playwright
def test_ai_agent_footer_link(page: Page):
    page.goto(BASE_URL)
    link = page.locator('footer a[href="/llms.txt"]')
    expect(link).to_be_visible()
    expect(link).to_have_text("read the guide for llm →")


@pytest.mark.playwright
def test_hidden_ai_div_removed(page: Page):
    page.goto(BASE_URL)
    assert page.locator('[aria-hidden="true"]').count() == 0, (
        "The old hidden AI notice div should have been removed"
    )
