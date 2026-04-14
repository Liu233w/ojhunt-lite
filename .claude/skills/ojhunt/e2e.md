# E2E Tests (Playwright)

See also **[testing.md](testing.md)** for shared pytest fixture and assertion conventions.

## Setup

- Tests use `test_*.py` naming convention (crawler unit tests use `*_test.py`)
- Marked with `@pytest.mark.playwright` — excluded from regular CI
- Require a running web server: `uv run pytest -m playwright tests/e2e/`
- Install browsers first: `uv run playwright install --with-deps chromium`
- Always run e2e tests after writing them — don't mark done until they pass

## Test quirks

- **localStorage**: Persistence tests must clear localStorage before testing:
  `page.evaluate("localStorage.clear()")` then `page.reload()`
- **Canceled queries**: Return to "pending" state (not "canceled"); the query button becomes
  visible again for retry
- **Button locators**: Use `.first` when multiple buttons exist in a row, e.g.:
  `row.locator("button.remove-btn").first`
