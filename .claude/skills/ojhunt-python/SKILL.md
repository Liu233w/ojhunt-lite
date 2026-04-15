---
name: ojhunt-python
description: Python conventions for this project - import order, code style, and dependency management. Load whenever the task involves Python code — reading existing code, planning a new module, writing or refactoring Python, or adding a dependency.
---

# Python conventions

## Import order

Standard library → third-party → typing:

```python
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

## Parallel execution

When editing multiple crawlers or running independent tasks, spawn sub-agents to work in
parallel. Strongly recommended for:
- Editing multiple crawler files simultaneously
- Running tests across multiple crawlers
- Analyzing multiple files independently
