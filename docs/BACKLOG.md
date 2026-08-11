# Backlog

Follow-ups that are real but were out of scope for the change that found them. Each entry says
what is wrong, why it was left, and where to start. Delete an entry when it ships.

## Crawlers swallow their own error messages

20 of the 33 crawlers end `query` with `except Exception: raise RuntimeError("Error while
parsing")`, which catches the more specific `RuntimeError(f"Server Response Error: {status}")`
raised inside the same `try`. An upstream outage is therefore reported as a parse failure and the
status code is lost from the CLI, the web app and the `/crawlers` availability check.

`except ValueError: raise` is already there; the fix is `except RuntimeError: raise` beside it.

Affected: `aizu`, `codechef`, `codewars`, `csu`, `darkbzoj`, `hdu`, `hust`, `loj`, `luogu`,
`nbut`, `nit`, `nowcoder`, `ojuz`, `poj`, `sdutoj`, `timus`, `toph`, `uoj`, `uva`, `vjudge`.

Left alone so far because it changes error behaviour across a third of the crawlers, which
deserves its own change rather than a drive-by in a documentation branch.

## EOlymp's `test_username` no longer resolves

`"vjudge5"` returns no members from the GraphQL API, so `./doit.sh test-crawler eolymp` fails 2 of
4 tests (on `main` too — it is not a regression) and the `/crawlers` page reports EOlymp offline.
Pick a live user and update `__crawler_meta__["test_username"]` in `src/ojhunt/crawlers/eolymp.py`.

## 14 crawlers have no `description`

`help(crawlers["<name>"])` and the `docs/library.md` table therefore give no hint about what to
type as a username — which matters more now that the generated help derives everything from
metadata ([ADR 0014](adr/0014-generated-crawler-help.md)).

Missing: `aizu`, `codechef`, `csu`, `darkbzoj`, `hdu`, `lightoj`, `loj`, `nbut`, `nit`, `poj`,
`sdutoj`, `timus`, `uoj`, `uva`.

Each one needs a look at the judge to say whether it wants a handle, a numeric id, or is
case-sensitive, so this is per-judge research rather than a mechanical pass.

## `/llms.txt` does not mention the Python library

[ADR 0002](adr/0002-agent-support-via-llmstxt.md) makes `/llms.txt` the guide for agents. It covers
the HTTP API and the CLI but not `from ojhunt.crawlers import crawlers`, even though the README and
the about page now point there. Add a short section pointing at `docs/library.md` in
`src/ojhunt/web/templates/llms.txt.jinja`.

## Login-type prose is written out in four registers

`LoginType`'s docstring, `_login_paragraph()` in `src/ojhunt/crawlers/_help.py`, the
`ojhunt.crawlers` package docstring and `docs/dev/crawlers.md` each phrase the same three facts for
a different audience, and `docs/library.md` renders two of them on one page. A new `LoginType`
member trips an assert rather than emitting the wrong text, so nothing lies silently — but four
texts still need editing by hand.

Option: put `explanation` and `credential_args` next to `LoginType.label` and generate the
paragraphs from there.

## Eolymp interpolates the username into its GraphQL query text

`src/ojhunt/crawlers/eolymp.py` builds its query with `%`-formatting and escapes the username by
hand (`username.replace('"', '\\"')`). GraphQL variables are the right mechanism: pass the query
with a `$search` parameter and send the value in the request's `variables` object. That removes
the manual escaping and the `# noqa: UP031`, because no brace has to survive a format call.

Left alone because it changes the request payload, so it needs its own network verification
against api.eolymp.com rather than a drive-by in a lint sweep.
