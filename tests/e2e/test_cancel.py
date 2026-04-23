import time
import pytest
from playwright.sync_api import Page, expect, Route

BASE_URL = "http://localhost:8080"


def _add_query(page: Page, crawler: str, username: str):
    page.select_option("select[x-model='selectedCrawler']", crawler)
    page.fill("input[placeholder='username']", username)
    page.click("button.btn:has-text('add')")


def _row(page: Page, text: str):
    return page.locator("#queries-tbl tbody tr").filter(has_text=text)


@pytest.mark.playwright
def test_cancel_query(page: Page):
    def delay_response(route: Route):
        if "api/crawlers" in route.request.url:
            time.sleep(5)
        route.continue_()

    page.route("**/*", delay_response)
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "tourist")
    row = _row(page, "CodeForces")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.iconbtn[title='query']").click()
    expect(row.locator("button.iconbtn[title='stop']")).to_be_visible(timeout=2000)
    row.locator("button.iconbtn[title='stop']").click()
    expect(row).to_have_class("r-pend", timeout=2000)
    expect(row.locator("button.iconbtn[title='query']")).to_be_visible()
    page.unroute("**/*", delay_response)


@pytest.mark.playwright
def test_cancel_shows_immediately(page: Page):
    def delay_response(route: Route):
        if "api/crawlers" in route.request.url:
            time.sleep(10)
        route.continue_()

    page.route("**/*", delay_response)
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "tourist")
    row = _row(page, "CodeForces")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.iconbtn[title='query']").click()
    expect(row.locator("button.iconbtn[title='stop']")).to_be_visible(timeout=1000)
    row.locator("button.iconbtn[title='stop']").click()
    expect(row).to_have_class("r-pend", timeout=500)
    page.unroute("**/*", delay_response)


@pytest.mark.playwright
def test_retry_after_cancel(page: Page):
    call_count = [0]

    def delay_then_respond(route: Route):
        if "api/crawlers" in route.request.url:
            call_count[0] += 1
            if call_count[0] == 1:
                time.sleep(10)
        route.continue_()

    page.route("**/*", delay_then_respond)
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "tourist")
    row = _row(page, "CodeForces")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.iconbtn[title='query']").click()
    expect(row.locator("button.iconbtn[title='stop']")).to_be_visible(timeout=2000)
    row.locator("button.iconbtn[title='stop']").click()
    expect(row).to_have_class("r-pend", timeout=2000)
    row.locator("button.iconbtn[title='query']").click()
    expect(row).to_have_class("r-ok", timeout=30000)
    page.unroute("**/*", delay_then_respond)
