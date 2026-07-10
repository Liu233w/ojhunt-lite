---
name: ojhunt-update-env
description: Single source of truth for where each piece of knowledge belongs (docs/dev/, docs/, ADRs, skills, hooks, commands, CLAUDE.md) and what must NOT be documented because it already lives in code or tests. Load BEFORE writing or editing ANY documentation, ADR, or skill — and whenever choosing where a fact should live or whether to document it at all — not only when explicitly asked to "update docs" or "capture learnings".
---

# Where knowledge lives in this project's environment

**Single source of truth:** Each piece of knowledge lives in exactly one layer. When adding
documentation, point to the authoritative source — don't inline definitions that already exist
elsewhere. Duplication causes drift.

**Workflow vs. convention — pick the right channel.** A **workflow** (a procedure you run on
demand: commit, implement a crawler, decide where knowledge goes) is a **skill**. A
**convention or reference fact** (code style, a schema, a gotcha, a test rule) is a **doc under
`docs/dev/`** — because skills are lazily triggered and unreliably loaded, whereas `docs/dev/`
is indexed by `docs/development.md`, which is `@`-imported into `CLAUDE.md` and therefore always
in context. Don't put a convention in a skill hoping it triggers; add it to `docs/dev/` and its
routing-table row.

**Command docs span multiple layers — search before changing.** Shell commands (e.g. how to
run tests, start the server, add a dependency) can be documented in skills, READMEs, `docs/`,
and referenced inside hook error messages. When a command changes, search all four locations
before closing the task: `grep -rn "the old command" .claude/skills/ README.md docs/ .claude/hooks/`

**Route to the right file, don't append to the nearest one.** When adding knowledge, name what
it's *about* in one phrase and put it where that phrase belongs. The file you're already editing
tends to absorb content from neighbouring domains — resist the easy append.

## README.md
Entry-level documentation: setup, usage examples, CLI flags, supported OJs.
Update when something operational changes (a command, a new crawler, a setup step).

## `docs/` (user-facing)
Documentation for users running or deploying the project:
- `docs/cli.md` — CLI usage reference
- `docs/web.md` — Web UI usage reference
- `docs/development.md` — the **development index**: setup, a routing table pointing into
  `docs/dev/`, and the ADR list. `@`-imported into `CLAUDE.md`, so keep it **short** — put
  detail in `docs/dev/`, not here.
- `docs/adr/` — Architectural decisions (see below)

## `docs/dev/` (internal conventions & reference)
The home for development conventions, schemas, templates, and gotchas — the knowledge you need
*while working* but that isn't a procedure. One file per domain:
- `docs/dev/crawlers.md` — crawler metadata schema, login types, return format, templates,
  HTML parsing, SSL, license header, archived-crawler rules
- `docs/dev/python.md` — import order, typing, error handling, dependencies (`uv add`)
- `docs/dev/testing.md` — pytest conventions, CI scope, page-route tests, markdown doc tests
- `docs/dev/e2e.md` — Playwright e2e / visual regression conventions
- `docs/dev/web.md` — FastAPI app, PDF internals, dev server, env vars, minimal-JS, CSS
- `docs/dev/hooks.md` — how project hooks work and the command-ban regex gotcha
- `docs/dev/deployment.md` — system fonts, `legacy.db`, PDF preview script

**When adding a fact here, add a routing-table row to `docs/development.md`** if the domain is
new, so the agent can find it. **Only document what's non-obvious** — if Claude can derive it by
reading the files, or it's enforced elsewhere (hook, test, linter), don't write it.

**When a well-written doc already covers a topic, reference it — don't replicate.** A skill or
another doc should point to the authoritative file plus any gotchas it doesn't capture.

## Skills (`.claude/skills/ojhunt-*/`)
**Workflows only** — a procedure the agent runs on demand. Currently:
- `ojhunt-implement` — end-to-end feature workflow (plan → implement → `full-check` → commit → fixups)
- `ojhunt-crawlers` — implement or debug a crawler (the procedure; reference is in `docs/dev/crawlers.md`)
- `ojhunt-commit` — commit workflow, conventions, ADR guidance
- `ojhunt-update-env` — this file

