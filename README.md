# OJHunt Lite

A lightweight async Python tool for querying Online Judge (OJ) statistics across multiple platforms. Track your accepted problems (AC) and total submissions from competitive programming platforms.

## Features

- **Self-contained crawlers**: Each crawler can be used independently with minimal dependencies
- **Async/await support**: Built on aiohttp for efficient concurrent requests
- **Command-line interface**: Query multiple OJ platforms simultaneously
- **Lightweight**: Only depends on `aiohttp` and `beautifulsoup4` libraries
- **Easy to maintain**: Simple, readable code with consistent interfaces
- **BSD-2 Licensed**: Free to use and modify

## Quick Example

```bash
$ uv run ojhunt.py tourist@codeforces tourist@atcoder
Querying CodeForces...
Querying AtCoder...
AtCoder done (1051 solved, 1.25s)
CodeForces done (2962 solved, 2.78s)

Total: 2962 solved / 6437 submissions

================================================================================
Crawler              Username             Solved     Submissions  Status
================================================================================
CodeForces           tourist              2962       5386         OK (2.78s)
AtCoder              tourist              1051       1051         OK (1.25s)
================================================================================
Completed: 2 OK, 0 failed (2.78s total)
```

## Installation

### Using uv (recommended)
```bash
git clone https://github.com/Liu233w/ojhunt-lite
cd ojhunt-lite
uv sync
```

## Usage

### Command Line Interface

Run `ojhunt --help` to see all available options.

Quick examples:
```bash
# Query single crawler
uv run ojhunt.py tourist@codeforces

# Query multiple crawlers
uv run ojhunt.py tourist@codeforces tourist@atcoder

# Use default username for multiple queries
uv run ojhunt.py -d tourist -- codeforces atcoder

# Query all platforms
uv run ojhunt.py -d tourist -a

# List available crawlers with details
uv run ojhunt.py --list

# Query yourself on VJudge (login and query same user)
uv run ojhunt.py myuser:mypass@vjudge

# Query someone else on VJudge (login as you, query them)
uv run ojhunt.py -l myuser:mypass@vjudge -- target_user@vjudge
```

### Login-Required Crawlers

Some crawlers (like VJudge) require authentication to query any user's statistics. You can provide credentials in two ways:

**1. Embedded credentials (query yourself):**
```bash
# Login as yourself, query your own stats
uv run ojhunt.py myuser:mypass@vjudge
```

**2. Using `-l` flag (query anyone):**
```bash
# Login as yourself, query someone else
uv run ojhunt.py -l myuser:mypass@vjudge -- target_user@vjudge

# Multiple login-required crawlers
uv run ojhunt.py -l user1:pass1@vjudge -l user2:pass2@otheroj -- target1@vjudge target2@otheroj
```

**Parsing rules for `user:pass@crawler`:**
- First `:` separates username from password
- Last `@` separates credentials from crawler name
- Examples:
  - `user:pass@vjudge` → username=`user`, password=`pass`, crawler=`vjudge`
  - `user:p@ss:word@vjudge` → username=`user`, password=`p@ss:word`, crawler=`vjudge`

**Error cases:**
- Querying a login-required crawler without credentials → error
- Using both embedded password and `-l` flag for same crawler → error (duplicate credentials)
- Providing credentials for a crawler that doesn't need them → error

### Using Crawlers Directly in Your Code

Each crawler is self-contained and can be imported directly. All crawlers are async functions:

```python
import asyncio
from crawlers.codeforces import query

async def main():
    async with aiohttp.ClientSession() as session:
        result = await query(session, "tourist")
        print(f"Solved: {result['solved']}")
        print(f"Submissions: {result['submissions']}")
        print(f"Problems: {result['solved_list']}")

asyncio.run(main())
```

Using with aiohttp session for better performance:
```python
import asyncio
import aiohttp
from crawlers import codeforces, atcoder, hdu

async def main():
    async with aiohttp.ClientSession() as session:
        # Crawlers will reuse the session
        results = await asyncio.gather(
            codeforces.query(session, "tourist"),
            atcoder.query(session, "tourist"),
            hdu.query(session, "vjudge4"),
        )
        for result in results:
            print(result)

asyncio.run(main())
```

