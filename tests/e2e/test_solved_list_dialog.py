import json

import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import BASE_URL, _add_query, _row


def _mock_listless(page: Page) -> None:
    page.route(
        "**/api/crawlers/atcoder/tourist",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "crawler": "atcoder",
                    "username": "tourist",
                    "error": False,
                    "data": {
                        "solved": 42,
                        "submissions": 100,
                        "solvedList": None,
                        "duration": 0.1,
                    },
                    "message": None,
                }
            ),
        ),
    )


def _mock_with_list(page: Page) -> None:
    page.route(
        "**/api/crawlers/codeforces/tourist",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "crawler": "codeforces",
                    "username": "tourist",
                    "error": False,
                    "data": {
                        "solved": 2,
                        "submissions": 5,
                        "solvedList": ["2A", "1A"],
                        "duration": 0.1,
                    },
                    "message": None,
                }
            ),
        ),
    )


@pytest.mark.playwright
def test_listless_crawler_dialog_shows_explanation(page: Page):
    page.goto(BASE_URL)
    _mock_listless(page)
    _add_query(page, "atcoder", "tourist")
    row = _row(page, "AtCoder")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.iconbtn[title='query']").click()
    expect(row).to_have_class("card r-ok", timeout=10000)

    row.locator("a.solved-link").click()
    dialog = page.locator("dialog[open]")
    expect(dialog).to_be_visible(timeout=3000)
    expect(dialog.locator(".dlg-hd .title")).to_contain_text("list not available")
    expect(dialog.locator(".dlg-hd .title")).not_to_contain_text("0 problems")
    expect(dialog.locator(".dlg-bd")).to_contain_text(
        "does not expose the list of individual problem IDs"
    )


@pytest.mark.playwright
def test_crawler_with_list_dialog_shows_problems(page: Page):
    page.goto(BASE_URL)
    _mock_with_list(page)
    _add_query(page, "codeforces", "tourist")
    row = _row(page, "CodeForces")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.iconbtn[title='query']").click()
    expect(row).to_have_class("card r-ok", timeout=10000)

    row.locator("a.solved-link").click()
    dialog = page.locator("dialog[open]")
    expect(dialog).to_be_visible(timeout=3000)
    expect(dialog.locator(".dlg-hd .title")).to_contain_text("2 problems")
    expect(dialog.locator(".dlg-bd")).to_contain_text("1A, 2A")
    expect(dialog.locator(".dlg-bd")).not_to_contain_text("list not available")
