import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import BASE_URL, _add_query, _row


@pytest.mark.playwright
def test_dropdown_populated(page: Page):
    page.goto(BASE_URL)
    crawler_select = page.locator("select[x-model='selectedCrawler']")
    option_count = crawler_select.locator("option").count()
    assert option_count > 1, "Dropdown should have more than just the placeholder"


@pytest.mark.playwright
def test_add_single_crawler(page: Page):
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "tourist")
    expect(_row(page, "CodeForces")).to_be_visible(timeout=5000)
    expect(
        _row(page, "CodeForces").locator("button.iconbtn[title='query']")
    ).to_be_visible()


@pytest.mark.playwright
def test_add_multiple_crawlers(page: Page):
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "tourist")
    expect(_row(page, "CodeForces")).to_be_visible(timeout=5000)
    _add_query(page, "atcoder", "tourist")
    expect(_row(page, "AtCoder")).to_be_visible(timeout=5000)


@pytest.mark.playwright
def test_add_all_crawlers(page: Page):
    page.goto(BASE_URL)
    _add_query(page, "*", "tourist")
    rows = page.locator("#queries-tbl tbody tr.r-pend")
    expect(rows.first).to_be_visible(timeout=5000)
    count = rows.count()
    assert count > 1, "Should add multiple rows for 'All Crawlers'"


@pytest.mark.playwright
def test_add_duplicate_crawler_shows_alert(page: Page):
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "tourist")
    expect(_row(page, "CodeForces")).to_be_visible(timeout=5000)
    page.on("dialog", lambda dialog: dialog.accept())
    _add_query(page, "codeforces", "tourist")
    expect(
        page.locator("#queries-tbl tbody tr").filter(has_text="CodeForces")
    ).to_have_count(1, timeout=5000)


@pytest.mark.playwright
def test_add_empty_username_shows_alert(page: Page):
    page.goto(BASE_URL)
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='username']", "")
    page.on("dialog", lambda dialog: dialog.accept())
    page.click("button.btn:has-text('add')")
    expect(page.locator("#queries-tbl tbody tr.r-pend")).to_have_count(0, timeout=5000)


@pytest.mark.playwright
def test_enter_key_adds_query_from_username_field(page: Page):
    page.goto(BASE_URL)
    page.fill("input[placeholder='username']", "tourist")
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.locator("input[placeholder='username']").press("Enter")
    expect(_row(page, "CodeForces")).to_be_visible(timeout=5000)


@pytest.mark.playwright
def test_enter_key_adds_query_from_crawler_select(page: Page):
    page.goto(BASE_URL)
    page.fill("input[placeholder='username']", "tourist")
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.locator("select[x-model='selectedCrawler']").press("Enter")
    expect(_row(page, "CodeForces")).to_be_visible(timeout=5000)
