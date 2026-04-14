# Development Guide

## Setup

```bash
uv sync
```

## Adding a New Crawler

1. Create `src/ojhunt/crawlers/your_crawler.py` with a BSD-2 license header
2. Implement `async def query(...)` and add `__crawler_meta__`
3. Create `tests/crawlers/your_crawler_test.py`
4. The crawler is auto-discovered — no other files need editing

### API-based crawler template

```python notest
"""BSD-2 License header..."""
import aiohttp
from typing import Dict, List, Union, Optional

__crawler_meta__ = {
    'title': 'Your OJ',
    'description': 'Description here',
    'url': 'https://your-oj.com/',
    'test_username': 'known_active_user',
}

async def query(session: aiohttp.ClientSession, username: str, password: Optional[str] = None) -> Dict[str, Union[int, List[str], None]]:
    if not username or not username.strip():
        raise ValueError('Please enter username')

    username = username.strip()

    async with session.get(
        f'https://your-oj.com/api/user/{username}',
        timeout=aiohttp.ClientTimeout(total=30)
    ) as response:
        if response.status == 404:
            raise ValueError('The user does not exist')
        data = await response.json()

    return {
        'solved': data['solved'],
        'submissions': data['submissions'],
        'solved_list': data.get('problems', None),
    }
```

### HTML-scraping crawler template

```python notest
"""BSD-2 License header..."""
import aiohttp
from selectolax.lexbor import LexborHTMLParser
from typing import Dict, List, Union, Optional

__crawler_meta__ = {
    'title': 'Your OJ',
    'description': 'Description here',
    'url': 'https://your-oj.com/',
    'test_username': 'known_active_user',
}

async def query(session: aiohttp.ClientSession, username: str, password: Optional[str] = None) -> Dict[str, Union[int, List[str]]]:
    if not username or not username.strip():
        raise ValueError('Please enter username')

    username = username.strip()

    async with session.get(
        f'https://your-oj.com/user/{username}',
        timeout=aiohttp.ClientTimeout(total=30)
    ) as response:
        if response.status == 404:
            raise ValueError('The user does not exist')
        html = await response.text()

    doc = LexborHTMLParser(html)
    solved = int(doc.css_first('span.solved-count').text(strip=True))
    submissions = int(doc.css_first('span.submission-count').text(strip=True))
    solved_list = [a.text(strip=True) for a in doc.css('.problem-list a.problem-id')]

    return {
        'solved': solved,
        'submissions': submissions,
        'solved_list': solved_list,
    }
```

### Login-required crawler template (Shared Account)

```python notest
__crawler_meta__ = {
    'title': 'Your OJ',
    'url': 'https://your-oj.com/',
    'login_type': 'shared_account',
    'test_username': 'known_active_user',
}

async def query(
    session: aiohttp.ClientSession,
    username: str,
    password: Optional[str] = None,
    login_user: Optional[str] = None,
    login_password: Optional[str] = None,
) -> Dict[str, Union[int, List[str], None]]:
    if login_user and login_password:
        actual_user, actual_pass = login_user, login_password
    elif password:
        actual_user, actual_pass = username, password
    else:
        raise ValueError('Login credentials required')
    # ... use actual_user and actual_pass for authentication
```

See [`src/ojhunt/crawlers/vjudge.py`](../src/ojhunt/crawlers/vjudge.py) and
[`src/ojhunt/crawlers/cses.py`](../src/ojhunt/crawlers/cses.py) for complete reference
implementations.

### `__crawler_meta__` fields

| Field | Required | Description |
|-------|----------|-------------|
| `title` | Yes | Display name |
| `url` | Yes | Homepage URL |
| `test_username` | Yes | Used for tests and `/crawlers` availability checks |
| `description` | No | Shown in web UI (default: `""`) |
| `cli_description` | No | Shown in `--list` CLI output instead of `description`. Use when CLI usage differs significantly (e.g., login instructions, ID vs. username). |
| `login_type` | No | `"shared_account"` or `"own_account"`; omit if no login required |
| `is_aggregator` | No | Whether this crawler aggregates problems from other platforms (e.g. VJudge). Aggregator `solved_list` entries are already prefixed with the source platform, so `/api/merge` skips re-prefixing. |

