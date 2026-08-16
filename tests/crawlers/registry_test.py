"""Unit tests for the ojhunt.crawlers registry attribute (see ADR 0013)."""

import os
import subprocess
import sys

import pytest

import ojhunt.crawlers
from ojhunt.core.models import CrawlerRegistry
from ojhunt.crawlers import crawlers as crawler_registry


def _crawlers_imported_by(import_line: str) -> int:
    """Count crawler modules a fresh interpreter ends up with.

    Fresh, because this test session has already imported the whole registry.
    """
    stdout = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys\n"
                f"{import_line}\n"
                "print(len([m for m in sys.modules"
                "           if m.startswith('ojhunt.crawlers.')"
                "           and not m.rpartition('.')[2].startswith('_')]))"
            ),
        ],
        capture_output=True,
        text=True,
        check=True,
        # pytest's `pythonpath = ["src"]` only touches this process, so hand the
        # child our own path — it need not have ojhunt pip-installed.
        env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
    ).stdout
    return int(stdout)


def test_crawlers_is_a_registry_of_every_crawler():
    assert isinstance(crawler_registry, CrawlerRegistry)
    assert "codeforces" in crawler_registry


def test_repeated_access_returns_the_same_registry():
    assert ojhunt.crawlers.crawlers is crawler_registry


def test_unknown_module_attribute_raises_attribute_error():
    with pytest.raises(AttributeError, match="has no attribute 'nope'"):
        _ = ojhunt.crawlers.nope


def test_dir_advertises_crawlers():
    assert "crawlers" in dir(ojhunt.crawlers)


def test_importing_one_crawler_does_not_discover_the_rest():
    """Copying a single crawler out stays cheap: no other crawler is imported."""
    assert _crawlers_imported_by("from ojhunt.crawlers.codeforces import query") == 1


def test_accessing_crawlers_discovers_them_all():
    imported = _crawlers_imported_by("from ojhunt.crawlers import crawlers")

    assert imported >= len(crawler_registry), (
        "_discover() imports every module in the package, and a module need not "
        "carry __crawler_meta__ to be imported — hence >=, not =="
    )
