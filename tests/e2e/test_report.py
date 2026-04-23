import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import BASE_URL, _add_query, _row


@pytest.mark.playwright
def test_report_generation(page: Page):
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "tourist")
    row = _row(page, "CodeForces")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.iconbtn[title='query']").click()
    expect(row).to_have_class("r-ok", timeout=30000)
    summary = page.locator(".summary")
    expect(summary).to_be_visible(timeout=5000)
    expect(summary.locator(".stat").first).to_be_visible()


@pytest.mark.playwright
def test_report_shows_solved_count(page: Page):
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "tourist")
    row = _row(page, "CodeForces")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.iconbtn[title='query']").click()
    expect(row).to_have_class("r-ok", timeout=30000)
    summary = page.locator(".summary")
    expect(summary).to_be_visible(timeout=5000)
    expect(summary).to_contain_text("total solved")


@pytest.mark.playwright
def test_report_hidden_before_query(page: Page):
    page.goto(BASE_URL)
    summary = page.locator(".summary")
    expect(summary).not_to_be_visible(timeout=5000)
