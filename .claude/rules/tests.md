---
paths:
  - "**/*_test.py"
  - "tests/**/*.py"
---

# Pytest conventions

Crawler-specific test conventions live in [`docs/dev/crawlers.md`](../../docs/dev/crawlers.md)
and the **ojhunt-crawlers** skill. Playwright e2e tests have their own rule in
[`e2e.md`](e2e.md).

## Running tests

```bash
# Single file
uv run pytest tests/<path>/<name>_test.py

# CI scope (excludes network + Playwright tests)
uv run pytest -m "not network and not playwright"

# Full suite
uv run pytest
```

**CI runs `pytest -m "not network and not playwright"` — never run crawler (network) tests
when debugging CI failures.**

To run everything at once before committing, use `./doit.sh full-check`: it starts the dev
server, runs lint + unit + e2e + visual, then stops the server (leaving a server you started
yourself untouched) and reports every failing suite. This is the gate the **ojhunt-implement**
workflow runs before it commits.

## Test structure

| Type | Location | Convention | Requires server |
|------|----------|-----------|-----------------|
| Crawler unit tests | `tests/crawlers/<name>_test.py` | `*_test.py` | No |
| Web unit tests | `tests/web/<module>_test.py` | `*_test.py` | No |
| Web e2e tests | `tests/e2e/test_*.py` | `test_*.py` | Yes (`localhost:8080`) |

Do not put unit tests in `tests/e2e/` — that folder is exclusively for Playwright tests.

## Page route unit tests

New page routes must have a corresponding unit test. Use `TestClient` with monkeypatching:

```python notest
from starlette.testclient import TestClient

client = TestClient(app, follow_redirects=False)

# File upload syntax:
files = {"field": ("name.pdf", bytes_content, "application/pdf")}
```

## Prefer discovery over a hardcoded list

A test that enumerates today's routes, crawlers, or files goes stale in silence: the thing it
was meant to catch is exactly the new entry nobody added to the list. Walk the router or glob
the directory instead. When a shape genuinely cannot be discovered, assert that no such shape
exists yet, so the day one appears the suite says so.

## Markdown doc tests

Python fenced blocks in `README.md` and `docs/` are collected by `pytest-markdown-docs`
and run as part of the standard CI suite (`not network and not playwright`).

- Use `python notest` in the fence header to exclude a block (network calls, incomplete templates)
- `notest` is the correct keyword — NOT `skip` (which is silently ignored)
