# AGENTS.md - Guidelines for AI Agents

## Working with Claude Code (Claude-specific notes)

- **Always edit `AGENTS.md` directly**, not `CLAUDE.md` — `CLAUDE.md` is a symlink to `AGENTS.md` and some tools may not follow it correctly.

## Project Overview

OJHunt Lite is an async Python tool for querying Online Judge statistics across 28 competitive programming platforms.

**Read these files first:**
- `README.md` - Usage examples, crawler templates, development setup

## Directory Structure

```
src/ojhunt/        # Installable package (pip install ojhunt)
    crawlers/      # Active crawlers (auto-discovered via __init__.py)
    core/          # Shared models and runner
    web/           # FastAPI web app
tests/             # Test suite (mirrors src/ojhunt/ layout)
    crawlers/      # Crawler unit tests
    cli/           # CLI unit tests
    web/           # Web unit tests
    e2e/           # Playwright e2e tests (require running server)
archived_crawlers/ # Dead/broken crawlers (not a package, not tested)
scripts/           # Developer utilities (not packaged)
```

## Parallel Execution

When editing multiple crawlers or performing independent tasks, spawn sub-agents to work in parallel. This is strongly recommended for:
- Editing multiple crawler files simultaneously
- Running tests across multiple crawlers
- Analyzing multiple files independently

## Build & Test Commands

```bash
uv sync                                                   # Install dependencies
uv add <package>                                          # Add a new dependency (don't specify version, let uv resolve)
uv run pytest                                                    # Run all tests
uv run pytest tests/crawlers/codeforces_test.py                  # Run single test file
uv run pytest tests/crawlers/codeforces_test.py::test_valid_user # Run single test
uv run ojhunt tourist@codeforces                          # Run CLI
uv run fastapi dev src/ojhunt/web/app.py --port 8080      # Run web dev server
uv run fastapi run src/ojhunt/web/app.py --port 8080      # Run web prod server
uv run ruff format .                                      # Run formatter (required after edits)
uv run ruff check .                                       # Run linter (required after edits)
```

To test web services, use tmux to manage the background server:

**Session name:** `ojhunt-web` | **Port:** `8080`

