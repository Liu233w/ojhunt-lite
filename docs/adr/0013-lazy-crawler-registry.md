# ADR 0013 — The Crawler Registry Is a Lazily Resolved Module Attribute

**Status:** Accepted

## Context

Crawler discovery walks `src/ojhunt/crawlers/`, imports every module that exports `query` and
`__crawler_meta__`, and builds a name → `CrawlerInfo` mapping. Every consumer needs the same
mapping: the CLI lists and validates crawler names, the web app renders the index and `/crawlers`
pages, and the availability checker loops over all of them.

Historically discovery was a function, `discover_crawlers()`, memoized with `functools.cache`. That
means callers write `crawlers = discover_crawlers()` at the top of a function to get at a value that
never changes after the first call — ceremony that says "compute this" about something already
computed. It also makes the library's first line of documentation a function call, when what a user
wants is the registry.

Two things constrain the alternative. Crawler files are meant to be copied out one at a time
(`docs/dev/crawlers.md`), and the README advertises importing exactly one:
`from ojhunt.crawlers.codeforces import query`. That path must not import the other 32 modules.
Separately, `crawlers` is already a local variable and a parameter name across the CLI and web
modules, so a package-level name spelled the same way would collide.

## Options Considered

### Option A: Keep a memoized `get_crawlers()` function

**Rejected because:** it is ceremony around a cached value. Nothing in the API needs to be a
function — there are no arguments, and no caller can observe a second call differing from the first.

### Option B: An eager module-level `crawlers = _discover()`

**Rejected because:** `import ojhunt.crawlers` runs when any submodule is imported, so
`from ojhunt.crawlers.codeforces import query` would pull in all 33 crawler modules. The cost is
small in wall-clock terms (measured at ~0.11 s either way) but it defeats the point of a
single-file, self-contained crawler.

### Option C: A module-level `crawlers` resolved on first access via PEP 562 (chosen)

`__getattr__` in `src/ojhunt/crawlers/__init__.py` returns `_discover()` when asked for `crawlers`;
`_discover()` is private and `@cache`d. Importing the package, or a single crawler module, does not
trigger discovery — only naming `crawlers` does. `__dir__` advertises it so it tab-completes, and
`help(ojhunt.crawlers)` lists it under `DATA`.

## Decision

**Option C.** The registry is the module attribute `ojhunt.crawlers.crawlers`, discovered on first
access. `discover_crawlers()`/`get_crawlers()` are removed rather than kept as aliases: they appear
in no released documentation, and #113 is the release that documents the library surface, so there
is no documented promise to keep.

## Consequences

- The documented spelling is `from ojhunt.crawlers import crawlers`, and it is what `README.md`,
  the package docstring and `docs/library.md` all show.
- **The `if TYPE_CHECKING: crawlers: CrawlerRegistry` declaration is load-bearing.** Ruff reports
  `F822` (undefined name in `__all__`) for a name only `__getattr__` provides, and type checkers
  cannot see through `__getattr__` either. The annotation satisfies both and creates no runtime
  binding, so discovery stays lazy. Deleting it breaks `./doit.sh lint`.
- **Consumers alias the import** — `from ojhunt.crawlers import crawlers as crawler_registry` in
  `__main__.py`, `cli/output.py`, `web/api.py`, `web/pages.py` and `web/crawler_status.py` — because
  those modules already use `crawlers` for locals and parameters. Functions that receive the
  registry as a `crawlers` parameter keep that name; they shadow a module global they never read.
- **Those module-level imports resolve the registry at import time, so the CLI and web app are
  eager** — `ojhunt --help` now discovers every crawler, which it used to skip entirely because
  `discover_crawlers()` ran after `parse_args()`. Measured, that is ~7 ms of discovery inside an
  `import ojhunt.crawlers` that costs ~130 ms either way (aiohttp and selectolax dominate), out of
  ~160 ms wall clock. Option B's cost is therefore paid by the applications; the laziness buys
  something only for a third party importing one crawler module, which is the case that matters
  (that path must not import 33 files).

  `from … import crawlers as crawler_registry` is what binds early: it reads the attribute, which
  runs `__getattr__`. Plain `import ojhunt.crawlers` plus `ojhunt.crawlers.crawlers[name]` at each
  use site would stay lazy *and* keep the import at module level, at the cost of a longer
  expression everywhere the registry is touched. The web app needs every crawler anyway, so this
  only ever mattered for `ojhunt --help`, and the shorter name won.
- **There is no way to rescan.** `_discover.cache_clear()` is not exposed, and a plugin mechanism
  that added crawlers after first access would need this decision revisited. Tests that need a
  different registry patch the consumer's `crawler_registry` name rather than clearing a cache.
- Discovery now happens at the first *attribute access* rather than at an explicit call, so a
  failure in a crawler module surfaces at a less obvious point — and because the consumers above
  read the attribute at import time, an escaping exception would abort `ojhunt --help` and uvicorn
  startup rather than one query. `_discover()` therefore catches `Exception` per module, warns on
  stderr and skips it: bad metadata raises `ValueError`, not only `ImportError`.
