# ADR 0007 — Label Cache in `nit` and `uva` Is Load-Bearing

**Status:** Accepted

## Context

Issue #59 explored making all crawlers usable as standalone copy-paste files — no package
required, just copy the `.py` file and `pip install aiohttp`.

Two crawlers, `nit.py` and `uva.py`, are aggregators that map internal problem IDs to
human-readable labels (e.g. `hdu-2181`, `poj-1000`). They do this by scraping individual
problem pages — one HTTP request per problem ID — with a rate-limit delay of 50 ms between
requests to avoid being blocked.

`_utils.py` provides `resolve_labels`, which caches resolved labels in a local SQLite
database (`problem_labels.db`). On the first query for a user with many solved problems
the cache is cold and hundreds of pages are fetched. On subsequent queries only new problems
are fetched; most return instantly from the cache.

## Options Considered

### Option A: Inject `resolve_labels` as an optional parameter; provide a no-cache fallback

Add `label_cache=None` to `query()`. When `None`, use an inline async function that calls
the resolver directly without any caching.

**Rejected because:** the no-cache path is not a "simple fallback" — it is a slow, painful
default. A user with 500 solved problems on NIT would wait 25+ seconds (500 × 50 ms) on
*every single call*, with no progress indication. The cache exists precisely because this
cost is unacceptable to repeat. Offering a no-cache path as a default misleads users into
thinking standalone use is equivalent to package use.

### Option B: Bundle `_utils.py` alongside; document that two files are needed

Allow standalone use by copying both the crawler file and `_utils.py`. Rate-limiting and
caching work as normal.

**Considered but not chosen:** Adds a second file to copy; the `_DB_PATH` default
(`problem_labels.db` in CWD) may surprise users. This could be revisited if demand is clear.

### Option C: Accept that `nit` and `uva` require the package; document this (chosen)

Drop the "every crawler is standalone" claim. Most crawlers (36/38) are genuinely
standalone — they only need `aiohttp`. `nit` and `uva` are exceptions documented as
requiring the installed package.

## Decision

**Option C.** The `_utils.py` label cache is load-bearing, not optional. `nit` and `uva`
require the full `ojhunt` package. The README no longer claims all crawlers are
standalone-copyable.

## Consequences

- The "self-contained crawlers" bullet is removed from `README.md`.
- `nit` and `uva` are noted as requiring the full package in the "Use Crawlers in Your Code"
  section.
- No changes to `nit.py`, `uva.py`, or `_utils.py` — the caching behaviour is unchanged.
- Option B remains open for a future PR if a clear use case emerges.
