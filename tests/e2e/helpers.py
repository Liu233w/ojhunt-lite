"""Shared helpers for e2e tests."""

import os
from pathlib import Path

from playwright.sync_api import Page


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
