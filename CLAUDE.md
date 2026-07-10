# CLAUDE.md

## Common commands

Run `./doit.sh help` for the full list. Key tasks:

- `./doit.sh lint` — ruff linter
- `./doit.sh test-unit` — unit tests (fast, no network, no browser)
- `./doit.sh test-e2e` — browser e2e tests, excluding visual (starts dev server if needed)
- `./doit.sh test-crawler <name>` — network tests for one crawler (e.g. `codeforces`)
- `./doit.sh test-visual` / `update-snapshots` — visual regression tests
- `./doit.sh start` / `kill` / `status` / `logs` — dev server lifecycle

When a `lint`/`test-*` task fails, its full output is already saved to `.doit/<task>.log` — **read that log** (e.g. `grep -nE 'FAILED|error' .doit/test-unit.log`) instead of re-running the task with `| tail`/`| grep`.

## Where to find documentation

- **Setup, usage, project structure** → [README.md](README.md)
- **Development conventions & reference** → the index in [docs/development.md](docs/development.md)
- **Architectural decisions** → [docs/adr/](docs/adr/)

The development index is imported below so its routing table — "working on X → read
`docs/dev/X.md`" — is always in context. Follow it to the right reference before starting work.

@docs/development.md

## Project skills

Skills hold only genuine **workflows** — a procedure you run on demand. Invoke via the Skill
tool (don't read skill files as plain text):

- **ojhunt-crawlers** — implement or debug a crawler
- **ojhunt-commit** — commit, commit conventions, ADRs
- **ojhunt-update-env** — decide where a new piece of knowledge belongs

**Conventions and reference** (Python style, tests, e2e, web layer, hooks, crawler reference,
deployment) are *not* skills — they live in `docs/dev/*.md`, indexed by the routing table in
`docs/development.md` (imported above). Read the matching doc before working in that area
rather than relying on a skill to trigger.

### Growing project knowledge

If the user mentions a workflow, convention, or recurring pattern that isn't captured yet,
route it: a **workflow/procedure** → a skill; a **convention or reference fact** →
`docs/dev/*.md` (and add a row to the routing table in `docs/development.md`); a **hard rule**
→ a hook. Ask the user before adding, and see the **ojhunt-update-env** skill for the full
routing map. Don't silently let project knowledge go undocumented.

### Self-correcting on repeated failures

When you fail on the same command or action more than once in a session, treat it as a
missing environment guardrail — not just a one-time mistake. After resolving the immediate
failure, propose a concrete fix: a hook (for "never do X"), a skill update (for "how to do
X correctly"), or a docs update (for reference material). Invoke the `ojhunt-update-env`
skill or raise it directly with the user.
