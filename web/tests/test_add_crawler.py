import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8080"


@pytest.mark.playwright
def test_dropdown_populated(page: Page):
    page.goto(BASE_URL)
    crawler_select = page.locator("select[x-model='selectedCrawler']")
    option_count = crawler_select.locator("option").count()
    assert option_count > 1, "Dropdown should have more than just the placeholder"


@pytest.mark.playwright
def test_add_single_crawler(page: Page):
    page.goto(BASE_URL)
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='Username']", "tourist")
    page.click('button:has-text("Add")')
    row = page.locator("tr.result-row").filter(has_text="CodeForces")
    expect(row).to_be_visible(timeout=5000)
    expect(row.locator("button.query-btn")).to_be_visible()


@pytest.mark.playwright
def test_add_multiple_crawlers(page: Page):
    page.goto(BASE_URL)
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='Username']", "tourist")
    page.click('button:has-text("Add")')
    row1 = page.locator("tr.result-row").filter(has_text="CodeForces")
    expect(row1).to_be_visible(timeout=5000)
    page.select_option("select[x-model='selectedCrawler']", "atcoder")
    page.fill("input[placeholder='Username']", "tourist")
    page.click('button:has-text("Add")')
    row2 = page.locator("tr.result-row").filter(has_text="AtCoder")
    expect(row2).to_be_visible(timeout=5000)


@pytest.mark.playwright
def test_add_all_crawlers(page: Page):
    page.goto(BASE_URL)
    page.select_option("select[x-model='selectedCrawler']", "*")
    page.fill("input[placeholder='Username']", "tourist")
    page.click('button:has-text("Add")')
    rows = page.locator("tr.result-row")
    expect(rows.first).to_be_visible(timeout=5000)
    count = rows.count()
    assert count > 1, "Should add multiple rows for 'All Crawlers'"


@pytest.mark.playwright
def test_add_duplicate_crawler_shows_alert(page: Page):
    page.goto(BASE_URL)
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='Username']", "tourist")
    page.click('button:has-text("Add")')
    row = page.locator("tr.result-row").filter(has_text="CodeForces")
    expect(row).to_be_visible(timeout=5000)
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='Username']", "tourist")
    page.on("dialog", lambda dialog: dialog.accept())
    page.click('button:has-text("Add")')
    rows = page.locator("tr.result-row").filter(has_text="CodeForces")
    expect(rows).to_have_count(1, timeout=5000)


@pytest.mark.playwright
def test_add_empty_username_shows_alert(page: Page):
    page.goto(BASE_URL)
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='Username']", "")
    page.on("dialog", lambda dialog: dialog.accept())
    page.click('button:has-text("Add")')
    rows = page.locator("tr.result-row")
    expect(rows).to_have_count(0, timeout=5000)
