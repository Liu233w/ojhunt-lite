import pytest
from playwright.sync_api import BrowserContext

BASE_URL = "http://localhost:8080"


@pytest.mark.playwright
def test_api_query_returns_json(context: BrowserContext):
    response = context.request.get(f"{BASE_URL}/api/crawlers/codeforces/tourist")
    assert response.status == 200
    data = response.json()
    assert data["error"] is False
    assert data["crawler"] == "codeforces"
    assert data["username"] == "tourist"
    assert "data" in data
    assert "solved" in data["data"]
    assert "submissions" in data["data"]


@pytest.mark.playwright
def test_api_query_user_not_found(context: BrowserContext):
    response = context.request.get(
        f"{BASE_URL}/api/crawlers/codeforces/nonexistentuser12345xyz"
    )
    assert response.status == 400
    data = response.json()
    assert data["error"] is True
    assert data["crawler"] == "codeforces"
    assert data["username"] == "nonexistentuser12345xyz"
    assert "message" in data


@pytest.mark.playwright
def test_api_query_unknown_crawler(context: BrowserContext):
    response = context.request.get(f"{BASE_URL}/api/crawlers/unknown_crawler/tourist")
    assert response.status == 400
    data = response.json()
    assert data["error"] is True
    assert data["crawler"] == "unknown_crawler"
    assert "Unknown crawler" in data["message"]


@pytest.mark.playwright
def test_api_crawlers_list(context: BrowserContext):
    response = context.request.get(f"{BASE_URL}/api/crawlers/")
    assert response.status == 200
    data = response.json()
    assert data["error"] is False
    assert "data" in data
    assert "codeforces" in data["data"]
