# AGENTS.md - Crawlers

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

## License Header

BSD-2 Clause license header (copy from existing crawler, use current year for new files).
- **Only add license headers to files in `src/ojhunt/crawlers/` folder** - users can copy individual crawler files.
- **Do NOT add license headers** to CLI, web, or other internal code.

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

## SSL

`ssl=False` is acceptable in crawler `session.get()` calls for sites with expired or self-signed certs **when no login is involved** — public stats queries have nothing sensitive in transit. Never bypass SSL for authenticated sessions (login crawlers, cookie-based auth).

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

## Archived Crawlers

Crawlers for dead sites or sites with unfixable issues are moved to `archived_crawlers/`. Do not list individual archived crawlers in documentation - point users to the folder instead.

**Important:**
- `archived_crawlers/` does NOT have an `__init__.py` - it's for archival only, not a package
- Tests in `archived_crawlers/` are NOT run by pytest
- Do not create stub crawlers that just raise exceptions - add them to `archived_crawlers/README.md` instead
