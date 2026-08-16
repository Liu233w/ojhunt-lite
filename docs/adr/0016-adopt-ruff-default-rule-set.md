# ADR 0016 — Adopt Ruff's Default Rule Set, Which Reverses the Typing Convention

**Status:** Accepted

## Context

`pyproject.toml` never pinned `[tool.ruff.lint] select`, so the project always linted with
whatever ruff shipped as its default. That default was stable for years at 59 rules
(`E4`, `E7`, `E9`, `F`). Ruff 0.16.0 expanded it to 413 rules. A dependabot bump from
0.15.22 to 0.16.0 therefore turned 0 findings into 534 across 98 files, and CI failed.

Two of the newly enabled rule groups collide with the codebase on purpose rather than by
accident:

- `UP006`, `UP007`, `UP035` and `UP045` — 341 of the 534 findings — demand PEP 585 and PEP 604
  syntax (`dict[str, X]`, `X | None`). The Python convention said the opposite: "Use `Dict`,
  `List`, `Union` from the `typing` module." Both rules cannot hold.
- `BLE001` flags 23 `except Exception` blocks. Every crawler ends in one by design.

## Options Considered

### Option A: Pin the old default set, `select = ["E4", "E7", "E9", "F"]`

**Rejected because:** it freezes the linter at the 2023 default forever and hides real defects
this bump surfaced. Four of them were genuine: two functions timed their own work by
subtracting `datetime.now()` readings, which an NTP step corrupts, and two rendered timestamps
named no timezone. A rule set chosen to produce zero findings cannot find those.

### Option B: Adopt the new default set, but keep the typing convention

**Rejected because:** it needs `ignore = ["UP006", "UP007", "UP035", "UP045"]` — a permanent
exemption whose only argument is that the code already looks that way. The
`format-lint-python.sh` hook runs `ruff check --fix` on every edited file, so without the
exemption the convention is unenforceable anyway, and with it the codebase keeps a style that
Python has deprecated since 3.9.

### Option C: Adopt the new default set and modernise the typing (chosen)

The autofix does the mechanical work. `requires-python` is already `>=3.12`, so no annotation
in this repo needs the `typing` spelling for compatibility.

## Decision

**Option C.** The default rule set stands as ruff ships it. Three narrow exceptions are
recorded in config, and three at the site:

| Exception | Where | Why |
|-----------|-------|-----|
| `ignore = ["BLE001"]` | `pyproject.toml` | The catch-all is the crawler contract: any parse or transport failure becomes a `RuntimeError` the runner reports per crawler, so one judge's surprise never aborts a run. |
| `extend-immutable-calls = ["fastapi.File"]` | `pyproject.toml` | `File(...)` in a parameter default is how FastAPI declares an upload. |
| `# noqa: FLY002` | `web/app.py` | The fix collapses the CSP into one 300-character line and deletes the comments inside it. That block is load-bearing — see [ADR 0010](0010-relaxed-csp-for-inline-alpine.md). |
| `# noqa: UP031` | `crawlers/eolymp.py` | `.format()` needs every brace in the GraphQL body doubled. |
| `# noqa: DTZ007` | `web/pdf.py` | The chart axis parses day keys that are already local-day strings. It needs their order, not an instant. |

`.claude/rules/python.md` now states the PEP 585/604 rule, and the `query()` templates in
`docs/dev/crawlers.md` were updated so a new crawler does not reintroduce the old style.

## Consequences

- A future ruff release that expands the defaults again will surface findings the same way.
  That is accepted: CI runs `./doit.sh lint`, so the bump fails loudly on the dependabot PR
  rather than landing silently.
- `Dict`, `List`, `Optional` and `Union` no longer appear in annotations. A patch that adds one
  back gets rewritten by the `format-lint-python.sh` hook on the next edit.
- The 413-rule set covers `SIM`, `C4`, `B`, `DTZ`, `RUF`, `PL` and more, so new code meets
  checks that were never applied to the code already in the tree.
- `./doit.sh lint` runs `ruff format --check` beside `ruff check`, because ruff 0.16 also
  formats Python blocks inside Markdown and that drift was invisible to a check-only gate.
  Both passes always run, so one report lists every problem.
