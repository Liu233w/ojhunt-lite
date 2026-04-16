---
name: ojhunt-cli
description: CLI entry point, argument parsing, credential handling, and output. Load whenever the task involves the CLI — reading, planning, implementing, or debugging argument parsing, query execution, credential handling, output formatting, or progress display.
---

# CLI

See `docs/cli.md` for usage reference (installation, invocation, credential format, JSON output).

## Running in development

```bash
uv run ojhunt tourist@codeforces
uv run ojhunt --list
uv run ojhunt --json tourist@codeforces
```
