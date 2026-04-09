# ADR 0006 — Legacy Lookup Restricted to ABP Username Only

**Status:** Accepted

## Context

`find_user` in `legacy_db.py` looked up users by matching the input string against two
independent fields:

1. `query_histories.main_username` — the OJ handle the user typed when running queries on
   the old acm-statistics site (e.g. "tourist" on Codeforces)
2. `users.username` — the ABP login username the user registered with on the old site

These two namespaces are independent. A user's ABP login name has no required relationship
to any OJ handle. The two-field lookup conflates them, which causes two problems:

**Correctness:** If user A's ABP username happens to equal user B's OJ handle, user A's lookup
returns user B's record from the `main_username` path. The wrong history is returned.

**Privacy:** `main_username` is a publicly visible OJ handle. Accepting it as a lookup key
allows anyone who knows a user's OJ handle to retrieve that user's cross-platform identity
data (which OJs they use and under which handles).

The UI already labels the field "the username you used on acm-statistics for logging-in",
implying ABP-only lookup was always the intent.

## Options Considered

### Option A: Match ABP username only (chosen)

`find_user` queries only `users.username`. `main_username` is fetched separately after the
ABP match for use as a display name in the PDF (since the OJ handle is more recognisable in
a competitive programming context than a site login).

**Consequence:** Users who queried the old site without registering (no `users` row, only
`query_histories` rows) lose access to their legacy data export.

### Option B: Keep both, deduplicate

Continue matching both fields but deduplicate results to avoid returning the same user twice.

**Rejected because:** This does not fix the correctness bug — user A can still get user B's
record if their ABP username matches user B's OJ handle.

### Option C: Separate endpoints

Provide two endpoints: one for ABP username lookup, one for OJ handle lookup.

**Rejected because:** Over-engineered for a one-off legacy export page. The UI text already
implies a single input type.

## Decision

**Option A.** `find_user` matches only on `users.username` (ABP login). `main_username` from
`query_histories` is fetched after the match and used as the PDF display name (fallback to
ABP username if no query history exists).

## Consequences

- Users who only ever queried anonymously (no account row in `users`) cannot retrieve their
  legacy data via the web UI. This is accepted as a tradeoff.
- The PDF display name continues to show the user's OJ handle where available, which is more
  meaningful than the site login in a competitive programming context.
- `find_user` no longer returns `match_type` or `main_username` — callers that previously
  read those fields are updated to derive `main_username` independently.
