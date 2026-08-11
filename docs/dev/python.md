# Python conventions

## Import order

Standard library → third-party → first-party, with a blank line between the groups.
`typing` and `collections.abc` are standard library, so they belong in the first group:

```python notest
import re
from collections.abc import Callable

import aiohttp
from selectolax.lexbor import LexborHTMLParser

from ojhunt.core.models import CrawlerResult
```

Ruff enforces this order (`I001`) and fixes it, so you do not have to sort by hand.

## Naming

- Files: `snake_case.py` (crawlers), `*_test.py` (tests)
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

## Typing

Use built-in generics and the `|` union syntax: `dict[str, int]`, `list[str]`, `str | None`.
Do not use `Dict`, `List`, `Optional` or `Union` from `typing` — ruff rewrites them
(`UP006`, `UP007`, `UP035`, `UP045`), and the `format-lint-python.sh` hook applies that
rewrite on every edit. Take `Callable` and `Awaitable` from `collections.abc`, not `typing`.

See [ADR 0016](../adr/0016-adopt-ruff-default-rule-set.md) for why this reversed.

## Prefer asserts and names over comments

State an invariant with `assert` — it documents *and* enforces:

```python notest
row = f"| {name} | {platform} | {notes} |"
assert row.count("|") == 4, f"malformed table row: {row!r}"
```

Asserts are for what the code guarantees itself. Data arriving from outside — a user's
argument, a judge's response — needs a real `raise`, because `python -O` strips asserts.

In tests, put the explanation in the assert message, not in a comment above it:
`assert "items" in listed, "dict's own attributes must survive"`.

Where a comment would explain *what* an expression produces, name the value instead:
`single_line_description = " ".join(text.split())`.

Keep comments for what neither can express — why a construct is load-bearing, or why
the obvious alternative is wrong.

## Error handling

- `ValueError`: User input errors (empty username, user not found)
- `RuntimeError`: Network failures, parsing errors, unexpected issues

## Dependencies

Never specify version numbers when adding dependencies. Use `uv add <package>` and let uv
resolve. This applies to all packages including FastAPI, uvicorn, etc.

`uv add` writes to `uv.lock` — use `dangerouslyDisableSandbox: true`, same as git write operations.

## Ruff removes imports before their usage

Ruff (pre-commit hook) runs between edits and strips imports that appear unused at
that moment. If you add an import in one `Edit` call and the code that uses it in a
second call, ruff will delete the import between the two calls.

**Fix:** always add new imports and the code that uses them in the same `Edit` call.

When import and usage are far apart (can't fit in one `old_string`), edit in this order:
1. Change the **usage** first — replace the call site to use the new symbol.
2. Add the **import** second — the formatter sees the symbol in use and keeps it.

Never add the import first: the formatter strips it before the next Edit lands.

## Parallel execution

When editing multiple crawlers or running independent tasks, spawn sub-agents to work in
parallel. Strongly recommended for:
- Editing multiple crawler files simultaneously
- Running tests across multiple crawlers
- Analyzing multiple files independently
