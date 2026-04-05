import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8080"


@pytest.mark.playwright
def test_legacy_banner_visible_by_default(page: Page):
    page.goto(BASE_URL)
    page.evaluate("localStorage.removeItem('legacy-banner-dismissed')")
    page.reload()
    banner = page.locator("#legacy-banner")
    expect(banner).to_be_visible()
    expect(banner).to_contain_text("Were you a user of the old acm-statistics site")
    expect(banner.locator('a[href="/pdf/legacy"]')).to_be_visible()


@pytest.mark.playwright
def test_legacy_banner_dismiss_hides_banner(page: Page):
    page.goto(BASE_URL)
    page.evaluate("localStorage.removeItem('legacy-banner-dismissed')")
    page.reload()
    page.locator("#legacy-banner button").click()
    expect(page.locator("#legacy-banner")).not_to_be_visible()


@pytest.mark.playwright
def test_legacy_banner_stays_hidden_after_reload(page: Page):
    page.goto(BASE_URL)
    page.evaluate("localStorage.removeItem('legacy-banner-dismissed')")
    page.reload()
    page.locator("#legacy-banner button").click()
    page.reload()
    expect(page.locator("#legacy-banner")).not_to_be_visible()


@pytest.mark.playwright
def test_legacy_banner_reappears_after_localstorage_cleared(page: Page):
    page.goto(BASE_URL)
    page.evaluate("localStorage.removeItem('legacy-banner-dismissed')")
    page.reload()
    page.locator("#legacy-banner button").click()
    page.evaluate("localStorage.removeItem('legacy-banner-dismissed')")
    page.reload()
    expect(page.locator("#legacy-banner")).to_be_visible()


@pytest.mark.playwright
def test_ai_agent_footer_link(page: Page):
    page.goto(BASE_URL)
    link = page.locator('footer a[href="/llms.txt"]')
    expect(link).to_be_visible()
    expect(link).to_have_text("Read the guide for LLM →")


@pytest.mark.playwright
def test_hidden_ai_div_removed(page: Page):
    page.goto(BASE_URL)
    assert page.locator('[aria-hidden="true"]').count() == 0, (
        "The old hidden AI notice div should have been removed"
    )
