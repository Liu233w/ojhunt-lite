# AGENTS.md - Web Tests

## Playwright Tests

- Tests use `test_*.py` naming convention (crawlers use `*_test.py`)
- Marked with `@pytest.mark.playwright` and excluded from regular CI
- Require running web server: `uv run pytest -m playwright tests/e2e/`
- Install browsers first: `uv run playwright install --with-deps chromium`

## Test Quirks

- Persistence tests must clear localStorage before testing: `page.evaluate("localStorage.clear()")`
- Canceled queries return to "pending" state (not "canceled"), query button becomes visible for retry
- Use `.first` for button locators when multiple buttons exist in a row (e.g., `row.locator("button.remove-btn").first`)
