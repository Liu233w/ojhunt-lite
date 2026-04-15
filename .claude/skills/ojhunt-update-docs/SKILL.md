---
name: ojhunt-update-docs
description: Documentation structure and agent workflow locations. Load whenever the task involves documentation — finding where docs live, planning changes, writing or updating docs, or updating skills and commands.
---

# Where to update documentation

**Single source of truth:** Each piece of knowledge lives in exactly one layer. When adding
documentation, point to the authoritative source — don't inline definitions that already exist
elsewhere. Duplication causes drift.

## README.md
Entry-level documentation: setup, usage examples, CLI flags, supported OJs.
Update when something operational changes (a command, a new crawler, a setup step).

## `docs/` (user-facing)
Documentation for users running or deploying the project:
- `docs/cli.md` — CLI usage reference
- `docs/web.md` — Web UI usage reference
- `docs/development.md` — Crawler contributor guide (`__crawler_meta__` fields, login types,
  templates, return format). Update when the crawler API or contribution process changes.
- `docs/adr/` — Architectural decisions (see below)

## Skills (`.claude/skills/ojhunt-*/`)
Workflow documentation: how to implement crawlers, how to commit, how to write tests, and
the conventions behind those workflows. Update when the *process* of doing something changes
in this project — not when the code changes.

**Only document what's non-obvious.** If Claude can derive it by reading the files, or if
it's enforced elsewhere (hook, test, linter), don't write it. Redundant entries create drift.

To add a new workflow:
1. Create `.claude/skills/ojhunt-<topic>/SKILL.md` with frontmatter:
   ```
   ---
   name: ojhunt-<topic>
   description: <one-line trigger description>
   ---
   ```

**Note:** Claude Code's skill loader does not support colon-namespaced sub-skills
(e.g. `ojhunt:topic`) at the project level. Each skill must be its own top-level
directory. Use the `ojhunt-` prefix to group related project skills.

## Commands (`.claude/commands/`)
Project-level slash commands that override global ones.
Create a command when the global equivalent needs project-specific context injected.

`/update-learnings` — captures session learnings and routes them to the right doc layer.

## `docs/adr/`
Significant architectural decisions and their rationale. See the **ojhunt-commit** skill for
when a decision warrants an ADR vs a commit message.

To add an ADR: create `docs/adr/NNNN-short-title.md` and add a one-line pointer to the ADR
list in `docs/development.md`.

## `CLAUDE.md`
Context that **every agent working on this project must know**, regardless of the task.
Update when something is so fundamental that any agent — without it — would make the wrong
call: project-wide invariants, hard constraints, or pointers to where documentation lives.

Keep entries minimal. `CLAUDE.md` is loaded into every conversation; bloat here costs context
on every invocation. If the knowledge is task-specific (e.g., "how to write a crawler"),
put it in a skill, not here.

---

## If unsure which layer

- Operational fact (setup, command, structure) → README
- User-facing reference → `docs/`
- Crawler contributor reference → `docs/development.md`
- Workflow or process → `.claude/skills/ojhunt-*/`
- Project-level command override → `.claude/commands/`
- Significant architectural decision (multiple approaches considered, choice non-obvious from code) → `docs/adr/`
- Small tactical change → commit message intent (no doc needed)
- "Never do X" or "always do Y after Z" → **hook first** (see **ojhunt-hooks** skill); once hook-enforced, do NOT also add a skill entry — the hook is the enforcement, a skill note just creates drift
- Project-wide invariant every agent must know, regardless of task → `CLAUDE.md`
