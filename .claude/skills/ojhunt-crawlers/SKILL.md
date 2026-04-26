---
name: ojhunt-crawlers
description: Crawlers - file locations, metadata schema, login types, and conventions. Load whenever the task touches crawlers in any way — reading the code, planning a new one, debugging, implementing, or reviewing crawler metadata.
---

# Crawlers

For `__crawler_meta__` field reference and login type concepts, see **`docs/development.md`**.
For test assertion conventions, invoke the **ojhunt-testing** skill.
For ADR guidance on significant design decisions, invoke the **ojhunt-commit** skill.

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

If profiles require numeric IDs (no username in URL), see "Numeric User ID Handling" below.

### Step 3: Identify the Data Source

Inspect network traffic (browser devtools Network tab, or Playwright) while loading a
profile page.

**API-based (preferred):** Look for XHR/Fetch requests returning JSON:
```
/api/user/{username}
/api/user/info?username={username}
/rest/users/{username}
/graphql (POST with query)
```

Test the API directly without a browser to confirm it works with plain HTTP. You can use
`page.evaluate()` to make `fetch()` calls from within Playwright if needed:
```python
result = page.evaluate("""
async () => {
  const r = await fetch('/api/user/tourist');
  return {status: r.status, data: await r.json()};
}
""")
```

**HTML scraping (fallback):** If no JSON API exists, parse the HTML profile page with
selectolax (see "HTML Parsing" below).

**Note:** React/Vue SPAs load data via JS. Only the API calls in the Network tab will work —
you cannot parse the initial HTML for SPA sites.

### Step 4: Numeric User ID Handling

If the site uses numeric IDs instead of usernames:

1. **Try username→ID lookup API first.** Inspect network traffic when searching on the site:
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

Use the appropriate template from "Crawler Templates" below.

### Step 6: Verification Checklist

- [ ] `TMPDIR=/private/tmp/claude-503 uv run pytest tests/crawlers/<name>_test.py` — all 3 standard tests pass
- [ ] `uv run ruff check .` — no lint errors
- [ ] `__crawler_meta__` has all required fields: `title`, `url`, `test_username`
- [ ] BSD-2 license header present (only in `src/ojhunt/crawlers/` files, not tests)
- [ ] `solved_list` is `None` (not `[]`) when unavailable
- [ ] Error messages match exactly: `"Please enter username"`, `"The user does not exist"`
- [ ] If crawler was previously archived: remove its files from `archived_crawlers/` and remove its entry from `archived_crawlers/README.md`

### Debugging a Broken Crawler

Start with the existing test harness — don't probe with `curl` first:

```bash
uv run pytest tests/crawlers/<name>_test.py -v --log-cli-level=DEBUG -s
```

The crawler's own `logger.debug()` calls reveal which HTTP call failed and what the response
looked like. Drop to manual `curl` only if the failure is opaque.

**Sandbox networking:** the shared `session` fixture in `tests/crawlers/conftest.py` already
passes `trust_env=True` so aiohttp routes through the sandbox HTTP proxy. Don't redefine the
fixture per file — just take `session` as a test parameter.

**Login crawlers + captcha:** Sites like VJudge trigger captchas on repeated rapid logins
from the same IP. Override the conftest fixture in your test file with a module-scoped one
so the cookie is reused across tests:

```python
@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def session():
    async with aiohttp.ClientSession(trust_env=True) as s:
        yield s
```

Match it with `@pytest.mark.asyncio(loop_scope="module")` on every test in the file. See
`tests/crawlers/vjudge_test.py` for the canonical example.

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

- **WAF blocking aiohttp**: Cloudflare and Akamai block non-browser requests. If a site
  requires browser rendering, it's not feasible for this aiohttp-based project.
- **SPA data**: React/Vue SPAs load data via JS. Only the API calls in the Network tab will
  work — you cannot parse the initial HTML.
- **Wrong JSON keys**: Always verify API response structure with a real fetch (via Playwright
  or manual curl) before coding.
- **Solved count vs solved list mismatch**: Some sites have uncategorized problems not in
  their problem lists. Add a comment in the test if `len(solved_list) < solved`.

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

The `session` fixture is provided by `tests/crawlers/conftest.py` — don't redefine it.

```python
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
- Test example: `tests/crawlers/codeforces_test.py`

---

## HTML Parsing

Use `selectolax.lexbor.LexborHTMLParser`.

Prefer CSS selectors over regex when extracting values from HTML structure. Use the
`lexbor-contains` pseudo-class to find an element by text, then navigate to siblings/children:

```python
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

---

## License Header

BSD-2 Clause license header (copy from existing crawler, use current year for new files).
- **Only add license headers to files in `src/ojhunt/crawlers/`** — users can copy individual crawler files.
- **Do NOT add license headers** to CLI, web, or other internal code.

---

## Login-Required Crawlers

There are two distinct types. Always identify which type before implementing.

**How to identify the type:** Visit the site as a guest and try to access another user's
profile. If it's blocked (login wall on all profiles), it's Shared Account. If profiles are
public for others but not yourself, it's Own Account.

**Own Account (`own_account`) — Login to see your own data only:**
- The platform only exposes a user's own stats when logged in.
- The crawler must log in *as the target user*.
- `login_user` and `login_password` equal `username` and `password`.
- CLI usage: `user:pass@crawler` (the `-l` flag is redundant).

**Shared Account (`shared_account`) — Any account can query any user:**
- The platform requires login, but any authenticated user can see any user's stats.
- A single shared account can query arbitrary target users.
- `login_user`/`login_password` (from `-l` flag) may differ from `username`.
- CLI usage: `-l mylogin:mypass@crawler -- target_user@<crawler>`.
- Example implementations: `src/ojhunt/crawlers/vjudge.py`, `src/ojhunt/crawlers/cses.py`

**`CrawlerMeta` field mapping:**
- `"login_type": "shared_account"` → Shared Account
- `"login_type": "own_account"` → Own Account
- key omitted → no login required

### Registration for Testing

If you need an account to test login behavior:
1. Try email registration via Playwright
2. Check for CAPTCHA / reCAPTCHA
3. If CAPTCHA is solvable (simple image-based), solve it
4. If CAPTCHA is unsolvable (reCAPTCHA v2/v3, hCaptcha), note this and skip
5. Save credentials to `archived_crawlers/test_accounts.md`

---

## SSL

`ssl=False` is acceptable in crawler `session.get()` calls for sites with expired or
self-signed certs **when no login is involved** — public stats queries have nothing sensitive
in transit. Never bypass SSL for authenticated sessions.

---

## Archived Crawlers

Crawlers for dead sites or sites with unfixable issues are moved to `archived_crawlers/`.

- `archived_crawlers/` does NOT have an `__init__.py` — it's for archival only, not a package
- Tests in `archived_crawlers/` are NOT run by pytest
- Do not create stub crawlers that just raise exceptions — add them to `archived_crawlers/README.md`
- Do not list individual archived crawlers in documentation — point users to the folder
