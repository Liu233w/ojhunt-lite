# AGENTS.md - Guidelines for AI Agents

## Project Overview

OJHunt Lite is an async Python tool for querying Online Judge statistics across 28 competitive programming platforms.

**Read these files first:**
- `README.md` - Usage examples, crawler templates, development setup

## Parallel Execution

When editing multiple crawlers or performing independent tasks, spawn sub-agents to work in parallel. This is strongly recommended for:
- Editing multiple crawler files simultaneously
- Running tests across multiple crawlers
- Analyzing multiple files independently

## Build & Test Commands

```bash
uv sync                                    # Install dependencies
uv add <package>                           # Add a new dependency (don't specify version, let uv resolve)
pytest                                     # Run all tests
pytest crawlers/codeforces_test.py         # Run single test file
pytest crawlers/codeforces_test.py::test_valid_user  # Run single test
uv run ojhunt.py --crawler codeforces --username tourist  # Run CLI
uv run fastapi dev web/app.py --port 8080 # Run web dev server
uv run fastapi run web/app.py --port 8080 # Run web prod server
uv run ruff check .                        # Run linter (required after edits)
```

To test web services, ask user to run the following code on their terminal to spin up the service:
```bash
VJUDGE_USERNAME= VJUDGE_PASSWORD= uv run fastapi dev web/app.py 2>&1 > logs/web.log
```

The user needs to fill the VJUDGE_USERNAME and VJUDGE_PASSWORD environment variables with their credentials before running the service.

For you to test the frontend, use playwright skills instructed in https://github.com/microsoft/playwright-cli

## Dependency Management

- **Never specify version numbers** when adding dependencies. Use `uv add <package>` and let uv resolve the version.
- This applies to all dependencies including FastAPI, uvicorn, etc.

## Updating AGENTS.md

When the user provides guidance about practices or conventions during a conversation (e.g., "use uv add without version numbers"), add those rules to this file automatically.

## Code Style

### Imports
Standard library -> Third-party -> Typing:
```python
import re
import aiohttp
from selectolax.lexbor import LexborHTMLParser
from typing import Dict, List, Union
```

### Naming
- Files: `snake_case.py` (crawlers), `*_test.py` (tests)
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

### Typing
Use `Dict`, `List`, `Union` from `typing` module (not `dict[str, ...]` syntax).

### HTML Parsing
Use `selectolax.lexbor.LexborHTMLParser`.

### License Header
BSD-2 Clause license header (copy from existing crawler, use current year for new files).
- **Only add license headers to files in `crawlers/` folder** - users can copy individual crawler files.
- **Do NOT add license headers** to CLI, web, or other internal code.

## Error Handling

- `ValueError`: User input errors (empty username, user not found)
- `RuntimeError`: Network failures, parsing errors, unexpected issues

## Test Structure

- Test file: `crawlers/<name>_test.py`
- Use `pytest_asyncio.fixture` for aiohttp session
- Standard test cases: `test_user_not_exist`, `test_username_with_space`, `test_valid_user`
- Use real test usernames from existing tests (e.g., `leoloveacm`, `vjudge5`)

### Testing New Features

When adding new features, tests are **required**:

- **Crawler changes**: Add/update tests in `crawlers/<name>_test.py`
- **Web backend changes**: Add API tests in `web/tests/test_api.py` or appropriate test file
- **Web frontend changes**: Add Playwright E2E tests in `web/tests/test_*.py`
- **CLI changes**: Add tests in `cli/<name>_test.py`

Run the relevant test suite after implementation to verify correctness.

### Playwright Tests

Playwright tests are located in `web/tests/` and test the web frontend:

```bash
# Install Playwright browsers (one-time setup)
uv run playwright install chromium

# Run Playwright tests (requires running web server)
uv run pytest -m playwright web/tests/

# Run all tests except Playwright
uv run pytest -m "not playwright"
```

**Prerequisites:**
- Start the web server before running Playwright tests: `uv run fastapi dev web/app.py --port 8080`
- Tests use `tourist` as the test user for Codeforces queries

### Test Assertions

Each test must assert all three fields: `solved`, `submissions`, `solved_list`:

1. **When all fields are available:**
   - `solved > 0`
   - `submissions >= solved`
   - `len(solved_list) == solved`

2. **When a field is not available from the API/site:**
   - Use `None` for `solved_list` (not empty list `[]`)
   - Use `0` for `submissions`
   - Add a comment in the test explaining why the field is unavailable

## Key Reference Files

| Purpose | File |
|---------|------|
| API-based crawler | `crawlers/codeforces.py` |
| HTML-scraping crawler | `crawlers/hdu.py` |
| Test example | `crawlers/codeforces_test.py` |
| CLI entry point | `ojhunt.py` |
| Archived crawlers | `archived_crawlers/` |

## Archived Crawlers

Crawlers for dead sites or sites with unfixable issues are moved to `archived_crawlers/`. Do not list individual archived crawlers in documentation - point users to the folder instead.

**Important:**
- `archived_crawlers/` does NOT have an `__init__.py` - it's for archival only, not a package
- Tests in `archived_crawlers/` are NOT run by pytest
- Do not create stub crawlers that just raise exceptions - add them to `archived_crawlers/README.md` instead

## Environment Variables

The web application accepts the following environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `VJUDGE_USERNAME` | For VJudge | Username for VJudge authentication |
| `VJUDGE_PASSWORD` | For VJudge | Password for VJudge authentication |
| `BUILD_TIME` | No | Build timestamp (Unix epoch or ISO format), shown on About page |
| `GIT_COMMIT_SHA` | No | Git commit hash, used to generate source code link on About page |
