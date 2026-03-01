"""
Unit tests for cli/output.py
"""

from typing import Any

from cli.models import Query
from cli.output import (
    check_duplicate_queries,
    validate_crawlers,
    validate_credentials,
)
from cli.parser import build_all_queries
from core.models import CrawlerInfo, CrawlerMeta


def _make_crawler(name: str, **meta_kwargs: Any) -> CrawlerInfo:
    """Helper to create a CrawlerInfo with a stub query function."""

    async def _stub_query(*args: Any, **kwargs: Any) -> dict:
        return {}

    return CrawlerInfo(
        name=name,
        meta=CrawlerMeta(
            title=meta_kwargs.get("title", name),
            **{k: v for k, v in meta_kwargs.items() if k != "title"},
        ),
        query=_stub_query,
    )


class TestBuildAllQueries:
    """Tests for build_all_queries function."""

    def test_build_all_queries(self):
        """Test building queries for all crawlers."""
        crawlers = {
            "codeforces": _make_crawler("codeforces", title="CodeForces"),
            "poj": _make_crawler("poj", title="POJ"),
            "hdu": _make_crawler("hdu", title="HDU"),
        }
        result = build_all_queries("tourist", crawlers)
        assert len(result) == 3
        assert all(q.username == "tourist" for q in result)
        assert set(q.crawler for q in result) == {"codeforces", "poj", "hdu"}

    def test_build_all_queries_empty(self):
        """Test with empty crawlers dict."""
        result = build_all_queries("user", {})
        assert result == []

    def test_build_all_queries_order(self):
        """Test that order is preserved from dict keys."""
        crawlers = {
            "a": _make_crawler("a"),
            "b": _make_crawler("b"),
            "c": _make_crawler("c"),
        }
        result = build_all_queries("user", crawlers)
        assert [q.crawler for q in result] == ["a", "b", "c"]


class TestCheckDuplicateQueries:
    """Tests for check_duplicate_queries function."""

    def test_no_duplicates(self, capsys):
        """Test that no warning is printed for unique queries."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="poj", username="user2"),
        ]
        check_duplicate_queries(queries)
        captured = capsys.readouterr()
        assert captured.err == ""

    def test_single_duplicate(self, capsys):
        """Test warning for a single duplicate query."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="codeforces", username="user1"),
        ]
        check_duplicate_queries(queries)
        captured = capsys.readouterr()
        assert "Warning: duplicate query 'user1@codeforces'" in captured.err
        assert "will run 2 times" in captured.err

    def test_multiple_duplicates(self, capsys):
        """Test warnings for multiple duplicate queries."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="codeforces", username="user1"),
            Query(crawler="poj", username="user2"),
            Query(crawler="poj", username="user2"),
        ]
        check_duplicate_queries(queries)
        captured = capsys.readouterr()
        assert "user1@codeforces" in captured.err
        assert "user2@poj" in captured.err

    def test_triple_duplicate(self, capsys):
        """Test count is correct for triple duplicates."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="codeforces", username="user1"),
            Query(crawler="codeforces", username="user1"),
        ]
        check_duplicate_queries(queries)
        captured = capsys.readouterr()
        assert "will run 3 times" in captured.err

    def test_empty_list(self, capsys):
        """Test with empty query list."""
        check_duplicate_queries([])
        captured = capsys.readouterr()
        assert captured.err == ""


