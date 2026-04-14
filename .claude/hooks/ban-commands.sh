#!/usr/bin/env bash
INPUT=$(cat)
COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // ""' 2>/dev/null)
[ -z "$COMMAND" ] && exit 0

if echo "$COMMAND" | grep -qE '^[[:space:]]*(sudo[[:space:]]+)?gh[[:space:]]'; then
    echo "ERROR: 'gh' CLI is banned — bot user has no GitHub credentials. Commit locally; the user handles push and PR creation." >&2
    exit 2
fi

if echo "$COMMAND" | grep -qE '(^|[;&|[:space:]])pip[[:space:]]+install'; then
    echo "ERROR: 'pip install' is banned. Use 'uv add <package>' instead." >&2
    exit 2
fi

exit 0
