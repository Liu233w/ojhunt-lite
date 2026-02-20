import pytest
from playwright.sync_api import BrowserContext

BASE_URL = "http://localhost:8080"


@pytest.mark.playwright
def test_api_query_returns_json(context: BrowserContext):
    response = context.request.get(f"{BASE_URL}/api/query/codeforces/tourist")
    assert response.status == 200
    data = response.json()
    assert "error" in data
    assert data["error"] is False
    assert "data" in data
    assert "solved" in data["data"]
    assert "submissions" in data["data"]


@pytest.mark.playwright
def test_api_query_user_not_found(context: BrowserContext):
    response = context.request.get(
        f"{BASE_URL}/api/query/codeforces/nonexistentuser12345xyz"
    )
    assert response.status == 400
    data = response.json()
    assert data["error"] is True
    assert "message" in data


@pytest.mark.playwright
def test_api_query_unknown_crawler(context: BrowserContext):
    response = context.request.get(f"{BASE_URL}/api/query/unknown_crawler/tourist")
    assert response.status == 400
    data = response.json()
    assert data["error"] is True
    assert "Unknown crawler" in data["message"]


@pytest.mark.playwright
def test_htmx_query_returns_html(context: BrowserContext):
    response = context.request.get(f"{BASE_URL}/htmx/query/codeforces/tourist")
    assert response.status == 200
    html = response.text()
    assert "<tr" in html
    assert "data-crawler" in html


@pytest.mark.playwright
def test_htmx_row_endpoint(context: BrowserContext):
    response = context.request.get(f"{BASE_URL}/htmx/row?q=tourist@codeforces")
    assert response.status == 200
    html = response.text()
    assert "<tr" in html
    assert 'data-crawler="codeforces"' in html
    assert 'data-username="tourist"' in html


@pytest.mark.playwright
def test_htmx_row_all_crawlers(context: BrowserContext):
    response = context.request.get(f"{BASE_URL}/htmx/row?q=tourist@*")
    assert response.status == 200
    html = response.text()
    assert 'data-username="tourist"' in html


@pytest.mark.playwright
def test_htmx_canceled_endpoint(context: BrowserContext):
    response = context.request.get(f"{BASE_URL}/htmx/canceled/codeforces/tourist")
    assert response.status == 200
    html = response.text()
    assert "<tr" in html
    assert "Canceled" in html


@pytest.mark.playwright
def test_api_crawlers_list(context: BrowserContext):
    response = context.request.get(f"{BASE_URL}/api/crawlers/")
    assert response.status == 200
    data = response.json()
    assert data["error"] is False
    assert "data" in data
    assert "codeforces" in data["data"]
