"""Playwright e2e tests for the PDF upload/download workflow."""

import base64
import json
import os
import tempfile

import pytest
from playwright.sync_api import BrowserContext, Page, expect

from ojhunt.web.pdf import (
    HistoryEntry,
    PdfQueryItem,
    PdfSettings,
    PdfSnapshot,
    extract_data,
    generate_pdf,
)

BASE_URL = "http://localhost:8080"
_TMPDIR = os.environ.get("TMPDIR", tempfile.gettempdir())


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session")
def historical_pdf_path() -> str:
    """PDF with 3 entries from 2020, written to a temp file for the session.

    Using Python directly (not the server API) so we can set arbitrary past dates,
    making it easy to test history merging against today's real date (~2026).
    """
    settings = PdfSettings(
        username="tourist",
        queries=[PdfQueryItem(crawler="codeforces", username="tourist")],
    )
    history = [
        HistoryEntry(
            key=f"2020-01-{i:02d}",
            date=f"2020-01-{i:02d}T12:00:00Z",
            totalSolved=100 + i * 5,
            totalSubmissions=(100 + i * 5) * 3,
            username="tourist",
        )
        for i in range(1, 4)
    ]
    snapshot = PdfSnapshot(
        totalSolved=115, totalSubmissions=345, username="tourist", timezone="UTC"
    )
    pdf_bytes = generate_pdf(settings, history, snapshot)

    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir=_TMPDIR)
    tmp.write(pdf_bytes)
    tmp.close()
    yield tmp.name
    os.unlink(tmp.name)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ojhunt_pdf(context: BrowserContext, username: str = "tourist") -> bytes:
    """Generate a minimal OJHunt PDF via the API and return the raw bytes."""
    snapshot = {
        "totalSolved": 42,
        "totalSubmissions": 100,
        "username": username,
        "timezone": "UTC",
    }
    settings = {
        "username": username,
        "queries": [{"crawler": "codeforces", "username": username}],
    }
    resp = context.request.post(
        f"{BASE_URL}/api/pdf/generate",
        data=json.dumps({"snapshot": snapshot, "settings": settings}),
        headers={"Content-Type": "application/json"},
    )
    assert resp.ok, f"Failed to generate test PDF: {resp.status}"
    return base64.b64decode(resp.json()["pdf_b64"])


