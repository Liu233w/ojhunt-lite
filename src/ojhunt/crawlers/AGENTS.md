# AGENTS.md - Crawlers

## Implementing a New Crawler

### Step 1: Accessibility Check

Verify the site is alive before doing anything else:

**Common dead-site signals:**
- Connection refused / ECONNREFUSED
- SSL certificate expired
- DNS not resolving
- Redirects to parking/error page

**Bot protection signals:**
- Cloudflare `cf-mitigated: challenge` header (403/200 with JS challenge)
- Cerberus JS PoW challenge (`data-app="Hydro"` or similar)
- Akamai WAF 403 response

If the site is dead → update `archived_crawlers/README.md` with the accurate reason and stop.

### Step 2: Find the User Profile URL

Try common patterns to find a known user's profile page:

```
/user/{username}
/users/{username}
/profile/{username}
/u/{username}
/{username}
/user/{numeric_id}
```

If profiles require numeric IDs (no username in URL), see the "Numeric User ID Handling" section below.

### Step 3: Identify the Data Source

Inspect network traffic (browser devtools Network tab, or Playwright) while loading a profile page.

**API-based (preferred):** Look for XHR/Fetch requests returning JSON:
```
/api/user/{username}
/api/user/info?username={username}
/rest/users/{username}
/graphql (POST with query)
```

Test the API directly without a browser to confirm it works with plain HTTP. You can use `page.evaluate()` to make `fetch()` calls from within Playwright if needed:
```python
result = page.evaluate("""
async () => {
  const r = await fetch('/api/user/tourist');
  return {status: r.status, data: await r.json()};
}
""")
```

**HTML scraping (fallback):** If no JSON API exists, parse the HTML profile page with selectolax (see "HTML Parsing" section below).

**Note:** React/Vue SPAs load data via JS. Only the API calls in the Network tab will work — you cannot parse the initial HTML for SPA sites.

### Step 4: Numeric User ID Handling

If the site uses numeric IDs instead of usernames:

1. **Try username→ID lookup API first.** Inspect network traffic when searching on the site. Look for endpoints like:
   ```
   /api/user/search?keyword={username}
   /api/search?q={username}&type=user
   ```

2. **If found:** Implement like `luogu.py` — try URL with input directly, fall back to search API.

3. **If not found (or requires auth):** Implement with ID only. Set description accordingly:
   ```python
   "description": "Please use your numeric user ID (visible in profile URL)"
   ```
   See: `src/ojhunt/crawlers/nod.py` (51Nod), `src/ojhunt/crawlers/luogu.py` (Luogu)

### Step 5: Crawler Implementation

Use the appropriate template from the "Crawler Templates" section below.

### Step 6: Verification Checklist

- [ ] `TMPDIR=/private/tmp/claude-503 uv run pytest tests/crawlers/<name>_test.py` — all 3 standard tests pass
- [ ] `uv run ruff check .` — no lint errors
- [ ] `__crawler_meta__` has all required fields: `title`, `url`, `test_username`
- [ ] BSD-2 license header present (only in `src/ojhunt/crawlers/` files, not tests)
- [ ] `solved_list` is `None` (not `[]`) when unavailable
- [ ] Error messages match exactly: `"Please enter username"`, `"The user does not exist"`
- [ ] If crawler was previously archived: remove its files from `archived_crawlers/` and remove its entry from `archived_crawlers/README.md`

### Decision Tree

```
Site accessible?
  No → Update archived README, stop
  Yes →
    WAF blocking aiohttp? (Cloudflare, Akamai)
      Yes → archive with "WAF blocks automated requests"
      No →
        User profiles public?
          Yes → Find JSON API or HTML → implement crawler
          No →
            Login type?
              Own Account → implement with user:pass login
              Shared Account → implement with shared account login (like vjudge.py)
```

### Common Pitfalls

- **WAF blocking aiohttp**: Cloudflare and Akamai block non-browser requests. If a site requires browser rendering, it's not feasible for this aiohttp-based project.
- **SPA data**: React/Vue SPAs load data via JS. Only the API calls in the Network tab will work — you cannot parse the initial HTML.
- **Wrong JSON keys**: Always verify API response structure with a real fetch (via Playwright or manual curl) before coding.
- **Solved count vs solved list mismatch**: Some sites have uncategorized problems not in their problem lists. Add a comment in the test if `len(solved_list) < solved`.

---

## Crawler Templates

### API-based Crawler

```python
# BSD 2-Clause License
# Copyright (c) <year>, <author>
# (copy full header from an existing crawler)

import aiohttp
from typing import Dict, List, Union

__crawler_meta__ = {
    "title": "OJ Name",
    "description": "Enter your username",
    "url": "https://example.com/",
    "test_username": "known_active_user",
}

async def query(session, username):
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

### Test Template

```python
import pytest, pytest_asyncio, aiohttp
from ojhunt.crawlers.example import query, __crawler_meta__

TEST_USERNAME = __crawler_meta__["test_username"]
NOT_EXIST_USERNAME = "fmv84zcq3hwu_notexist"

@pytest_asyncio.fixture
async def session():
    async with aiohttp.ClientSession() as s:
        yield s

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
- Test example: `tests/crawlers/codeforces_test.py`

---

## HTML Parsing

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

---

## License Header

BSD-2 Clause license header (copy from existing crawler, use current year for new files).
- **Only add license headers to files in `src/ojhunt/crawlers/` folder** - users can copy individual crawler files.
- **Do NOT add license headers** to CLI, web, or other internal code.

---

## Login-Required Crawlers

There are two distinct types of login-required crawlers. Always identify which type before implementing.

**How to identify the type:** Visit the site as a guest and try to access another user's profile. If it's blocked (login wall on all profiles), it's Shared Account. If profiles are public for others but not for yourself, it's Own Account.

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

**Reference implementations:**
- Shared Account: `src/ojhunt/crawlers/vjudge.py`, `src/ojhunt/crawlers/cses.py`

**`CrawlerMeta` field mapping:**
- `"login_type": "shared_account"` → Shared Account (supports `-l` flag; any account can query any user)
- `"login_type": "own_account"` → Own Account (must log in as the target user)
- key omitted → no login required

### Registration for Testing

If you need an account to test login behavior:
1. Try email registration via Playwright
2. Check for CAPTCHA / reCAPTCHA
3. If CAPTCHA is solvable (image-based simple ones), solve it
4. If CAPTCHA is unsolvable (reCAPTCHA v2/v3, hCaptcha), note this and skip
5. Save credentials to `archived_crawlers/test_accounts.md`

---

## SSL

`ssl=False` is acceptable in crawler `session.get()` calls for sites with expired or self-signed certs **when no login is involved** — public stats queries have nothing sensitive in transit. Never bypass SSL for authenticated sessions (login crawlers, cookie-based auth).

---

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

---

## Archived Crawlers

Crawlers for dead sites or sites with unfixable issues are moved to `archived_crawlers/`. Do not list individual archived crawlers in documentation - point users to the folder instead.

**Important:**
- `archived_crawlers/` does NOT have an `__init__.py` - it's for archival only, not a package
- Tests in `archived_crawlers/` are NOT run by pytest
- Do not create stub crawlers that just raise exceptions - add them to `archived_crawlers/README.md` instead
