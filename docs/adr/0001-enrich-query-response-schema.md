# ADR 0001: Enrich Query Response Schema and Add Merge Endpoint

## Status

Accepted

## Context

The existing `GET /api/crawlers/{crawler}/{username}` endpoint returns only:

```json
{"solved": 2962, "submissions": 5386, "solvedList": [...], "duration": 2.78}
```

The response does not include `crawler` or `username`, so any client collecting results
from multiple endpoints must annotate each response manually before processing them together.

VJudge is a virtual judge that hosts problems mirrored from other platforms (Codeforces,
AtCoder, etc.). Its `solvedList` contains tagged problem IDs like `CF_1234A`. When a user
queries both VJudge and Codeforces, the same problem may appear in both result sets,
inflating the total unique solved count. Deduplication logic currently lives in the
frontend JavaScript, and is partially duplicated in Python.

## Decision

1. **Add `crawler` and `username` fields to `QueryResult`** (the per-crawler API response).
   This is a non-breaking additive change — existing clients that ignore unknown fields are
   unaffected.

2. **Add `POST /api/merge`** that accepts `List[QueryResult]` (the enriched schema above)
   and returns a deduplicated summary across all supplied results. The merge logic handles
   VJudge cross-platform deduplication server-side.

3. **Update the frontend** to use `POST /api/merge` for the final total instead of running
   merge logic in JavaScript. Per-crawler requests still fire in parallel for progressive
   display; the merge call happens once all results are collected.

Reusing `QueryResult` as the merge input means no separate input schema is needed.
The client collects per-crawler responses verbatim and POSTs them as an array.

## Consequences

- VJudge deduplication logic is consolidated in Python — the JavaScript duplicate is removed.
- The frontend gains one extra HTTP round-trip at the end (cheap, after all crawling is done).
- `crawler` and `username` in the response make results self-describing, which also enables
  the agent support use case (ADR 0002).
- The `POST /api/merge` endpoint is a stateless pure function — it does no crawling, so
  server load impact is negligible.
