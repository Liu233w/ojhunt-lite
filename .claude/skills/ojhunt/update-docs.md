# Where to update documentation

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

## Skills (`.claude/skills/ojhunt/`)
Workflow documentation: how to implement crawlers, how to commit, how to write tests, and
the conventions behind those workflows. Update when the *process* of doing something changes
in this project — not when the code changes.

To add a new workflow:
1. Create `.claude/skills/ojhunt/<topic>.md`
2. Add a link + one-line trigger description to `SKILL.md`

## Commands (`.claude/commands/`)
Project-level slash commands that override global ones.
Create a command when the global equivalent needs project-specific context injected.

## `docs/adr/`
Significant architectural decisions and their rationale. See `commit.md` for when a decision
warrants an ADR vs a commit message.

To add an ADR: create `docs/adr/NNNN-short-title.md` and add a one-line pointer to the ADR
list in `docs/development.md`.

---

## If unsure which layer

- Operational fact (setup, command, structure) → README
- User-facing reference → `docs/`
- Crawler contributor reference → `docs/development.md`
- Workflow or process → `.claude/skills/ojhunt/`
- Project-level command override → `.claude/commands/`
- Significant architectural decision (multiple approaches considered, choice non-obvious from code) → `docs/adr/`
- Small tactical change → commit message intent (no doc needed)
