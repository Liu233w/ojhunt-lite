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

# In tests the explanation belongs in the assert message, not in a comment above it
# (.claude/rules/python.md). Ruff has no rule for this, and it is a one-line pattern.
# Only the text this edit introduced is scanned: the suite still carries older comments,
# and flagging those would fire on every unrelated edit until someone cleaned them up.
if [[ "$FILE" == *_test.py || "$FILE" == */tests/* ]]; then
    ADDED=$(echo "$INPUT" | jq -r '.tool_input.new_string // .tool_input.content // ""' 2>/dev/null)
    HITS=$(printf '%s\n' "$ADDED" | awk '
        /^[[:space:]]*#/ { comment = 1; text = $0; next }
        /^[[:space:]]*assert[[:space:](]/ { if (comment) print text }
        { comment = 0 }
    ')
    if [[ -n "$HITS" ]]; then
        echo "$FILE: this edit puts a comment directly above an assert. Move the explanation into the assert message (see .claude/rules/python.md):" >&2
        echo "$HITS" >&2
        exit 2
    fi
fi
exit 0
