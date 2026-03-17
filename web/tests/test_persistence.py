import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8080"


@pytest.mark.playwright
def test_crawlers_persist_on_reload(page: Page):
    page.goto(BASE_URL)
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='Username']", "tourist")
    page.click('button:has-text("Add")')
    row = page.locator("tr.result-row").filter(has_text="CodeForces")
    expect(row).to_be_visible(timeout=5000)
    page.reload()
    row = page.locator("tr.result-row").filter(has_text="CodeForces")
    expect(row).to_be_visible(timeout=5000)
    expect(row.locator("button.query-btn")).to_be_visible()


@pytest.mark.playwright
def test_username_persists_when_crawler_added(page: Page):
    page.goto(BASE_URL)
    page.fill("input[placeholder='Username']", "testuser")
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.click('button:has-text("Add")')
    row = page.locator("tr.result-row").filter(has_text="testuser")
    expect(row).to_be_visible(timeout=5000)
    page.reload()
    expect(page.locator("input[placeholder='Username']")).to_have_value("testuser")


@pytest.mark.playwright
def test_cleared_row_does_not_persist(page: Page):
    page.goto(BASE_URL)
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='Username']", "tourist")
    page.click('button:has-text("Add")')
    row = page.locator("tr.result-row").filter(has_text="CodeForces")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.remove-btn").click()
    expect(row).not_to_be_visible(timeout=2000)
    page.reload()
    row = page.locator("tr.result-row").filter(has_text="CodeForces")
    expect(row).not_to_be_visible(timeout=5000)


@pytest.mark.playwright
def test_clear_all_removes_persistence(page: Page):
    page.goto(BASE_URL)
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='Username']", "tourist")
    page.click('button:has-text("Add")')
    row = page.locator("tr.result-row").filter(has_text="CodeForces")
    expect(row).to_be_visible(timeout=5000)
    page.click('button:has-text("Clear All")')
    expect(row).not_to_be_visible(timeout=2000)
    page.reload()
    row = page.locator("tr.result-row").filter(has_text="CodeForces")
    expect(row).not_to_be_visible(timeout=5000)
    storage_value = page.evaluate("localStorage.getItem('ojhunt-queries')")
    data = eval(storage_value) if storage_value else None
    assert data is None or len(data.get("queries", [])) == 0, (
        "localStorage queries should be empty"
    )
