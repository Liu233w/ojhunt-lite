import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8080"


@pytest.mark.playwright
def test_report_generation(page: Page):
    page.goto(BASE_URL)
    page.select_option("#crawler-select", "codeforces")
    page.fill("#username-input", "tourist")
    page.click('button:has-text("Add")')
    row = page.locator('tr[data-crawler="codeforces"][data-username="tourist"]')
    expect(row).to_be_visible(timeout=5000)
    row.locator(".query-btn").click()
    expect(row).to_have_class("result-row success", timeout=30000)
    report = page.locator("#report-container .report")
    expect(report).to_be_visible(timeout=5000)
    expect(report.locator("strong:has-text('Total:')")).to_be_visible()


@pytest.mark.playwright
def test_report_shows_solved_count(page: Page):
    page.goto(BASE_URL)
    page.select_option("#crawler-select", "codeforces")
    page.fill("#username-input", "tourist")
    page.click('button:has-text("Add")')
    row = page.locator('tr[data-crawler="codeforces"][data-username="tourist"]')
    expect(row).to_be_visible(timeout=5000)
    row.locator(".query-btn").click()
    expect(row).to_have_class("result-row success", timeout=30000)
    report = page.locator("#report-container .report")
    expect(report).to_be_visible(timeout=5000)
    expect(report).to_contain_text("solved")
