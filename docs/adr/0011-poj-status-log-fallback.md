# ADR 0011 — POJ Falls Back to the `/status` Log When `/userstatus` Is Blocked

**Status:** Accepted

## Context

The POJ crawler read a user's totals from the per-user summary page
`http://poj.org/userstatus?user_id=<name>` — one request returning solved count,
submission count, and the full solved list (from an inline `p(id)` script).

POJ has since disabled that route at the **nginx layer**: `/userstatus` (and
`/userstatusrank`) return a bare `nginx/1.18.0` 403 for our requests, regardless of
User-Agent, headers, or cookies, while the rest of the site (`/`, `/problem`, `/status`)
serves normally. The homepage also dropped its `userstatus` link, though `/status` rows
still link usernames to the now-dead page. The block is **not** a login gate (a POJ login
requirement would come from the Java app, not nginx), and we could not determine whether it
is geo-based or a global route disable — POJ is known to restrict some access by region, and
a self-hoster on a network POJ still serves may get `/userstatus` normally.

The only public per-user data source that still works is the submission log
`http://poj.org/status?user_id=<name>`. It is paginated (cursor-based via `top=`/`bottom=`,
`size=` clamped at 500 rows/page), supports a `result=0` Accepted filter, and — critically —
exposes **no per-user total** anywhere on the page.

## Options Considered

### Option A: Switch entirely to the `/status` log (drop `/userstatus`)

Always walk the `/status` log; delete the summary-page code.

**Rejected because:** it throws away the fast single-request path for anyone POJ still serves
`/userstatus` to (plausibly self-hosters inside the allowed region). It would force every
query — even where the clean summary works — into a multi-page walk, and permanently lose the
cheap totals the summary page provides.

### Option B: Leave the crawler on `/userstatus` only

Keep the existing code; accept that POJ shows offline.

**Rejected because:** the crawler is broken for out-of-network users (the live site reports
POJ offline). Doing nothing abandons those users when a working public alternative exists.

### Option C: Dual-path — `/userstatus` primary, `/status` fallback on 403 (chosen)

Try `/userstatus` first. On HTTP 403, fall back to walking the public `/status` log:
paginate newest-first (`size=500`, `top=<smallest RunID on page>` cursor) counting all rows
for `submissions` and collecting distinct Accepted `problem?id` values for `solved` /
`solved_list`.

## Decision

**Option C.** The `/userstatus` primary path is **load-bearing, not dead code** — it is the
fast path for deployments POJ still serves it to, and the 403 fallback is the only reason the
crawler works elsewhere. Do not delete the `/userstatus` request just because it 403s from a
given vantage point; that would regress those deployments back to a full log walk (Option A).

Two constraints shaped the fallback:

- **No page cap.** A cap would bound worst-case requests but silently under-count high-volume
  users, and we do not add production behaviour purely to speed up tests. Instead the test
  user is `leoloveacm` (24 solved, 90 submissions, one page) so tests and health checks stay
  fast without capping real queries. A "cursor failed to advance" guard prevents infinite
  loops but is not a functional cap.
- **Empty log ⇒ "user does not exist".** `/status` returns HTTP 200 with an empty table for
  both a non-existent user and a real user with zero submissions — it does not validate the
  `user_id`. The two are indistinguishable, so the fallback raises
  `ValueError("The user does not exist")` on an empty log (matching the summary path's
  empty-data behaviour). A real user with zero submissions is misreported as missing; this
  edge case is accepted.

## Consequences

- `src/ojhunt/crawlers/poj.py` gains `_query_via_status`; `query()` dispatches to it on a 403
  from `/userstatus`. The summary-page parsing is unchanged.
- From outside POJ's allowed network the tests exercise **only** the fallback (`/userstatus`
  always 403s here); the primary summary path is not covered by CI and must be validated
  manually from an allowed network if its markup is suspected to have changed.
- `submissions` from the fallback is the total row count across all pages; there is no cheap
  shortcut, so a high-volume user costs `ceil(total / 500)` sequential requests.
- If POJ re-enables `/userstatus` for everyone, the primary path resumes transparently and the
  fallback goes dormant — no code change needed.
