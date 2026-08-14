"""Tests for the comment-above-assert lint rule (lint/rules/comment_above_assert.py).

The edge cases are the point of this file. A trailing comment and an own-line
comment are indistinguishable in the parse tree, so every case below pins which
line the rule blames — the earlier YAML version of this rule reported three
different outcomes for the same violation depending on what followed it.
"""

import importlib.util
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parents[2]
RULE_PATH = REPO_ROOT / "lint" / "rules" / "comment_above_assert.py"


def _rule():
    """Import the rule, which lives outside the package (mirrors docs_test.py)."""
    spec = importlib.util.spec_from_file_location("comment_above_assert", RULE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rule = _rule()


def _lines(source: str) -> list[int]:
    return [f.line for f in rule.find_violations(source, Path("probe.py"))]


# ---------------------------------------------------------------------------
# Own-line comment above an assert — the case the rule exists for
# ---------------------------------------------------------------------------


def test_own_line_comment_mid_body():
    source = """
def test_x():
    result = query()
    # the crawler reports only an AC count
    assert result["submissions"] == result["solved"]
"""
    assert _lines(source) == [5], "the assert below an own-line comment is flagged"


def test_own_line_comment_as_first_statement():
    source = """
def test_x():
    # the crawler reports only an AC count
    assert result["submissions"] == result["solved"]
"""
    assert _lines(source) == [4], (
        "a comment before the first statement attaches to the def, not the body — "
        "the rule must still reach the assert inside the block"
    )


def test_own_line_comment_inside_a_method():
    source = """
class TestThing:
    def test_x(self):
        # explanation
        assert value == 1
"""
    assert _lines(source) == [5], "nesting depth must not matter"


def test_comment_block_reports_once():
    source = """
def test_x():
    imported = discover()
    # first line of the explanation
    # second line of the explanation
    assert imported >= len(registry)
"""
    assert _lines(source) == [6], "a multi-line comment block yields one finding"


def test_flagged_even_when_the_assert_has_a_message():
    source = """
def test_x():
    value = compute()
    # this says something the message does not
    assert value == 1, "value must be one"
"""
    assert _lines(source) == [5], "a message does not excuse a comment beside it"


# ---------------------------------------------------------------------------
# Trailing comments — reported on their own line, never on the one below
# ---------------------------------------------------------------------------


def test_trailing_comment_on_an_assert_is_blamed_on_that_assert():
    source = """
def test_x():
    result = query()
    assert result["solved"] > 0  # the judge under-reports by one
    assert result["submissions"] > 0
"""
    assert _lines(source) == [4], (
        "line 4 carries the comment; line 5 is innocent and must not be blamed"
    )


@pytest.mark.parametrize(
    ("what_follows", "description"),
    [
        ("", "nothing — the assert ends the body"),
        ("    cleanup()\n", "a statement that is not an assert"),
        ("    assert other > 0\n", "another assert"),
    ],
)
def test_trailing_comment_is_caught_whatever_follows(what_follows, description):
    source = f"""
def test_x():
    result = query()
    assert result["solved"] > 0  # the judge under-reports by one
{what_follows}"""
    assert _lines(source) == [4], f"must be caught when followed by {description}"


# ---------------------------------------------------------------------------
# Cases that must stay silent
# ---------------------------------------------------------------------------


def test_trailing_comment_on_a_non_assert_is_ignored():
    source = """
def test_x():
    reset_env()
    config = load_config()  # defaults come from .env
    assert config.debug is False
"""
    assert _lines(source) == [], (
        "the comment explains the assignment it sits on, not the assert below it"
    )


def test_comment_above_a_non_assert_is_ignored():
    source = """
def test_x():
    # build the client once
    client = TestClient(app)
    assert client is not None
"""
    assert _lines(source) == [], "the comment explains the statement it sits above"


def test_assert_with_a_message_and_no_comment_is_ignored():
    source = """
def test_x():
    result = query()
    assert result["solved"] > 0, "the test user has solved something"
"""
    assert _lines(source) == []


@pytest.mark.parametrize(
    "pragma",
    ["# type: ignore[arg-type]", "# noqa: E501", "# fmt: skip", "# NOQA"],
)
def test_tool_pragmas_are_ignored(pragma):
    source = f"""
def test_x():
    result = query()
    assert isinstance(result, Mapping)  {pragma}
"""
    assert _lines(source) == [], (
        f"{pragma} is addressed to another tool, so it cannot move into the message"
    )


def test_trailing_comment_at_the_end_of_a_body_is_ignored():
    source = """
def test_x():
    assert value == 1
    # a note that trails the whole body
"""
    assert _lines(source) == [], "no statement follows, so nothing is explained"


# ---------------------------------------------------------------------------
# Scope — the hook hands the rule whatever file just changed
# ---------------------------------------------------------------------------


def test_scope_covers_this_test_file():
    covered = {path.resolve() for path in rule.scoped_files()}
    assert Path(__file__).resolve() in covered, (
        "a named file inside SCOPE must reach the scanner"
    )


def test_a_named_file_outside_the_scope_is_skipped(tmp_path):
    stray = tmp_path / "stray_test.py"
    stray.write_text(
        "def test_x():\n    # explanation\n    assert value == 1\n", encoding="utf-8"
    )
    assert rule.find_violations(stray.read_text(encoding="utf-8"), stray), (
        "the probe must violate the rule, or the next assertion proves nothing"
    )
    assert rule.main([str(stray)]) == 0, (
        "only SCOPE decides what the rule covers — otherwise the hook blocks on "
        "files ./doit.sh lint never looks at"
    )


# ---------------------------------------------------------------------------
# The rule holds over the repository it guards
# ---------------------------------------------------------------------------


def test_repository_is_clean():
    findings = rule.scan(sorted(REPO_ROOT.glob(rule.SCOPE)))
    assert findings == [], "\n".join(str(f) for f in findings)
