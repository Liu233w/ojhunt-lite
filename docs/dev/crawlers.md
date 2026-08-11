# Crawlers — reference

Reference material for crawler contributors: metadata schema, login types, return format,
code templates, and conventions. For the **step-by-step procedure** of adding or debugging a
crawler (accessibility check, decision tree, verification checklist), invoke the
**ojhunt-crawlers** skill.

## `__crawler_meta__` fields

| Field | Required | Description |
|-------|----------|-------------|
| `title` | Yes | Display name |
| `url` | Yes | Homepage URL |
| `test_username` | Yes | Used for tests and `/crawlers` availability checks |
| `description` | No | Shown in web UI (default: `""`) |
| `cli_description` | No | Shown in `--list` CLI output instead of `description`. Use when CLI usage differs significantly (e.g., login instructions, ID vs. username). |
| `login_type` | No | `"shared_account"` or `"own_account"`; omit if no login required |
| `is_aggregator` | No | Whether this crawler aggregates problems from other platforms (e.g. VJudge, NIT). Aggregators mirror problems from source OJs and submit on behalf of users using their own shared accounts — not the user's personal accounts. Aggregator `solved_list` entries must be pre-prefixed with the source platform name (e.g. `codeforces-1A`), so `/api/merge` uses them as-is and skips re-prefixing. See [ADR 0008](../adr/0008-unique-solved-dedup-design.md) for the deduplication rationale. |

## Login types

There are two distinct types. Always identify which type before implementing.

**How to identify the type:** Visit the site as a guest and try to access another user's
profile. If it's blocked (login wall on all profiles), it's Shared Account. If profiles are
public for others but not yourself, it's Own Account.

**Own Account (`own_account`)** — the platform only shows a user's own stats when logged in.
The crawler logs in *as the target user*: `login_user`/`login_password` equal `username`/`password`.
CLI: `user:pass@crawler` (the `-l` flag is redundant).

**Shared Account (`shared_account`)** — any authenticated user can view any user's stats.
A single shared account queries arbitrary targets; `login_user`/`login_password` (from `-l`) may
differ from `username`. CLI: `-l mylogin:mypass@crawler -- target@crawler`.
Example implementations: `src/ojhunt/crawlers/vjudge.py`, `src/ojhunt/crawlers/cses.py`.

`login_type` field mapping: `"shared_account"` → Shared Account; `"own_account"` → Own Account;
key omitted → no login required.

## Return format

All crawlers return:

```python notest
{
    "solved": int,  # Number of accepted problems
    "submissions": int,  # Total submissions, never below "solved"
    "solved_list": list | None,  # Problem IDs (None if unavailable)
}
```

A judge that publishes no submission total: report `solved` there, not `0` — every accepted
problem cost at least one submission, and `/api/merge` and `ojhunt --json` sum the field, so a
zero makes the total smaller than the solved count inside it. Where the number is scraped and a
page can lose it, clamp with `max(submissions, solved)`. See
[ADR 0015](../adr/0015-submissions-floor-is-solved.md); the crawler's own network test asserts it.

Judge-specific quirks — what a count actually measures, what to type as a username — belong in
the crawler file and its `description`. `core/models.py` describes the shape of a result, never
any judge's behaviour.

## Crawler templates

`query` needs a docstring: `help()` on the crawler joins it to the text generated from
`__crawler_meta__` ([ADR 0014](../adr/0014-generated-crawler-help.md)), and a unit test fails
without it. The module docstring is not available for this — it holds the license header.

### API-based crawler

