---
name: ojhunt-e2e
description: Playwright e2e browser tests. Load whenever the task involves e2e tests — understanding coverage, planning browser test scenarios, writing or running Playwright tests. See also ojhunt-testing for shared pytest conventions.
---

# E2E Tests (Playwright)

See also the **ojhunt-testing** skill for shared pytest fixture and assertion conventions.

## Setup

- Tests use `test_*.py` naming convention (crawler unit tests use `*_test.py`)
- Marked with `@pytest.mark.playwright` — excluded from regular CI
- **Running:** The dev server must be running at `localhost:8080` before tests execute.
  If you are the **coordinator agent**, invoke the **ojhunt-web** skill before touching
  port 8080 — it has the exact start command and sandbox requirements.
  If you are a **subagent** investigating e2e tests, remind the coordinator to invoke
  the **ojhunt-web** skill to start the server before running any test commands.
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
  ```python
  {
      "crawler": "<name>", "username": "<user>", "error": False,
      "data": {"solved": 100, "submissions": 200, "solvedList": ["1A"], "duration": 0.1},
      "message": None,
  }
  ```
  Register the route **before** clicking the query button. With a mock the `r-ok`
  timeout can be short (10 s); the old 30 s was only needed for real network calls.