class TestValidateCrawlers:
    """Tests for validate_crawlers function."""

    def test_all_valid(self):
        """Test with all valid crawlers."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="poj", username="user2"),
        ]
        crawlers = {
            "codeforces": _make_crawler("codeforces"),
            "poj": _make_crawler("poj"),
        }
        assert validate_crawlers(queries, crawlers) is True

    def test_unknown_crawler(self, capsys):
        """Test with unknown crawler."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="unknown", username="user2"),
        ]
        crawlers = {
            "codeforces": _make_crawler("codeforces"),
        }
        assert validate_crawlers(queries, crawlers) is False
        captured = capsys.readouterr()
        assert "unknown crawler(s): unknown" in captured.err

    def test_multiple_unknown_crawlers(self, capsys):
        """Test with multiple unknown crawlers (sorted in output)."""
        queries = [
            Query(crawler="zebra", username="user1"),
            Query(crawler="alpha", username="user2"),
        ]
        crawlers = {
            "codeforces": _make_crawler("codeforces"),
        }
        assert validate_crawlers(queries, crawlers) is False
        captured = capsys.readouterr()
        assert "unknown crawler(s): alpha, zebra" in captured.err

    def test_empty_queries(self):
        """Test with empty query list."""
        crawlers = {
            "codeforces": _make_crawler("codeforces"),
        }
        assert validate_crawlers([], crawlers) is True

    def test_empty_crawlers(self):
        """Test with empty crawlers dict and no queries."""
        assert validate_crawlers([], {}) is True


class TestValidateCredentials:
    """Tests for validate_credentials function."""

    def test_no_auth_required(self):
        """Test crawler that doesn't require authentication."""
        queries = [Query(crawler="codeforces", username="user1")]
        crawlers = {
            "codeforces": _make_crawler("codeforces"),
        }
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_login_with_embedded_password(self):
        """Test requires_login crawler with embedded password."""
        queries = [Query(crawler="vjudge", username="user1", password="pass")]
        crawlers = {
            "vjudge": _make_crawler("vjudge", requires_login=True),
        }
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_login_with_flag_credentials(self):
        """Test requires_login crawler with -l flag credentials."""
        queries = [Query(crawler="vjudge", username="user1")]
        crawlers = {
            "vjudge": _make_crawler("vjudge", requires_login=True),
        }
        crawler_logins = {"vjudge": ("loginuser", "pass")}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_login_missing_credentials(self, capsys):
        """Test requires_login crawler without any credentials."""
        queries = [Query(crawler="vjudge", username="user1")]
        crawlers = {
            "vjudge": _make_crawler("vjudge", requires_login=True),
        }
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "requires login credentials" in captured.err

    def test_requires_login_duplicate_credentials(self, capsys):
        """Test requires_login crawler with both embedded and flag credentials."""
        queries = [Query(crawler="vjudge", username="user1", password="pass")]
        crawlers = {
            "vjudge": _make_crawler("vjudge", requires_login=True),
        }
        crawler_logins = {"vjudge": ("loginuser", "pass2")}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "duplicate credentials" in captured.err

    def test_requires_password_provided(self):
        """Test requires_password crawler with password provided."""
        queries = [Query(crawler="someoj", username="user1", password="pass")]
        crawlers = {
            "someoj": _make_crawler("someoj", requires_password=True),
        }
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True

    def test_requires_password_missing(self, capsys):
        """Test requires_password crawler without password."""
        queries = [Query(crawler="someoj", username="user1")]
        crawlers = {
            "someoj": _make_crawler("someoj", requires_password=True),
        }
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "requires a password" in captured.err

    def test_unwanted_password_in_query(self, capsys):
        """Test crawler that doesn't require auth but password provided."""
        queries = [Query(crawler="codeforces", username="user1", password="pass")]
        crawlers = {
            "codeforces": _make_crawler("codeforces"),
        }
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is False
        captured = capsys.readouterr()
        assert "does not require credentials" in captured.err

    def test_empty_queries(self):
        """Test with empty query list."""
        crawlers = {
            "codeforces": _make_crawler("codeforces"),
        }
        crawler_logins = {}
        assert validate_credentials([], crawlers, crawler_logins) is True

    def test_multiple_queries_mixed(self):
        """Test multiple queries with different auth requirements."""
        queries = [
            Query(crawler="codeforces", username="user1"),
            Query(crawler="vjudge", username="user2", password="pass"),
        ]
        crawlers = {
            "codeforces": _make_crawler("codeforces"),
            "vjudge": _make_crawler("vjudge", requires_login=True),
        }
        crawler_logins = {}
        assert validate_credentials(queries, crawlers, crawler_logins) is True