```python notest
# BSD 2-Clause License
# Copyright (c) <year>, <author>
# (copy the full header from an existing crawler)

import aiohttp

__crawler_meta__ = {
    "title": "OJ Name",
    "description": "Enter your username",
    "url": "https://example.com/",
    "test_username": "known_active_user",
}


async def query(
    session: aiohttp.ClientSession, username: str, password: str | None = None
) -> dict[str, int | list[str] | None]:
    """Query OJ Name for user statistics.

    Args:
        session: aiohttp ClientSession
        username: The user's handle on OJ Name

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or the user does not exist
        RuntimeError: If the request fails or the response cannot be parsed
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")
    username = username.strip()

    try:
        async with session.get(
            f"https://example.com/api/user/{username}",
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 404:
                raise ValueError("The user does not exist")
            response.raise_for_status()
            data = await response.json()
    except aiohttp.ClientError as e:
        raise RuntimeError(f"Request failed: {str(e)}")

    return {
        "solved": data["solved_count"],
        "submissions": data["submission_count"],
        "solved_list": [str(p) for p in data.get("solved_problems", [])] or None,
    }
```

### HTML-scraping crawler

```python notest
# BSD 2-Clause License header (copy from an existing crawler)

import aiohttp
from selectolax.lexbor import LexborHTMLParser

__crawler_meta__ = {
    "title": "Your OJ",
    "description": "Description here",
    "url": "https://your-oj.com/",
    "test_username": "known_active_user",
}


async def query(
    session: aiohttp.ClientSession, username: str, password: str | None = None
) -> dict[str, int | list[str] | None]:
    """Query Your OJ for user statistics.

    Args:
        session: aiohttp ClientSession
        username: The user's handle on Your OJ

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If username is empty or the user does not exist
        RuntimeError: If a page cannot be fetched or parsed
    """
    if not username or not username.strip():
        raise ValueError("Please enter username")
    username = username.strip()

    async with session.get(
        f"https://your-oj.com/user/{username}",
        timeout=aiohttp.ClientTimeout(total=30),
    ) as response:
        if response.status == 404:
            raise ValueError("The user does not exist")
        html = await response.text()

    doc = LexborHTMLParser(html)
    solved = int(doc.css_first("span.solved-count").text(strip=True))
    submissions = int(doc.css_first("span.submission-count").text(strip=True))
    solved_list = [a.text(strip=True) for a in doc.css(".problem-list a.problem-id")]

    return {
        "solved": solved,
        "submissions": submissions,
        "solved_list": solved_list or None,
    }
```

### Login-required crawler (shared account)

```python notest
__crawler_meta__ = {
    "title": "Your OJ",
    "url": "https://your-oj.com/",
    "login_type": "shared_account",
    "test_username": "known_active_user",
}


async def query(
    session: aiohttp.ClientSession,
    username: str,
    password: str | None = None,
    login_user: str | None = None,
    login_password: str | None = None,
) -> dict[str, int | list[str] | None]:
    """Query Your OJ for user statistics.

    Your OJ hides profiles from guests, so a login is always required. Any account
    can look up any user: pass shared credentials as login_user / login_password.

    Args:
        session: aiohttp ClientSession
        username: The user being queried
        password: Password for `username`, to query your own account
        login_user: Account to authenticate as; takes precedence over password
        login_password: Password for login_user

    Returns:
        Dictionary with keys: solved, submissions, solved_list

    Raises:
        ValueError: If credentials are missing or the user does not exist
        RuntimeError: If the login or a request fails
    """
    if login_user and login_password:
        actual_user, actual_pass = login_user, login_password
    elif password:
        actual_user, actual_pass = username, password
    else:
        raise ValueError("Login credentials required")
    # ... use actual_user and actual_pass for authentication
```

### Test template

The `session` fixture is provided by `tests/crawlers/conftest.py` — don't redefine it.

```python notest
import pytest
from ojhunt.crawlers.example import query, __crawler_meta__

TEST_USERNAME = __crawler_meta__["test_username"]
NOT_EXIST_USERNAME = "fmv84zcq3hwu_notexist"


@pytest.mark.asyncio
async def test_user_not_exist(session):
    with pytest.raises(ValueError, match="The user does not exist"):
        await query(session, NOT_EXIST_USERNAME)


@pytest.mark.asyncio
async def test_username_with_space(session):
    with pytest.raises(ValueError):
        await query(session, "   ")


@pytest.mark.asyncio
async def test_valid_user(session):
    result = await query(session, TEST_USERNAME)
    assert result["solved"] > 0
    assert result["submissions"] >= result["solved"]
    assert len(result["solved_list"]) == result["solved"]
    # If solved_list unavailable: assert result["solved_list"] is None
```

