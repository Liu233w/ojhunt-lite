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
    expect(row).to_have_class("card r-ok", timeout=30000)
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
    expect(row).to_have_class("card r-ok", timeout=30000)
    summary = page.locator(".summary")
    expect(summary).to_be_visible(timeout=5000)
    expect(summary).to_contain_text("total solved")


@pytest.mark.playwright
def test_report_hidden_before_query(page: Page):
    page.goto(BASE_URL)
    summary = page.locator(".summary")
    expect(summary).not_to_be_visible(timeout=5000)


@pytest.mark.playwright
def test_download_button_disabled_while_downloading(page: Page):
    page.goto(BASE_URL)
    _add_query(page, "codeforces", "tourist")
    row = _row(page, "CodeForces")
    expect(row).to_be_visible(timeout=5000)
    row.locator("button.iconbtn[title='query']").click()
    expect(row).to_have_class("card r-ok", timeout=30000)
    expect(page.locator(".summary")).to_be_visible(timeout=5000)

    # Stub window.fetch so the PDF endpoint stalls until we release it.
    # JS-level stubbing avoids Playwright route handlers, which block the
    # Playwright event loop and prevent DOM assertions from running while
    # the request is in flight.
    page.evaluate("""() => {
        const orig = window.fetch;
        window.__releasePdfDownload = null;
        window.fetch = function(url, ...args) {
            if (url.includes('/api/pdf/generate')) {
                return new Promise((resolve) => {
                    window.__releasePdfDownload = () => resolve(new Response(
                        JSON.stringify({pdf_b64: btoa('%PDF-1.4 dummy'), date: '2026-04-27'}),
                        {status: 200, headers: {'Content-Type': 'application/json'}}
                    ));
                });
            }
            return orig(url, ...args);
        };
    }""")

    btn = page.locator(".download-card .btn.primary")
    spinner = btn.locator(".loading-dots")

    btn.click()
    expect(btn).to_be_disabled(timeout=3000)
    expect(spinner).to_be_visible(timeout=3000)

    # Release the stall and verify button recovers
    page.evaluate(
        "() => { window.__releasePdfDownload && window.__releasePdfDownload(); }"
    )
    expect(btn).not_to_be_disabled(timeout=5000)
    expect(spinner).not_to_be_visible(timeout=5000)
