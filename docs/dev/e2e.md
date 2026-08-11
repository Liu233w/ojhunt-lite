# E2E tests (Playwright)

See [`docs/dev/testing.md`](testing.md) for shared pytest fixture and assertion conventions.

## Setup

- Tests use `test_*.py` naming convention (crawler unit tests use `*_test.py`)
- Marked with `@pytest.mark.playwright` — excluded from regular CI
- **Running:** The dev server must be running at `localhost:8080` before tests execute.
  Start it with `./doit.sh start` (`dangerouslyDisableSandbox: true`; idempotent).
  Run visual tests: `./doit.sh test-visual` (starts server if needed; `dangerouslyDisableSandbox: true`).
  Update visual snapshots: `./doit.sh update-snapshots` (same sandbox requirement).
- **Visual diff on failure:** `conftest.py` writes `actual.png`, `expected.png`, `diff.png`
  to `test-results/visual/<name>/` when a snapshot mismatch occurs.
  Or have the user run directly: `! uv run pytest -m playwright tests/e2e/`
- Install browsers first: `uv run playwright install --with-deps chromium`
- Always run e2e tests after writing or modifying them — don't mark done until they pass

## Test quirks

- **localStorage**: Persistence tests must clear localStorage before testing:
  `page.evaluate("localStorage.clear()")` then `page.reload()`
- **Canceled queries**: Return to "pending" state (not "canceled"); the query button becomes
  visible again for retry
- **Button locators**: Use `.first` when multiple buttons exist in a row, e.g.:
  `row.locator("button.remove-btn").first`
- **`to_have_class` matching**: Playwright's `to_have_class(string)` does **exact**
  matching on the full class attribute, not CSS-token matching. Card elements always
  carry exactly two classes (`"card"` + one status class), so use the full string:
  `to_have_class("card r-ok")`, `to_have_class("card r-err")`, etc. Do not use
  `re.compile(r"r-ok")` — it would also match unrelated classes like `"foo-ok"`.
- **Always intercept crawler API calls**: Any test that needs a query result (even as
  setup to test something else) must intercept `**/api/crawlers/<name>/<user>` with
  `page.route(...)` and `route.fulfill(...)`. Never let e2e tests hit the real crawler
  network — live calls are flaky and can hit rate limits. Real crawler integration is
  covered by `test_query.py`. The success response shape is:
  ```python notest
  {
      "crawler": "<name>",
      "username": "<user>",
      "error": False,
      "data": {"solved": 100, "submissions": 200, "solvedList": ["1A"], "duration": 0.1},
      "message": None,
  }
  ```
  Register the route **before** clicking the query button. With a mock the `r-ok`
  timeout can be short (10 s); the old 30 s was only needed for real network calls.
