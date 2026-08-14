"""Lint rule: the explanation next to an assert belongs in its message.

A comment is invisible when the assertion fails; a message prints with the
failure. See `.claude/rules/python.md`.

This rule is Python rather than YAML because it needs source position. A
trailing comment and an own-line comment are the same shape in the parse tree —
both are sibling nodes between two statements — so only line and column tell
them apart. Getting that wrong reports the violation on the innocent line below
it, or misses it entirely when no assert follows.

Run over the default scope, or over named files. A named file outside the scope
is skipped, so the edit-time hook can pass whatever file just changed and still
report exactly what CI reports:

    uv run python lint/rules/comment_above_assert.py
    uv run python lint/rules/comment_above_assert.py tests/web/api_test.py
"""

import sys
from dataclasses import dataclass
from pathlib import Path

from ast_grep_py import SgNode, SgRoot

RULE_ID = "comment-above-assert"
MESSAGE = "move the explanation into the assert message"

NOTE = """\
A comment is silent when the assert fails; a message prints.

    # the crawler reports only an AC count
    assert result["submissions"] == result["solved"]

    assert result["submissions"] == result["solved"], (
        "the crawler reports only an AC count"
    )
"""

# Files the rule applies to, relative to the repository root.
SCOPE = "tests/**/*.py"

# A tool directive is addressed to another program, so "move it into the assert
# message" is not advice anybody can take.
PRAGMAS = ("# type:", "# noqa", "# pragma:", "# fmt:", "# ruff:")


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    comment: str

    def __str__(self) -> str:
        return f"{self.path}:{self.line}: {RULE_ID}: {MESSAGE}\n    {self.comment}"


def _trailing_statement(comment: SgNode) -> SgNode | None:
    """The statement this comment trails, or None when it sits on its own line."""
    previous = comment.prev()
    if previous is None:
        return None
    if previous.range().end.line != comment.range().start.line:
        return None
    return previous


def _statement_below(comment: SgNode) -> SgNode | None:
    """The statement this comment sits above.

    A comment before the *first* statement of a body attaches to the enclosing
    definition instead of the body, so the next sibling is the block itself.
    """
    below = comment.next()
    if below is not None and below.kind() == "block":
        children = below.children()
        return children[0] if children else None
    return below


def find_violations(source: str, path: Path) -> list[Finding]:
    """Every assert in `source` whose explanation sits in a comment."""
    findings = []
    for comment in SgRoot(source, "python").root().find_all(kind="comment"):
        text = comment.text().strip()
        if text.lower().startswith(PRAGMAS):
            continue
        trailed = _trailing_statement(comment)
        target = trailed if trailed is not None else _statement_below(comment)
        if target is None or target.kind() != "assert_statement":
            continue
        findings.append(Finding(path, target.range().start.line + 1, text))
    return findings


def scan(paths: list[Path]) -> list[Finding]:
    findings = []
    for path in sorted(paths):
        findings.extend(find_violations(path.read_text(encoding="utf-8"), path))
    return findings


def scoped_files() -> list[Path]:
    """Every file in SCOPE. The rule owns its scope, not its callers.

    The hook passes the single file that just changed, whatever it is. Filtering
    here is what keeps the hook and `./doit.sh lint` from disagreeing about
    which files the rule covers.
    """
    return sorted(Path(__file__).parents[2].glob(SCOPE))


def main(argv: list[str]) -> int:
    scope = scoped_files()
    if argv:
        covered = {path.resolve() for path in scope}
        paths = [path for path in map(Path, argv) if path.resolve() in covered]
    else:
        paths = scope
    findings = scan(paths)
    for finding in findings:
        print(finding, file=sys.stderr)
    if findings:
        print(f"\n{NOTE}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
