"""Shared helpers for e2e tests."""

from playwright.sync_api import Page

BASE_URL = "http://localhost:8080"


def _add_query(page: Page, crawler: str, username: str) -> None:
    page.select_option("select[x-model='selectedCrawler']", crawler)
    page.fill("input[placeholder='username']", username)
    page.click("button.btn:has-text('add')")


def _row(page: Page, text: str):
    return page.locator("#queries-tbl tbody tr").filter(has_text=text)


def _clear_storage(page: Page) -> None:
    page.evaluate("localStorage.clear()")
    page.reload()
