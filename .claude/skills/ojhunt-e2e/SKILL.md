---
name: ojhunt-e2e
description: Playwright e2e browser tests. Load whenever the task involves e2e tests — understanding coverage, planning browser test scenarios, writing or running Playwright tests. See also ojhunt-testing for shared pytest conventions.
---

# E2E Tests (Playwright)

See also the **ojhunt-testing** skill for shared pytest fixture and assertion conventions.

## Setup

- Tests use `test_*.py` naming convention (crawler unit tests use `*_test.py`)
- Marked with `@pytest.mark.playwright` — excluded from regular CI
- Require a running web server: `uv run pytest -m playwright tests/e2e/`
- **macOS sandbox**: Playwright cannot launch Chromium under the Claude Code sandbox (macOS
  Mach port rendezvous is blocked). Always run e2e tests with `dangerouslyDisableSandbox: true`
  in the Bash tool, or have the user run them directly via `! uv run pytest -m playwright tests/e2e/`
- Install browsers first: `uv run playwright install --with-deps chromium`
- Always run e2e tests after writing or modifying them — don't mark done until they pass

## Test quirks

- **localStorage**: Persistence tests must clear localStorage before testing:
  `page.evaluate("localStorage.clear()")` then `page.reload()`
- **Canceled queries**: Return to "pending" state (not "canceled"); the query button becomes
  visible again for retry
- **Button locators**: Use `.first` when multiple buttons exist in a row, e.g.:
  `row.locator("button.remove-btn").first`
- **Mocking external APIs**: When a test exercises logic *around* a crawler (e.g. PDF
  history merging), use `page.route("**/api/crawlers/<name>/<user>", handler)` with
  `route.fulfill(...)` instead of hitting the real API. Real crawler integration is
  covered by `test_query.py`. Multiple consecutive live calls can hit rate limits in CI.
