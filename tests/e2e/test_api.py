import json

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
    response = context.request.get(f"{BASE_URL}/api/crawlers")
    assert response.status == 200
    data = response.json()
    assert data["error"] is False
    assert "data" in data
    assert "codeforces" in data["data"]


@pytest.mark.playwright
def test_api_merge_empty(context: BrowserContext):
    response = context.request.post(
        f"{BASE_URL}/api/merge",
        data=json.dumps([]),
        headers={"Content-Type": "application/json"},
    )
    assert response.status == 200
    data = response.json()
    assert data["uniqueSolved"] == 0
    assert data["totalSubmissions"] == 0


@pytest.mark.playwright
def test_api_merge_basic(context: BrowserContext):
    # Two normal crawlers with no overlapping problems
    body = [
        {
            "crawler": "codeforces",
            "username": "u1",
            "error": False,
            "data": {
                "solved": 2,
                "submissions": 5,
                "solvedList": ["1A", "2A"],
                "duration": 1.0,
            },
        },
        {
            "crawler": "atcoder",
            "username": "u1",
            "error": False,
            "data": {
                "solved": 2,
                "submissions": 3,
                "solvedList": ["abc001_a", "abc001_b"],
                "duration": 1.0,
            },
        },
    ]
    response = context.request.post(
        f"{BASE_URL}/api/merge",
        data=json.dumps(body),
        headers={"Content-Type": "application/json"},
    )
    assert response.status == 200
    data = response.json()
    assert data["uniqueSolved"] == 4
    assert data["totalSubmissions"] == 8


@pytest.mark.playwright
def test_api_merge_dedup(context: BrowserContext):
    # codeforces solved ["1A"] + vjudge solved ["codeforces-1A", "hdu-1000"]
    # "codeforces-1A" from vjudge matches "codeforces-1A" from normal codeforces prefix
    # so uniqueSolved should be 2 (codeforces-1A + hdu-1000), not 3

    body = [
        {
            "crawler": "codeforces",
            "username": "u1",
            "error": False,
            "data": {
                "solved": 1,
                "submissions": 2,
                "solvedList": ["1A"],
                "duration": 1.0,
            },
        },
        {
            "crawler": "vjudge",
            "username": "u1",
            "error": False,
            "data": {
                "solved": 2,
                "submissions": 3,
                "solvedList": ["codeforces-1A", "hdu-1000"],
                "duration": 1.0,
            },
        },
    ]
    response = context.request.post(
        f"{BASE_URL}/api/merge",
        data=json.dumps(body),
        headers={"Content-Type": "application/json"},
    )
    assert response.status == 200
    data = response.json()
    assert data["uniqueSolved"] == 2
    assert data["totalSubmissions"] == 5


@pytest.mark.playwright
def test_api_merge_skips_errors(context: BrowserContext):
    body = [
        {
            "crawler": "codeforces",
            "username": "u1",
            "error": False,
            "data": {
                "solved": 3,
                "submissions": 5,
                "solvedList": ["1A", "2A", "3A"],
                "duration": 1.0,
            },
        },
        {
            "crawler": "atcoder",
            "username": "u1",
            "error": True,
            "message": "User not found",
        },
    ]
    response = context.request.post(
        f"{BASE_URL}/api/merge",
        data=json.dumps(body),
        headers={"Content-Type": "application/json"},
    )
    assert response.status == 200
    data = response.json()
    assert data["uniqueSolved"] == 3
    assert data["totalSubmissions"] == 5
