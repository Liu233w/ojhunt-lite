---
name: ojhunt-update-env
description: Project environment structure — where each type of knowledge belongs across docs/, skills, hooks, commands, and CLAUDE.md. Load whenever the task involves documentation, creating or updating skills, adding hooks or commands, updating CLAUDE.md, deciding where a new piece of knowledge should live, or capturing session learnings.
---

# Where knowledge lives in this project's environment

**Single source of truth:** Each piece of knowledge lives in exactly one layer. When adding
documentation, point to the authoritative source — don't inline definitions that already exist
elsewhere. Duplication causes drift.

**Route between sibling skills, don't append to the most-used one:** When adding to a skill,
name what the new section is *about* in one phrase and check whether a sibling `ojhunt-*`
skill owns that phrase. The dominant skill tends to absorb content from neighbouring domains
because authors append where they're already editing — resist the easy append.

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

**When a well-written doc file already covers the topic, the skill should be a thin pointer
to that file plus any gotchas the doc doesn't capture. Don't replicate discoverable content.**

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
Update when you need mechanical enforcement, not just reminders. See **ojhunt-hooks** skill.

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

Keep entries minimal. `CLAUDE.md` is loaded into every conversation; bloat here costs context
on every invocation. If the knowledge is task-specific (e.g., "how to write a crawler"),
put it in a skill, not here.

---

## If unsure which layer

- Operational fact (setup, command, structure) → README
- User-facing reference → `docs/`
- Crawler contributor reference → `docs/development.md`
- Workflow or process → `.claude/skills/ojhunt-*/`
- "Never do X" or "always do Y after Z" → **hook first** (see **ojhunt-hooks** skill); once hook-enforced, do NOT also add a skill entry — the hook is the enforcement, a skill note just creates drift
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
brief — skill files are loaded into every prompt.

### Step 4: Apply with approval

Ask the user which changes to apply. Only edit the files they approve.

**Important:** Documentation updates (skill files, README, `docs/`) are the
primary output — always propose at least one. Memory updates are optional
and secondary; never substitute memory for documentation.
