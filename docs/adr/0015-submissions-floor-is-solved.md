# ADR 0015 — A Crawler Never Reports Fewer `submissions` Than `solved`

**Status:** Accepted

## Context

`submissions` is meant to be the user's total submission count, but not every judge publishes one.
Three shapes existed in the crawlers:

- Most judges publish a real total, which the crawler returns. 26 of the 33 crawler tests already
  asserted `result["submissions"] >= result["solved"]`.
- `kilonova`, `yukicoder`, `yosupo` and `vnoj` publish nothing and returned `0`.
- `atcoder` and `codewars` publish only an accepted count and return that — which for both equals
  `solved`. `eolymp` returns `submissionsAccepted`.

Both `ojhunt --json` and `POST /api/merge` reduce the field with a plain sum
(`total_submissions = sum(r.submissions ...)`). A `0` from a user with 500 solved problems made
that total meaningless in the direction nobody expects: a submissions figure smaller than the
number of accepted problems inside it. Parsing gaps do the same thing silently — `poj` reads solved
and submissions from two links in ill-formatted HTML, and `nit` from two table rows, so either can
come back `0` while the other parses.

## Options Considered

### Option A: Keep `0` as an "unknown" sentinel and document it

**Rejected because:** `0` does not survive aggregation. Summing sentinels with real counts produces
a number that is neither a total nor a bound, and every consumer — CLI, `/api/merge`, the PDF table,
any library user — would have to know to filter zeros.

### Option B: Clamp centrally, in `CrawlerResult.__post_init__`

**Rejected because:** it puts crawler knowledge in `core/models.py`. The model is a container for
what a crawler reported; making it silently rewrite that value hides which judges have the quirk and
couples the core to their behaviour. A crawler is where the judge's limitation is known, so it is
where the substitution belongs.

### Option C: Each crawler reports at least its own solved count (chosen)

Every accepted problem cost at least one submission, so `solved` is a sound floor, and the crawler
that knows the judge publishes no total is the one that applies it.

## Decision

**Option C.** `submissions >= solved` holds for every crawler, enforced in the crawler files:

- Judges that publish no total report the solved count, with a comment saying so.
- Where a value is scraped and can go missing (`poj`, `nit`, `eolymp`), the return clamps with
  `max(submissions, solved)`.
- `core/models.py` stays free of this: `CrawlerResult.submissions` is whatever the crawler reported.

## Consequences

- `submissions` is a **lower bound**, not always a total, so the summed totals in `ojhunt --json`,
  `/api/merge` and the PDF breakdown are lower bounds too — previously they were neither.
- Users of the four affected judges see their solved count where they used to see `0`.
- A new crawler that cannot find a submission count returns `solved`, not `0` — see the return
  format in [`docs/dev/crawlers.md`](../dev/crawlers.md). Nothing enforces this centrally; the
  per-crawler network test asserting `submissions >= solved` is the check.
- A judge that publishes some *other* count instead of a total (Eolymp's accepted submissions) says
  so in its own `description`, which `help()` on that crawler prints.
