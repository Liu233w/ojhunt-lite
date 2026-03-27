# ADR 0003: Rename is_virtual_judge to is_aggregator

## Status

Accepted

## Context

The field `is_virtual_judge` (Python) / `isVirtualJudge` (API/JS) was introduced to
flag crawlers whose `solvedList` entries are already prefixed with the source platform
(e.g. `codeforces-1A`, `hdu-1000`). The merge endpoint uses this flag to skip
re-prefixing those entries, avoiding double-counting when a user queries both an
aggregator and a native platform.

The name `is_virtual_judge` created a naming collision: **VJudge** is a specific website
(`vjudge.net`), while "virtual judge" is a category of platform that hosts problems
mirrored from other OJs. Crawlers named `vjudge` and the flag `is_virtual_judge` looked
like they referred to the same thing, making it unclear whether the flag was VJudge-specific
or a general type marker.

## Decision

Rename the concept to **aggregator** throughout the codebase:

- Python: `CrawlerMeta.is_virtual_judge` → `is_aggregator`
- Crawler meta dicts: `"is_virtual_judge"` key → `"is_aggregator"`
- API: `CrawlerInfo.isVirtualJudge` → `isAggregator`

For backward compatibility, keep `isVirtualJudge` as a deprecated alias in the
`CrawlerInfo` API response, populated with the same value as `isAggregator`. It will
be removed in a future version once clients have migrated.

The internal Python field and crawler meta dict key are renamed without a compatibility
shim — they are internal and not part of the public API contract.

## Consequences

- The distinction between VJudge (a site) and aggregator (a platform type) is now clear
  in code and documentation.
- Existing API clients reading `isVirtualJudge` continue to work unchanged.
- New clients should use `isAggregator`.
- Adding a new aggregator crawler requires only setting `"is_aggregator": True` in its
  `__crawler_meta__` — no other files need updating.
