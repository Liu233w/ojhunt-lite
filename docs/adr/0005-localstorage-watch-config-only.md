# ADR 0005 — localStorage Sync via $watch (Config-Only Persistence)

**Status:** Accepted

## Context

`app.js` needs to persist two things across page loads:

1. **Config** — which crawlers/usernames to query (`username` + `[{crawler, username}]`)
2. **Query results** — `solved`, `submissions`, `solvedList`, `rawResponse`, `status`

The original implementation called `saveQueries()` at every mutation site (`addQuery`,
`removeQuery`, `clearAll`, `uploadReport`). This was error-prone: any new code path that
mutated queries had to remember to call `saveQueries()` manually.

## Options Considered

### Option A: `@alpinejs/persist` plugin

Use `Alpine.$persist(value).as('key')` to auto-sync reactive fields to localStorage.
Eliminates all manual call sites cleanly.

**Rejected because:** Adds an extra CDN dependency (`@alpinejs/persist`) for functionality
that Alpine's built-in `$watch` already provides. The plugin also doesn't support custom
serialization, making it harder to exclude non-serializable fields.

### Option B: Full live-state persistence (results + rawResponse)

Persist the entire `queries` array including query results so users see their last results
after a page refresh.

**Rejected because:** `rawResponse` is load-bearing for partial retry. When a user retries
a single query, `calculateReport()` must POST all queries' `rawResponse`s to `/api/merge`
to compute the deduplicated total. If `rawResponse` is not persisted, partial retry produces
a wrong report (only counts the one retried query). Workarounds (persisting `rawResponse`,
getter functions, separate cache objects) added complexity without a clear win. `abortController`
is also unserializable.

### Option C: `$watch` with config-only persistence (chosen)

Use Alpine's built-in `$watch` to call `saveQueries()` whenever `username` or `queries`
changes. Add a second watch on `cachedReport` to sync the cached report. This replaces all
manual `saveQueries()` call sites with two watches in `init()`.

## Decision

**Option C.** Config-only persistence (`username` + `[{crawler, username}]` +
`cachedReport`) via `$watch`. Query results are runtime-only and lost on page refresh.
No extra dependencies; same localStorage keys as before. How the cached report itself is
written and read is [ADR 0017](0017-cached-report-is-one-record.md).

## Consequences

- `saveQueries()` and `loadSavedQueries()` become private helpers called only from `init()`
- No `saveQueries()` calls scattered across `addQuery`, `removeQuery`, `clearAll`, `uploadReport`
- Query results are lost on refresh — same behavior as before this change
- `calculateReport()` is also triggered by the `queries` watch, replacing all explicit
  `calculateReport()` call sites and fixing the race condition where concurrent query
  completions could POST to `/api/merge` simultaneously with stale data
  (solved by aborting the previous in-flight merge request via `AbortController`)
