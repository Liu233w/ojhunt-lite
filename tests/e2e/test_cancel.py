import time
import pytest
from playwright.sync_api import Page, expect, Route

BASE_URL = "http://localhost:8080"


@pytest.mark.playwright
def test_cancel_query(page: Page):
    def delay_response(route: Route):
        if "api/crawlers" in route.request.url:
            time.sleep(5)
        route.continue_()

    page.route("**/*", delay_response)
    page.goto(BASE_URL)
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='Username']", "tourist")
    page.click('button:has-text("Add")')
    row = page.locator("tbody.result-row").filter(has_text="CodeForces")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.query-btn").click()
    expect(row.locator("button.cancel-btn")).to_be_visible(timeout=2000)
    row.locator("button.cancel-btn").click()
    expect(row).to_have_class("result-row pending", timeout=2000)
    expect(row.locator("button.query-btn")).to_be_visible()
    page.unroute("**/*", delay_response)


@pytest.mark.playwright
def test_cancel_shows_immediately(page: Page):
    def delay_response(route: Route):
        if "api/crawlers" in route.request.url:
            time.sleep(10)
        route.continue_()

    page.route("**/*", delay_response)
    page.goto(BASE_URL)
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='Username']", "tourist")
    page.click('button:has-text("Add")')
    row = page.locator("tbody.result-row").filter(has_text="CodeForces")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.query-btn").click()
    expect(row.locator("button.cancel-btn")).to_be_visible(timeout=1000)
    row.locator("button.cancel-btn").click()
    expect(row).to_have_class("result-row pending", timeout=500)
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
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='Username']", "tourist")
    page.click('button:has-text("Add")')
    row = page.locator("tbody.result-row").filter(has_text="CodeForces")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.query-btn").click()
    expect(row.locator("button.cancel-btn")).to_be_visible(timeout=2000)
    row.locator("button.cancel-btn").click()
    expect(row).to_have_class("result-row pending", timeout=2000)
    row.locator("button.query-btn").click()
    expect(row).to_have_class("result-row success", timeout=30000)
    page.unroute("**/*", delay_then_respond)
