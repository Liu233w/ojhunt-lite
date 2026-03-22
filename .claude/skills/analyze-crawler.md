---
description: >
  Guide for analyzing an online judge website and implementing a new crawler for it.
  Use this when you need to check if a site is crawlable, find its API, handle authentication,
  or implement a new crawler from scratch.
---

# Analyze and Implement OJ Crawler

## Overview

This skill walks you through the process of:
1. Checking if an OJ site is alive and accessible
2. Finding the data source (API vs HTML scraping)
3. Identifying authentication requirements
4. Handling special cases (numeric IDs, bot protection)
5. Implementing and testing the crawler

---

## Step 1: Accessibility Check

First, verify the site is alive:

```python
# Quick check with WebFetch or playwright-cli
# Check for: HTTP status, SSL errors, timeout, redirect destination
```

**Common dead-site signals:**
- Connection refused / ECONNREFUSED
- SSL certificate expired
- DNS not resolving
- Redirects to parking/error page

**Bot protection signals:**
- Cloudflare `cf-mitigated: challenge` header (403/200 with JS challenge)
- Cerberus JS PoW challenge (`data-app="Hydro"` or similar)
- Akamai WAF 403 response

If the site is dead → update `archived_crawlers/README.md` with accurate reason and stop.

---

## Step 2: Find the User Profile URL

Visit the site and find a known user's profile page. Try common patterns:

```
/user/{username}
/users/{username}
/profile/{username}
/u/{username}
/{username}
/user/{numeric_id}
```

If profiles require numeric IDs (no username in URL), check Step 4.

---

## Step 3: Identify the Data Source

Open browser devtools (Network tab) or use Playwright to inspect network traffic while loading a profile page.

### API-based (preferred)
Look for XHR/Fetch requests returning JSON. Common patterns:
```
/api/user/{username}
/api/user/info?username={username}
/rest/users/{username}
/graphql (POST with query)
```

Test the API directly without a browser to see if it works with plain HTTP:
```python
# In playwright-cli, use page.evaluate() to make fetch() calls:
result = page.evaluate("""
async () => {
  const r = await fetch('/api/user/tourist');
  return {status: r.status, data: await r.json()};
}
""")
```

### HTML scraping (fallback)
If no JSON API exists, parse the HTML profile page with selectolax.

---

## Step 4: Numeric User ID Handling

If the site uses numeric IDs instead of usernames:

1. **Try username→ID lookup API first.** Inspect network traffic when searching on the site. Look for endpoints like:
   ```
   /api/user/search?keyword={username}
   /api/search?q={username}&type=user
   ```

2. **If found:** Implement like luogu.py — try URL with input directly, fall back to search API.

3. **If not found (or requires auth):** Implement with ID only. Set description accordingly:
   ```python
   "description": "Please use your numeric user ID (visible in profile URL)"
   ```
   See: `crawlers/nod.py` (51Nod), `crawlers/luogu.py` (Luogu)

---

## Step 5: Authentication Requirements

### Check if login is required

Visit the profile page as a guest (in Playwright without cookies). Look for:
- Login prompt / redirect to login page
- "Please login to see statistics" message
- Profile loads but shows no data

### Determine the login TYPE

**Type A — Login to see your own data only:**
- Guest access: Other users' profiles are visible; only your own profile is hidden
- OR: All profiles are hidden, but each user can only see their own
- Implementation: The crawler logs in as the target user
- CLI: `user:pass@crawler`

**Type B — Any account can query anyone:**
- Guest access: All user profiles are hidden regardless of whose they are
- Once logged in: You can view any user's profile
- Implementation: One account is enough to query any user
- CLI: `-l mylogin:mypass@crawler -- target@crawler`
- Reference: `crawlers/vjudge.py`

### Registration

If you need an account to test login behavior:
1. Try email registration via Playwright
2. Check for CAPTCHA / reCAPTCHA
3. If CAPTCHA is solvable (image-based simple ones), solve it
4. If CAPTCHA is unsolvable (reCAPTCHA v2/v3, hCaptcha), note this and skip
5. Save credentials to `archived_crawlers/test_accounts.md`

---

## Step 6: Implementation

### Crawler template (API-based)
```python
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

### Test template
```python
import pytest, pytest_asyncio, aiohttp
from crawlers.example import query, __crawler_meta__

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

---

## Step 7: Verification Checklist

- [ ] `uv run pytest crawlers/<name>_test.py` — all 3 standard tests pass
- [ ] `uv run ruff check .` — no lint errors
- [ ] `__crawler_meta__` has all required fields: `title`, `url`, `test_username`
- [ ] BSD-2 license header present (only in `crawlers/` files, not tests)
- [ ] `solved_list` is `None` (not `[]`) when unavailable
- [ ] Error messages match: "Please enter username", "The user does not exist"
- [ ] If crawler was previously archived: remove its files from `archived_crawlers/` and remove its entry from `archived_crawlers/README.md`

---

## Common Pitfalls

- **WAF blocking aiohttp**: Cloudflare and Akamai block non-browser requests. If a site requires browser rendering, it's not feasible for this aiohttp-based project.
- **SPA data**: React/Vue SPAs load data via JS. Only the API calls in the Network tab will work — you cannot parse the initial HTML.
- **Wrong JSON keys**: Always verify API response structure with a real fetch (via Playwright or manual curl) before coding.
- **Solved count vs solved list mismatch**: Some sites have uncategorized problems not in their problem lists. Add a comment in the test if `len(solved_list) < solved`.

---

## Decision Tree

```
Site accessible?
  No → Update archived README, stop
  Yes →
    User profiles public?
      Yes → Find JSON API or HTML → implement crawler
      No →
        Login type A or B?
          A → implement with user:pass login
          B → implement with shared account login (like vjudge.py)
        WAF blocking aiohttp?
          Yes → archive with "WAF blocks automated requests"
          No → implement
```
