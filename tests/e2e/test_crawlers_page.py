import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import BASE_URL


@pytest.mark.playwright
def test_crawlers_page_loads(page: Page):
    page.goto(f"{BASE_URL}/crawlers")
    expect(page).to_have_title("Supported Crawlers - OJHunt Lite")
    rows = page.locator("table tbody tr")
    assert rows.count() > 0


@pytest.mark.playwright
def test_crawlers_page_has_known_crawler(page: Page):
    page.goto(f"{BASE_URL}/crawlers")
    expect(page.locator(".tag-cell", has_text="codeforces")).to_be_visible()
    expect(page.locator(".clw-tbl .name", has_text="CodeForces")).to_be_visible()


@pytest.mark.playwright
def test_crawlers_page_shows_status(page: Page):
    page.goto(f"{BASE_URL}/crawlers")
    rows = page.locator("table tbody tr")
    count = rows.count()
    for i in range(count):
        row = rows.nth(i)
        status_cell = row.locator("td:nth-child(4) span")
        text = status_cell.text_content()
        assert text in ("online", "offline", "waiting")


@pytest.mark.playwright
def test_crawlers_page_has_links(page: Page):
    page.goto(f"{BASE_URL}/crawlers")
    links = page.locator(".clw-tbl .name a")
    assert links.count() > 0
    # Verify links have href attributes pointing to external sites
    first_href = links.first.get_attribute("href")
    assert first_href.startswith("http")


@pytest.mark.playwright
def test_crawlers_page_home_link(page: Page):
    page.goto(f"{BASE_URL}/crawlers")
    page.click("a.tb-brand")
    expect(page).to_have_url(f"{BASE_URL}/")


@pytest.mark.playwright
def test_crawlers_status_updates(page: Page):
    """Verify that at least one crawler has been checked (not all waiting)."""
    page.goto(f"{BASE_URL}/crawlers")
    # The background checker starts immediately, so after a short wait
    # at least the first crawler should have a status
    page.wait_for_timeout(5000)
    page.reload()
    statuses = page.locator("table tbody td:nth-child(4) span")
    count = statuses.count()
    has_checked = False
    for i in range(count):
        text = statuses.nth(i).text_content()
        if text in ("online", "offline"):
            has_checked = True
    assert has_checked, "Expected at least one crawler to have been checked"
