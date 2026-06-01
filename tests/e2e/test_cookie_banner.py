import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import BASE_URL, _clear_storage

_BANNER = "#cookie-banner"
_OK = "#cookie-ok"
_CONSENT_KEY = "ojhunt-cookie-consent"


@pytest.mark.playwright
def test_banner_shows_on_fresh_visit(page: Page):
    page.goto(BASE_URL)
    _clear_storage(page)
    expect(page.locator(_BANNER)).to_be_visible(timeout=5000)


@pytest.mark.playwright
def test_ok_dismisses_and_persists(page: Page):
    page.goto(BASE_URL)
    _clear_storage(page)
    expect(page.locator(_BANNER)).to_be_visible(timeout=5000)

    page.click(_OK)
    expect(page.locator(_BANNER)).not_to_be_visible(timeout=2000)
    assert page.evaluate(f"localStorage.getItem('{_CONSENT_KEY}')") == "1"

    page.reload()
    expect(page.locator(_BANNER)).not_to_be_visible(timeout=2000)