```bash
# Check if service is running
tmux has-session -t ojhunt-web 2>/dev/null && echo "Running" || echo "Not running"

# Start server (if not running)
tmux new-session -d -s ojhunt-web -c <project folder> "uv run fastapi dev src/ojhunt/web/app.py --port 8080"

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
- **Only add license headers to files in `src/ojhunt/crawlers/` folder** - users can copy individual crawler files.
- **Do NOT add license headers** to CLI, web, or other internal code.

## Error Handling

- `ValueError`: User input errors (empty username, user not found)
- `RuntimeError`: Network failures, parsing errors, unexpected issues

## Login-Required Crawlers

There are two distinct types of login-required crawlers. Always identify which type before implementing:

**Own Account (`own_account`) — Login to see your own data only:**
- The platform only exposes a user's own stats when they are logged in.
- The crawler must log in *as the target user* to retrieve their data.
- `login_user` and `login_password` equal `username` and `password`.
- CLI usage: `user:pass@crawler` (the `-l` flag is redundant/inapplicable).
- Example platforms: QOJ, LightOJ, Jisuanke (if implemented).

**Shared Account (`shared_account`) — Any account can query any user:**
- The platform requires login, but once authenticated any user's stats are visible.
- A single shared account can query arbitrary target users.
- `login_user`/`login_password` (from `-l` flag) may differ from `username`.
- CLI usage: `-l mylogin:mypass@crawler -- target@crawler`.
- Example platforms (implemented): CSES, VJudge.

**How to identify the type:** Visit the site as a guest and try to access another user's profile. If it's blocked (login wall on all profiles), it's Shared Account. If profiles are public for others but not for yourself, it's Own Account.

**Reference implementations:**
- Shared Account: `src/ojhunt/crawlers/vjudge.py`, `src/ojhunt/crawlers/cses.py`

**`CrawlerMeta` field mapping:**
- `"login_type": "shared_account"` → Shared Account (supports `-l` flag; any account can query any user)
- `"login_type": "own_account"` → Own Account (must log in as the target user)
- key omitted → no login required

## Crawler Metadata Fields (`__crawler_meta__`)

| Field | Required | Description |
|-------|----------|-------------|
| `title` | Yes | Display name |
| `url` | Yes | Homepage URL |
| `test_username` | Yes | Used for tests and `/crawlers` availability checks |
| `description` | No | Shown in web UI (default: `""`) |
| `cli_description` | No | Shown in `--list` CLI output instead of `description` when present. Use for crawlers where the CLI usage differs significantly (e.g., login instructions, ID vs. username). |
| `login_type` | No | `"shared_account"` or `"own_account"`; omit if no login required |
| `is_aggregator` | No | Whether this crawler aggregates problems from other platforms (e.g. VJudge, NIT). Aggregator solvedLists are already prefixed with the source platform, so `/api/merge` skips re-prefixing them. |

## Architectural Decisions

### When to write an ADR

The user works in two modes:

- **Plan mode** — the user arrives with a concrete plan; refine and implement it directly. No ADR needed unless the plan itself involves a significant design decision.
- **Normal mode discussion** — the user is exploring options and is unsure what to do. When a decision crystallizes from that discussion, write the ADR *before* implementing.

A discussion-mode conversation is the signal. If you find yourself in open-ended back-and-forth about trade-offs, that's the right moment to propose creating an ADR once alignment is reached.

A decision warrants an ADR if:
- Multiple approaches were considered and one was rejected
- The decision won't be obvious from reading the code
- Future contributors might be tempted to reverse it without understanding the context

### How to write an ADR

Create `docs/adr/NNNN-short-title.md` (see https://adr.github.io/) and add a one-line pointer to `docs/development.md`. Status should be one of: `Proposed`, `Accepted`, `Deprecated`, `Superseded`.

Write the ADR before starting implementation. If implementation reveals the decision needs to change, update the ADR first — don't silently deviate from it.

## Design Principles

- **Easy to add new crawlers.** Adding a new crawler should only require creating one crawler file + one test file. All crawler-specific data (metadata, test username) lives in `__crawler_meta__`. Avoid centralizing crawler-specific data elsewhere — if adding a crawler requires editing unrelated files, that's a design smell.
- **Challenge decisions.** When a proposed approach duplicates data, makes adding crawlers harder, or adds unnecessary complexity — flag it before implementing.

## Test Structure

- **Crawler tests**: `tests/crawlers/<name>_test.py` — unit tests for individual crawlers
- **Web unit tests**: `tests/web/<module>_test.py` (e.g. `tests/web/api_test.py`) — pure Python, no server needed
- **Web e2e tests**: `tests/e2e/test_*.py` — Playwright only, require a running server at `localhost:8080`

Do not put unit tests in `tests/e2e/` — that folder is exclusively for Playwright e2e tests.

New page routes must have a corresponding unit test. Use `TestClient(app, follow_redirects=False)` and `monkeypatch` to mock functions in `pages.py`. File upload testing: `files={"field": ("name.pdf", bytes, "application/pdf")}`.

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
| API-based crawler | `src/ojhunt/crawlers/codeforces.py` |
| HTML-scraping crawler | `src/ojhunt/crawlers/hdu.py` |
| Test example | `tests/crawlers/codeforces_test.py` |
| Crawler metadata model | `src/ojhunt/core/models.py` |
| CLI entry point | `src/ojhunt/__main__.py` |
| Archived crawlers | `archived_crawlers/` |
| Shared Account login crawler | `src/ojhunt/crawlers/vjudge.py` |
| Numeric ID crawler | `src/ojhunt/crawlers/luogu.py`, `src/ojhunt/crawlers/nod.py` |
| Crawler analysis guide | `.claude/skills/analyze-crawler.md` |
| Legacy DB query functions (web) | `src/ojhunt/web/legacy_db.py` |
| Page route tests example | `tests/web/pages_test.py` |

## Archived Crawlers

Crawlers for dead sites or sites with unfixable issues are moved to `archived_crawlers/`. Do not list individual archived crawlers in documentation - point users to the folder instead.

**Important:**
- `archived_crawlers/` does NOT have an `__init__.py` - it's for archival only, not a package
- Tests in `archived_crawlers/` are NOT run by pytest
- Do not create stub crawlers that just raise exceptions - add them to `archived_crawlers/README.md` instead

## PDF internals

- `extract_data(pdf_bytes)` returns `PdfEmbeddedData` — has `settings` and `history` only. It does **not** have a `snapshot`; the snapshot is never embedded in the PDF. Build one manually from history if needed.
- For page routes returning `application/pdf` on success and HTML on error: return explicit `Response(content=..., media_type="application/pdf")` or `HTMLResponse(...)` — do not use `response_class=HTMLResponse` on the decorator.
- When adding form-based page endpoints accessible to agents, document them in `llms.txt`.

## Containerfile

The container copies the entire `src/ojhunt/` directory as a single unit (`COPY src/ojhunt ./ojhunt`). No changes to `Containerfile` are needed when adding new crawlers or modules within the package.

## Environment Variables

The web application accepts the following environment variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `LOGIN_USERNAME__<CRAWLER>` | For shared-account crawlers | Username for crawler authentication (uppercase crawler name) |
| `LOGIN_PASSWORD__<CRAWLER>` | For shared-account crawlers | Password for crawler authentication (uppercase crawler name) |
| `BUILD_TIME` | No | Build timestamp (Unix epoch or ISO format), shown on About page |
| `GIT_COMMIT_SHA` | No | Git commit hash, used to generate source code link on About page |

To discover which crawlers require login, run:
```bash
uv run ojhunt --list --json | jq 'with_entries(select(.value.login_type | contains("account")))'
```

**Credentials** are stored in `.env` (gitignored) — loaded automatically by `load_dotenv()` in `src/ojhunt/web/app.py`, no need to `source .env` manually. Create `.env` if it doesn't exist and add entries for each login-required crawler:
```
LOGIN_USERNAME__<CRAWLER>=...
LOGIN_PASSWORD__<CRAWLER>=...
```

The user will need to fill the fields.

### Testing CLI with Login-Required Crawlers

For `shared_account` crawlers, tests read credentials from `.env` automatically — no need to extract them manually. If `.env` doesn't exist, create it first with the relevant credentials.

The CLI test pattern for shared-account crawlers:
```bash
uv run ojhunt -l username:password@<crawler> -- target_user@<crawler>
```
