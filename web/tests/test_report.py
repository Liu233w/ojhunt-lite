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
    expect(row.locator(".status.success, .status:has-text('Solved')")).to_be_visible(
        timeout=30000
    )
    report = page.locator("#report-container .report")
    expect(report).to_be_visible(timeout=5000)
    expect(report.locator("strong:has-text('Total Solved:')")).to_be_visible()


@pytest.mark.playwright
def test_report_opens_in_new_tab(page: Page):
    page.goto(BASE_URL)
    page.select_option("#crawler-select", "codeforces")
    page.fill("#username-input", "tourist")
    page.click('button:has-text("Add")')
    row = page.locator('tr[data-crawler="codeforces"][data-username="tourist"]')
    expect(row).to_be_visible(timeout=5000)
    row.locator(".query-btn").click()
    expect(row.locator(".status.success, .status:has-text('Solved')")).to_be_visible(
        timeout=30000
    )
    report = page.locator("#report-container .report")
    expect(report).to_be_visible(timeout=5000)
    report_link = report.locator("a[target='_blank']")
    expect(report_link).to_be_visible()
