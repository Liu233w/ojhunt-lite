from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image
from playwright.sync_api import Page

from e2e.helpers import BASE_URL

_SNAPSHOTS_DIR = Path(__file__).parent / "__snapshots__"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--update-snapshots",
        action="store_true",
        default=False,
        help="Overwrite stored visual regression snapshots with current screenshots.",
    )


@pytest.fixture
def assert_snapshot(pytestconfig: pytest.Config):
    """Fixture for pixel-level screenshot comparison.

    Usage::

        def test_visual(page, assert_snapshot):
            page.goto("/")
            assert_snapshot(page.screenshot(full_page=True), name="page.png")

    Run with ``--update-snapshots`` to create or overwrite baselines.
    Snapshots are stored in ``tests/e2e/__snapshots__/``.
    """
    update: bool = pytestconfig.getoption("--update-snapshots")

    def _assert(screenshot: bytes, *, name: str) -> None:
        path = _SNAPSHOTS_DIR / name
        if update or not path.exists():
            _SNAPSHOTS_DIR.mkdir(parents=True, exist_ok=True)
            path.write_bytes(screenshot)
            action = "updated" if update else "created"
            pytest.skip(f"snapshot {action}: {name}")
        expected = Image.open(BytesIO(path.read_bytes()))
        actual = Image.open(BytesIO(screenshot))
        if actual.size != expected.size:
            pytest.fail(
                f"Visual diff [{name}]: size changed {expected.size} → {actual.size}"
            )
        if actual.tobytes() != expected.tobytes():
            pytest.fail(f"Visual diff [{name}]: pixel data differs")

    return _assert


@pytest.fixture
def page(page: Page) -> Page:
    page.set_default_timeout(10000)
    return page


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL
