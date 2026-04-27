#!/usr/bin/env bash
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)
[ -z "$COMMAND" ] && exit 0

if echo "$COMMAND" | grep -qE '^[[:space:]]*(sudo[[:space:]]+)?gh[[:space:]]'; then
    echo "ERROR: 'gh' CLI is banned — bot user has no GitHub credentials. Commit locally; the user handles push and PR creation." >&2
    exit 2
fi

if echo "$COMMAND" | grep -qE '^[[:space:]]*(sudo[[:space:]]+)?pip[[:space:]]+install'; then
    echo "ERROR: 'pip install' is banned. Use 'uv add <package>' instead." >&2
    exit 2
fi

if echo "$COMMAND" | grep -qE '^[[:space:]]*(sudo[[:space:]]+)?uvicorn[[:space:]]'; then
    echo "ERROR: Do not start the dev server with 'uvicorn' directly. Load the ojhunt-web skill for the correct start command." >&2
    exit 2
fi

if echo "$COMMAND" | grep -qE 'uv[[:space:]]+run[[:space:]]+pytest' \
   && ! echo "$COMMAND" | grep -qE -- '[[:space:]]-m[[:space:]]|-m[[:space:]]' \
   && ! echo "$COMMAND" | grep -qE '\.py|tests/[a-z]'; then
    echo "ERROR: Bare 'uv run pytest' runs ALL tests including slow network/crawler and Playwright e2e tests. Use a scoped command:
  uv run pytest -m \"not network and not playwright\"   # unit tests (CI scope)
  uv run pytest -m playwright tests/e2e/               # e2e only
  uv run pytest tests/path/to/specific_file.py         # single file" >&2
    exit 2
fi

exit 0
