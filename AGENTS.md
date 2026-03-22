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

To test web services, use tmux to manage the background server:

**Session name:** `ojhunt-web` | **Port:** `8080`

```bash
# Check if service is running
tmux has-session -t ojhunt-web 2>/dev/null && echo "Running" || echo "Not running"

# Start server (if not running)
tmux new-session -d -s ojhunt-web -c <project folder> "uv run fastapi dev web/app.py --port 8080"

# View logs
tmux capture-pane -t ojhunt-web -p

# Stop server
tmux kill-session -t ojhunt-web
```

**Workflow:**
1. Check if `ojhunt-web` session exists before starting
2. Keep the server running after testing (don't stop it)
3. User can ask to stop the service
4. If tmux is not installed, inform user it works best with tmux

Then use `curl` or Playwright skills to test the frontend.

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

Prefer CSS selectors over regex when extracting values from HTML structure. Use the `lexbor-contains` pseudo-class to find an element by its text content, then navigate to sibling/child elements for the value:

```python
# Find a <td> containing "Submission count", then get the next sibling <td>
# Note: do NOT include a trailing colon in the text — lexbor parses it as CSS pseudo-class syntax
count = doc.css_first('td:lexbor-contains("Submission count") + td').text(strip=True)

# Check presence of text in a container
if doc.css_first('.content:lexbor-contains("Please login")'):
    ...
```

Reserve `re` for strings that are not structured HTML — e.g. extracting a numeric ID from a URL (`/user/(\d+)`), or parsing a value embedded mid-sentence in a text node (`"Solved tasks: 150/400"`). See `archived_crawlers/fzu.py` for a reference example.

### License Header
BSD-2 Clause license header (copy from existing crawler, use current year for new files).
- **Only add license headers to files in `crawlers/` folder** - users can copy individual crawler files.
- **Do NOT add license headers** to CLI, web, or other internal code.

## Error Handling

- `ValueError`: User input errors (empty username, user not found)
- `RuntimeError`: Network failures, parsing errors, unexpected issues

## Login-Required Crawlers

There are two distinct types of login-required crawlers. Always identify which type before implementing:

**Type A — Login to see your own data only:**
- The platform only exposes a user's own stats when they are logged in.
- The crawler must log in *as the target user* to retrieve their data.
- `login_user` and `login_password` equal `username` and `password`.
- CLI usage: `user:pass@crawler` (the `-l` flag is redundant/inapplicable).
- Example platforms: QOJ, LightOJ, Jisuanke (if implemented).

**Type B — Any account can query any user:**
- The platform requires login, but once authenticated any user's stats are visible.
- A single shared account can query arbitrary target users.
- `login_user`/`login_password` (from `-l` flag) may differ from `username`.
- CLI usage: `-l mylogin:mypass@crawler -- target@crawler`.
- Example platforms: VJudge.

**How to identify the type:** Visit the site as a guest and try to access another user's profile. If it's blocked (login wall on all profiles), it's Type B. If profiles are public for others but not for yourself, it's Type A.

**Reference implementations:**
- Type B: `crawlers/vjudge.py`

## Crawler Metadata Fields (`__crawler_meta__`)

| Field | Required | Description |
|-------|----------|-------------|
| `title` | Yes | Display name |
| `url` | Yes | Homepage URL |
| `test_username` | Yes | Used for tests and `/crawlers` availability checks |
| `description` | No | Shown in web UI (default: `""`) |
| `cli_description` | No | Shown in `--list` CLI output instead of `description` when present. Use for crawlers where the CLI usage differs significantly (e.g., login instructions, ID vs. username). |
| `requires_login` | No | Requires credentials via `user:pass@crawler` or `-l` flag |
| `requires_password` | No | Requires password embedded in query |
| `is_virtual_judge` | No | Whether this is a virtual judge |

## Design Principles

- **Easy to add new crawlers.** Adding a new crawler should only require creating one crawler file + one test file. All crawler-specific data (metadata, test username) lives in `__crawler_meta__`. Avoid centralizing crawler-specific data elsewhere — if adding a crawler requires editing unrelated files, that's a design smell.
- **Challenge decisions.** When a proposed approach duplicates data, makes adding crawlers harder, or adds unnecessary complexity — flag it before implementing.

## Test Structure

- Test file: `crawlers/<name>_test.py`
- Use `pytest_asyncio.fixture` for aiohttp session
- Standard test cases: `test_user_not_exist`, `test_username_with_space`, `test_valid_user`
- `TEST_USERNAME` comes from the crawler's `__crawler_meta__["test_username"]` — import it, don't hardcode

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
| Crawler metadata model | `core/models.py` |
| CLI entry point | `ojhunt.py` |
| Archived crawlers | `archived_crawlers/` |
| Type B login crawler | `crawlers/vjudge.py` |
| Numeric ID crawler | `crawlers/luogu.py`, `crawlers/nod.py` |
| Crawler analysis guide | `.claude/skills/analyze-crawler.md` |

## Archived Crawlers

Crawlers for dead sites or sites with unfixable issues are moved to `archived_crawlers/`. Do not list individual archived crawlers in documentation - point users to the folder instead.

**Important:**
- `archived_crawlers/` does NOT have an `__init__.py` - it's for archival only, not a package
- Tests in `archived_crawlers/` are NOT run by pytest
- Do not create stub crawlers that just raise exceptions - add them to `archived_crawlers/README.md` instead

## Containerfile

When adding new Python packages/modules, update `Containerfile` to COPY the new directory. The container builds by copying each package individually (not a full `COPY . .`).

## Environment Variables

The web application accepts the following environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `LOGIN_USERNAME__VJUDGE` | For VJudge | Username for VJudge authentication |
| `LOGIN_PASSWORD__VJUDGE` | For VJudge | Password for VJudge authentication |
| `LOGIN_USERNAME__CSES` | For CSES | Username for CSES authentication |
| `LOGIN_PASSWORD__CSES` | For CSES | Password for CSES authentication |
| `VJUDGE_USERNAME` | Legacy | Backwards-compat alias for `LOGIN_USERNAME__VJUDGE` |
| `VJUDGE_PASSWORD` | Legacy | Backwards-compat alias for `LOGIN_PASSWORD__VJUDGE` |
| `BUILD_TIME` | No | Build timestamp (Unix epoch or ISO format), shown on About page |
| `GIT_COMMIT_SHA` | No | Git commit hash, used to generate source code link on About page |

**Credentials** are stored in `.env` (gitignored) — loaded automatically by `load_dotenv()` in `web/app.py`, no need to `source .env` manually:
```
LOGIN_USERNAME__VJUDGE=...
LOGIN_PASSWORD__VJUDGE=...
LOGIN_USERNAME__CSES=...
LOGIN_PASSWORD__CSES=...
```

The user will need to fill the fields.

### Testing CLI with VJudge

For CLI testing with VJudge, read credentials from `.env` and construct the command:
```bash
uv run ojhunt.py -l username:password@vjudge -- target_user@vjudge
```
