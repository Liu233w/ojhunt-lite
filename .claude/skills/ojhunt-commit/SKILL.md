---
name: ojhunt-commit
description: Git operations, commit conventions, and ADRs. Load when preparing to commit, writing agent/worker prompts that include git steps, planning a change that may warrant an ADR, or evaluating whether a design decision needs documentation.
---

# Commit conventions

## Git operations require sandbox bypass

Always use `dangerouslyDisableSandbox: true` for any git write operation (add, commit, reset,
rebase, etc.) — the sandbox blocks writes to `.git/`.

## Do not push to remote

Commit locally; the user handles push and PR creation.

## Commit hygiene

- **pyproject.toml and uv.lock must be in the same commit.** If they end up in separate
  commits during a session, squash them via interactive rebase before the session ends.
- **Corrections go in new fixup commits, not amends.** Use `git commit --fixup=<sha>` so the
  user can review what changed. To squash fixups: `GIT_SEQUENCE_EDITOR=true git rebase -i
  --autosquash <base-sha>` (requires `dangerouslyDisableSandbox: true`).
- When UI/nav elements change, scan `tests/e2e/` for selectors referencing the old element
  and include the test fix in the same commit.

## Commit messages should capture intent

The diff already shows *what* changed. The message should explain *why* — the motivation,
the problem being solved, or the trade-off made. This matters especially for small tactical
changes, because `git log` and `git blame` are the only place their intent is recorded.

If unsure of the user's intent, ask before committing.

## When to write an ADR

**Plan mode** — the user arrives with a concrete plan; implement it. No ADR needed unless
the plan itself involves a significant design decision.

**Discussion mode** — the user is exploring options. When a decision crystallises from
open-ended back-and-forth, write the ADR *before* implementing.

A decision warrants an ADR if:
- Multiple approaches were considered and one was rejected
- The decision won't be obvious from reading the code
- Future contributors might be tempted to reverse it without understanding the context

Small tactical changes do **not** warrant an ADR — their intent belongs in the commit message.

## How to write an ADR

Create `docs/adr/NNNN-short-title.md` and add a one-line pointer to the ADR list in
`docs/development.md`. Status: `Proposed`, `Accepted`, `Deprecated`, or `Superseded`.

Write the ADR *before* starting implementation. If implementation reveals the decision needs
to change, update the ADR first.
