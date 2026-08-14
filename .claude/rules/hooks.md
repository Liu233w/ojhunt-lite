---
paths:
  - ".claude/hooks/**"
  - ".claude/settings.json"
---

# Project hooks

Hooks enforce constraints mechanically. Check `.claude/settings.json` to see
what's currently active.

## Location

Scripts live in `.claude/hooks/`, wired in `.claude/settings.json` (checked
into git — not `settings.local.json`, not `~/.claude/`).

## Write a check only when it is cheap and deterministic

A hook earns its place when the rule is a one-line pattern with an unambiguous fix. If the
check needs judgement, a rule under `.claude/rules/` states the convention instead — a noisy
hook trains everyone to ignore it.

## Regex gotcha for command bans

Do NOT use `(^|[;&|[:space:]])word[[:space:]]` — this matches the word inside
quoted strings and heredocs (e.g. commit messages containing the banned word).

Use `^[[:space:]]*(sudo[[:space:]]+)?word[[:space:]]` to only match when the
word is the actual command at the start of the line.
