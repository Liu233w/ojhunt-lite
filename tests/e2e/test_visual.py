"""Visual regression tests — LOCAL ONLY, skipped in CI.

Workflow:
  1. Start the dev server on port 8080.
  2. Capture baselines:
       ./doit.sh update-snapshots
     Commit the generated __snapshots__ directory alongside this file.
  3. After each CSS/layout change, verify no visual diff:
       uv run pytest -m playwright tests/e2e/test_visual.py

On failure, actual/expected/diff PNGs are written to test-results/visual/.

Why not CI: Playwright screenshot comparisons are sensitive to font rendering
differences across OS/machines, producing false failures on CI.
"""

import json
import os
import urllib.parse

import pytest
from playwright.sync_api import Page, Route, expect

from e2e.helpers import BASE_URL, _add_query, _clear_storage, _row

# Deterministic availability fixture: a few crawlers in each state so all
# three CSS variants (r-ok / r-err / r-pend) are visible in the snapshot.
_CRAWLERS_TEST_AVAILABILITY = urllib.parse.quote(
    json.dumps({"codeforces": "online", "atcoder": "offline"})
)

pytestmark = [
    pytest.mark.playwright,
    pytest.mark.skipif(
        bool(os.environ.get("CI")), reason="visual tests are local-only"
    ),
]

# ── Mock API responses ────────────────────────────────────────────────────────

_MOCK_OK = json.dumps(
    {
        "crawler": "codeforces",
        "username": "tourist",
        "error": False,
        "data": {
            "solved": 2000,
            "submissions": 5000,
            "solvedList": ["1A", "1B"],
            "duration": 0.1,
        },
        "message": None,
    }
)

_MOCK_ERR = json.dumps(
    {
        "crawler": "codeforces",
        "username": "notfound",
        "error": True,
        "data": None,
        "message": "User not found",
    }
)


def _snap(page: Page, assert_snapshot, name: str) -> None:
    """Wait for network idle (fonts loaded) then take a full-page snapshot."""
    page.wait_for_load_state("networkidle")
    assert_snapshot(page.screenshot(full_page=True), name=name)


# ── Home page — empty state ───────────────────────────────────────────────────


@pytest.mark.parametrize(
    "width,height,label",
    [
        (1280, 900, "desktop"),
        (820, 900, "tablet"),
        (375, 812, "mobile"),
    ],
)
def test_home_empty(page: Page, assert_snapshot, width: int, height: int, label: str):
    page.set_viewport_size({"width": width, "height": height})
    page.goto(BASE_URL)
    _clear_storage(page)
    _snap(page, assert_snapshot, f"home-empty-{label}.png")


# ── Home page — pending cards (added but not queried) ────────────────────────


@pytest.mark.parametrize(
    "width,height,label",
    [
        (1280, 900, "desktop"),
        (820, 900, "tablet"),
        (375, 900, "mobile"),
    ],
)
def test_home_pending_cards(
    page: Page, assert_snapshot, width: int, height: int, label: str
):
    page.set_viewport_size({"width": width, "height": height})
    page.goto(BASE_URL)
    _clear_storage(page)
    _add_query(page, "codeforces", "tourist")
    _add_query(page, "atcoder", "tourist")
    expect(_row(page, "CodeForces")).to_be_visible(timeout=5000)
    expect(_row(page, "AtCoder")).to_be_visible(timeout=5000)
    _snap(page, assert_snapshot, f"home-pending-cards-{label}.png")


# ── Home page — successful query (r-ok card) ─────────────────────────────────


def test_home_ok_card(page: Page, assert_snapshot):
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(BASE_URL)
    _clear_storage(page)

    def _ok(route: Route) -> None:
        route.fulfill(status=200, content_type="application/json", body=_MOCK_OK)

    page.route("**/api/crawlers/codeforces/tourist", _ok)
    _add_query(page, "codeforces", "tourist")
    page.click("button.btn.primary:has-text('query all')")
    expect(_row(page, "CodeForces")).to_have_class("card r-ok", timeout=15000)
    _snap(page, assert_snapshot, "home-ok-card-desktop.png")


# ── Home page — failed query (r-err card) ────────────────────────────────────


def test_home_err_card(page: Page, assert_snapshot):
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(BASE_URL)
    _clear_storage(page)

    def _err(route: Route) -> None:
        route.fulfill(status=200, content_type="application/json", body=_MOCK_ERR)

    page.route("**/api/crawlers/codeforces/notfound", _err)
    _add_query(page, "codeforces", "notfound")
    page.click("button.btn.primary:has-text('query all')")
    expect(_row(page, "CodeForces")).to_have_class("card r-err", timeout=15000)
    _snap(page, assert_snapshot, "home-err-card-desktop.png")


# ── Other pages ───────────────────────────────────────────────────────────────


def test_about_page(page: Page, assert_snapshot):
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(f"{BASE_URL}/about")
    _snap(page, assert_snapshot, "about-desktop.png")


@pytest.mark.parametrize(
    "width,height,label",
    [
        (1280, 900, "desktop"),
        (820, 900, "tablet"),
        (375, 812, "mobile"),
    ],
)
def test_crawlers_page(
    page: Page, assert_snapshot, width: int, height: int, label: str
):
    page.set_viewport_size({"width": width, "height": height})
    # Inject deterministic availability via test_availability JSON parameter so
    # the full table renders with all three states (r-ok / r-err / r-pend).
    page.goto(f"{BASE_URL}/crawlers?test_availability={_CRAWLERS_TEST_AVAILABILITY}")
    _snap(page, assert_snapshot, name=f"crawlers-{label}.png")


def test_pdf_legacy_page(page: Page, assert_snapshot):
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(f"{BASE_URL}/pdf/legacy")
    _snap(page, assert_snapshot, "pdf-legacy-desktop.png")


def test_pdf_merge_page(page: Page, assert_snapshot):
    page.set_viewport_size({"width": 1280, "height": 900})
    page.goto(f"{BASE_URL}/pdf/merge")
    _snap(page, assert_snapshot, "pdf-merge-desktop.png")
