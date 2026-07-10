---
name: ojhunt-crawlers
description: Workflow for implementing or debugging an OJ crawler — accessibility check, data-source discovery, decision tree, and verification checklist. Load whenever the task is to add a new crawler or fix a broken one. For the crawler reference (metadata schema, login types, templates, HTML parsing, SSL, archived rules) read docs/dev/crawlers.md.
---

# Implementing a crawler

This skill is the **procedure**. The reference material it points to —
`__crawler_meta__` fields, login types, code templates, HTML parsing, SSL, license header,
archived-crawler rules — lives in **`docs/dev/crawlers.md`**. Read that alongside these steps.

For general pytest conventions see **`docs/dev/testing.md`**. For ADR guidance on significant
design decisions, invoke the **ojhunt-commit** skill.

## Implementing a New Crawler

### Step 1: Accessibility Check

**Read `archived_crawlers/README.md` first.** It lists every platform already known to be
dead, WAF-blocked, or unfixable. If the site is already there, stop — don't re-investigate.

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

**SSL caveat:** Tools like WebFetch validate certificates and will report an SSL error as if
the site is unreachable. Before concluding a site is dead due to an expired cert, verify
with `curl -skI https://example.com/user/1` (`-k` bypasses cert validation). If the server
responds, the crawler may still work with `ssl=False` — but also check that the response
body contains actual data and not a server-side error page (see "Parsing failures" below).

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
```python notest
result = page.evaluate("""
async () => {
  const r = await fetch('/api/user/tourist');
  return {status: r.status, data: await r.json()};
}
""")
```

**HTML scraping (fallback):** If no JSON API exists, parse the HTML profile page with
selectolax (see "HTML parsing" in `docs/dev/crawlers.md`).

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
   ```python notest
   "description": "Please use your numeric user ID (visible in profile URL)"
   ```
   See: `src/ojhunt/crawlers/nod.py` (51Nod), `src/ojhunt/crawlers/luogu.py` (Luogu)

### Step 5: Crawler Implementation

Use the appropriate template from **`docs/dev/crawlers.md`** (API-based, HTML-scraping, or
shared-account login). It also documents the `__crawler_meta__` fields, return format, login
types, HTML parsing, SSL policy, and license-header rules.

### Step 6: Verification Checklist

- [ ] `uv run pytest tests/crawlers/<name>_test.py` — all 3 standard tests pass
- [ ] `uv run ruff check .` — no lint errors
- [ ] `__crawler_meta__` has all required fields: `title`, `url`, `test_username`
- [ ] BSD-2 license header present (only in `src/ojhunt/crawlers/` files, not tests)
- [ ] `solved_list` is `None` (not `[]`) when unavailable
- [ ] Error messages match exactly: `"Please enter username"`, `"The user does not exist"`
- [ ] If crawler was previously archived: remove its files from `archived_crawlers/` and remove its entry from `archived_crawlers/README.md`

## Debugging a Broken Crawler

Start with the existing test harness — don't probe with `curl` first:

```bash
uv run pytest tests/crawlers/<name>_test.py -v --log-cli-level=DEBUG -s
```

The crawler's own `logger.debug()` calls reveal which HTTP call failed and what the response
looked like. Drop to manual `curl` only if the failure is opaque.

**Parsing failures after a successful connection:** If the crawler raises
`RuntimeError("Error while parsing")`, the site may be returning a server error page rather
than a changed HTML structure. Check the raw response before updating selectors:
`curl -sk --user-agent "Mozilla/5.0" https://example.com/user/2 | head -c 500`. A ~700-byte
response with a PHP stack trace is a server-side issue — no selector change will fix it.
Spawn a background sonnet agent to probe alternate endpoints rather than probing inline
(avoids flooding the main context with large HTML responses).

**Sandbox networking:** the shared `session` fixture in `tests/crawlers/conftest.py` already
passes `trust_env=True` so aiohttp routes through the sandbox HTTP proxy. Don't redefine the
fixture per file — just take `session` as a test parameter.

**Login crawlers + captcha:** Sites like VJudge trigger captchas on repeated rapid logins
from the same IP. Override the conftest fixture in your test file with a module-scoped one
so the cookie is reused across tests:

```python notest
@pytest_asyncio.fixture(scope="module", loop_scope="module")
async def session():
    async with aiohttp.ClientSession(trust_env=True) as s:
        yield s
```

Match it with `@pytest.mark.asyncio(loop_scope="module")` on every test in the file. See
`tests/crawlers/vjudge_test.py` for the canonical example.

## Decision Tree

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
            Login type? (see login types in docs/dev/crawlers.md)
              Own Account → implement with user:pass login
              Shared Account → implement with shared account login (like vjudge.py)
```

## Common Pitfalls

- **WAF blocking aiohttp**: Cloudflare and Akamai block non-browser requests. If a site
  requires browser rendering, it's not feasible for this aiohttp-based project.
- **SPA data**: React/Vue SPAs load data via JS. Only the API calls in the Network tab will
  work — you cannot parse the initial HTML.
- **Wrong JSON keys**: Always verify API response structure with a real fetch (via Playwright
  or manual curl) before coding.
- **Solved count vs solved list mismatch**: Some sites have uncategorized problems not in
  their problem lists. Add a comment in the test if `len(solved_list) < solved`.

## Standard test cases

Every crawler test file must have all three (see the test template in `docs/dev/crawlers.md`):

```python notest
async def test_user_not_exist(session): ...   # raises ValueError "The user does not exist"
async def test_username_with_space(session): ...  # raises ValueError
async def test_valid_user(session): ...  # asserts solved/submissions/solved_list
```

Import `TEST_USERNAME` from `__crawler_meta__["test_username"]` — don't hardcode. The `session`
fixture comes from `tests/crawlers/conftest.py`. In `test_valid_user` assert all three fields;
when a field is unavailable use `None` for `solved_list` / `0` for `submissions` and add a
comment. For login crawlers needing module-scoped cookie reuse, see "Login crawlers + captcha"
above.

**Login-required crawler testing (CLI):** for `shared_account` crawlers, tests read credentials
from `.env` automatically — create `.env` first if it doesn't exist:

```bash
uv run ojhunt -l username:password@<crawler> -- target_user@<crawler>
```

Discover which crawlers require login:
```bash
uv run ojhunt --list --json | jq 'with_entries(select(.value.login_type | contains("account")))'
```