### Web Interface

Start the web server:

```bash
uv run python -m web.run
```

The web interface will be available at http://127.0.0.1:8080

For VJudge support, set environment variables:

```bash
VJUDGE_USERNAME=user VJUDGE_PASSWORD=pass uv run python -m web.run
```

## Supported Platforms

See [crawlers module](./crawlers)

### Archived Crawlers

Some crawlers have been archived due to site closures or technical issues. See [archived_crawlers](./archived_crawlers) for details.

## Return Format

All crawlers return a dictionary with the following structure:

```python
{
    "solved": int,           # Number of accepted problems
    "submissions": int,      # Total number of submissions
    "solved_list": list|None # List of problem IDs (may be None for some platforms)
}
```

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific crawler tests
pytest crawlers/codeforces_test.py

# Run with verbose output
pytest -v

# Exclude network-dependent tests (for CI environments)
pytest -m "not network"

# Run only network tests
pytest -m network
```

#### Testing Login-Required Crawlers

For crawlers that require authentication (e.g., VJudge), set environment variables before running tests:

```bash
# Set credentials for VJudge tests
export VJUDGE_USERNAME=your_username
export VJUDGE_PASSWORD=your_password

# Run VJudge tests
pytest crawlers/vjudge_test.py
```

Tests will be automatically skipped if the required environment variables are not set.

### Adding a New Crawler

1. Create `crawlers/your_crawler.py` with BSD-2 license header (year 2026)
2. Implement the `async def query(session: aiohttp.ClientSession, username: str, password: Optional[str] = None) -> dict` function
3. Add `__crawler_meta__` dictionary with platform metadata
4. Create `crawlers/your_crawler_test.py` with pytest-asyncio tests
5. The crawler will be automatically discovered by the CLI

**For API-based crawlers:**
```python
"""BSD-2 License header..."""
import aiohttp
from typing import Dict, List, Union, Optional

__crawler_meta__ = {
    'title': 'Your OJ',
    'description': 'Description here',
    'url': 'https://your-oj.com/',
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

**For login-required crawlers (e.g., VJudge):**
```python
__crawler_meta__ = {
    'title': 'Your OJ',
    'description': 'Description here',
    'url': 'https://your-oj.com/',
    'requires_login': True,  # Any valid account can query any user
}

async def query(
    session: aiohttp.ClientSession,
    username: str,
    password: Optional[str] = None,      # Embedded: user:pass@crawler
    login_user: Optional[str] = None,    # From -l flag
    login_password: Optional[str] = None,
) -> Dict[str, Union[int, List[str], None]]:
    # Determine which credentials to use
    if login_user and login_password:
        # Using -l flag: login as one user, query another
        actual_user, actual_pass = login_user, login_password
    elif password:
        # Using embedded password: login as target user
        actual_user, actual_pass = username, password
    else:
        raise ValueError('Login credentials required')
    # ... use actual_user and actual_pass for authentication
```

**For HTML-scraping crawlers:**
```python
"""BSD-2 License header..."""
import aiohttp
from selectolax.lexbor import LexborHTMLParser
from typing import Dict, List, Union, Optional

__crawler_meta__ = {
    'title': 'Your OJ',
    'description': 'Description here',
    'url': 'https://your-oj.com/',
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

    # Use PyQuery for maintainable HTML parsing
    solved = doc.css_first('span.solved-count').text().strip()
    submissions = doc.css_first('span.submission-count').text().strip()

    # Extract problem list
    problem_links = doc.css('.problem-list a.problem-id')
    solved_list = [link.text().strip() for link in problem_links]

    return {
        'solved': solved,
        'submissions': submissions,
        'solved_list': solved_list,
    }
```

## License

BSD 2-Clause License - See individual crawler files for full license text.

## Credits

This is a simplified Python rewrite of [acm-statistics](https://github.com/liu233w/acm-statistics).

Special thanks to test account providers: @leoloveacm, @2013300262
