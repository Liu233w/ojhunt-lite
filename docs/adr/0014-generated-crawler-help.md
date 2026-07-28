# ADR 0014 — Crawler `help()` Text Is Generated, Not Written Per Crawler File

**Status:** Accepted

## Context

Issue #113 asked for documentation reachable from Python itself: `help()` on a crawler should say
what it queries, whether it needs a login, and how to pass arguments.

The obvious place for that text is each crawler module's docstring, so that
`help(ojhunt.crawlers.cses)` answers the question. That slot is taken. Every file in
`src/ojhunt/crawlers/` opens with the BSD 2-Clause license as its module docstring, because
individual crawler files are meant to be copied into other projects and must carry their license
with them (`docs/dev/crawlers.md`). Moving the license into `#` comments would free the slot, but
it rewrites the header of all 34 files and changes the shape a user sees when they copy one.

The same facts are already declared once per crawler, in `__crawler_meta__` — title, URL,
description, `login_type`, `is_aggregator` — and the accepted arguments are already recoverable
from the `query` signature, which is how `__main__.py` decides whether to pass credentials.

## Options Considered

### Option A: Convert the license to `#` comments and hand-write a module docstring per crawler

**Rejected because:** it churns every crawler file, and the per-file prose would restate
`__crawler_meta__` in a second voice. The web UI and CLI read the metadata; the docstring would
drift from it the first time a title or login type changed.

### Option B: A `crawler_help(name)` function users call instead of `help()`

**Rejected because:** the issue asks for `help()`. A parallel documentation function is one more
thing to discover, and `help()` remains wrong for anyone who doesn't find it.

### Option C: Generate the text from metadata and attach it to the objects `help()` already works on (chosen)

`render_crawler_doc()` in `src/ojhunt/crawlers/_help.py` builds the text from `CrawlerMeta` plus
`inspect.signature(query)`. Registry discovery (ADR 0013) assigns it to each `CrawlerInfo`
instance's `__doc__` and appends it to the `query` function it hands out.

Per-instance `__doc__` is what makes this work: `pydoc` renders an instance's own `__doc__` under
its `repr`, so `help(crawlers["cses"])` prints the generated text. `CrawlerInfo.__repr__` is
compact so that first line stays readable.

## Decision

**Option C.** Crawler `help()` text is generated at registry build time from `__crawler_meta__` and
the `query` signature. License headers stay as module docstrings, untouched.

## Consequences

- `help(crawlers["<name>"])` and `help(crawlers["<name>"].query)` are the documented entry points
  for a single crawler; `help(ojhunt.crawlers)` is the entry point for the library.
- `help(ojhunt.crawlers.<name>)` still shows the license. That is the cost of keeping crawler files
  copy-pasteable, and the reason the two `help()` targets above exist.
- Adding a crawler documents it automatically — no per-crawler prose to write beyond the `query`
  docstring, which `tests/crawlers/docs_test.py` requires.
- The generated text is only as good as `__crawler_meta__`. A crawler with an empty `description`
  gets no username-format hint, so `description` carries more weight than before.
- **Every crawler's login and aggregator wording comes from `_login_paragraph()`, so no crawler
  file repeats it.** The explanation itself is still written out in three registers — the
  `LoginType` docstring, the package docstring, and `docs/dev/crawlers.md` — for three audiences,
  and `docs/library.md` renders two of them on one page. A new `LoginType` member has to be added
  to `_login_paragraph()` and `LoginType.label`; both assert or raise rather than emitting the
  wrong text.
- `docs/library.md` is a committed snapshot, so it goes stale as soon as a docstring changes.
  `tests/crawlers/docs_test.py` compares it against the generator, so `test-unit` fails until
  `./doit.sh gen-docs` runs.