**Key references:**
- API-based crawler: `src/ojhunt/crawlers/codeforces.py`
- HTML-scraping crawler: `src/ojhunt/crawlers/hdu.py`
- Shared-account login: `src/ojhunt/crawlers/vjudge.py`, `src/ojhunt/crawlers/cses.py`
- Test example: `tests/crawlers/codeforces_test.py`

## HTML parsing

Use `selectolax.lexbor.LexborHTMLParser`.

Prefer CSS selectors over regex when extracting values from HTML structure. Use the
`lexbor-contains` pseudo-class to find an element by text, then navigate to siblings/children:

```python notest
# Find a <td> containing "Submission count", then get the next sibling <td>
# Note: do NOT include a trailing colon — lexbor parses it as CSS pseudo-class syntax
count = doc.css_first('td:lexbor-contains("Submission count") + td').text(strip=True)

# Check presence of text in a container
if doc.css_first('.content:lexbor-contains("Please login")'):
    ...
```

Reserve `re` for strings that are not structured HTML — e.g. extracting a numeric ID from a
URL (`/user/(\d+)`), or parsing a value embedded mid-sentence in a text node
(`"Solved tasks: 150/400"`).

## License header

BSD-2 Clause license header (copy from an existing crawler, use the current year for new files).
- **Only add license headers to files in `src/ojhunt/crawlers/`** — users can copy individual crawler files.
- **Do NOT add license headers** to CLI, web, or other internal code.

## SSL

`ssl=False` is acceptable in crawler `session.get()` calls for sites with expired or
self-signed certs **when no login is involved** — public stats queries have nothing sensitive
in transit. Never bypass SSL for authenticated sessions.

## Outbound request identification

The web app and CLI build their `aiohttp` session via `create_session()` in
`src/ojhunt/core/session.py`, which seeds every request with an OJHunt `User-Agent` and an
always-on `X-OJHunt` header linking to `ojhunt.com` (so queried OJs can identify us and reach
out). See [ADR 0012](../adr/0012-identify-outbound-requests.md).

Implications for crawler code:

- **Don't add identity headers in a crawler file.** They come from the session. Crawler files
  stay copy-pasteable and carry no OJHunt branding.
- **You may override `User-Agent` per request** to dodge bot-blocking (see `poj.py`,
  `vjudge.py`). That only replaces the UA — the `X-OJHunt` header still rides along, so we
  stay identifiable. This is the one sanctioned reason to set headers inside a crawler.
- **Tests run through the same headers.** `tests/crawlers/conftest.py` builds the `session`
  fixture with `create_session(trust_env=True)`, so a crawler test failing only because the
  OJHunt UA is blocked means that crawler needs a per-request browser UA.

## Registration for testing

If you need an account to test login behavior:
1. Try email registration via Playwright
2. Check for CAPTCHA / reCAPTCHA
3. If CAPTCHA is solvable (simple image-based), solve it
4. If CAPTCHA is unsolvable (reCAPTCHA v2/v3, hCaptcha), note this and skip
5. Save credentials to `archived_crawlers/test_accounts.md`

## Archived crawlers

Crawlers for dead sites or sites with unfixable issues are moved to `archived_crawlers/`.

- `archived_crawlers/` does NOT have an `__init__.py` — it's for archival only, not a package
- Tests in `archived_crawlers/` are NOT run by pytest
- Do not create stub crawlers that just raise exceptions — add them to `archived_crawlers/README.md`
- Do not list individual archived crawlers in documentation — point users to the folder
