import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import BASE_URL, _add_query, _row


@pytest.mark.playwright
def test_query_success(page: Page):
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "tourist")
    row = _row(page, "CodeForces")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.iconbtn[title='query']").click()
    expect(row).to_have_class("card r-ok", timeout=30000)
    expect(row.locator("a.solved-link")).to_be_visible(timeout=30000)


@pytest.mark.playwright
def test_query_user_not_found(page: Page):
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "nonexistentuser12345xyz")
    row = _row(page, "nonexistentuser12345xyz")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.iconbtn[title='query']").click()
    expect(row).to_have_class("card r-err", timeout=30000)


@pytest.mark.playwright
def test_query_multiple(page: Page):
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "tourist")
    row1 = _row(page, "CodeForces")
    expect(row1).to_be_visible(timeout=5000)
    _add_query(page, "atcoder", "tourist")
    row2 = _row(page, "AtCoder")
    expect(row2).to_be_visible(timeout=5000)
    page.click("button.btn.primary:has-text('query all')")
    expect(row1).to_have_class("card r-ok", timeout=30000)
    expect(row2).to_have_class("card r-ok", timeout=30000)


@pytest.mark.playwright
def test_retry_after_error(page: Page):
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "nonexistentuser12345xyz")
    row = _row(page, "nonexistentuser12345xyz")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.iconbtn[title='query']").click()
    expect(row).to_have_class("card r-err", timeout=30000)
    expect(row.locator("button.iconbtn[title='retry']")).to_be_visible()
    row.locator("button.iconbtn[title='retry']").click()
    expect(row).to_have_class("card r-err", timeout=30000)
