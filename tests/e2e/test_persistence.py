import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import BASE_URL, _add_query, _clear_storage, _row


@pytest.mark.playwright
def test_crawlers_persist_on_reload(page: Page):
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "tourist")
    expect(_row(page, "CodeForces")).to_be_visible(timeout=5000)
    page.reload()
    expect(_row(page, "CodeForces")).to_be_visible(timeout=5000)
    expect(
        _row(page, "CodeForces").locator("button.iconbtn[title='query']")
    ).to_be_visible()


@pytest.mark.playwright
def test_username_persists_when_crawler_added(page: Page):
    page.goto(BASE_URL)
    page.fill("input[placeholder='username']", "testuser")
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.click("button.btn:has-text('add')")
    expect(_row(page, "testuser")).to_be_visible(timeout=5000)
    page.reload()
    expect(page.locator("input[placeholder='username']")).to_have_value("testuser")


@pytest.mark.playwright
def test_cleared_row_does_not_persist(page: Page):
    page.goto(BASE_URL)
    _clear_storage(page)
    _add_query(page, "codeforces", "tourist")
    row = _row(page, "CodeForces")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.iconbtn[title='remove']").first.click()
    expect(row).not_to_be_visible(timeout=2000)
    page.reload()
    expect(_row(page, "CodeForces")).not_to_be_visible(timeout=5000)
