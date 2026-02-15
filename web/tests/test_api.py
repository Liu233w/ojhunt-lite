import pytest
from playwright.sync_api import APIRequestContext

BASE_URL = "http://localhost:8080"


@pytest.mark.playwright
def test_api_query_returns_json(api_request_context: APIRequestContext):
    response = api_request_context.get("/api/query/codeforces/tourist")
    assert response.status == 200
    data = response.json()
    assert "error" in data
    assert data["error"] is False
    assert "data" in data
    assert "solved" in data["data"]
    assert "submissions" in data["data"]


@pytest.mark.playwright
def test_api_query_user_not_found(api_request_context: APIRequestContext):
    response = api_request_context.get("/api/query/codeforces/nonexistentuser12345xyz")
    assert response.status == 400
    data = response.json()
    assert data["error"] is True
    assert "message" in data


@pytest.mark.playwright
def test_api_query_unknown_crawler(api_request_context: APIRequestContext):
    response = api_request_context.get("/api/query/unknown_crawler/tourist")
    assert response.status == 400
    data = response.json()
    assert data["error"] is True
    assert "Unknown crawler" in data["message"]


@pytest.mark.playwright
def test_api_query_with_htmx_returns_html(api_request_context: APIRequestContext):
    response = api_request_context.get(
        "/api/query/codeforces/tourist", headers={"HX-Request": "true"}
    )
    assert response.status == 200
    html = response.text()
    assert "<tr" in html
    assert "data-crawler" in html


@pytest.mark.playwright
def test_api_row_endpoint(api_request_context: APIRequestContext):
    response = api_request_context.get("/api/row?q=tourist@codeforces")
    assert response.status == 200
    html = response.text()
    assert "<tr" in html
    assert 'data-crawler="codeforces"' in html
    assert 'data-username="tourist"' in html


@pytest.mark.playwright
def test_api_row_all_crawlers(api_request_context: APIRequestContext):
    response = api_request_context.get("/api/row?q=tourist@*")
    assert response.status == 200
    html = response.text()
    assert 'data-username="tourist"' in html


@pytest.mark.playwright
def test_api_crawlers_list(api_request_context: APIRequestContext):
    response = api_request_context.get("/api/crawlers/")
    assert response.status == 200
    data = response.json()
    assert data["error"] is False
    assert "data" in data
    assert "codeforces" in data["data"]
