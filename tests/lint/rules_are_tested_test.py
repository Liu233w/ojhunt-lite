"""Every lint rule must ship with its own tests.

Discovered from the directory rather than listed here: a hardcoded list would go
stale on exactly the rule nobody remembered to add to it.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).parents[2]
RULES_DIR = REPO_ROOT / "lint" / "rules"
YAML_TESTS_DIR = REPO_ROOT / "lint" / "rule-tests"
PYTHON_TESTS_DIR = Path(__file__).parent


def test_every_python_rule_has_a_pytest_file():
    missing = [
        rule.name
        for rule in sorted(RULES_DIR.glob("*.py"))
        if not (PYTHON_TESTS_DIR / f"{rule.stem}_test.py").exists()
    ]
    assert not missing, (
        f"{missing} have no tests — add tests/lint/<rule>_test.py covering which "
        "line each case is blamed on"
    )


def test_every_yaml_rule_has_an_ast_grep_test_file():
    missing = [
        rule.name
        for rule in sorted(RULES_DIR.glob("*.yml"))
        if not (YAML_TESTS_DIR / f"{rule.stem}-test.yml").exists()
    ]
    assert not missing, (
        f"{missing} have no tests — add lint/rule-tests/<rule>-test.yml with valid "
        "and invalid cases, then run ./doit.sh lint-rules"
    )


def test_at_least_one_rule_exists():
    rules = list(RULES_DIR.glob("*.py")) + list(RULES_DIR.glob("*.yml"))
    assert rules, "lint/rules/ is empty — did a rule get deleted by accident?"
