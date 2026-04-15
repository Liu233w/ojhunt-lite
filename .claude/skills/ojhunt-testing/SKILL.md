---
name: ojhunt-testing
description: Unit tests and crawler tests. Use when writing or running pytest tests (non-Playwright).
---

# Unit Tests & Crawler Tests

See also the **ojhunt-e2e** skill for Playwright-specific testing.

## Running tests

```bash
# Always prefix with TMPDIR — sandbox blocks /tmp
TMPDIR=/private/tmp/claude-503 uv run pytest tests/crawlers/<name>_test.py

# CI scope (excludes network + Playwright tests)
uv run pytest -m "not network and not playwright"

# Full suite
uv run pytest
```

**CI runs `pytest -m "not network and not playwright"` — never run crawler (network) tests
when debugging CI failures.**

## Test structure

| Type | Location | Convention | Requires server |
|------|----------|-----------|-----------------|
| Crawler unit tests | `tests/crawlers/<name>_test.py` | `*_test.py` | No |
| Web unit tests | `tests/web/<module>_test.py` | `*_test.py` | No |
| Web e2e tests | `tests/e2e/test_*.py` | `test_*.py` | Yes (`localhost:8080`) |

Do not put unit tests in `tests/e2e/` — that folder is exclusively for Playwright tests.

## Pytest fixtures

Use `pytest_asyncio.fixture` for aiohttp sessions:

```python
import pytest, pytest_asyncio, aiohttp

@pytest_asyncio.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s
```

## Standard crawler test cases

Every crawler test file must have all three:

```python
TEST_USERNAME = __crawler_meta__["test_username"]  # import, don't hardcode
NOT_EXIST_USERNAME = "fmv84zcq3hwu_notexist"

async def test_user_not_exist(session): ...
async def test_username_with_space(session): ...
async def test_valid_user(session): ...
```

## Test assertions for crawlers

Assert all three fields in `test_valid_user`:

**When all fields are available:**
```python
assert result["solved"] > 0
assert result["submissions"] >= result["solved"]
assert len(result["solved_list"]) == result["solved"]
```

**When a field is unavailable from the site:**
- `solved_list`: use `None` (not `[]`); add a comment explaining why
- `submissions`: use `0`; add a comment explaining why

If `len(solved_list) < solved` (uncategorized problems not in the problem list), add a
comment in the test explaining the discrepancy.

## Page route unit tests

New page routes must have a corresponding unit test. Use `TestClient` with monkeypatching:

```python
from starlette.testclient import TestClient
client = TestClient(app, follow_redirects=False)

# File upload syntax:
files={"field": ("name.pdf", bytes_content, "application/pdf")}
```

## Markdown doc tests

Python fenced blocks in `README.md` and `docs/` are collected by `pytest-markdown-docs`
and run as part of the standard CI suite (`not network and not playwright`).

- Use `python notest` in the fence header to exclude a block (network calls, incomplete templates)
- `notest` is the correct keyword — NOT `skip` (which is silently ignored)

## Login-required crawler testing (CLI)

For `shared_account` crawlers, tests read credentials from `.env` automatically — create
`.env` first if it doesn't exist. The CLI test pattern:

```bash
uv run ojhunt -l username:password@<crawler> -- target_user@<crawler>
```

To discover which crawlers require login:
```bash
uv run ojhunt --list --json | jq 'with_entries(select(.value.login_type | contains("account")))'
```
