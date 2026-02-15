import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8080"


@pytest.mark.playwright
def test_query_success(page: Page):
    page.goto(BASE_URL)
    page.select_option("#crawler-select", "codeforces")
    page.fill("#username-input", "tourist")
    page.click('button:has-text("Add")')
    row = page.locator('tr[data-crawler="codeforces"][data-username="tourist"]')
    expect(row).to_be_visible(timeout=5000)
    row.locator(".query-btn").click()
    expect(row).to_have_class("result-row success", timeout=30000)
    expect(row.locator("td:nth-child(3)")).not_to_have_text("N/A", timeout=30000)


@pytest.mark.playwright
def test_query_user_not_found(page: Page):
    page.goto(BASE_URL)
    page.select_option("#crawler-select", "codeforces")
    page.fill("#username-input", "nonexistentuser12345xyz")
    page.click('button:has-text("Add")')
    row = page.locator(
        'tr[data-crawler="codeforces"][data-username="nonexistentuser12345xyz"]'
    )
    expect(row).to_be_visible(timeout=5000)
    row.locator(".query-btn").click()
    expect(row).to_have_class("result-row error", timeout=30000)


@pytest.mark.playwright
def test_query_multiple(page: Page):
    page.goto(BASE_URL)
    page.select_option("#crawler-select", "codeforces")
    page.fill("#username-input", "tourist")
    page.click('button:has-text("Add")')
    row1 = page.locator('tr[data-crawler="codeforces"][data-username="tourist"]')
    expect(row1).to_be_visible(timeout=5000)
    page.select_option("#crawler-select", "atcoder")
    page.fill("#username-input", "tourist")
    page.click('button:has-text("Add")')
    row2 = page.locator('tr[data-crawler="atcoder"][data-username="tourist"]')
    expect(row2).to_be_visible(timeout=5000)
    page.click('button:has-text("Query All")')
    expect(row1).to_have_class("result-row success", timeout=30000)
    expect(row2).to_have_class("result-row success", timeout=30000)


@pytest.mark.playwright
def test_retry_after_error(page: Page):
    page.goto(BASE_URL)
    page.select_option("#crawler-select", "codeforces")
    page.fill("#username-input", "nonexistentuser12345xyz")
    page.click('button:has-text("Add")')
    row = page.locator(
        'tr[data-crawler="codeforces"][data-username="nonexistentuser12345xyz"]'
    )
    expect(row).to_be_visible(timeout=5000)
    row.locator(".query-btn").click()
    expect(row).to_have_class("result-row error", timeout=30000)
    expect(row.locator(".retry-btn")).to_be_visible()
    row.locator(".retry-btn").click()
    expect(row).to_have_class("result-row error", timeout=30000)
