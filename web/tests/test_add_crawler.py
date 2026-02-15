import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8080"


@pytest.mark.playwright
def test_dropdown_populated(page: Page):
    page.goto(BASE_URL)
    crawler_select = page.locator("#crawler-select")
    option_count = crawler_select.locator("option").count()
    assert option_count > 1, "Dropdown should have more than just the placeholder"


@pytest.mark.playwright
def test_add_single_crawler(page: Page):
    page.goto(BASE_URL)
    page.select_option("#crawler-select", "codeforces")
    page.fill("#username-input", "tourist")
    page.click('button:has-text("Add")')
    row = page.locator('tr[data-crawler="codeforces"][data-username="tourist"]')
    expect(row).to_be_visible(timeout=5000)
    expect(row.locator(".query-btn")).to_be_visible()


@pytest.mark.playwright
def test_add_multiple_crawlers(page: Page):
    page.goto(BASE_URL)
    page.select_option("#crawler-select", "codeforces")
    page.fill("#username-input", "tourist")
    page.click('button:has-text("Add")')
    page.select_option("#crawler-select", "atcoder")
    page.fill("#username-input", "tourist")
    page.click('button:has-text("Add")')
    row1 = page.locator('tr[data-crawler="codeforces"][data-username="tourist"]')
    row2 = page.locator('tr[data-crawler="atcoder"][data-username="tourist"]')
    expect(row1).to_be_visible(timeout=5000)
    expect(row2).to_be_visible(timeout=5000)


@pytest.mark.playwright
def test_add_all_crawlers(page: Page):
    page.goto(BASE_URL)
    page.select_option("#crawler-select", "*")
    page.fill("#username-input", "tourist")
    page.click('button:has-text("Add")')
    rows = page.locator('tr[data-username="tourist"]')
    expect(rows.first).to_be_visible(timeout=5000)
    count = rows.count()
    assert count > 1, "Should add multiple rows for 'All Crawlers'"


@pytest.mark.playwright
def test_add_duplicate_crawler(page: Page):
    page.goto(BASE_URL)
    page.select_option("#crawler-select", "codeforces")
    page.fill("#username-input", "tourist")
    page.click('button:has-text("Add")')
    page.select_option("#crawler-select", "codeforces")
    page.fill("#username-input", "tourist")
    page.click('button:has-text("Add")')
    rows = page.locator('tr[data-crawler="codeforces"][data-username="tourist"]')
    count = rows.count()
    assert count == 2, (
        "Should allow adding duplicate entries (users can remove manually)"
    )


@pytest.mark.playwright
def test_add_empty_username(page: Page):
    page.goto(BASE_URL)
    page.select_option("#crawler-select", "codeforces")
    page.fill("#username-input", "")
    page.click('button:has-text("Add")')
    username_input = page.locator("#username-input")
    expect(username_input).to_have_attribute("required", "")
