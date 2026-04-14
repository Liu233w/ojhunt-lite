---
name: ojhunt
description: Project-specific workflows and conventions for ojhunt-lite. Invoke before starting any task in this project.
---

# OJHunt Lite Skills

Read the relevant file for your task:

- **[crawlers.md](crawlers.md)** — Adding or fixing crawlers. Use when implementing a new crawler, debugging an existing one, or working with crawler metadata.
- **[web.md](web.md)** — Web layer, PDF internals, API routes, running the dev server. Use when working on the FastAPI app, PDF features, or environment setup.
- **[testing.md](testing.md)** — Unit tests and crawler tests. Use when writing or running pytest tests (non-Playwright).
- **[e2e.md](e2e.md)** — Playwright e2e tests. Use when writing or running browser tests. See also `testing.md` for shared conventions.
- **[commit.md](commit.md)** — Committing, git operations, and ADRs. Use before any commit or when considering whether a decision warrants an ADR.
- **[python.md](python.md)** — Python code style, imports, dependencies. Use when writing Python code in this project.
- **[update-docs.md](update-docs.md)** — Where to update documentation and agent workflows. Use when adding or updating any documentation.

---

## Skill structure

The entry point is this file (`SKILL.md`). Sub-topics are flat `.md` files in the same
directory — nested sub-directories are not supported by the skill loader.

To add a new workflow:
1. Create `.claude/skills/ojhunt/<topic>.md`
2. Add a link + one-line trigger description above

---

## Growing these skills

If the user mentions a workflow, convention, or recurring pattern that isn't covered by an
existing sub-skill, ask them: *"Should I update an existing skill or create a new one for this?"*
Don't silently let project knowledge go undocumented.
