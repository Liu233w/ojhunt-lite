#!/usr/bin/env bash
INPUT=$(cat)
FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // ""' 2>/dev/null)
[[ "$FILE" == *.py ]] || exit 0

if command -v uv &>/dev/null; then
    uv run ruff format "$FILE" 2>/dev/null || true
    uv run ruff check --fix "$FILE" 2>/dev/null || true
elif command -v ruff &>/dev/null; then
    ruff format "$FILE" 2>/dev/null || true
    ruff check --fix "$FILE" 2>/dev/null || true
fi
exit 0
