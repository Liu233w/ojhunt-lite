import pytest
from playwright.sync_api import Page, expect

from e2e.helpers import BASE_URL


@pytest.mark.playwright
def test_docs_page_renders(page: Page):
    """Swagger UI must fully render: its JS executes under the CSP, fetches
    /openapi.json, and paints the API title block. A blank page (the old CDN
    breakage) leaves .swagger-ui .info empty."""
    csp_errors: list[str] = []
    page.on(
        "console",
        lambda msg: (
            csp_errors.append(msg.text)
            if "Content Security Policy" in msg.text
            else None
        ),
    )
    page.goto(f"{BASE_URL}/docs")
    expect(page).to_have_title("OJHunt Lite - Swagger UI")
    expect(page.locator(".swagger-ui .info")).to_be_visible()
    # The rendered title comes from the fetched OpenAPI document.
    expect(page.locator(".swagger-ui .info .title")).to_contain_text("OJHunt Lite")
    assert not csp_errors, f"CSP violations on /docs: {csp_errors}"


@pytest.mark.playwright
def test_redoc_page_renders(page: Page):
    """ReDoc must render: it loads the self-hosted standalone bundle and runs
    its blob: web worker (allowed via worker-src in the CSP)."""
    csp_errors: list[str] = []
    page.on(
        "console",
        lambda msg: (
            csp_errors.append(msg.text)
            if "Content Security Policy" in msg.text
            else None
        ),
    )
    page.goto(f"{BASE_URL}/redoc")
    expect(page).to_have_title("OJHunt Lite - ReDoc")
    # ReDoc renders into a <redoc> custom element; the API title appears once
    # the worker has parsed the spec.
    expect(page.locator("redoc h1")).to_contain_text("OJHunt Lite")
    assert not csp_errors, f"CSP violations on /redoc: {csp_errors}"
