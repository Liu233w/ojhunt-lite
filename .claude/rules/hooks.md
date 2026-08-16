---
paths:
  - ".claude/hooks/**"
  - ".claude/settings.json"
---

# Project hooks

Hooks decide *when* a check runs. Check `.claude/settings.json` to see what is currently
active.

## Location

Scripts live in `.claude/hooks/`, wired in `.claude/settings.json` (checked
into git — not `settings.local.json`, not `~/.claude/`).

## Keep the check out of the hook

`format-lint-python.sh` runs ruff and then every rule in `lint/rules/` over the file that
changed. What each rule checks is defined there, not here, so the hook and `./doit.sh lint`
can never disagree. Adding a check to the hook alone gives you a rule that CI does not run and
nobody can test — write it in `lint/rules/` instead (see `.claude/rules/lint-rules.md`).

## Regex gotcha for command bans

Do NOT use `(^|[;&|[:space:]])word[[:space:]]` — this matches the word inside
quoted strings and heredocs (e.g. commit messages containing the banned word).

Use `^[[:space:]]*(sudo[[:space:]]+)?word[[:space:]]` to only match when the
word is the actual command at the start of the line.
