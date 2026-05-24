# ADR 0008 — Unique Solved Deduplication Design

**Status:** Accepted

## Context

`/api/merge` and the CLI report a single "unique solved" count across all queried crawlers.
Two design questions arose:

1. **How should aggregators (VJudge, NIT, etc.) interact with native-OJ crawlers in the dedup?**
2. **Crawlers that return `solved_list=None` (luogu, leetcode, atcoder, etc.) were being silently
   dropped from the total. How should their counts be included?**

### Aggregator behaviour

Aggregators mirror problems from source OJs and submit on behalf of users using the
aggregator's own shared accounts on those OJs. A user solving a problem via an aggregator
and solving the same problem directly on the native OJ are two independent activities —
the aggregator submission does not appear on the user's native OJ profile.

## Deduplication is at the problem/algorithm level

Deduplication is intentional and correct. The reasoning: solving an algorithm problem is
binary. Once a user has solved it, solving it again (via a different platform, a different
path, or multiple times within the same aggregator) adds no new learning. The unique solved
count represents the breadth of a user's solved problem set, not a submission count.

This also means aggregator + native OJ dedup is correct. If a user solved Codeforces 1A
both through an aggregator and directly on Codeforces, they have solved that algorithm
problem once. `collect_solved_problems()` in `core/stats.py` normalises all problem IDs
to `{source_oj}-{problem_id}` so duplicates collapse regardless of which path was used.

## Options considered for listless crawlers

Some crawlers cannot or do not expose the user's solved problem list — they return only a
count (`solved_list=None`). Before this was fixed, their counts were silently dropped.

### Option A: Skip listless crawlers (previous behaviour)

Report 0 contribution from any crawler without a `solved_list`.

**Rejected because:** a user with 200 luogu solves sees them contribute nothing to their
total. The under-count is worse than any over-count.

### Option B: Subtract aggregator overlap, then add remainder

Process aggregators first; for each listless crawler, subtract the number of that OJ's
problems already contributed by an aggregator, then add the remainder directly.

**Rejected because:** aggregator counts and native OJ counts are independent activities
(see above). Subtracting aggregator overlap would be semantically wrong — it would penalise
a user for solving problems on both platforms.

### Option C: Add raw count directly (chosen)

Add `solved` from each successful listless crawler directly, without any dedup against
aggregators.

This may over-count in the rare case where a problem appears in both an aggregator's list
and the same OJ's listless count. Over-counting is the lesser evil: the total becomes a
slight upper bound rather than a definite under-count.

## Decision

**Option C.** `get_unique_solved()` in `core/stats.py` combines:
1. `len(collect_solved_problems(results))` — deduped count from crawlers with a `solved_list`.
2. `sum(r.solved for successful listless crawlers)` — raw counts added directly.

`collect_solved_problems()` is unchanged and continues to handle aggregator/native-OJ
dedup correctly.

## Consequences

- Listless crawlers (luogu, leetcode, atcoder, lightoj, toph, tlx, csg, hust, eolymp)
  now contribute their `solved` count to the total.
- The unique solved total is an upper bound when a user queries both an aggregator and
  a listless crawler that the aggregator covers. This is accepted.
- Future crawlers that gain a `solved_list` automatically get proper dedup with no
  changes needed to the stats layer.
