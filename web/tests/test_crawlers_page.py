import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8080"


@pytest.mark.playwright
def test_crawlers_page_loads(page: Page):
    page.goto(f"{BASE_URL}/crawlers")
    expect(page).to_have_title("Crawlers - OJHunt Lite")
    rows = page.locator("table tbody tr")
    assert rows.count() > 0


@pytest.mark.playwright
def test_crawlers_page_has_known_crawler(page: Page):
    page.goto(f"{BASE_URL}/crawlers")
    expect(page.locator(".crawler-tag", has_text="codeforces")).to_be_visible()
    expect(page.locator(".crawler-link", has_text="CodeForces")).to_be_visible()


@pytest.mark.playwright
def test_crawlers_page_shows_status(page: Page):
    page.goto(f"{BASE_URL}/crawlers")
    rows = page.locator("table tbody tr")
    count = rows.count()
    for i in range(count):
        row = rows.nth(i)
        status_cell = row.locator("td:nth-child(4) span")
        text = status_cell.text_content()
        assert text in ("Online", "Offline", "Waiting...", "Offline (No Credentials)")


@pytest.mark.playwright
def test_crawlers_page_has_links(page: Page):
    page.goto(f"{BASE_URL}/crawlers")
    links = page.locator("table tbody a.crawler-link")
    assert links.count() > 0
    # Verify links have href attributes pointing to external sites
    first_href = links.first.get_attribute("href")
    assert first_href.startswith("http")


@pytest.mark.playwright
def test_crawlers_page_back_link(page: Page):
    page.goto(f"{BASE_URL}/crawlers")
    page.click("a.back-link")
    expect(page).to_have_url(f"{BASE_URL}/")


@pytest.mark.playwright
def test_crawlers_status_updates(page: Page):
    """Verify that at least one crawler has been checked (not all Waiting)."""
    page.goto(f"{BASE_URL}/crawlers")
    # The background checker starts immediately, so after a short wait
    # at least the first crawler should have a status
    page.wait_for_timeout(5000)
    page.reload()
    statuses = page.locator("table tbody td:nth-child(4) span")
    count = statuses.count()
    has_checked = False
    has_waiting = False
    for i in range(count):
        text = statuses.nth(i).text_content()
        if text in ("Online", "Offline", "Offline (No Credentials)"):
            has_checked = True
        if text == "Waiting...":
            has_waiting = True
    # At least one should be checked (first crawler)
    assert has_checked, "Expected at least one crawler to have been checked"
    # And some should still be waiting (one-by-one checking)
    assert has_waiting, "Expected some crawlers to still be waiting"
