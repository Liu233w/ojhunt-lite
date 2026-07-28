---
name: ojhunt-commit
description: Git operations, commit conventions, and ADRs. Load when preparing to commit, writing agent/worker prompts that include git steps, planning a change that may warrant an ADR, or evaluating whether a design decision needs documentation.
allowed-tools: Read, Bash(git add:*), Bash(git status:*), Bash(git diff:*), Bash(git log:*), Bash(git branch:*), Bash(git commit:*)
---

# Running a commit

When invoked to perform a commit (e.g. via `/ojhunt-commit` or when the user
asks to commit), use this flow. The conventions below apply.

## User instruction

$ARGUMENTS

## Task

Create a single git commit using the conventions below, based on the user
instruction and the current changes.

**First, gather current state yourself** by running these at commit time, with `-C` pinned to
this repo's absolute root:

```bash
git -C /Users/shuminliu/source/personal/ojhunt-lite status --short         # staged/unstaged
git -C /Users/shuminliu/source/personal/ojhunt-lite branch --show-current  # current branch
git -C /Users/shuminliu/source/personal/ojhunt-lite log --oneline -10      # recent subjects, to match style
```

**Why `-C` and not bare `git`:** if the session added sibling repos and any command `cd`'d into
one, the shell cwd has drifted and bare `git` silently reports *another repo's* state — a valid
`git status` and `git log` of the wrong project. `nothing to commit, working tree clean` then
reads as a clean repo, so the commit is skipped while real changes sit unstaged. Nothing in the
output signals the error. `git -C "$(git rev-parse --show-toplevel)"` does **not** fix this — it
resolves against the drifted cwd too, so the path must be literal.

If the user instruction is empty, infer intent from the diff. If intent is
unclear, ask before committing.

If `git status` reported config errors (e.g. missing `user.email`), surface
that to the user and stop — do NOT silently set git config.

Stage and commit in a single message with parallel tool calls. Do not push.

### Squash workflow (when instruction contains "squash with")

The preferred workflow is **fixup-first, squash-last** — never squash immediately:

1. **Create fixup! commit(s)**: Stage the relevant files and run
   `git commit --fixup=<sha>` (requires `dangerouslyDisableSandbox: true`).
   If the commit message also needs changing, additionally create an `amend!`
   commit — see "Rewording a commit message" below.
   Show the user `git log --oneline -5` so they can review.
2. **Stop and wait** for the user to confirm they are happy. Do not proceed to
   rebase without explicit user approval.
3. **Squash**: Once the user is satisfied, run
   `GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash <target-sha>^`
   (requires `dangerouslyDisableSandbox: true`). `-i` is required because
   `--autosquash` only works in interactive mode; `GIT_SEQUENCE_EDITOR=true`
   suppresses the editor so no prompt appears.

### Rewording a commit message

Use `git commit --fixup=amend:<sha>` (git ≥ 2.32). **Not**
`--fixup=reword:<sha>` — autosquash does not recognise the `reword!` prefix and
leaves a stray commit behind. Do **not** combine `-m` with `--fixup=amend:`;
git rejects it.

1. `git show <sha> --format="%B" --no-patch` — read the original message.
2. Write the new message to `.doit/commit-msg.txt`. The subject must be
   `amend! <exact original subject>`; the body becomes the replacement message
   after autosquash.
3. `GIT_EDITOR="cp .doit/commit-msg.txt" git commit --allow-empty --fixup=amend:<sha>`
   (requires `dangerouslyDisableSandbox: true`).
4. `git show <new-sha> --format="%B" --no-patch` — verify before squashing.

### Scoping a fixup

`git commit --fixup` commits **the index** — stage the paths that belong to that target
and leave everything else unstaged. Never `git stash` to scope a commit: it reverts
unstaged work, including edits the user made themselves.

`git add -p` is unavailable (no interactive flags). To split one file's changes across
two fixups, save the finished version first, write the intermediate content, stage it,
commit, then restore:

```bash
cp <path> .doit/split.final    # save FIRST — nothing else holds these hunks
python3 -c "..."               # rewrite <path>: HEAD content + only target A's hunks
git add <path> && git commit --fixup=<sha-A>
cp .doit/split.final <path>    # restore; the remaining hunks go to the next fixup
```

`.doit/` is gitignored and inside the repo, so it survives the sandbox bypass that git
writes need — `$TMPDIR` is unset there.

### Verifying a squash

A `fixup!` diff is computed against the **final** tree but replays at its target commit, so
expect conflicts wherever that commit's surroundings differ — and expect a mis-scoped hunk to
land in a commit that cannot work yet. Both are invisible until the rebase runs.

Rehearse on a throwaway branch, never on the user's:

```bash
git checkout -b scratch/squash-test
GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash <base>^   # resolve era-correctly
git diff <branch> scratch/squash-test                          # gate: must be empty
for sha in $(git rev-list --reverse main..HEAD); do
  git checkout -q "$sha" && ./doit.sh lint && ./doit.sh test-unit   # each commit alone
done
```

To repair a commit mid-history, stop on it:
`GIT_SEQUENCE_EDITOR='sed -i "" -e "s/^pick <sha>/edit <sha>/"' git rebase -i main`, amend,
`git rebase --continue`. Then move the branch with `git reset --hard scratch/squash-test` —
`git branch -f` refuses while the branch is checked out.

---

# Commit conventions

## Git operations require sandbox bypass

Always use `dangerouslyDisableSandbox: true` for any git write operation (add, commit, reset,
rebase, etc.) — the sandbox blocks writes to `.git/`.

Git **read** operations (`git log`, `git status`, `git diff`, `git branch`, `git show`) do
NOT need sandbox bypass — run them in the sandbox like any other read command.

## Do not push to remote

Commit locally; the user handles push and PR creation.

## Commit hygiene

- **pyproject.toml and uv.lock must be in the same commit.** If they end up in separate
  commits during a session, squash them via interactive rebase before the session ends.
- **Corrections go in new fixup commits, not amends.** Use `git commit --fixup=<sha>` so the
  user can review what changed. Follow the squash workflow above — create the fixup!, wait
  for approval, then `GIT_SEQUENCE_EDITOR=true git rebase -i --autosquash <base-sha>`.
- When UI/nav elements change, scan `tests/e2e/` for selectors referencing the old element
  and include the test fix in the same commit.

## Closing GitHub issues

When a commit fixes a GitHub issue, include `Resolves #N` on its own line in the
commit body. GitHub will auto-close the issue when the commit lands on the default
branch.

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
