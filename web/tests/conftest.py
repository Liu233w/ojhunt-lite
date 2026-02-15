import pytest
from playwright.sync_api import Page

BASE_URL = "http://localhost:8080"


@pytest.fixture
def page(page: Page) -> Page:
    page.set_default_timeout(10000)
    return page


@pytest.fixture(scope="session")
def base_url():
    return BASE_URL
