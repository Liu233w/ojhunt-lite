import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import BASE_URL, _add_query, _clear_storage, _row

_CLEAR_ALL_BTN = "button.btn.ghost.danger:has-text('clear all')"


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


@pytest.mark.playwright
def test_clear_all_button_hidden_when_no_rows(page: Page):
    page.goto(BASE_URL)
    _clear_storage(page)
    expect(page.locator(_CLEAR_ALL_BTN)).not_to_be_visible(timeout=2000)


@pytest.mark.playwright
def test_clear_all_button_visible_when_rows_exist(page: Page):
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "tourist")
    expect(_row(page, "CodeForces")).to_be_visible(timeout=5000)
    expect(page.locator(_CLEAR_ALL_BTN)).to_be_visible(timeout=5000)


@pytest.mark.playwright
def test_clear_all_removes_all_rows(page: Page):
    page.goto(BASE_URL)
    _clear_storage(page)
    _add_query(page, "codeforces", "tourist")
    _add_query(page, "atcoder", "tourist")
    expect(_row(page, "CodeForces")).to_be_visible(timeout=5000)
    expect(_row(page, "AtCoder")).to_be_visible(timeout=5000)
    page.locator(_CLEAR_ALL_BTN).click()
    expect(_row(page, "CodeForces")).not_to_be_visible(timeout=2000)
    expect(_row(page, "AtCoder")).not_to_be_visible(timeout=2000)


@pytest.mark.playwright
def test_clear_all_does_not_persist(page: Page):
    page.goto(BASE_URL)
    _clear_storage(page)
    _add_query(page, "codeforces", "tourist")
    expect(_row(page, "CodeForces")).to_be_visible(timeout=5000)
    page.locator(_CLEAR_ALL_BTN).click()
    expect(_row(page, "CodeForces")).not_to_be_visible(timeout=2000)
    page.reload()
    expect(_row(page, "CodeForces")).not_to_be_visible(timeout=5000)