Update a skill when the *process* of doing something changes. Do **not** add convention/reference
facts to a skill — those go in `docs/dev/` (see above).

To add a new skill:
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

## Hooks (`.claude/hooks/` + `.claude/settings.json`)
Hard enforcement rules — things the agent must never do or must always do automatically.
Update when you need mechanical enforcement, not just reminders. See `docs/dev/hooks.md`.

## Commands (`.claude/commands/`)
Project-level slash commands that override global ones.
Create a command when the global equivalent needs project-specific context injected.

Skills can also embed `!`shell command`` substitutions and `$ARGUMENTS` directly,
so prefer extending an existing skill (e.g. **ojhunt-commit** owns `/commit`-style
behavior) over adding a parallel command file.

**Gotcha when documenting these features in prose:** the arguments placeholder
gets substituted on render even inside inline-code spans, so writing it
literally in skill prose erases it. Describe it ("the arguments placeholder")
rather than using the literal token, and reserve the literal token for the
section that should actually receive the user's input.

## `docs/adr/`
Significant architectural decisions and their rationale. See the **ojhunt-commit** skill for
when a decision warrants an ADR vs a commit message.

To add an ADR: create `docs/adr/NNNN-short-title.md` and add a one-line pointer to the ADR
list in `docs/development.md`.

## `CLAUDE.md`
Context that **every agent working on this project must know**, regardless of the task.
Update when something is so fundamental that any agent — without it — would make the wrong
call: project-wide invariants, hard constraints, or pointers to where documentation lives.

Keep entries minimal. `CLAUDE.md` is loaded into every conversation (and it `@`-imports
`docs/development.md`, so that index costs context on every invocation too — keep it lean). If
the knowledge is task-specific (e.g., "how to write a crawler"), put it in a skill or `docs/dev/`,
not here.

---

## If unsure which layer

- Operational fact (setup, command, structure) → README
- User-facing reference → `docs/cli.md` / `docs/web.md`
- Development convention, style, schema, or gotcha for a code area → `docs/dev/<area>.md`
  (add a routing-table row in `docs/development.md` if the domain is new)
- Workflow or process (a procedure run on demand) → `.claude/skills/ojhunt-*/`
- "Never do X" or "always do Y after Z" → **hook first** (see `docs/dev/hooks.md`); once
  hook-enforced, do NOT also add a doc/skill entry — the hook is the enforcement, a note just
  creates drift
- Project-level command override → `.claude/commands/`
- Significant architectural decision (multiple approaches considered, choice non-obvious from code) → `docs/adr/`
- Small tactical change → commit message intent (no doc needed)
- Project-wide invariant every agent must know, regardless of task → `CLAUDE.md`

---

## Capturing session learnings

When the user asks to capture session learnings (e.g. "what did we learn",
"update the docs"), follow this flow. The first two steps are silent — only
start outputting at step 3.

### Step 1 (silent): Reflect

Identify what was non-obvious, missing, or corrected that would help future
sessions:
- Workflows, conventions, or gotchas not yet documented
- Feedback or corrections from the user on how to approach work
- Project state changes: features shipped, decisions made, bugs resolved

### Step 2 (silent): Route changes

Use the routing rules above to decide where each learning belongs. Do not
route from memory — re-read the relevant section if unsure.

### Step 3: Show proposed changes

For each learning, show the target file and a concise diff. Keep additions
brief — `docs/development.md` is loaded into every prompt via the `@`-import.

### Step 4: Apply with approval

Ask the user which changes to apply. Only edit the files they approve.

**Important:** Documentation updates (`docs/dev/`, `docs/`, README, skills) are the
primary output — always propose at least one. Memory updates are optional
and secondary; never substitute memory for documentation.