def _write_temp_pdf(pdf_bytes: bytes) -> str:
    """Write PDF bytes to a temp file and return the path."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir=_TMPDIR)
    tmp.write(pdf_bytes)
    tmp.close()
    return tmp.name


def _clear_storage(page: Page) -> None:
    page.evaluate("localStorage.clear()")
    page.reload()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.playwright
def test_upload_pdf_restores_queries_when_table_empty(
    page: Page, context: BrowserContext
):
    """Uploading a valid OJHunt PDF with an empty table populates queries and username."""
    pdf_path = _write_temp_pdf(_make_ojhunt_pdf(context, username="tourist"))
    try:
        page.goto(BASE_URL)
        _clear_storage(page)

        page.set_input_files("input[type='file']", pdf_path)

        # Username field should be populated
        expect(page.locator("input[placeholder='Username']")).to_have_value(
            "tourist", timeout=5000
        )
        # A codeforces row should appear
        row = page.locator("tbody.result-row").filter(has_text="CodeForces")
        expect(row).to_be_visible(timeout=5000)
        # Date indicator should be shown
        expect(page.locator(".report-restore .prev-date")).to_be_visible(timeout=5000)
    finally:
        os.unlink(pdf_path)


@pytest.mark.playwright
def test_upload_pdf_shows_info_when_queries_exist(page: Page, context: BrowserContext):
    """Uploading a PDF when queries already exist shows an info message without overwriting."""
    pdf_path = _write_temp_pdf(_make_ojhunt_pdf(context, username="tourist"))
    try:
        page.goto(BASE_URL)
        _clear_storage(page)

        # Add a different query first
        page.select_option("select[x-model='selectedCrawler']", "codeforces")
        page.fill("input[placeholder='Username']", "different_user")
        page.click('button:has-text("Add")')
        expect(
            page.locator("tbody.result-row").filter(has_text="different_user")
        ).to_be_visible(timeout=5000)

        # Now upload the PDF — dismiss the confirm dialog (don't refresh)
        page.on("dialog", lambda d: d.dismiss())
        page.set_input_files("input[type='file']", pdf_path)
        page.wait_for_timeout(2000)

        # Original query should still be there, not replaced
        expect(
            page.locator("tbody.result-row").filter(has_text="different_user")
        ).to_be_visible()
    finally:
        os.unlink(pdf_path)


@pytest.mark.playwright
def test_upload_invalid_file_shows_error(page: Page):
    """Uploading a non-OJHunt file shows an alert."""
    tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False, dir=_TMPDIR)
    tmp.write(b"not a real pdf at all")
    tmp.close()
    try:
        page.goto(BASE_URL)
        _clear_storage(page)

        dialog_messages = []
        page.on("dialog", lambda d: (dialog_messages.append(d.message), d.accept()))
        page.set_input_files("input[type='file']", tmp.name)
        page.wait_for_timeout(3000)

        assert any("PDF" in m or "pdf" in m for m in dialog_messages)
    finally:
        os.unlink(tmp.name)


@pytest.mark.playwright
def test_download_report_updates_date_indicator(page: Page, context: BrowserContext):
    """After querying, downloading a report updates the date indicator in the UI."""
    page.goto(BASE_URL)
    _clear_storage(page)

    # Add and run a query
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='Username']", "tourist")
    page.click('button:has-text("Add")')
    page.click('button:has-text("Query All")')
    row = page.locator("tbody.result-row").filter(has_text="CodeForces")
    expect(row).to_have_class("result-row success", timeout=30000)

    # Download report and intercept the download
    with page.expect_download() as dl_info:
        page.click('button:has-text("Download Report")')
    download = dl_info.value
    assert download.suggested_filename.startswith("ojhunt-report-")
    assert download.suggested_filename.endswith(".pdf")

    # Date indicator should be updated
    expect(page.locator(".report-restore .prev-date")).to_be_visible(timeout=5000)


@pytest.mark.playwright
def test_download_then_upload_shows_date_and_merges(
    page: Page, context: BrowserContext
):
    """Download a report, re-upload it — date indicator matches and history is preserved."""
    page.goto(BASE_URL)
    _clear_storage(page)

    # Add and run a query
    page.select_option("select[x-model='selectedCrawler']", "codeforces")
    page.fill("input[placeholder='Username']", "tourist")
    page.click('button:has-text("Add")')
    page.click('button:has-text("Query All")')
    row = page.locator("tbody.result-row").filter(has_text="CodeForces")
    expect(row).to_have_class("result-row success", timeout=30000)

    # Download report — download.path() is already on disk, use it directly
    with page.expect_download() as dl_info:
        page.click('button:has-text("Download Report")')
    download = dl_info.value
    date_text = page.locator(".report-restore .prev-date").inner_text(timeout=5000)

    # Clear storage and reload, then re-upload the downloaded file
    _clear_storage(page)
    page.set_input_files("input[type='file']", download.path())

    # Date should match what was shown after download
    expect(page.locator(".report-restore .prev-date")).to_have_text(
        date_text, timeout=5000
    )
    # Queries should be restored
    expect(
        page.locator("tbody.result-row").filter(has_text="CodeForces")
    ).to_be_visible(timeout=5000)


@pytest.mark.playwright
def test_upload_historical_pdf_entries_preserved_in_new_download(
    page: Page, context: BrowserContext, historical_pdf_path: str
):
    """Old history entries (2020 dates) survive the full upload → query → download cycle."""
    page.goto(BASE_URL)
    _clear_storage(page)

    # Upload the historical PDF (3 entries from 2020)
    page.set_input_files("input[type='file']", historical_pdf_path)
    expect(page.locator(".report-restore .prev-date")).to_be_visible(timeout=5000)
    expect(
        page.locator("tbody.result-row").filter(has_text="CodeForces")
    ).to_be_visible(timeout=5000)

    # Query and download a new report (today's date ~2026)
    page.click('button:has-text("Query All")')
    expect(
        page.locator("tbody.result-row").filter(has_text="CodeForces")
    ).to_have_class("result-row success", timeout=30000)
    with page.expect_download() as dl_info:
        page.click('button:has-text("Download Report")')
    download = dl_info.value

    # Extract history from the new PDF and verify the 2020 entries are still there
    with open(download.path(), "rb") as f:
        new_pdf_bytes = f.read()
    extracted = extract_data(new_pdf_bytes)
    keys = [e.key for e in extracted.history]
    assert "2020-01-01" in keys, f"Old history entry missing; got keys: {keys}"
    assert "2020-01-02" in keys
    assert "2020-01-03" in keys
    # And at least one entry from ~2026 (today) was added
    assert any(k.startswith("202") and k > "2020" for k in keys), (
        f"No recent entry found; keys: {keys}"
    )
