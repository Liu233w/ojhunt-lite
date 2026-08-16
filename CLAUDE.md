# CLAUDE.md

## Common commands

Run `./doit.sh help` for the full list. Key tasks:

- `./doit.sh lint` — ruff plus the project's own rules in `lint/rules/`
- `./doit.sh test-unit` — unit tests (fast, no network, no browser)
- `./doit.sh test-e2e` — browser e2e tests, excluding visual (starts dev server if needed)
- `./doit.sh test-crawler <name>` — network tests for one crawler (e.g. `codeforces`)
- `./doit.sh test-visual` / `update-snapshots` — visual regression tests
- `./doit.sh full-check` — lint + rule tests + all tests (unit, e2e, visual); starts & stops the server
- `./doit.sh start` / `kill` / `status` / `logs` — dev server lifecycle

When a `lint*`/`test-*`/`full-check` task fails, its full output is already saved to `.doit/<task>.log` — **read that log** (e.g. `grep -nE 'FAILED|error' .doit/test-unit.log`) instead of re-running the task with `| tail`/`| grep`. `full-check` runs each step as its own task, so read the specific step's log (`.doit/test-e2e.log`, `.doit/test-visual.log`, …); its own stdout is only a short `full-check PASSED/FAILED` summary, so don't pipe it through `| tail` either.

## Where to find documentation

- **Setup, usage, project structure** → [README.md](README.md)
- **Development conventions & reference** → the index in [docs/development.md](docs/development.md)
- **Architectural decisions** → [docs/adr/](docs/adr/)

Code conventions load by themselves: `.claude/rules/*.md` carry `paths:` frontmatter, so the
Python, test, e2e, web-layer, docs and hook rules enter context when you open a matching file.
The development index below routes what no file pattern can trigger.

@docs/development.md

## Project skills

Skills hold only genuine **workflows** — a procedure you run on demand. Invoke via the Skill
tool (don't read skill files as plain text):

- **ojhunt-implement** — end-to-end feature workflow (plan → implement → full-check → commit)
- **ojhunt-crawlers** — implement or debug a crawler
- **ojhunt-commit** — commit, commit conventions, ADRs
- **ojhunt-update-env** — decide where a new piece of knowledge belongs

**Conventions and reference** are *not* skills. A convention tied to editing a kind of file
lives in `.claude/rules/*.md` and loads on its own. Crawler reference and ops knowledge stay in
`docs/dev/*.md`, routed by the table in `docs/development.md` (imported above).

### Growing project knowledge

If the user mentions a workflow, convention, or recurring pattern that isn't captured yet,
route it: a **workflow/procedure** → a skill; a **convention tied to a kind of file** →
`.claude/rules/*.md` with `paths:` frontmatter; a **fact no file pattern can trigger** →
`docs/dev/*.md` plus a routing-table row; a **cheap deterministic check** → a hook. Ask the
user before adding, and see the **ojhunt-update-env** skill for the full routing map. Don't
silently let project knowledge go undocumented.

### Self-correcting on repeated failures

When you fail on the same command or action more than once in a session, treat it as a
missing environment guardrail — not just a one-time mistake. After resolving the immediate
failure, propose a concrete fix: a hook (for "never do X"), a skill update (for "how to do
X correctly"), or a docs update (for reference material). Invoke the `ojhunt-update-env`
skill or raise it directly with the user.
