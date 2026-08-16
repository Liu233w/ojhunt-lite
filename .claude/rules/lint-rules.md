---
paths:
  - "lint/**"
  - "tests/lint/**"
---

# Project lint rules

Rules the project enforces on its own code, beyond what ruff covers. They live in
`lint/rules/`, run from `./doit.sh lint`, and run again from the edit-time hook on the single
file that changed — one definition, so the hook cannot drift from CI.

```bash
./doit.sh lint          # every rule over the whole repo
./doit.sh lint-rules    # the rules' own tests
uv run python lint/rules/<rule>.py <file>...   # one rule, one file
```

## When a convention earns a rule

A rule pays for itself when the convention is objective and somebody will break it without
noticing. If judging a case needs context the parser does not have, leave the convention in
`.claude/rules/*.md` as prose — a rule that misfires teaches everyone to ignore it.

Before writing prose, check whether a rule can assert it instead: a rule fails when somebody
breaks the convention, a paragraph does not.

## Pick the form

| Form | Use when | Tests |
|------|----------|-------|
| `lint/rules/<id>.yml` | The match is purely structural — a node shape, nesting, a pattern | `lint/rule-tests/<id>-test.yml` |
| `lint/rules/<id>.py` | The match needs source position, file paths, or cross-file state | `tests/lint/<id>_test.py` |

Position is the usual reason to reach for Python. A YAML rule sees the parse tree, where a
trailing comment and an own-line comment are the same shape; only line and column separate
them. `comment_above_assert.py` exists for exactly that reason — its docstring says so.

A Python rule is a script: `find_violations(source, path)` for tests to call, and a `main()`
that takes file arguments, prints to stderr and returns 1 on a finding. Copy the shape from
`lint/rules/comment_above_assert.py`.

For ast-grep's rule syntax, node kinds and relational operators, query the ast-grep
documentation through Context7 rather than looking for it here.

## Every rule ships with its tests

`tests/lint/rules_are_tested_test.py` fails when a rule has no test file, so this is not a
convention you can forget. Cover the edge cases, not just the happy path — for anything
position-sensitive, pin **which line** each case is blamed on, and include the cases that must
stay silent.