### Login types

**Own Account (`own_account`)** — the platform only shows a user's own stats when logged in.
The crawler logs in *as the target user*. CLI: `user:pass@crawler`.

**Shared Account (`shared_account`)** — any authenticated user can view any user's stats.
A single shared account queries arbitrary targets. CLI: `-l mylogin:mypass@crawler -- target@crawler`.

## Return Format

All crawlers return:

```python
{
    "solved": int,            # Number of accepted problems
    "submissions": int,       # Total submissions (0 if unavailable)
    "solved_list": list|None  # Problem IDs (None if unavailable)
}
```

## Test File Locations

| Type | Location | Convention | Requires server |
|------|----------|-----------|-----------------|
| Crawler unit tests | `tests/crawlers/<name>_test.py` | `*_test.py` | No |
| Web unit tests | `tests/web/<module>_test.py` | `*_test.py` | No |
| Web e2e tests | `tests/e2e/test_*.py` | `test_*.py` | Yes (`localhost:8080`) |

## System Fonts for PDF Generation

PDF generation uses Unicode fonts to support non-latin usernames (CJK, Arabic, Hebrew, etc.).
The font is discovered at startup from the host system — no font files are bundled.

**Linux / Docker** — install both packages:

```bash
apt-get install fonts-noto fonts-noto-cjk-core
```

The `Containerfile` already includes this step, so production builds work out of the box.
For local Linux development, install the packages once and restart the server.

**macOS** — Arial Unicode (`/Library/Fonts/Arial Unicode.ttf`) is used automatically; no
extra steps needed.

**Neither font found** — the PDF generator falls back to Helvetica (latin-1 only). Non-latin
characters will raise an error.

## Deploying legacy.db

The `/pdf/legacy` page reads `legacy.db` from the current working directory at runtime.
The app works normally if the file is absent — the export form is simply disabled.

**Local**: place `legacy.db` in the project root.

**Docker / Podman**: mount the file at `/app/legacy.db` using an **absolute path**:
```bash
docker run -v $(pwd)/legacy.db:/app/legacy.db:ro <image>
```

The `legacy.db` file is gitignored — it contains personal data and must never be committed.
Generate it from the MySQL dump with:
```bash
uv run python scripts/import_legacy.py
```

## PDF Preview

Generate preview PDFs with 1, 10, 30, and 100 history entries for visual inspection:

```bash
uv run python scripts/generate_preview_pdf.py
# Writes preview_001_entries.pdf … preview_100_entries.pdf in scripts/previews/ (gitignored)
```

## Architecture Decisions

Significant architectural decisions and their rationale are recorded in [`docs/adr/`](./adr/).

- [ADR 0001](./adr/0001-enrich-query-response-schema.md) — Enrich query response schema and add `/api/merge`
- [ADR 0002](./adr/0002-agent-support-via-llmstxt.md) — Agent support via `/llms.txt`
- [ADR 0003](./adr/0003-rename-is-virtual-judge-to-is-aggregator.md) — Rename `isVirtualJudge` to `isAggregator`
- [ADR 0004](./adr/0004-history-pdf-backup.md) — History tracking via PDF backup/restore (no database)
- [ADR 0005](./adr/0005-localstorage-watch-config-only.md) — localStorage sync via $watch (config-only persistence)
- [ADR 0006](./adr/0006-legacy-lookup-abp-username-only.md) — legacy lookup restricted to ABP username only
- [ADR 0007](./adr/0007-label-cache-is-load-bearing.md) — label cache in `nit`/`uva` is load-bearing; those crawlers require the full package
