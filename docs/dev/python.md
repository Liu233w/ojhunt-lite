# Python conventions

## Import order

Standard library → third-party → typing:

```python notest
import re
import aiohttp
from selectolax.lexbor import LexborHTMLParser
from typing import Dict, List, Union
```

## Naming

- Files: `snake_case.py` (crawlers), `*_test.py` (tests)
- Functions/variables: `snake_case`
- Constants: `UPPER_SNAKE_CASE`

## Typing

Use `Dict`, `List`, `Union` from the `typing` module — not the `dict[str, ...]` syntax.

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
