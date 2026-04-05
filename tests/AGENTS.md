# AGENTS.md - Tests

## Test Structure

- **Crawler tests**: `tests/crawlers/<name>_test.py` — unit tests for individual crawlers
- **Web unit tests**: `tests/web/<module>_test.py` (e.g. `tests/web/api_test.py`) — pure Python, no server needed
- **Web e2e tests**: `tests/e2e/test_*.py` — Playwright only, require a running server at `localhost:8080`

Do not put unit tests in `tests/e2e/` — that folder is exclusively for Playwright e2e tests.

New page routes must have a corresponding unit test. Use `TestClient(app, follow_redirects=False)` and `monkeypatch` to mock functions in `pages.py`. File upload testing: `files={"field": ("name.pdf", bytes, "application/pdf")}`.

- Use `pytest_asyncio.fixture` for aiohttp session
- Standard test cases: `test_user_not_exist`, `test_username_with_space`, `test_valid_user`
- `TEST_USERNAME` comes from the crawler's `__crawler_meta__["test_username"]` — import it, don't hardcode

## Test Assertions for crawlers

Each test must assert all three fields: `solved`, `submissions`, `solved_list`:

1. **When all fields are available:**
   - `solved > 0`
   - `submissions >= solved`
   - `len(solved_list) == solved`

2. **When a field is not available from the API/site:**
   - Use `None` for `solved_list` (not empty list `[]`)
   - Use `0` for `submissions`
   - Add a comment in the test explaining why the field is unavailable
