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

# The project's own rules (lint/rules/), on the one file that just changed. Same
# rules ./doit.sh lint runs over everything, so the hook cannot drift from CI.
# Each rule decides whether the file is in its own scope.
command -v uv &>/dev/null || exit 0

# An environment that cannot run anything (fresh clone, offline uv cache) would
# otherwise fail every rule and block every edit on a uv traceback. The exit code
# cannot tell that apart afterwards: a rule that raises also exits 1. The ruff
# steps above skip for the same reason.
uv run python -c "" &>/dev/null || exit 0

FAILURES=""
collect() {
    OUTPUT=$("$@" 2>&1) || FAILURES+="$OUTPUT"$'\n'
    return 0
}

for RULE in lint/rules/*.py; do
    [ -e "$RULE" ] || continue
    collect uv run python "$RULE" "$FILE"
done
if compgen -G "lint/rules/*.yml" >/dev/null; then
    collect uv run ast-grep scan "$FILE"
fi
if [[ -n "$FAILURES" ]]; then
    printf '%s\n' "$FAILURES" >&2
    exit 2
fi
exit 0
