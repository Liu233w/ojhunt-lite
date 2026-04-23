import pytest
from playwright.sync_api import Page

from e2e.helpers import BASE_URL


@pytest.fixture
def page(page: Page) -> Page:
    page.set_default_timeout(10000)
    return page


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL
