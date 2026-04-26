# CLAUDE.md

## Where to find documentation

- **Setup, usage, project structure** → [README.md](README.md)
- **Crawler contributor reference, deployment** → [docs/development.md](docs/development.md)
- **Architectural decisions** → [docs/adr/](docs/adr/)

## Project skills

All skills whose name starts with `ojhunt-` are project-specific workflows for this repo. Check their descriptions to find the right one for your task. Use the Skill tool to invoke them — do not read skill files directly as plain text.

### Growing these skills

If the user mentions a workflow, convention, or recurring pattern that isn't covered by an
existing sub-skill, ask them: *"Should I update an existing skill or create a new one for this?"*
Don't silently let project knowledge go undocumented.

### Self-correcting on repeated failures

When you fail on the same command or action more than once in a session, treat it as a
missing environment guardrail — not just a one-time mistake. After resolving the immediate
failure, propose a concrete fix: a hook (for "never do X"), a skill update (for "how to do
X correctly"), or a docs update (for reference material). Invoke the `ojhunt-update-env`
skill or raise it directly with the user.
