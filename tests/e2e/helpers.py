"""Shared helpers for e2e tests."""

import base64
import os
from pathlib import Path

from playwright.sync_api import Page, expect


def _dev_server_port() -> str:
    """Port the dev server under test is listening on.

    ``doit.sh`` exports ``OJHUNT_DEV_PORT`` (git worktrees use a dynamic port);
    fall back to the port ``doit.sh start`` recorded in ``.doit/server.port``,
    then the legacy default ``8080`` for a plain ``pytest`` run on the main checkout.
    """
    port = os.environ.get("OJHUNT_DEV_PORT")
    if not port:
        portfile = Path(__file__).resolve().parents[2] / ".doit" / "server.port"
        if portfile.exists():
            port = portfile.read_text().strip()
    return port or "8080"


BASE_URL = f"http://localhost:{_dev_server_port()}"


def _add_query(page: Page, crawler: str, username: str) -> None:
    page.select_option("select[x-model='selectedCrawler']", crawler)
    page.fill("input[placeholder='username']", username)
    page.click("button.btn:has-text('add')")


def _row(page: Page, text: str):
    return page.locator("#queries-tbl .card").filter(has_text=text)


def _clear_storage(page: Page) -> None:
    page.evaluate("localStorage.clear()")
    page.reload()


def _drag_drop_pdf(page: Page, pdf_bytes: bytes, filename: str = "report.pdf") -> None:
    """Simulate dragging a PDF onto the (visible) report slot via synthetic events."""
    pdf_b64 = base64.b64encode(pdf_bytes).decode()
    data_transfer = page.evaluate_handle(
        """([b64, name]) => {
            const dt = new DataTransfer();
            const bytes = Uint8Array.from(atob(b64), c => c.charCodeAt(0));
            const file = new File([bytes], name, {type: 'application/pdf'});
            dt.items.add(file);
            return dt;
        }""",
        [pdf_b64, filename],
    )
    # Target the empty slot specifically — both slots are in the DOM (x-show only
    # toggles display), so the strict-mode locator needs a disambiguating selector.
    slot = page.locator(".report-slot:not(.loaded)")
    slot.dispatch_event("dragover", {"dataTransfer": data_transfer})
    slot.dispatch_event("drop", {"dataTransfer": data_transfer})


def _dismiss_cookie_banner(page: Page) -> None:
    """Click OK to dismiss the fixed cookie banner so it doesn't obscure snapshots."""
    banner = page.locator("#cookie-banner")
    if banner.is_visible():
        page.click("#cookie-ok")
        expect(banner).to_be_hidden()
