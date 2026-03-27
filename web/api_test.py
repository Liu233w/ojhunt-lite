"""
Unit tests for CrawlerResult DTO (from_model / to_model conversions).
These tests do not require a running web server.
"""

from core.models import CrawlerInfo, NullCrawler
from core.models import QueryResult as CoreQueryResult
from crawlers import discover_crawlers
from web.api import CrawlerResult, QueryResult


def make_crawler(name: str = "codeforces") -> CrawlerInfo:
    crawlers = discover_crawlers()
    return crawlers[name]


# --- from_model ---


def test_from_model_success():
    crawler = make_crawler("codeforces")
    core = CoreQueryResult(
        crawler=crawler,
        username="tourist",
        success=True,
        solved=100,
        submissions=200,
        solved_list=["1A", "2A"],
        duration=1.5,
    )
    dto = CrawlerResult.from_model(core)

    assert dto.crawler == "codeforces"
    assert dto.username == "tourist"
    assert dto.error is False
    assert dto.message is None
    assert dto.data is not None
    assert dto.data.solved == 100
    assert dto.data.submissions == 200
    assert dto.data.solvedList == ["1A", "2A"]
    assert dto.data.duration == 1.5


def test_from_model_failure():
    crawler = make_crawler("codeforces")
    core = CoreQueryResult(
        crawler=crawler,
        username="nobody",
        success=False,
        error="User not found",
    )
    dto = CrawlerResult.from_model(core)

    assert dto.crawler == "codeforces"
    assert dto.username == "nobody"
    assert dto.error is True
    assert dto.message == "User not found"
    assert dto.data is None


def test_from_model_no_solved_list():
    crawler = make_crawler("codeforces")
    core = CoreQueryResult(
        crawler=crawler,
        username="tourist",
        success=True,
        solved=50,
        submissions=80,
        solved_list=None,
        duration=0.9,
    )
    dto = CrawlerResult.from_model(core)

    assert dto.error is False
    assert dto.data.solvedList is None
    assert dto.data.solved == 50


# --- to_model ---


def test_to_model_success():
    dto = CrawlerResult(
        crawler="codeforces",
        username="tourist",
        error=False,
        data=QueryResult(
            solved=100, submissions=200, solvedList=["1A", "2A"], duration=1.5
        ),
    )
    core = dto.to_model()

    assert core.success is True
    assert core.username == "tourist"
    assert core.crawler.name == "codeforces"
    assert core.solved == 100
    assert core.submissions == 200
    assert core.solved_list == ["1A", "2A"]
    assert core.duration == 1.5
    assert core.error is None


def test_to_model_error():
    dto = CrawlerResult(
        crawler="codeforces",
        username="nobody",
        error=True,
        message="User not found",
    )
    core = dto.to_model()

    assert core.success is False
    assert core.username == "nobody"
    assert core.error == "User not found"


def test_to_model_unknown_crawler():
    dto = CrawlerResult(
        crawler="nonexistent_crawler",
        username="tourist",
        error=False,
        data=QueryResult(solved=5, submissions=10, solvedList=["1A"], duration=0.5),
    )
    core = dto.to_model()

    # Unknown crawler falls back to NullCrawler; result is still considered
    # successful so its problems are included in merge (prefixed with crawler name)
    assert core.success is True
    assert isinstance(core.crawler, NullCrawler)
    assert core.solved_list == ["1A"]


# --- round-trip ---


def test_round_trip_success():
    crawler = make_crawler("atcoder")
    original = CoreQueryResult(
        crawler=crawler,
        username="tourist",
        success=True,
        solved=300,
        submissions=400,
        solved_list=["abc001_a", "abc001_b"],
        duration=2.0,
    )
    restored = CrawlerResult.from_model(original).to_model()

    assert restored.success == original.success
    assert restored.username == original.username
    assert restored.crawler.name == original.crawler.name
    assert restored.solved == original.solved
    assert restored.submissions == original.submissions
    assert restored.solved_list == original.solved_list


def test_round_trip_failure():
    crawler = make_crawler("codeforces")
    original = CoreQueryResult(
        crawler=crawler,
        username="nobody",
        success=False,
        error="Rate limited",
    )
    restored = CrawlerResult.from_model(original).to_model()

    assert restored.success is False
    assert restored.username == original.username
    assert restored.error == original.error
