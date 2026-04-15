---
name: ojhunt-hooks
description: Claude Code hooks for this project - existing rules and how to add new ones. Load when adding, reviewing, or planning enforcement rules or automation, or when the user asks what constraints are currently active.
---

# Project Hooks

Hooks enforce constraints mechanically. Check `.claude/settings.json` to see
what's currently active.

## Location

Scripts live in `.claude/hooks/`, wired in `.claude/settings.json` (checked
into git — not `settings.local.json`, not `~/.claude/`).

## Regex gotcha for command bans

Do NOT use `(^|[;&|[:space:]])word[[:space:]]` — this matches the word inside
quoted strings and heredocs (e.g. commit messages containing the banned word).

Use `^[[:space:]]*(sudo[[:space:]]+)?word[[:space:]]` to only match when the
word is the actual command at the start of the line.
