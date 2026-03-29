# Development Guide

## Setup

```bash
uv sync
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific crawler tests
pytest crawlers/codeforces_test.py

# Exclude network-dependent tests (for CI)
pytest -m "not network"

# Run only network tests
pytest -m network

# Run playwright/e2e tests (requires running web server)
pytest -m playwright web/tests/
```

### Testing Login-Required Crawlers

Set environment variables before running tests:

```bash
export LOGIN_USERNAME__VJUDGE=your_username
export LOGIN_PASSWORD__VJUDGE=your_password
pytest crawlers/vjudge_test.py
```

Tests are automatically skipped if required environment variables are not set.

## Adding a New Crawler

1. Create `crawlers/your_crawler.py` with a BSD-2 license header
2. Implement `async def query(...)` and add `__crawler_meta__`
3. Create `crawlers/your_crawler_test.py`
4. The crawler is auto-discovered — no other files need editing

### API-based crawler template

```python
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

```python
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

```python
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

See [`crawlers/vjudge.py`](../crawlers/vjudge.py) and [`crawlers/cses.py`](../crawlers/cses.py) for complete reference implementations.

## Return Format

All crawlers return:

```python
{
    "solved": int,            # Number of accepted problems
    "submissions": int,       # Total submissions (0 if unavailable)
    "solved_list": list|None  # Problem IDs (None if unavailable)
}
```

## PDF Preview

Generate preview PDFs with 1, 10, 30, and 100 history entries for visual inspection:

```bash
uv run python scripts/generate_preview_pdf.py
# Writes preview_001_entries.pdf … preview_100_entries.pdf in scripts/previews/ (gitignored)
```

All history entries are dated from 2020, so you can upload a preview PDF to the web UI
and test the "merge with existing history" feature against today's date.

## Linting

```bash
uv run ruff check .
```

Run after every edit.

## Architecture Decisions

Significant architectural decisions and their rationale are recorded in [`docs/adr/`](./adr/).
See those files to understand *why* things are shaped the way they are before proposing changes.

- [ADR 0001](./adr/0001-enrich-query-response-schema.md) — Enrich query response schema and add `/api/merge`
- [ADR 0002](./adr/0002-agent-support-via-llmstxt.md) — Agent support via `/llms.txt`
- [ADR 0003](./adr/0003-rename-is-virtual-judge-to-is-aggregator.md) — Rename `isVirtualJudge` to `isAggregator`
- [ADR 0004](./adr/0004-history-pdf-backup.md) — History tracking via PDF backup/restore (no database)
