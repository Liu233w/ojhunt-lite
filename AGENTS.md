# AGENTS.md - Guidelines for AI Agents

## Working with Claude Code (Claude-specific notes)

- **Always edit `AGENTS.md` directly**, not `CLAUDE.md` — `CLAUDE.md` is a symlink to `AGENTS.md` and some tools may not follow it correctly.
- **Subdirectory context files are always named `AGENTS.md`**, not `CLAUDE.md`.

## Subdirectory Context

Load these when working in specific areas:
- `src/ojhunt/crawlers/AGENTS.md` — HTML parsing, login types, metadata fields, license headers, archived crawlers
- `src/ojhunt/web/AGENTS.md` — PDF internals, environment variables
- `src/ojhunt/cli/AGENTS.md` — CLI login flags, credential testing patterns
- `tests/AGENTS.md` — test structure, assertion conventions
- `tests/e2e/AGENTS.md` — Playwright quirks

## Project History

- **npuacm.info** — built by others (Jiduo Zhang); credited in the footer as inspiration. Never stored user data. Unrelated to this codebase.
- **github.com/Liu233w/acm-statistics** — the author's rewrite with history storage; deployed as a web service. Known at various times as *ACM Statistics*, *OJ Analyzer*, and *OJHunt*. Hit by a CloudCone VPS compromise in October 2025 — data after 2025-10-22 was lost. `legacy.db` preserves part of its data (history and crawler settings).
- **github.com/Liu233w/ojhunt-lite** (this repo) — complete rewrite from scratch as *OJHunt Lite*; no server-side user data storage.

When writing UI copy or docs referring to "the old site", it means the acm-statistics deployment — not npuacm.info.

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
uv run pytest -m "not network and not playwright"                # Run tests as CI does (skips crawler + e2e tests)
uv run pytest                                                    # Run all tests
uv run pytest tests/crawlers/codeforces_test.py                  # Run single test file
uv run pytest tests/crawlers/codeforces_test.py::test_valid_user # Run single test
uv run ojhunt tourist@codeforces                          # Run CLI
uv run fastapi dev src/ojhunt/web/app.py --port 8080      # Run web dev server
uv run fastapi run src/ojhunt/web/app.py --port 8080      # Run web prod server
uv run ruff format .                                      # Run formatter (required after edits)
uv run ruff check .                                       # Run linter (required after edits)
```

**Never use `gh` commands** — the bot user does not have GitHub credentials.

To test web services, use the Claude background task system to run the server:

**Port:** `8080`

**Workflow:**
1. Run `uv run fastapi dev src/ojhunt/web/app.py --port 8080` in the background; for Claude Code, disable the sandbox (the file watcher and loopback networking are sandbox-blocked)
2. Keep the server running after testing (don't stop it)
3. The user can ask to stop the service; to free port 8080: `lsof -ti :8080 | xargs kill -9`
4. Note: background tasks do not persist between conversations — restart at the beginning of each new session if needed

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

## Error Handling

- `ValueError`: User input errors (empty username, user not found)
- `RuntimeError`: Network failures, parsing errors, unexpected issues

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

## Containerfile

The container copies the entire `src/ojhunt/` directory as a single unit (`COPY src/ojhunt ./ojhunt`). No changes to `Containerfile` are needed when adding new crawlers or modules within the package.
