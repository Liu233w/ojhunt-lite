---
name: ojhunt-implement
description: End-to-end feature workflow — plan (in plan mode) → approval → implement → ./doit.sh full-check → commit → fixups. Load whenever the user invokes /ojhunt-implement or asks to implement/build/add a feature and wants the full plan-implement-test-commit loop rather than a one-off edit.
---

# Implementing a feature

This skill is the **procedure** for taking a feature from request to committed code.
It only orchestrates — the *conventions* for each area (Python style, tests, web
layer, crawlers, …) live in `docs/dev/*.md`, indexed by the routing table in
`docs/development.md`. Read the matching doc **before** you write code in that area.

## User request

$ARGUMENTS

## Workflow

Work through these in order. Each step exists to keep a fast feedback loop and to
make the change reviewable — don't skip ahead.

1. **Plan first, and get approval.** If you are not already in plan mode, enter it
   (EnterPlanMode) — planning before editing is what lets the user redirect the
   approach cheaply, before any code is written. Explore the relevant code, read the
   matching `docs/dev/*.md`, then draft a concrete plan and present it for approval
   (ExitPlanMode). **Do not implement until the user approves** — the request above
   is a starting point, not a mandate to build immediately.

2. **Implement the approved plan.** Follow the conventions in the `docs/dev/` file(s)
   for the area you're touching. Keep the change scoped to what was approved.

3. **Verify with `./doit.sh full-check`.** This starts the dev server, runs lint +
   unit + e2e + visual tests, then stops the server — the same gate you'd want green
   before committing. When it fails, **read `.doit/<task>.log`** (e.g.
   `grep -nE 'FAILED|error' .doit/test-e2e.log`) rather than re-running with
   `| tail`/`| grep`; the full output is already captured there. Fix and re-run until
   green. If a UI change *legitimately* shifts a visual snapshot, regenerate it with
   `./doit.sh update-snapshots` and commit the updated snapshot alongside the change.

4. **Commit.** Invoke the **ojhunt-commit** skill to create the commit(s) using the
   project's conventions (intent-capturing messages, `Resolves #N`, ADRs when a
   decision warrants one).

5. **Handle follow-up suggestions as fixups.** When the user has more changes after
   the commit, implement them and record each as a `git commit --fixup=<sha>` commit
   — never `git commit --amend` — so the user can review what changed. Follow the
   fixup-first, squash-last workflow in the **ojhunt-commit** skill: create the
   fixup!, wait for approval, then autosquash.
